import unittest
from unittest.mock import MagicMock, patch
import pandas as pd
import sys
import os

# Mock streamlit before importing dashboard
# We need to mock st.cache_data to be a simple pass-through decorator
# and st.error/st.warning etc to verify calls if needed.
sys.modules['streamlit'] = MagicMock()
# Define a side_effect for cache_data to return the function itself (pass-through)
def identity_decorator(func=None, **kwargs):
    if func:
        return func
    def _inner(f):
        return f
    return _inner

sys.modules['streamlit'].cache_data = identity_decorator
sys.modules['streamlit'].sidebar = MagicMock()
# Configure st.tabs to return a list of 2 mocks (since we use 2 tabs)
sys.modules['streamlit'].tabs.return_value = [MagicMock(), MagicMock()]
# Configure st.columns to return a list of 2 mocks (since we use 2 columns)
sys.modules['streamlit'].columns.return_value = [MagicMock(), MagicMock()]
# Configure st.button to return False so we don't enter interaction blocks
sys.modules['streamlit'].button.return_value = False
# etc.

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

from dashboard import fetch_data, calculate_mas

class TestDashboard(unittest.TestCase):

    def test_calculate_mas(self):
        # Create dummy data
        df = pd.DataFrame({
            'close': [100 + i for i in range(100)]
        })
        
        df = calculate_mas(df)
        
        self.assertIn('EMA_20', df.columns)
        self.assertIn('SMA_50', df.columns)
        self.assertFalse(df['EMA_20'].isnull().all())
        
    @patch('dashboard.sqlalchemy.create_engine')
    @patch('dashboard.pd.read_sql')
    def test_fetch_data(self, mock_read_sql, mock_engine):
        # Mock successful fetch data
        df_query_result = pd.DataFrame({
            'time': pd.to_datetime(['2021-01-01']),
            'close': [100],
            'volume': [100]
        })
        mock_read_sql.return_value = df_query_result
        
        result = fetch_data('BTC/USDT')
        
        self.assertFalse(result.empty)
        self.assertIn('close', result.columns)
        self.assertIsInstance(result.index, pd.DatetimeIndex)

if __name__ == '__main__':
    unittest.main()
