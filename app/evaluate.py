"""Evaluate the analysis service's model on data it has never seen.

The model is trained on the older part of the price history and scored on the
newer part, with a one-hour gap between them. A training row's label looks one
hour ahead, so without the gap the last training labels would be computed from
test-period prices.

Two questions are answered for each symbol:

1. Classification: when the model predicts a >1% rise within the hour, how
   often is it right (precision), and how many of the real rises does it catch
   (recall)? Precision only means something next to the base rate - how often
   a rise happens anyway.
2. Trading: if you bought on every signal and sold an hour later, paying
   exchange fees, would you beat simply trading every hour or holding?

Usage (inside the stack, after backfilling some history):
    docker compose run --rm analysis python evaluate.py
"""
import argparse
import asyncio

import numpy as np
import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

from analysis import (
    FEATURES, HORIZON_MINUTES, SYMBOLS, add_target, build_model, calculate_indicators, get_db_pool,
)

HORIZON_GAP = HORIZON_MINUTES  # rows dropped between train and test
TEST_FRACTION = 0.3
MIN_TRAIN_ROWS = 100
DECISION_THRESHOLD = 0.5       # the service's own cut-off (model.predict)
FEE = 0.001                    # 0.1% per side, Binance's standard spot fee


def chronological_split(df, test_fraction=TEST_FRACTION, gap=HORIZON_GAP):
    """Split into (train, test) by time, leaving `gap` rows between them."""
    n_test = round(len(df) * test_fraction)
    train_end = len(df) - n_test - gap
    if n_test == 0 or train_end < MIN_TRAIN_ROWS:
        raise ValueError(f"Need more data to split: {len(df)} rows gives {max(train_end, 0)} training rows")
    return df.iloc[:train_end], df.iloc[len(df) - n_test:]


def classification_metrics(y_true, y_pred, y_prob):
    """Precision, recall and F1 for the 'rise' class, with the base rate to compare against."""
    has_both_classes = len(np.unique(y_true)) == 2
    return {
        'rows': len(y_true),
        'base_rate': float(np.mean(y_true)),
        'predicted_positives': int(np.sum(y_pred)),
        'precision': float(precision_score(y_true, y_pred, zero_division=0)),
        'recall': float(recall_score(y_true, y_pred, zero_division=0)),
        'f1': float(f1_score(y_true, y_pred, zero_division=0)),
        'roc_auc': float(roc_auc_score(y_true, y_prob)) if has_both_classes else None,
    }


def signal_backtest(prices, signals, horizon=HORIZON_MINUTES, fee=FEE):
    """Buy on each signal, sell `horizon` rows later; one position at a time."""
    returns = []
    i = 0
    while i + horizon < len(prices):
        if signals[i]:
            returns.append(prices[i + horizon] / prices[i] * (1 - fee) ** 2 - 1)
            i += horizon
        else:
            i += 1
    if not returns:
        return {'trades': 0, 'win_rate': None, 'mean_return': None, 'total_return': None}
    returns = np.array(returns)
    return {
        'trades': len(returns),
        'win_rate': float(np.mean(returns > 0)),
        'mean_return': float(np.mean(returns)),
        'total_return': float(np.prod(1 + returns) - 1),
    }


def rise_probabilities(model, X):
    """P(rise) for each row; all zeros if training never saw a rise."""
    if 1 not in model.classes_:
        return np.zeros(len(X))
    return model.predict_proba(X)[:, list(model.classes_).index(1)]


def evaluate_symbol(df, test_fraction=TEST_FRACTION):
    """Train on the older data, score on the newer data. df needs time, price, volume."""
    labelled = add_target(calculate_indicators(df.copy())).dropna().reset_index(drop=True)
    train, test = chronological_split(labelled, test_fraction)

    model = build_model()
    model.fit(train[FEATURES], train['target'].astype(int))

    y_true = test['target'].astype(int).to_numpy()
    y_prob = rise_probabilities(model, test[FEATURES])
    y_pred = y_prob >= DECISION_THRESHOLD
    prices = test['price'].to_numpy()

    return {
        'labelled_rows': len(labelled),
        'train_rows': len(train),
        'test_rows': len(test),
        'train_base_rate': float(train['target'].mean()),
        'test_period': (test['time'].iloc[0], test['time'].iloc[-1]),
        'model': classification_metrics(y_true, y_pred, y_prob),
        'backtest': signal_backtest(prices, y_pred),
        'every_hour_baseline': signal_backtest(prices, np.ones(len(prices), dtype=bool)),
        'buy_and_hold': float(prices[-1] / prices[0] * (1 - FEE) ** 2 - 1),
    }


def _pct(value):
    return "n/a" if value is None else f"{value:+.2%}"


def _rate(value):
    return "n/a" if value is None else f"{value:.1%}"


def format_report(symbol, r):
    m, bt, base = r['model'], r['backtest'], r['every_hour_baseline']
    start, end = (t.strftime('%Y-%m-%d %H:%M') for t in r['test_period'])
    auc = "n/a" if m['roc_auc'] is None else f"{m['roc_auc']:.3f}"
    return "\n".join([
        f"### {symbol}",
        f"Trained on {r['train_rows']:,} minutes, tested on {r['test_rows']:,} unseen minutes ({start} to {end} UTC).",
        "",
        "| Classification (test set) | Value |",
        "|---|---|",
        f"| Base rate: minutes followed by a >1% rise | {_rate(m['base_rate'])} (training: {_rate(r['train_base_rate'])}) |",
        f"| Rise predictions made | {m['predicted_positives']:,} |",
        f"| Precision | {_rate(m['precision'])} |",
        f"| Recall | {_rate(m['recall'])} |",
        f"| F1 | {m['f1']:.3f} |",
        f"| ROC AUC (0.5 = chance) | {auc} |",
        "",
        "| Back-test (test set, 0.1% fee per side) | Trades | Win rate | Mean per trade | Total |",
        "|---|---|---|---|---|",
        f"| Model signals | {bt['trades']} | {_rate(bt['win_rate'])} | {_pct(bt['mean_return'])} | {_pct(bt['total_return'])} |",
        f"| Trade every hour (baseline) | {base['trades']} | {_rate(base['win_rate'])} | {_pct(base['mean_return'])} | {_pct(base['total_return'])} |",
        f"| Buy and hold | 1 | | | {_pct(r['buy_and_hold'])} |",
        "",
    ])


async def load_history(pool, symbol):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            'SELECT time, price, volume FROM market_data WHERE symbol = $1 ORDER BY time ASC', symbol
        )
    return pd.DataFrame([dict(r) for r in rows], columns=['time', 'price', 'volume'])


async def main(symbols, test_fraction):
    pool = await get_db_pool()
    try:
        for symbol in symbols:
            df = await load_history(pool, symbol)
            try:
                print(format_report(symbol, evaluate_symbol(df, test_fraction)))
            except ValueError as error:
                print(f"### {symbol}\nSkipped: {error}. Run backfill.py to load more history.\n")
    finally:
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the signal model on held-out data.")
    parser.add_argument("--symbol", action="append", dest="symbols", help="Symbol to evaluate (repeatable)")
    parser.add_argument("--test-fraction", type=float, default=TEST_FRACTION)
    args = parser.parse_args()
    asyncio.run(main(args.symbols or SYMBOLS, args.test_fraction))
