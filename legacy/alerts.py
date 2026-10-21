#alerts.py
import data_storage
import error_handling

def check_price_change(coin_id, percentage_threshold, time_period, market_data):
    if len(market_data) < 2:
        raise ValueError("Not enough data points to check for price change")
    
    latest_price = market_data[-1][2]
    previous_price = market_data[-time_period][2]
    price_change_percentage = ((latest_price - previous_price) / previous_price) * 100
    
    return price_change_percentage


def send_price_change_notification(coin_id, price_change_percentage):
    subject = f"Price Alert for {coin_id}"
    content = (
        f"The price of {coin_id} has changed by {price_change_percentage:.2f}%.\n"
        "Please check your cryptocurrency data collector for more information."
    )
    
    error_handling.send_email(subject, content)


def check_and_notify_price_change(coin_id, percentage_threshold, time_period, market_data):
    try:
        price_change_percentage = check_price_change(coin_id, percentage_threshold, time_period, market_data)
        
        if abs(price_change_percentage) >= percentage_threshold:
            send_price_change_notification(coin_id, price_change_percentage)
    except Exception as e:
        error_handling.handle_error(e)


if __name__ == "__main__":
    test_coin_id = "bitcoin"
    test_percentage_threshold = 5
    test_time_period = 1

    try:
        market_data = [
            ("bitcoin", 1617062400000, 58781.1, 1098136177282, 34876159896),
            ("bitcoin", 1617148800000, 58009.7, 1083474389567, 35561252184),
        ]

        check_and_notify_price_change(test_coin_id, test_percentage_threshold, test_time_period, market_data)
        print("Test passed: check_and_notify_price_change")
    except Exception as e:
        error_handling.handle_error(e)
