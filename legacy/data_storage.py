#data_storage.py
import sqlite3
import time
from datetime import datetime

DB_FILE = 'crypto_data.db'


def create_tables():
    conn = sqlite3.connect(DB_FILE)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS coins (
            id TEXT PRIMARY KEY,
            symbol TEXT,
            name TEXT
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS market_data (
            coin_id TEXT,
            timestamp INTEGER,
            price REAL,
            high_24h REAL,
            low_24h REAL,
            market_cap REAL,
            total_volume REAL,
            FOREIGN KEY (coin_id) REFERENCES coins (id)
        )
    """)

    conn.commit()
    conn.close()



def insert_coin(coin_id, symbol, name):
    conn = sqlite3.connect(DB_FILE)

    conn.execute(
        "INSERT OR IGNORE INTO coins (id, symbol, name) VALUES (?, ?, ?)",
        (coin_id, symbol, name)
    )

    conn.commit()
    conn.close()


def insert_market_data(coin_id, timestamp, price, high_24h, low_24h, market_cap, total_volume):
    connection = sqlite3.connect("crypto_data.db")
    cursor = connection.cursor()

    # Check if data with the same coin_id and timestamp already exists
    cursor.execute("SELECT * FROM market_data WHERE coin_id = ? AND timestamp = ?", (coin_id, timestamp))
    existing_data = cursor.fetchone()

    if existing_data is None:
        # If data doesn't exist, insert new data
        cursor.execute("INSERT INTO market_data (coin_id, timestamp, price, high_24h, low_24h, market_cap, total_volume) VALUES (?, ?, ?, ?, ?, ?, ?)",
                       (coin_id, timestamp, price, high_24h, low_24h, market_cap, total_volume))
    else:
        # If data exists, update the existing data
        cursor.execute("UPDATE market_data SET price = ?, high_24h = ?, low_24h = ?, market_cap = ?, total_volume = ? WHERE coin_id = ? AND timestamp = ?",
                       (price, high_24h, low_24h, market_cap, total_volume, coin_id, timestamp))

    connection.commit()
    connection.close()


def get_all_coins():
    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute("SELECT * FROM coins")
    coins = cursor.fetchall()

    conn.close()

    return coins


def get_market_data(coin_id):
    conn = sqlite3.connect(DB_FILE)

    cursor = conn.execute(
        "SELECT * FROM market_data WHERE coin_id = ? ORDER BY timestamp ASC",
        (str(coin_id),)  # Convert coin_id to a string
    )
    market_data = cursor.fetchall()

    conn.close()

    return market_data



def test_module():
    create_tables()

    # Test insert_coin and get_all_coins
    insert_coin("bitcoin", "btc", "Bitcoin")
    insert_coin("ethereum", "eth", "Ethereum")

    coins = get_all_coins()
    print("All coins:", coins)
    assert len(coins) == 2

    # Test insert_market_data and get_market_data
    timestamp = int(time.time())
    insert_market_data("bitcoin", timestamp, 50000, 55000, 48000, 1000000000, 1000000)
    insert_market_data("ethereum", timestamp, 3000, 3200, 2800, 500000000, 500000)

    market_data_bitcoin = get_market_data("bitcoin")
    market_data_ethereum = get_market_data("ethereum")
    print("Market data for Bitcoin:", market_data_bitcoin)
    print("Market data for Ethereum:", market_data_ethereum)
    assert len(market_data_bitcoin) == 1
    assert len(market_data_ethereum) == 1


if __name__ == "__main__":
    test_module()
