import backtrader as bt
import pandas as pd
import sqlalchemy
import os
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import datetime
import numpy as np

# Database Configuration
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_NAME = os.getenv("DB_NAME", "crypto")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password")

DB_URL = f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"

# Custom Data Feed to include Sentiment
class SentimentPandasData(bt.feeds.PandasData):
    lines = ('sentiment',)
    params = (
        ('sentiment', -1), # Index of sentiment column in dataframe, -1 = autodetect if named 'sentiment'
    )

class SentimentRSIStrategy(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('buy_threshold', 30),
        ('sell_threshold', 70),
        ('sentiment_threshold', 0.5),
    )

    def __init__(self):
        # Use TA-Lib RSI for robustness against ZeroDivisionError (sustained trends)
        self.rsi = bt.talib.RSI(self.data.close, timeperiod=self.params.rsi_period)
        self.sentiment = self.data.sentiment
        
        self.orders = [] # Keep track of orders

    def next(self):
        if not self.position:
            # Buy Condition: Oversold (RSI < 30) AND Good Sentiment (> 0.5)
            if self.rsi < self.params.buy_threshold and self.sentiment > self.params.sentiment_threshold:
                self.buy()
                self.orders.append({'type': 'buy', 'price': self.data.close[0], 'time': self.data.datetime.datetime(0)})
        else:
            # Sell Condition: Overbought (RSI > 70) 
            # (Just a simple exit strategy for demonstration)
            if self.rsi > self.params.sell_threshold:
                self.sell()
                self.orders.append({'type': 'sell', 'price': self.data.close[0], 'time': self.data.datetime.datetime(0)})

def fetch_data(symbol):
    try:
        engine = sqlalchemy.create_engine(DB_URL)
        # Fetch market data and join with sentiment
        # We need to aggregate sentiment to the same timeframe as market data if they differ.
        # Assuming market_data is 1m and sentiment is sporadic.
        # For simplicity, let's fetch market data and "fill" sentiment or join on time.
        # Since this is a backtest on historic data, let's assume we have aligned data or we forward fill sentiment.
        
        query = sqlalchemy.text("""
            SELECT m.time, m.price AS close, m.volume, m.price AS open, m.price AS high, m.price AS low,
                   COALESCE(s.score, 0) AS sentiment
            FROM market_data m
            LEFT JOIN sentiment_data s ON m.time = s.time AND m.symbol = s.symbol
            WHERE m.symbol = :symbol
            ORDER BY m.time ASC
        """)

        df = pd.read_sql(query, engine, params={"symbol": symbol})
        if df.empty:
            return None
            
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        # Forward fill sentiment to apply last known sentiment to current price candle
        df['sentiment'] = df['sentiment'].replace(0, np.nan).ffill().fillna(0)
        
        return df
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def run_backtest(symbol='BTC/USDT'):
    cerebro = bt.Cerebro()
    
    df = fetch_data(symbol)
    
    if df is None:
        print("No data found.")
        return

    # Add Data Feed
    data = SentimentPandasData(dataname=df)
    cerebro.adddata(data)
    
    # Add Strategy
    cerebro.addstrategy(SentimentRSIStrategy)
    
    # Run
    print(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    strategies = cerebro.run()
    final_value = cerebro.broker.getvalue()
    print(f"Final Portfolio Value: {final_value:.2f}")
    
    # Visualization (Plotly)
    strat = strategies[0]
    generate_plot(df, strat.orders, final_value, symbol)

def generate_plot(df, orders, final_value, symbol):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.03, subplot_titles=(f'{symbol} Price & Signals', 'Equities/Indicators'),
                        row_width=[0.2, 0.7])

    # Candlestick
    fig.add_trace(go.Candlestick(x=df.index,
                                 open=df['open'], high=df['high'],
                                 low=df['low'], close=df['close'], name='Price'), 
                  row=1, col=1)

    # Buy Markers
    buy_times = [o['time'] for o in orders if o['type'] == 'buy']
    buy_prices = [o['price'] for o in orders if o['type'] == 'buy']
    
    fig.add_trace(go.Scatter(x=buy_times, y=buy_prices, mode='markers', 
                             marker=dict(symbol='triangle-up', color='green', size=15),
                             name='Buy'), row=1, col=1)

    # Sell Markers
    sell_times = [o['time'] for o in orders if o['type'] == 'sell']
    sell_prices = [o['price'] for o in orders if o['type'] == 'sell']
    
    fig.add_trace(go.Scatter(x=sell_times, y=sell_prices, mode='markers', 
                             marker=dict(symbol='triangle-down', color='red', size=15),
                             name='Sell'), row=1, col=1)

    # Add annotation for Final PnL
    pnl = final_value - 10000 # Assuming default 10k start
    fig.add_annotation(text=f"Final PnL: ${pnl:.2f}", 
                       xref="paper", yref="paper", x=1, y=1, showarrow=False)

    fig.update_layout(title_text=f"Backtest Results for {symbol}", height=800)
    
    output_file = 'backtest_results.html'
    fig.write_html(output_file)
    print(f"Plot saved to {output_file}")

if __name__ == "__main__":
    run_backtest()
