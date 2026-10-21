"""Seed TimescaleDB with recent 1-minute candles so analysis and the dashboard
have history to work with straight away, instead of waiting hours for the
ingestion loop to accumulate it.

Usage (inside the stack):
    docker compose run --rm ingestion python backfill.py --hours 48
"""
import argparse
import asyncio
from datetime import datetime, timezone

import ccxt.async_support as ccxt

from ingestion import SYMBOLS, get_db_pool

MS_PER_MINUTE = 60_000
EXCHANGE_PAGE_LIMIT = 1000  # Binance returns at most 1000 candles per request


async def fetch_history(exchange, symbol, hours):
    """Page through 1m candles from `hours` ago until now."""
    since = exchange.milliseconds() - hours * 60 * MS_PER_MINUTE
    rows = []
    while True:
        candles = await exchange.fetch_ohlcv(symbol, timeframe="1m", since=since, limit=EXCHANGE_PAGE_LIMIT)
        if not candles:
            break
        rows.extend(
            (datetime.fromtimestamp(ts / 1000, tz=timezone.utc), symbol, close, volume)
            for ts, _open, _high, _low, close, volume in candles
        )
        since = candles[-1][0] + MS_PER_MINUTE
        if len(candles) < EXCHANGE_PAGE_LIMIT:
            break
    return rows


async def backfill(hours):
    exchange = ccxt.binance()
    pool = await get_db_pool()
    try:
        for symbol in SYMBOLS:
            rows = await fetch_history(exchange, symbol, hours)
            async with pool.acquire() as conn:
                # Replace the window rather than append, so re-running is safe
                if rows:
                    await conn.execute(
                        "DELETE FROM market_data WHERE symbol = $1 AND time >= $2", symbol, rows[0][0]
                    )
                await conn.copy_records_to_table(
                    "market_data", records=rows, columns=["time", "symbol", "price", "volume"]
                )
            print(f"{symbol}: inserted {len(rows)} candles")
    finally:
        await exchange.close()
        await pool.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hours", type=int, default=48, help="How much history to load (default 48)")
    asyncio.run(backfill(parser.parse_args().hours))
