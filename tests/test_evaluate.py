import os
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

import analysis
import evaluate


def make_prices(n, start=100.0, step=0.0, seed=0):
    """Minute-level price frame with an optional linear trend plus noise."""
    rng = np.random.default_rng(seed)
    prices = start + step * np.arange(n) + rng.normal(0, 0.05, n)
    return pd.DataFrame({
        'time': pd.date_range('2026-01-01', periods=n, freq='1min'),
        'price': prices,
        'volume': rng.random(n),
    })


class TestAddTarget(unittest.TestCase):

    def test_labels_a_rise_above_the_threshold_as_one(self):
        horizon = analysis.HORIZON_MINUTES
        prices = [100.0] * (horizon + 1)
        prices[horizon] = 102.0  # +2% exactly one horizon after row 0
        df = pd.DataFrame({'price': prices})

        result = analysis.add_target(df)

        self.assertEqual(result['target'].iloc[0], 1)

    def test_labels_a_rise_below_the_threshold_as_zero(self):
        horizon = analysis.HORIZON_MINUTES
        prices = [100.0] * (horizon + 1)
        prices[horizon] = 100.5  # +0.5%, under the 1% threshold
        df = pd.DataFrame({'price': prices})

        result = analysis.add_target(df)

        self.assertEqual(result['target'].iloc[0], 0)

    def test_leaves_the_final_horizon_unlabelled(self):
        # The future price is unknown for the last hour, so it must not be
        # labelled "no rise" - that would teach the model a false negative
        df = make_prices(200)

        result = analysis.add_target(df)

        self.assertTrue(result['target'].tail(analysis.HORIZON_MINUTES).isna().all())
        self.assertFalse(result['target'].head(200 - analysis.HORIZON_MINUTES).isna().any())

    def test_does_not_mutate_its_input(self):
        df = make_prices(100)

        analysis.add_target(df)

        self.assertNotIn('target', df.columns)


class TestChronologicalSplit(unittest.TestCase):

    def test_test_set_comes_strictly_after_the_training_set(self):
        df = make_prices(1000)

        train, test = evaluate.chronological_split(df, test_fraction=0.3, gap=60)

        self.assertLess(train['time'].max(), test['time'].min())

    def test_leaves_a_gap_so_training_labels_cannot_see_test_prices(self):
        df = make_prices(1000)

        train, test = evaluate.chronological_split(df, test_fraction=0.3, gap=60)

        gap_rows = test.index.min() - train.index.max() - 1
        self.assertEqual(gap_rows, 60)

    def test_uses_the_requested_test_fraction(self):
        df = make_prices(1000)

        _, test = evaluate.chronological_split(df, test_fraction=0.3, gap=60)

        self.assertEqual(len(test), 300)

    def test_rejects_data_too_small_to_split(self):
        df = make_prices(50)

        with self.assertRaises(ValueError):
            evaluate.chronological_split(df, test_fraction=0.3, gap=60)


class TestClassificationMetrics(unittest.TestCase):

    def test_computes_precision_recall_and_base_rate(self):
        y_true = np.array([1, 1, 0, 0, 0, 0, 0, 0, 0, 1])
        y_pred = np.array([1, 0, 1, 0, 0, 0, 0, 0, 0, 1])
        y_prob = np.array([.9, .4, .8, .1, .2, .1, .3, .2, .1, .7])

        metrics = evaluate.classification_metrics(y_true, y_pred, y_prob)

        self.assertAlmostEqual(metrics['base_rate'], 0.3)
        self.assertAlmostEqual(metrics['precision'], 2 / 3)
        self.assertAlmostEqual(metrics['recall'], 2 / 3)
        self.assertEqual(metrics['predicted_positives'], 3)
        self.assertIsNotNone(metrics['roc_auc'])

    def test_reports_zero_precision_when_the_model_never_predicts_a_rise(self):
        y_true = np.array([1, 0, 0, 0])
        y_pred = np.array([0, 0, 0, 0])
        y_prob = np.array([.4, .1, .2, .3])

        metrics = evaluate.classification_metrics(y_true, y_pred, y_prob)

        self.assertEqual(metrics['precision'], 0.0)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['predicted_positives'], 0)

    def test_roc_auc_is_none_when_the_test_set_has_one_class(self):
        y_true = np.array([0, 0, 0])
        metrics = evaluate.classification_metrics(y_true, np.array([0, 0, 0]), np.array([.1, .2, .3]))

        self.assertIsNone(metrics['roc_auc'])


class TestSignalBacktest(unittest.TestCase):

    def test_signals_in_a_rising_market_make_money_before_fees(self):
        df = make_prices(500, step=0.1)
        signals = np.zeros(500, dtype=bool)
        signals[0] = True

        result = evaluate.signal_backtest(df['price'].to_numpy(), signals, horizon=60, fee=0.0)

        self.assertEqual(result['trades'], 1)
        self.assertGreater(result['mean_return'], 0)

    def test_fees_are_charged_on_entry_and_exit(self):
        prices = np.full(200, 100.0)
        signals = np.zeros(200, dtype=bool)
        signals[0] = True

        result = evaluate.signal_backtest(prices, signals, horizon=60, fee=0.001)

        self.assertAlmostEqual(result['mean_return'], (1 - 0.001) ** 2 - 1)

    def test_ignores_signals_while_a_trade_is_open(self):
        prices = np.full(200, 100.0)
        signals = np.ones(200, dtype=bool)

        result = evaluate.signal_backtest(prices, signals, horizon=60, fee=0.0)

        # Trades at rows 0, 60 and 120; row 180 has no exit price inside the data
        self.assertEqual(result['trades'], 3)

    def test_reports_no_trades_cleanly(self):
        result = evaluate.signal_backtest(np.full(200, 100.0), np.zeros(200, dtype=bool), horizon=60, fee=0.001)

        self.assertEqual(result['trades'], 0)
        self.assertIsNone(result['mean_return'])


class TestEvaluateSymbol(unittest.TestCase):

    def test_returns_metrics_for_the_model_and_its_baselines(self):
        df = make_prices(3000, step=0.01)

        report = evaluate.evaluate_symbol(df)

        self.assertIn('model', report)
        self.assertIn('backtest', report)
        self.assertIn('every_hour_baseline', report)
        self.assertIn('buy_and_hold', report)
        self.assertEqual(report['test_rows'] + report['train_rows'] + evaluate.HORIZON_GAP,
                         report['labelled_rows'])


if __name__ == '__main__':
    unittest.main()
