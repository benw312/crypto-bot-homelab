# Crypto Bot Homelab

A containerised crypto market-data platform that runs on a home server. It
ingests live BTC and ETH prices every minute into a time-series database,
computes technical indicators, trains a machine-learning signal model per
asset, backtests trading strategies and serves an interactive dashboard with
a paper-trading simulator.

![Dashboard: 48 hours of BTC/USDT price with EMA 20 and SMA 50 overlays](docs/images/dashboard-market.png)

**Stack:** Python 3.12 · asyncio · TimescaleDB (PostgreSQL) · Docker Compose ·
ccxt · TA-Lib · scikit-learn · Backtrader · Streamlit · Plotly · pandas

---

## Highlights

- **Microservice architecture.** Ingestion, analysis and the dashboard run as
  independent containers sharing one TimescaleDB instance, so each can be
  restarted, scaled or replaced without touching the others.
- **Time-series storage.** Market and sentiment data live in TimescaleDB
  hypertables, which partition by time automatically and keep minute-level
  queries fast as history grows.
- **Async ingestion with batched writes.** An `asyncio` loop pulls 1-minute
  candles from the exchange via `ccxt` and bulk-loads them with Postgres
  `COPY`, which keeps disk I/O low on modest homelab hardware.
- **ML signal generation.** The analysis service computes RSI, MACD and
  Bollinger Bands with TA-Lib, then trains a Random Forest per asset to predict
  whether the price will rise more than 1% in the next hour.
- **Backtesting.** A Backtrader strategy combines RSI with a sentiment
  threshold and plots trades on an interactive Plotly chart.
- **Dashboard and paper trading.** A Streamlit UI shows price against moving
  averages and lets you simulate buys and sells against a virtual wallet.
- **Tested.** Unit tests cover ingestion, indicators, model training and
  prediction, the backtest flow and the dashboard's data layer, with network
  and database calls mocked.

## Screenshots

| Market overview | Paper trading |
|---|---|
| ![Market overview](docs/images/dashboard-market.png) | ![Paper trading simulator with an open BTC position](docs/images/dashboard-paper-trading.png) |

## Architecture

```mermaid
flowchart LR
    EX[(Binance<br/>public API)] -->|1m candles via ccxt| ING[Ingestion<br/>service]
    ING -->|batched COPY| DB[(TimescaleDB<br/>hypertables)]
    DB --> ANA[Analysis service<br/>TA-Lib + Random Forest]
    DB --> DASH[Streamlit<br/>dashboard :8501]
    DB --> BT[Backtester<br/>Backtrader + Plotly]
```

| Container | Entry point | Role |
|---|---|---|
| `timescaledb` | — | Stores `market_data` and `sentiment_data` hypertables. The schema is created on first start from `migrations/`. |
| `crypto_ingestion` | `app/ingestion.py` | Fetches the latest 1-minute candle for each symbol every 60 seconds and batch-inserts it. |
| `crypto_analysis` | `app/analysis.py` | Every 15 minutes, computes indicators over the last 500 minutes and trains or loads a model per symbol to score the latest candle. |
| `crypto_dashboard` | `app/dashboard.py` | Streamlit UI on port 8501. |

`app/backtest.py` and `app/backfill.py` are run on demand (see below).

## Getting started

**Prerequisites:** Docker with Docker Compose. No exchange API keys are needed,
because only public market data is used.

```bash
git clone https://github.com/benw312/crypto-bot-homelab.git
cd crypto-bot-homelab
cp .env.example .env            # set DB_PASSWORD (and DB_PORT if 5432 is taken)
docker compose up --build -d
```

Then open <http://localhost:8501>.

The ingestion loop adds one row per minute, so the charts start almost empty.
To load the last 48 hours of history straight away:

```bash
docker compose run --rm ingestion python backfill.py --hours 48
```

To run a backtest, which writes `backtest_results.html`:

```bash
docker compose run --rm analysis python backtest.py
```

## Running the tests

TA-Lib is bundled in the Docker image, so the easiest way to run the tests is
inside the container:

```bash
docker compose run --rm -v "$PWD":/repo -w /repo analysis python -m unittest discover tests
```

To run them locally instead:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r app/requirements.txt
python -m unittest discover tests
```

## Project structure

```
├── app/                    # Current microservices (one shared Docker image)
│   ├── ingestion.py        # Exchange → TimescaleDB loop
│   ├── analysis.py         # Indicators, model training, signals
│   ├── dashboard.py        # Streamlit UI and paper trading
│   ├── backtest.py         # Backtrader strategy and Plotly report
│   ├── backfill.py         # One-off historical data loader
│   ├── Dockerfile
│   └── requirements.txt
├── migrations/             # TimescaleDB schema (hypertables)
├── tests/                  # Unit tests
├── legacy/                 # The original Raspberry Pi version (see below)
├── docker-compose.yml
└── .env.example
```

## How it evolved

The project started as a single scheduled Python script on a **Raspberry Pi**
(`legacy/`). That version:

- polled CoinGecko for prices and stored them in SQLite,
- hand-implemented over a dozen indicators (SMA, EMA, MACD, RSI, Bollinger
  Bands, stochastic oscillator, ATR, OBV, parabolic SAR, Ichimoku and more),
- scored Reddit and Twitter sentiment with TextBlob and VADER,
- published everything to InfluxDB for Grafana dashboards,
- sent email alerts on large price moves and backed up nightly to Amazon S3.

As it grew, the monolith became hard to change, so it was re-platformed into
the services above: TimescaleDB replaced SQLite and InfluxDB, a proper indicator
library replaced the hand-written maths, and Docker Compose made it portable
beyond the Pi. The legacy code is kept for reference and reads its credentials
from environment variables (see `.env.example`).

## Limitations and roadmap

- **Sentiment is not yet wired into the new pipeline.** The scoring function
  and the database table are ready, but there is no live social feed. The
  backtest's sentiment filter therefore never triggers on real data, and the
  strategy makes no trades until a feed is added. Twitter's free streaming API
  has since been withdrawn, so Reddit is the likely source.
- **Signals are logged, not stored.** The next step is to write predictions to
  a `signals` table and plot them on the dashboard.
- **The "Live Mode" toggle is a UI placeholder.** No orders are ever sent to an
  exchange.
- **The model target is deliberately simple** (a >1% rise within an hour). In a
  quiet market a 500-minute window may contain no rises at all, in which case
  the service skips the signal rather than guessing.

## License

[MIT](LICENSE) © 2026 Ben Wallbridge
