import asyncio
import sys
import unittest
from unittest.mock import MagicMock, patch
import os
from datetime import datetime

# Add app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../app')))

# We can import ingestion directly now, but we still need to patch network calls
# to avoid hitting real exchanges or DBs during unit tests.
# However, we can use real vaderSentiment if installed.
import ingestion

class TestIngestion(unittest.TestCase):
    
    def test_analyze_sentiment(self):
        # Use REAL vaderSentiment
        # "Bitcoin is great!" should have a positive compound score
        score = ingestion.analyze_sentiment("Bitcoin is great!")
        print(f"Sentiment Score: {score}")
        self.assertIsInstance(score, float)
        self.assertTrue(score > 0)

    def test_fetch_ohlcv_success(self):
        async def run_test():
            # Mock the exchange object from ccxt
            mock_exchange = MagicMock()
            
            # Determine what fetch_ohlcv returns in reality: a list of lists
            # [timestamp, open, high, low, close, volume]
            # We need to simulate the coroutine
            future = asyncio.Future()
            fake_data = [[1609459200000, 29000, 29100, 28900, 29050, 100]]
            future.set_result(fake_data)
            
            mock_exchange.fetch_ohlcv.return_value = future
            
            result = await ingestion.fetch_ohlcv(mock_exchange, 'BTC/USDT')
            
            self.assertIsNotNone(result)
            timestamp, symbol, price, volume = result
            self.assertEqual(symbol, 'BTC/USDT')
            self.assertEqual(price, 29050)
            self.assertEqual(volume, 100)
            self.assertIsInstance(timestamp, datetime)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

    def test_batch_insert_market_data(self):
        async def run_test():
            # Mock database pool and connection
            mock_pool = MagicMock()
            mock_conn = MagicMock()
            
            # Async Context Manager for pool.acquire
            conn_context = MagicMock()
            conn_context.__aenter__.return_value = mock_conn
            conn_context.__aexit__.return_value = None
            mock_pool.acquire.return_value = conn_context
            
            # copy_records_to_table is a coroutine
            future = asyncio.Future()
            future.set_result(None)
            mock_conn.copy_records_to_table.return_value = future
            
            data = [('time', 'BTC/USDT', 29000, 100)]
            
            await ingestion.batch_insert_market_data(mock_pool, data)
            
            mock_conn.copy_records_to_table.assert_called_once()
            args, kwargs = mock_conn.copy_records_to_table.call_args
            self.assertEqual(args[0], 'market_data')
            self.assertEqual(kwargs['records'], data)
            self.assertEqual(kwargs['columns'], ['time', 'symbol', 'price', 'volume'])

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_test())
        loop.close()

if __name__ == '__main__':
    unittest.main()
