#main.py
import psutil
import sqlite3
import schedule
import time
from api_client import fetch_coin_data
from data_storage import insert_market_data, get_market_data, create_tables
from data_processing import simple_moving_average, exponential_moving_average, moving_average_convergence_divergence, relative_strength_index, bollinger_bands, rate_of_change
from grafana_publisher import publish_market_data, publish_sma, publish_ema, publish_macd, publish_rsi, publish_bollinger_bands, publish_roc, publish_reddit_data
from alerts import check_and_notify_price_change
from backup import backup_data
from reddit import analyze_posts

# Configuration
coin_ids = ["bitcoin", "ethereum"]
fetch_interval_minutes = 1
reddit_interval_minutes = 1
sma_interval = 5
ema_interval = 12
rsi_interval = 14
bollinger_bands_interval = 20
roc_interval = 14
price_change_threshold = 5
backup_interval_hours = 24

def analyze_and_publish_reddit_data():
    data = analyze_posts(limit=50)
    for coin_id, coin_data in data.items():
        average_sentiment = float(coin_data['average_sentiment'])
        publish_reddit_data(coin_id, coin_data['post_count'], average_sentiment)

def fetch_and_process_data():
    create_tables()

    for coin_id in coin_ids:
        coin_data = fetch_coin_data(coin_id)

        if not coin_data:
            print(f"Failed to fetch data for {coin_id}")
            continue

        timestamp = int(time.time() * 1e9)
        price = coin_data['price']
        high_24h = coin_data['high_24h']
        low_24h = coin_data['low_24h']
        market_cap = coin_data['market_cap']
        total_volume = coin_data['total_volume']

        print(f"Fetch coins successful for {coin_id} - Price: {price}")
        insert_market_data(coin_id, timestamp, price, high_24h, low_24h, market_cap, total_volume)

        def get_row_count(coin_id):
            connection = sqlite3.connect("crypto_data.db")
            cursor = connection.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM market_data WHERE coin_id = '{coin_id}'")
            row_count = cursor.fetchone()[0]
            connection.close()
            return row_count

        row_count = get_row_count(coin_id)
        print(f"Add to .db file successful for {coin_id} - current number of rows: {row_count}")

        market_data = get_market_data(coin_id)

        if len(market_data) >= sma_interval:
            sma_data = simple_moving_average(coin_id, sma_interval)
            publish_sma(coin_id, sma_data)
        else:
            print(f"Not enough data points to calculate SMA for {coin_id}. Expected {sma_interval}, found {len(market_data)}")
        
        if len(market_data) >= ema_interval:
            ema_data = exponential_moving_average(coin_id, ema_interval)
            publish_ema(coin_id, ema_data)
        else:
            print(f"Not enough data points to calculate EMA for {coin_id}. Expected {ema_interval}, found {len(market_data)}")

        short_window_size = 12
        long_window_size = 26
        signal_window_size = 9
        if len(market_data) >= long_window_size:
            macd_data, signal_line_data = moving_average_convergence_divergence(coin_id, short_window_size, long_window_size, signal_window_size)
            publish_macd(coin_id, macd_data, signal_line_data)
        else:
            print(f"Not enough data points to calculate MACD for {coin_id}. Expected at least {long_window_size}, found {len(market_data)}")

        if len(market_data) >= rsi_interval + 1:
            rsi_data = relative_strength_index(coin_id, rsi_interval)
            publish_rsi(coin_id, rsi_data)
        else:
            print(f"Not enough data points to calculate RSI for {coin_id}. Expected {rsi_interval + 1}, found {len(market_data)}")

        if len(market_data) >= bollinger_bands_interval:
            upper_band_data, sma_data, lower_band_data = bollinger_bands(coin_id, bollinger_bands_interval)
            publish_bollinger_bands(coin_id, upper_band_data, sma_data, lower_band_data)
        else:
            print(f"Not enough data points to calculate Bollinger Bands for {coin_id}. Expected {bollinger_bands_interval}, found {len(market_data)}")

        if len(market_data) >= roc_interval + 1:
            roc_data = rate_of_change(coin_id, roc_interval)
            publish_roc(coin_id, roc_data)
        else:
            print(f"Not enough data points to calculate ROC for {coin_id}. Expected {roc_interval + 1}, found {len(market_data)}")

        publish_market_data(coin_id)
        check_and_notify_price_change(coin_id, price_change_threshold, sma_interval, market_data)

def monitor_system():
    cpu_usage = psutil.cpu_percent()
    ram_usage = psutil.virtual_memory().percent

    # Print the usage stats
    print(f"CPU usage: {cpu_usage}%")
    print(f"RAM usage: {ram_usage}%")

def perform_backup():
    backup_data()

# Schedule tasks
schedule.every(fetch_interval_minutes).minutes.do(fetch_and_process_data)
schedule.every(reddit_interval_minutes).minutes.do(analyze_and_publish_reddit_data)
schedule.every(backup_interval_hours).hours.do(perform_backup)
schedule.every(60).seconds.do(monitor_system)

# Main loop
if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)