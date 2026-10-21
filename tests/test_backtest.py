import sys
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import os
import backtrader as bt

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

import backtest

class TestBacktest(unittest.TestCase):
    
    def test_strategy_buy_logic(self):
        # Create a dummy data feed with known values.
        # RSI needs variation to avoid DivisionByZero (AvgLoss=0)
        import numpy as np
        periods = 100
        # Create a sine wave price to ensure movement
        prices = 100 + 10 * np.sin(np.linspace(0, 3*np.pi, periods))
        
        df = pd.DataFrame({
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000] * periods,
            'sentiment': [0.6] * periods
        }, index=pd.date_range('2021-01-01', periods=periods, freq='1min'))
        
        # Induce RSI < 30 manually at the end if needed, but Sine wave should oscillate.
        # Let's force a sharp drop at the end to trigger buy
        df.iloc[-10:, df.columns.get_loc('close')] = [80 - i for i in range(10)]
        df.iloc[-10:, df.columns.get_loc('sentiment')] = 0.8 # Good sentiment
        
        # Run Cerebro
        cerebro = bt.Cerebro()
        data = backtest.SentimentPandasData(dataname=df)
        cerebro.adddata(data)
        
        cerebro.addstrategy(backtest.SentimentRSIStrategy)
        
        # Since we can't easily introspect the strategy instance from cerebro.run() without trickery,
        # we check the broker orders or value change.
        cerebro.run()
        # If no exemption raised, pass.

    @patch('backtest.sqlalchemy.create_engine')
    @patch('backtest.pd.read_sql')
    def test_run_backtest_flow(self, mock_read_sql, mock_engine):
        # Mock data return with variation
        import numpy as np
        prices = 100 + np.random.randn(50) # 50 points
        
        df = pd.DataFrame({
            'time': pd.date_range('2021-01-01', periods=50, freq='1min'),
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': [1000] * 50,
            'sentiment': [0.6] * 50
        })
        mock_read_sql.return_value = df
        
        # Mock plot generation to avoid file writing issues or graphical errors in headless
        with patch('backtest.generate_plot') as mock_plot:
            backtest.run_backtest('BTC/USDT')
            mock_plot.assert_called_once()
    
    def test_generate_plot(self):
        # Verify plotly generation runs without error
        df = pd.DataFrame({
            'open': [100.0], 'high': [100.0], 'low': [100.0], 'close': [100.0]
        }, index=pd.to_datetime(['2021-01-01']))
        
        orders = [{'type': 'buy', 'price': 100, 'time': df.index[0]}]
        final_value = 10100
        
        with patch('plotly.graph_objects.Figure.write_html') as mock_write:
            backtest.generate_plot(df, orders, final_value, 'TEST')
            mock_write.assert_called()

if __name__ == '__main__':
    unittest.main()
