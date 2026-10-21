#data_processing.py
import data_storage


def simple_moving_average(coin_id, window_size):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size:
        print(f"Not enough data points to calculate the simple moving average. Expected {window_size}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    sma = []
    for i in range(len(prices) - window_size + 1):
        window = prices[i:i + window_size]
        sma_value = sum(window) / window_size
        sma.append(sma_value)

    return sma


def exponential_moving_average(coin_id, window_size):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size:
        print(f"Not enough data points to calculate the exponential moving average. Expected {window_size}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    ema = []
    alpha = 2 / (window_size + 1)  # Calculate the smoothing factor

    # Calculate the first EMA value as a simple moving average
    initial_sma = sum(prices[:window_size]) / window_size
    ema.append(initial_sma)

    # Calculate the remaining EMA values using the previous EMA and the current price
    for i in range(window_size, len(prices)):
        ema_value = (prices[i] - ema[-1]) * alpha + ema[-1]
        ema.append(ema_value)

    return ema

def exponential_moving_average_given_data(data, window_size):
    if len(data) < window_size:
        print(f"Not enough data points to calculate EMA. Expected at least {window_size}, found {len(data)}")
        return []

    ema = [sum(data[:window_size]) / window_size]  # Seed the EMA with the average of the first window
    multiplier = 2 / (window_size + 1)

    for i in range(window_size, len(data)):
        ema.append((data[i] - ema[-1]) * multiplier + ema[-1])

    return ema[window_size - 1:]


def moving_average_convergence_divergence(coin_id, short_window_size=12, long_window_size=26, signal_window_size=9):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < long_window_size:
        print(f"Not enough data points to calculate the MACD. Expected at least {long_window_size}, found {len(market_data)}")
        return [], []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    # Calculate the short and long term EMAs
    short_ema = exponential_moving_average(coin_id, short_window_size)
    long_ema = exponential_moving_average(coin_id, long_window_size)

    # Calculate the MACD values
    macd = [short_ema[i] - long_ema[i] for i in range(len(long_ema))]

    # Calculate the signal line values
    signal_line = exponential_moving_average_given_data(macd, signal_window_size)
    
    return macd, signal_line


def relative_strength_index(coin_id, window_size=14):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size + 1:
        print(f"Not enough data points to calculate the RSI. Expected at least {window_size + 1}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    gains = []
    losses = []

    # Calculate gains and losses
    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))

    avg_gain = sum(gains[:window_size]) / window_size
    avg_loss = sum(losses[:window_size]) / window_size

    rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
    rsi = [100 - (100 / (1 + rs))]

    # Calculate the remaining RSI values
    for i in range(window_size, len(gains)):
        avg_gain = (avg_gain * (window_size - 1) + gains[i]) / window_size
        avg_loss = (avg_loss * (window_size - 1) + losses[i]) / window_size
        rs = avg_gain / avg_loss if avg_loss != 0 else float('inf')
        rsi.append(100 - (100 / (1 + rs)))

    return rsi


def bollinger_bands(coin_id, window_size=20, num_std_dev=2):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size:
        print(f"Not enough data points to calculate the Bollinger Bands. Expected at least {window_size}, found {len(market_data)}")
        return [], [], []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    sma = simple_moving_average(coin_id, window_size)
    upper_band = []
    lower_band = []

    for i in range(len(sma)):
        window = prices[i:i + window_size]
        std_dev = (sum([(price - sma[i])**2 for price in window]) / window_size) ** 0.5
        upper_band.append(sma[i] + num_std_dev * std_dev)
        lower_band.append(sma[i] - num_std_dev * std_dev)

    return upper_band, sma, lower_band


def rate_of_change(coin_id, window_size):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size + 1:
        print(f"Not enough data points to calculate the Rate of Change. Expected at least {window_size + 1}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    roc = []
    for i in range(window_size, len(prices)):
        roc_value = (prices[i] - prices[i - window_size]) / prices[i - window_size] * 100
        roc.append(roc_value)

    return roc

def stochastic_oscillator(coin_id, window_size=14):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size + 1:
        print(f"Not enough data points to calculate the Stochastic Oscillator. Expected at least {window_size + 1}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data
    highs = [entry[3] for entry in market_data]  # Extract the high prices from the market_data
    lows = [entry[4] for entry in market_data]  # Extract the low prices from the market_data

    stoch_osc = []

    for i in range(window_size, len(prices)):
        highest_high = max(highs[i-window_size:i])
        lowest_low = min(lows[i-window_size:i])
        current_close = prices[i]

        if highest_high != lowest_low:
            stoch_value = (current_close - lowest_low) / (highest_high - lowest_low) * 100
        else:
            stoch_value = 0

        stoch_osc.append(stoch_value)

    return stoch_osc


def average_true_range(coin_id, window_size=14):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size + 1:
        print(f"Not enough data points to calculate the Average True Range. Expected at least {window_size + 1}, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data
    highs = [entry[3] for entry in market_data]  # Extract the high prices from the market_data
    lows = [entry[4] for entry in market_data]  # Extract the low prices from the market_data

    true_ranges = []

    for i in range(1, len(prices)):
        tr1 = highs[i] - lows[i]
        tr2 = abs(highs[i] - prices[i - 1])
        tr3 = abs(lows[i] - prices[i - 1])
        true_range = max(tr1, tr2, tr3)
        true_ranges.append(true_range)

    atr = [sum(true_ranges[:window_size]) / window_size]

    for i in range(window_size, len(true_ranges)):
        atr_value = (atr[-1] * (window_size - 1) + true_ranges[i]) / window_size
        atr.append(atr_value)

    return atr


def on_balance_volume(coin_id):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < 2:
        print(f"Not enough data points to calculate the On-Balance Volume. Expected at least 2, found {len(market_data)}")
        return []

    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data
    volumes = [entry[6] for entry in market_data]  # Extract the volumes from the market_data

    obv = [0]  # Initialize the OBV list with the first value as 0

    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1]:
            obv.append(obv[-1] + volumes[i])
        elif prices[i] < prices[i - 1]:
            obv.append(obv[-1] - volumes[i])
        else:
            obv.append(obv[-1])

    return obv


def parabolic_sar(coin_id, start_af=0.02, max_af=0.2):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < 2:
        print(f"Not enough data points to calculate the Parabolic SAR. Expected at least 2, found {len(market_data)}")
        return []

    high_prices = [entry[3] for entry in market_data]  # Extract the high prices from the market_data
    low_prices = [entry[4] for entry in market_data]  # Extract the low prices from the market_data

    sar = [low_prices[0]]  # Initialize the SAR list with the first value as the first low price
    trend = 1  # Initialize the trend as uptrend (1 for uptrend, -1 for downtrend)
    extreme_point = high_prices[0]  # Initialize the extreme point with the first high price
    acceleration_factor = start_af

    for i in range(1, len(high_prices)):
        prev_sar = sar[-1]

        if trend == 1:
            new_sar = prev_sar + acceleration_factor * (extreme_point - prev_sar)
            if new_sar > min(low_prices[i], low_prices[i - 1]):
                new_sar = min(low_prices[i], low_prices[i - 1])

            if high_prices[i] > extreme_point:
                extreme_point = high_prices[i]
                acceleration_factor = min(acceleration_factor + start_af, max_af)

            if new_sar > low_prices[i]:
                new_sar = extreme_point
                extreme_point = low_prices[i]
                trend = -1
                acceleration_factor = start_af
        else:
            new_sar = prev_sar + acceleration_factor * (extreme_point - prev_sar)
            if new_sar < max(high_prices[i], high_prices[i - 1]):
                new_sar = max(high_prices[i], high_prices[i - 1])

            if low_prices[i] < extreme_point:
                extreme_point = low_prices[i]
                acceleration_factor = min(acceleration_factor + start_af, max_af)

            if new_sar < high_prices[i]:
                new_sar = extreme_point
                extreme_point = high_prices[i]
                trend = 1
                acceleration_factor = start_af

        sar.append(new_sar)

    return sar


def commodity_channel_index(coin_id, window_size=20):
    market_data = data_storage.get_market_data(coin_id)

    if len(market_data) < window_size:
        print(f"Not enough data points to calculate the Commodity Channel Index. Expected at least {window_size}, found {len(market_data)}")
        return []

    high_prices = [entry[3] for entry in market_data]  # Extract the high prices from the market_data
    low_prices = [entry[4] for entry in market_data]  # Extract the low prices from the market_data
    close_prices = [entry[2] for entry in market_data]  # Extract the close prices from the market_data

    typical_prices = [(high + low + close) / 3 for high, low, close in zip(high_prices, low_prices, close_prices)]

    cci = []
    for i in range(len(typical_prices) - window_size + 1):
        window = typical_prices[i:i + window_size]
        sma = sum(window) / window_size
        mean_deviation = sum(abs(tp - sma) for tp in window) / window_size
        cci_value = (typical_prices[i + window_size - 1] - sma) / (0.015 * mean_deviation)
        cci.append(cci_value)

    return cci


def ichimoku_cloud(coin_id):
    market_data = data_storage.get_market_data(coin_id)

    high_prices = [entry[3] for entry in market_data]  # Extract the high prices from the market_data
    low_prices = [entry[4] for entry in market_data]  # Extract the low prices from the market_data

    conversion_line = []
    base_line = []
    leading_span_a = []
    leading_span_b = []

    for i in range(len(high_prices)):
        if i >= 8:
            conversion_line.append((max(high_prices[i - 8:i]) + min(low_prices[i - 8:i])) / 2)

        if i >= 25:
            base_line.append((max(high_prices[i - 25:i]) + min(low_prices[i - 25:i])) / 2)
            leading_span_a.append((conversion_line[-1] + base_line[-1]) / 2)

        if i >= 51:
            leading_span_b.append((max(high_prices[i - 51:i]) + min(low_prices[i - 51:i])) / 2)

    return conversion_line, base_line, leading_span_a, leading_span_b


def fibonacci_retracement(coin_id):
    market_data = data_storage.get_market_data(coin_id)
    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    highest_price = max(prices)
    lowest_price = min(prices)

    retracement_levels = {
        '0.0%': lowest_price,
        '23.6%': lowest_price + 0.236 * (highest_price - lowest_price),
        '38.2%': lowest_price + 0.382 * (highest_price - lowest_price),
        '50.0%': lowest_price + 0.5 * (highest_price - lowest_price),
        '61.8%': lowest_price + 0.618 * (highest_price - lowest_price),
        '76.4%': lowest_price + 0.764 * (highest_price - lowest_price),
        '100.0%': highest_price,
    }

    return retracement_levels


def pivot_points(coin_id, method="standard"):
    market_data = data_storage.get_market_data(coin_id)
    prices = [entry[2] for entry in market_data]  # Extract the prices from the market_data

    last_data = market_data[-1]
    last_high = last_data[3]
    last_low = last_data[4]
    last_close = last_data[2]

    if method == "standard":
        pivot = (last_high + last_low + last_close) / 3
        r1 = 2 * pivot - last_low
        s1 = 2 * pivot - last_high
        r2 = pivot + (last_high - last_low)
        s2 = pivot - (last_high - last_low)
        r3 = last_high + 2 * (pivot - last_low)
        s3 = last_low - 2 * (last_high - pivot)

    return {"P": pivot, "R1": r1, "S1": s1, "R2": r2, "S2": s2, "R3": r3, "S3": s3}

if __name__ == '__main__':
        
    # Test the simple_moving_average function
    coin_id = 'bitcoin'
    window_size = 7
    sma = simple_moving_average(coin_id, window_size)
    """
    print(f"Simple Moving Average for {coin_id} with window size {window_size}:")
    print(sma[:30])

    # Test the exponential_moving_average function
    ema = exponential_moving_average(coin_id, window_size)
    print(f"Exponential Moving Average for {coin_id} with window size {window_size}:")
    print(ema[:30])

    
    # Test the moving_average_convergence_divergence function
    short_window_size = 12
    long_window_size = 26
    signal_window_size = 9
    macd, signal_line = moving_average_convergence_divergence(coin_id, short_window_size, long_window_size, signal_window_size)
    print(f"MACD for {coin_id} with short window {short_window_size} and long window {long_window_size}:")
    print(macd[:30])
    print(f"Signal Line for {coin_id} with window size {signal_window_size}:")
    print(signal_line[:30])

    
    # Test the relative_strength_index function
    window_size = 14
    rsi = relative_strength_index(coin_id, window_size)
    print(f"Relative Strength Index for {coin_id} with window size {window_size}:")
    print(rsi[:30])

    
    # Test the bollinger_bands function
    window_size = 20
    num_std_dev = 2
    upper_band, sma, lower_band = bollinger_bands(coin_id, window_size, num_std_dev)
    print(f"Bollinger Bands for {coin_id} with window size {window_size} and {num_std_dev} standard deviations:")
    print("Upper Band:", upper_band[:30])
    print("Simple Moving Average:", sma[:30])
    print("Lower Band:", lower_band[:30])

    
    # Test the rate_of_change function
    window_size = 12
    roc = rate_of_change(coin_id, window_size)
    print(f"Rate of Change for {coin_id} with window size {window_size} (first 30 results):")
    print(roc[:30])

    
    # Test the stochastic_oscillator function
    window_size = 14
    stoch_osc = stochastic_oscillator(coin_id, window_size)
    print(f"Stochastic Oscillator for {coin_id} with window size {window_size} (first 30 results):")
    print(stoch_osc[:30])

    
    # Test the average_true_range function
    window_size = 14
    atr = average_true_range(coin_id, window_size)
    print(f"Average True Range for {coin_id} with window size {window_size} (first 30 results):")
    print(atr[:30])
    

    # Test the on_balance_volume function
    obv = on_balance_volume(coin_id)
    print(f"On-Balance Volume for {coin_id} (first 30 results):")
    print(obv[:30])

    
    # Test the parabolic_sar function
    start_af = 0.02
    max_af = 0.2
    sar = parabolic_sar(coin_id, start_af, max_af)
    print(f"Parabolic SAR for {coin_id} with start AF {start_af} and max AF {max_af} (first 30 results):")
    print(sar[:30])

    
    # Test the commodity_channel_index function
    window_size = 20
    cci = commodity_channel_index(coin_id, window_size)
    print(f"Commodity Channel Index for {coin_id} with window size {window_size} (first 30 results):")
    print(cci[:30])

    
    # Test the ichimoku_cloud function
    conversion_line, base_line, leading_span_a, leading_span_b = ichimoku_cloud(coin_id)
    print(f"Ichimoku Cloud for {coin_id} (first 30 results):")
    print("Conversion Line:", conversion_line[:30])
    print("Base Line:", base_line[:30])
    print("Leading Span A:", leading_span_a[:30])
    print("Leading Span B:", leading_span_b[:30])

    
    # Test the fibonacci_retracement function
    retracement_levels = fibonacci_retracement(coin_id)
    print(f"Fibonacci Retracement for {coin_id}:")
    for level, value in retracement_levels.items():
        print(f"{level}: {value}")
    """

    # Test the pivot_points function
    method = "standard"
    pivot_points_values = pivot_points(coin_id, method)
    print(f"Pivot Points ({method}) for {coin_id}:")
    for level, value in pivot_points_values.items():
        print(f"{level}: {value}")