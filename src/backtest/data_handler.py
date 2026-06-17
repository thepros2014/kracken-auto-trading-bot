"""
Backtesting Data Handler Module
Handles loading and preprocessing of historical data for backtesting
"""

import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os

# Handle imports when running as module vs script
try:
    from src.data.manager import DataManager
    from src.kraken.client import KrakenClient
except ImportError:
    # Fallback for when src is not in path
    from data.manager import DataManager
    from kraken.client import KrakenClient

logger = logging.getLogger(__name__)

class BacktestDataHandler:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the backtesting data handler
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        # For backtesting, we'll create a simplified data manager
        # that doesn't require live API connections
        self.data_manager = None
        self.use_mock_data = True
        
        logger.info("Backtesting data handler initialized (using mock data)")
    
    async def load_historical_data(self, 
                                 symbol: str, 
                                 start_date: str, 
                                 end_date: str) -> List[List]:
        """
        Load historical OHLCV data for backtesting
        
        Args:
            symbol: Trading pair symbol (e.g., 'XBT/USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of OHLCV data [timestamp, open, high, low, close, volume]
        """
        logger.info(f"Loading historical data for {symbol} from {start_date} to {end_date}")
        
        # Generate mock data for testing purposes
        return self._generate_mock_data(symbol, start_date, end_date)
    
    def _generate_mock_data(self, symbol: str, start_date: str, end_date: str) -> List[List]:
        """
        Generate mock OHLCV data for testing
        
        Args:
            symbol: Trading pair symbol
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of mock OHLCV data
        """
        try:
            # Convert dates to datetime objects
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Calculate number of hours
            hours_diff = int((end_dt - start_dt).total_seconds() / 3600)
            
            # Generate mock data
            mock_data = []
            base_price = 50000.0 if 'XBT' in symbol or 'BTC' in symbol else 3000.0
            
            for i in range(min(hours_diff, 1000)):  # Limit to 1000 candles for testing
                timestamp = int(start_dt.timestamp() * 1000) + (i * 3600000)
                
                # Generate realistic price movement
                change_percent = np.random.normal(0, 0.02)  # 2% volatility
                open_price = base_price * (1 + change_percent)
                
                # Add some intraday volatility
                high_price = open_price * (1 + abs(np.random.normal(0, 0.01)))
                low_price = open_price * (1 - abs(np.random.normal(0, 0.01)))
                close_price = open_price * (1 + np.random.normal(0, 0.005))
                volume = np.random.uniform(10, 100)
                
                # Ensure high >= low and high >= open,close and low <= open,close
                high_price = max(high_price, open_price, close_price)
                low_price = min(low_price, open_price, close_price)
                
                mock_data.append([timestamp, open_price, high_price, low_price, close_price, volume])
                base_price = close_price  # Use close as base for next period
            
            logger.info(f"Generated {len(mock_data)} mock candles for {symbol}")
            return mock_data
            
        except Exception as e:
            logger.error(f"Error generating mock data: {e}")
            return []
    
    def resample_data(self, data: List[List], target_timeframe: str) -> List[List]:
        """
        Resample OHLCV data to a different timeframe
        
        Args:
            data: OHLCV data [timestamp, open, high, low, close, volume]
            target_timeframe: Target timeframe (e.g., '4h', '1d')
            
        Returns:
            Resampled OHLCV data
        """
        if not data:
            return []
        
        try:
            # Convert to DataFrame for resampling
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Resample
            resampled = df.resample(target_timeframe).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            # Convert back to list format
            result = []
            for timestamp, row in resampled.iterrows():
                result.append([
                    int(timestamp.timestamp() * 1000),
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ])
            
            return result
            
        except Exception as e:
            logger.error(f"Error resampling data: {e}")
            return data
    
    def get_data_info(self, data: List[List]) -> Dict[str, Any]:
        """
        Get information about the loaded data
        
        Args:
            data: OHLCV data
            
        Returns:
            Dictionary with data information
        """
        if not data:
            return {
                'count': 0,
                'start_date': None,
                'end_date': None,
                'symbol': None
            }
        
        try:
            timestamps = [candle[0] for candle in data]
            start_dt = datetime.fromtimestamp(min(timestamps) / 1000)
            end_dt = datetime.fromtimestamp(max(timestamps) / 1000)
            
            return {
                'count': len(data),
                'start_date': start_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'end_date': end_dt.strftime('%Y-%m-%d %H:%M:%S'),
                'date_range_days': (end_dt - start_dt).days
            }
        except Exception as e:
            logger.error(f"Error getting data info: {e}")
            return {
                'count': len(data) if data else 0,
                'start_date': None,
                'end_date': None,
                'symbol': None
            }