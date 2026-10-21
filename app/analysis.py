import asyncio
import os
import joblib
import pandas as pd
import numpy as np
import talib
import asyncpg
from sklearn.ensemble import RandomForestClassifier
from datetime import datetime

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "crypto")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

MODEL_FILE = 'model.joblib'
SYMBOLS = ['BTC/USDT', 'ETH/USDT']

# Model definition, shared with evaluate.py so the evaluation scores exactly
# the model this service runs
FEATURES = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_middle', 'bb_lower', 'volume']
HORIZON_MINUTES = 60    # ingestion writes one row per minute, so 60 rows = 1 hour
RISE_THRESHOLD = 0.01   # target: price more than 1% higher one hour later

async def get_db_pool():
    return await asyncpg.create_pool(
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        host=DB_HOST
    )

async def fetch_data(pool, symbol, limit=500):
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            'SELECT time, price, volume FROM market_data WHERE symbol = $1 ORDER BY time DESC LIMIT $2',
            symbol, limit
        )
        return rows

def calculate_indicators(df):
    """
    Calculate RSI, MACD, Bollinger Bands using TA-Lib.
    Assumes df has 'price' column (which we treat as close).
    """
    # TA-Lib requires double precision numpy arrays
    close_prices = df['price'].values.astype(np.float64)

    # RSI
    df['rsi'] = talib.RSI(close_prices, timeperiod=14)

    # MACD
    macd, macd_signal, macd_hist = talib.MACD(close_prices, fastperiod=12, slowperiod=26, signalperiod=9)
    df['macd'] = macd
    df['macd_signal'] = macd_signal
    df['macd_hist'] = macd_hist

    # Bollinger Bands
    upper, middle, lower = talib.BBANDS(close_prices, timeperiod=20, nbdevup=2, nbdevdn=2, matype=0)
    df['bb_upper'] = upper
    df['bb_middle'] = middle
    df['bb_lower'] = lower
    
    return df

def add_target(df):
    """
    Return a copy of df with a 'target' column: 1 if the price is more than
    RISE_THRESHOLD higher HORIZON_MINUTES rows later, else 0.

    The final HORIZON_MINUTES rows have no future price yet, so their target is
    NaN rather than 0 - labelling them "no rise" would invent false negatives.
    """
    future_price = df['price'].shift(-HORIZON_MINUTES)
    target = (future_price > df['price'] * (1 + RISE_THRESHOLD)).astype(float)
    return df.assign(target=target.where(future_price.notna()))


def build_model():
    return RandomForestClassifier(n_estimators=100, random_state=42)


def train_or_load_model(df):
    """
    Load the model if it exists, otherwise train a new one.

    Target: will the price rise more than 1% within the next hour?
    Ingestion writes one row per minute, so one hour ahead is shift(-60).
    """
    if os.path.exists(MODEL_FILE):
        print("Loading existing model...")
        return joblib.load(MODEL_FILE)
    
    print("Training new model...")
    # Drop warm-up rows (MACD needs ~33) and the final hour (no future price yet)
    train_df = add_target(df).dropna()
    
    if len(train_df) < 10:
        print("Not enough data to train.")
        return None

    clf = build_model()
    clf.fit(train_df[FEATURES], train_df['target'].astype(int))
    
    joblib.dump(clf, MODEL_FILE)
    print("Model saved.")
    return clf

def predict_signal(model, df):
    if model is None:
        return None
    
    # Predict on the latest row
    latest_row = df.iloc[[-1]] 
    # Ensure no NaNs in latest features (indicators should be calculable if we have 500 rows)
    if latest_row[FEATURES].isnull().values.any():
        print("Latest row has NaN features. Cannot predict.")
        return None
        
    X_new = latest_row[FEATURES]
    if 1 not in model.classes_:
        # Training window never saw a >1% rise, so there is no "rise" class to score
        print("Model was trained on a single class. Cannot score a rise probability.")
        return None

    prediction = model.predict(X_new)[0]
    rise_index = list(model.classes_).index(1)
    prob = model.predict_proba(X_new)[0][rise_index]

    return prediction, prob

async def main_loop():
    print("Starting Analysis Module...")
    
    try:
        pool = await get_db_pool()
        print("Connected to DB.")
    except Exception as e:
        print(f"Failed to connect to DB: {e}")
        return

    while True:
        print(f"Running analysis at {datetime.now()}...")
        
        for symbol in SYMBOLS:
            rows = await fetch_data(pool, symbol, limit=500)
            if not rows or len(rows) < 100:
                print(f"Not enough data for {symbol}. Skipping.")
                continue
                
            # Convert to DataFrame
            # asyncpg rows are record objects, need to convert
            data = [dict(r) for r in rows]
            df = pd.DataFrame(data)
            # Sort by time ascending (DB returned DESC)
            df = df.sort_values('time').reset_index(drop=True)
            
            # Calculate Indicators
            df = calculate_indicators(df)
            
            # One model per symbol: Bollinger Band levels are in price units, so a
            # shared model would mix BTC (~$60k) and ETH (~$3k) scales.
            model_file_symbol = f"model_{symbol.replace('/', '_')}.joblib"
            global MODEL_FILE
            MODEL_FILE = model_file_symbol
            
            model = train_or_load_model(df)
            
            # Predict
            signal = predict_signal(model, df) if model else None
            if signal:
                pred, prob = signal
                print(f"Signal for {symbol}: Prediction={pred} (Prob={prob:.2f})")
                # Here we would insert signal to DB or trigger alert
        
        # Sleep 15 minutes
        print("Analysis complete. Sleeping for 15 minutes...")
        await asyncio.sleep(15 * 60)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("Stopping Analysis Module.")
