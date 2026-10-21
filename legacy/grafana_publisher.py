#grafana_publisher.py
import os
from influxdb import InfluxDBClient
import data_storage
from unittest.mock import MagicMock

# InfluxDB credentials are read from the environment (see .env.example)
INFLUXDB_HOST = os.getenv("INFLUXDB_HOST", "localhost")
INFLUXDB_PORT = int(os.getenv("INFLUXDB_PORT", "8086"))
INFLUXDB_USERNAME = os.environ["INFLUXDB_USERNAME"]
INFLUXDB_PASSWORD = os.environ["INFLUXDB_PASSWORD"]
INFLUXDB_DB = os.getenv("INFLUXDB_DB", "crypto")

client = InfluxDBClient(host=INFLUXDB_HOST, port=INFLUXDB_PORT, username=INFLUXDB_USERNAME, password=INFLUXDB_PASSWORD)
client.switch_database(INFLUXDB_DB)

def publish_market_data(coin_id):
    market_data = data_storage.get_market_data(coin_id)

    if not market_data:
        raise ValueError("No market data available for the specified coin")

    points = []
    for entry in market_data:
        timestamp, price, high_24h, low_24h, market_cap, total_volume = entry[1:]
        point = {
            "measurement": "market_data",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "price": price,
                "high_24h": high_24h,
                "low_24h": low_24h,
                "market_cap": market_cap,
                "total_volume": total_volume,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_sma(coin_id, sma_data):
    if not sma_data:
        raise ValueError("No SMA data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, sma_value in enumerate(sma_data):
        timestamp = market_data[i + len(market_data) - len(sma_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "sma",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "value": sma_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_ema(coin_id, ema_data):
    if not ema_data:
        raise ValueError("No EMA data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, ema_value in enumerate(ema_data):
        timestamp = market_data[i + len(market_data) - len(ema_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "ema",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "value": ema_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_macd(coin_id, macd_data, signal_line_data):
    if not macd_data or not signal_line_data:
        raise ValueError("No MACD or Signal Line data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, (macd_value, signal_line_value) in enumerate(zip(macd_data, signal_line_data)):
        timestamp = market_data[i + len(market_data) - len(macd_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "macd",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "macd": macd_value,
                "signal_line": signal_line_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_rsi(coin_id, rsi_data):
    if not rsi_data:
        raise ValueError("No RSI data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, rsi_value in enumerate(rsi_data):
        timestamp = market_data[i + len(market_data) - len(rsi_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "rsi",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "value": rsi_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_bollinger_bands(coin_id, upper_band_data, sma_data, lower_band_data):
    if not upper_band_data or not sma_data or not lower_band_data:
        raise ValueError("No Bollinger Bands data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, (upper_band_value, sma_value, lower_band_value) in enumerate(zip(upper_band_data, sma_data, lower_band_data)):
        timestamp = market_data[i + len(market_data) - len(upper_band_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "bollinger_bands",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "upper_band": upper_band_value,
                "middle_band": sma_value,
                "lower_band": lower_band_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_roc(coin_id, roc_data):
    if not roc_data:
        raise ValueError("No ROC data available for the specified coin")

    market_data = data_storage.get_market_data(coin_id)

    points = []
    for i, roc_value in enumerate(roc_data):
        timestamp = market_data[i + len(market_data) - len(roc_data)][1]  # Use the correct timestamp
        point = {
            "measurement": "roc",
            "tags": {
                "coin_id": coin_id,
            },
            "time": timestamp,
            "fields": {
                "value": roc_value,
            }
        }
        points.append(point)

    client.write_points(points)

def publish_reddit_data(coin_id, post_count, average_sentiment):
    point = {
        "measurement": "reddit_data",
        "tags": {
            "coin_id": coin_id,
        },
        "fields": {
            "post_count": post_count,
            "average_sentiment": average_sentiment
        }
    }
    client.write_points([point])

if __name__ == "__main__":
    # Setup testing
    coin_id = "bitcoin"
    market_data = [
        ("bitcoin", 1617062400000, 58781.1, 1098136177282, 34876159896),
        ("bitcoin", 1617148800000, 58009.7, 1083474389567, 35561252184),
    ]
    data_storage.get_market_data = MagicMock(return_value=market_data)
    client.write_points = MagicMock()

    # Test publish_market_data()
    publish_market_data(coin_id)
    client.write_points.assert_called_once()

    print("Test passed: publish_market_data")

    # Test publish_sma()
    sma_data = [58781.1, 58009.7]
    publish_sma(coin_id, sma_data)
    client.write_points.assert_called()

    print("Test passed: publish_sma")
