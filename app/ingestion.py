import asyncio
import os
import ccxt.async_support as ccxt
import asyncpg
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "crypto")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

# symbols to track
SYMBOLS = ['BTC/USDT', 'ETH/USDT']

# Sentiment Analyzer
analyzer = SentimentIntensityAnalyzer()

async def get_db_pool():
    return await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )

async def fetch_ohlcv(exchange, symbol):
    try:
        # Fetch the latest 1m candle: [timestamp, open, high, low, close, volume].
        # The schema stores a single price per minute, so the close is used.
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='1m', limit=1)
        if ohlcv:
            latest = ohlcv[-1]
            timestamp = datetime.fromtimestamp(latest[0] / 1000.0)
            price = latest[4]
            volume = latest[5]
            return (timestamp, symbol, price, volume)
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
        return None

def analyze_sentiment(text, source="unknown"):
    """
    Lightweight, rule-based sentiment analyzer.
    Returns: (timestamp, symbol_related_if_any, score, source)
    """
    score = analyzer.polarity_scores(text)
    # Compound score is the normalized metric [-1, 1]
    return score['compound']

async def batch_insert_market_data(pool, data_batch):
    """
    Batch insert market data into TimescaleDB to minimize disk I/O.
    data_batch: list of tuples (time, symbol, price, volume)
    """
    if not data_batch:
        return

    async with pool.acquire() as conn:
        try:
            await conn.copy_records_to_table(
                'market_data',
                records=data_batch,
                columns=['time', 'symbol', 'price', 'volume']
            )
            print(f"Inserted {len(data_batch)} market data records.")
        except Exception as e:
            print(f"Error batch inserting market data: {e}")

async def batch_insert_sentiment_data(pool, data_batch):
    """
    Batch insert sentiment data into TimescaleDB.
    data_batch: list of tuples (time, symbol, score, source)
    """
    if not data_batch:
        return

    async with pool.acquire() as conn:
        try:
            await conn.copy_records_to_table(
                'sentiment_data',
                records=data_batch,
                columns=['time', 'symbol', 'score', 'source']
            )
            print(f"Inserted {len(data_batch)} sentiment data records.")
        except Exception as e:
            print(f"Error batch inserting sentiment data: {e}")

async def main_loop():
    print("Starting Ingestion Engine...")
    
    # Public market data only - no exchange API keys are needed
    exchange = ccxt.binance()
    
    # Connect to DB
    try:
        pool = await get_db_pool()
        print("Connected to TimescaleDB.")
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    while True:
        start_time = asyncio.get_event_loop().time()
        
        market_data_batch = []
        
        # 1. Fetch Market Data
        for symbol in SYMBOLS:
            data = await fetch_ohlcv(exchange, symbol)
            if data:
                market_data_batch.append(data)
        
        # 2. Insert Market Data
        if market_data_batch:
            await batch_insert_market_data(pool, market_data_batch)

        # 3. Sentiment: analyze_sentiment() and batch_insert_sentiment_data() are
        #    ready, but no live social feed is wired in yet (see README roadmap).

        # Sleep for the remainder of the minute
        elapsed = asyncio.get_event_loop().time() - start_time
        sleep_time = max(0, 60 - elapsed)
        print(f"Loop completed. Sleeping for {sleep_time:.2f}s...")
        await asyncio.sleep(sleep_time)

    await exchange.close()
    await pool.close()

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Stopping Ingestion Engine.")
