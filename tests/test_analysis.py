import sys
import unittest
from unittest.mock import MagicMock, patch
import os
import pandas as pd
import numpy as np
import talib
import joblib

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

import analysis

class TestAnalysis(unittest.TestCase):
    
    def setUp(self):
        # Create a sample DataFrame with enough data for indicators
        # RSI needs 14, MACD needs 26+9=35, BB needs 20.
        # Let's create 100 rows
        dates = pd.date_range(start='2021-01-01', periods=100, freq='15min')
        prices = np.linspace(100, 200, 100) + np.random.normal(0, 1, 100)
        self.df = pd.DataFrame({'time': dates, 'price': prices, 'volume': np.random.rand(100)})

    def test_calculate_indicators(self):
        # This uses REAL TA-Lib
        result_df = analysis.calculate_indicators(self.df.copy())
        
        # Check columns exist
        expected_cols = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_middle', 'bb_lower']
        for col in expected_cols:
            self.assertIn(col, result_df.columns)
            
        # Check values are calculated (not all Nan)
        # First few will be NaN due to lookback, but tail should be valid
        self.assertFalse(result_df['rsi'].tail().isnull().any())
        self.assertFalse(result_df['macd'].tail().isnull().any())
        self.assertFalse(result_df['bb_upper'].tail().isnull().any())

    def test_train_model(self):
        # Mock file operations to avoid overwriting real model file
        with patch('os.path.exists', return_value=False), \
             patch('joblib.dump') as mock_dump:
            
            # We need valid indicators first
            df = analysis.calculate_indicators(self.df.copy())
            
            # Use real training logic
            model = analysis.train_or_load_model(df)
            
            self.assertIsNotNone(model)
            # Verify it's a RandomForestClassifier (duck typing or isinstance)
            self.assertTrue(hasattr(model, 'predict'))
            
            # Verify dump was called
            mock_dump.assert_called()

    def test_predict_signal(self):
        # Train a real model first on dummy data
        df = analysis.calculate_indicators(self.df.copy())
        
        # Setup target
        future_close = df['price'].shift(-10) # reduced shift for test data size
        df['target'] = (future_close > df['price']).astype(int)
        train_df = df.dropna()
        
        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=10)
        features = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_middle', 'bb_lower', 'volume']
        model.fit(train_df[features], train_df['target'])
        
        # Predict on latest row of original df (after calc indicators)
        full_df = analysis.calculate_indicators(self.df.copy())
        
        pred, prob = analysis.predict_signal(model, full_df)
        
        self.assertIn(pred, [0, 1])
        self.assertTrue(0 <= prob <= 1)

    def test_predict_signal_returns_none_when_model_saw_one_class(self):
        # A quiet market can produce a training window with no >1% rise at all
        df = analysis.calculate_indicators(self.df.copy())
        train_df = df.dropna()

        from sklearn.ensemble import RandomForestClassifier
        model = RandomForestClassifier(n_estimators=10)
        features = ['rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_middle', 'bb_lower', 'volume']
        model.fit(train_df[features], [0] * len(train_df))

        self.assertIsNone(analysis.predict_signal(model, df))

if __name__ == '__main__':
    unittest.main()
