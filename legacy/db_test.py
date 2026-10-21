import sqlite3
from data_storage import insert_market_data, get_market_data, create_tables

# Test code
if __name__ == "__main__":
    create_tables()

    # Step 1: Insert sample data
    sample_data = [
        {
            'coin_id': 'bitcoin',
            'price': 50000,
            'market_cap': 900000000000,
            'total_volume': 45000000000,
            'timestamp': '2023-04-30 00:00:00'
        },
        {
            'coin_id': 'ethereum',
            'price': 3000,
            'market_cap': 300000000000,
            'total_volume': 15000000000,
            'timestamp': '2023-04-30 00:00:00'
        }
    ]

    for data in sample_data:
        insert_market_data(data['coin_id'], data['timestamp'], data['price'], data['market_cap'], data['total_volume'])

    # Step 2: Update the sample data
    updated_sample_data = [
        {
            'coin_id': 'bitcoin',
            'price': 51000,
            'market_cap': 920000000000,
            'total_volume': 46000000000,
            'timestamp': '2023-04-30 01:00:00'
        },
        {
            'coin_id': 'ethereum',
            'price': 3100,
            'market_cap': 310000000000,
            'total_volume': 15500000000,
            'timestamp': '2023-04-30 01:00:00'
        }
    ]

    for data in updated_sample_data:
        insert_market_data(data['coin_id'], data['timestamp'], data['price'], data['market_cap'], data['total_volume'])

    # Step 3: Fetch and print data from the database
    def fetch_all_data():
        connection = sqlite3.connect("crypto_data.db")
        cursor = connection.cursor()

        cursor.execute("SELECT * FROM market_data ORDER BY timestamp ASC")
        rows = cursor.fetchall()

        connection.close()

        return rows

    all_data = fetch_all_data()

    for row in all_data:
        print(row)
