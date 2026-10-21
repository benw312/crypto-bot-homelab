#api_client.py
import requests
from pycoingecko import CoinGeckoAPI

cg = CoinGeckoAPI()

def fetch_coin_data(coin_id, currency='gbp'):
    try:
        data = cg.get_coin_by_id(coin_id, localization='false', vs_currency=currency)
        market_data = data['market_data']
        return {
            'price': market_data['current_price'][currency],
            'high_24h': market_data['high_24h'][currency],
            'low_24h': market_data['low_24h'][currency],
            'market_cap': market_data['market_cap'][currency],
            'total_volume': market_data['total_volume'][currency],
            '24h_price_change': market_data['price_change_percentage_24h_in_currency'][currency],
            '7d_price_change': market_data['price_change_percentage_7d_in_currency'][currency],
            '30d_price_change': market_data['price_change_percentage_30d_in_currency'][currency],
            '1y_price_change': market_data['price_change_percentage_1y_in_currency'][currency],
        }
    except Exception as e:
        print(f"Error fetching data for {coin_id}: {e}")
        return None

if __name__ == "__main__":
    # Test the fetch_coin_data function
    coin_ids = ["bitcoin", "ethereum", "binancecoin", "cardano", "ripple", "solana", "polkadot"]
    for coin_id in coin_ids:
        coin_data = fetch_coin_data(coin_id)
        print(f"Market data for {coin_id}:")
        print(coin_data)
        print("\n")
