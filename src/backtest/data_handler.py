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

from ..data.manager import DataManager
from ..kraken.client import KrakenClient

logger = logging.getLogger(__name__)

class BacktestDataHandler:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the backtesting data handler
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        # We'll create a mock Kraken client for data fetching
        # In a real implementation, this would use actual API keys
        self.kraken_client = KrakenClient(
            api_key=config.get('kraken', {}).get('api_key', ''),
            api_secret=config.get('kraken', {}).get('api_secret', ''),
            sandbox=True
        )
        self.data_manager = DataManager(self.kraken_client, config)
        
        logger.info("Backtesting data handler initialized")
    
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
        
        try:
            # Convert dates to datetime objects
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d')
            
            # Calculate approximate number of candles needed
            # Assuming 1h timeframe, 24 candles per day
            days_diff = (end_dt - start_dt).days
            estimated_candles = days_diff * 24
            
            # Add buffer for weekends and holidays
            limit = max(estimated_candles * 2, 1000)
            
            # Fetch historical data
            ohlcv_data = await self.data_manager.get_historical_data(
                symbol=symbol,
                timeframe=self.config.get('trading', {}).get('timeframe', '1h'),
                limit=limit
            )
            
            # Filter data by date range
            filtered_data = []
            start_timestamp = int(start_dt.timestamp() * 1000)
            end_timestamp = int(end_dt.timestamp() * 1000) + (24 * 60 * 60 * 1000)  # End of day
            
            for candle in ohlcv_data:
                timestamp = candle[0]  # Assuming timestamp is first element
                if start_timestamp <= timestamp <= end_timestamp:
                    filtered_data.append(candle)
            
            logger.info(f"Loaded {len(filtered_data)} candles for {symbol}")
            return filtered_data
            
        except Exception as e:
            logger.error(f"Error loading historical data: {e}")
            # Return empty list if we can't fetch data
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