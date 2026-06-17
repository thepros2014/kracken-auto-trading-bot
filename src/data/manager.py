"""
Data Manager Module
Handles data fetching, storage, and preprocessing for the trading bot
"""
import asyncio
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import os
import json

logger = logging.getLogger(__name__)

class DataManager:
    def __init__(self, kraken_client, config: Dict):
        self.kraken_client = kraken_client
        self.config = config
        self.cache = {}
        self.cache_ttl = config.get('data', {}).get('cache_ttl_hours', 1)
        self.storage_path = config.get('data', {}).get('storage_path', './data/historical')
        self.update_frequency = config.get('data', {}).get('update_frequency_seconds', 30)
        
        # Create storage directory
        os.makedirs(self.storage_path, exist_ok=True)
        
        logger.info("Data manager initialized")
    
    async def get_historical_data(self, symbol: str, timeframe: str = '1h', 
                                 limit: int = 100, start_date: str = None, 
                                 end_date: str = None) -> List[List]:
        """Get historical OHLCV data"""
        try:
            # Check cache first
            cache_key = f"{symbol}_{timeframe}_{limit}"
            if cache_key in self.cache:
                cached_data, timestamp = self.cache[cache_key]
                if (datetime.now() - timestamp).total_seconds() < self.cache_ttl * 3600:
                    logger.debug(f"Returning cached data for {symbol}")
                    return cached_data
            
            # Fetch from exchange
            ohlcv = await self.kraken_client.fetch_ohlcv(symbol, timeframe, limit)
            
            # Cache the data
            self.cache[cache_key] = (ohlcv, datetime.now())
            
            # Save to storage
            await self._save_to_storage(symbol, timeframe, ohlcv)
            
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            # Try to load from storage as fallback
            return await self._load_from_storage(symbol, timeframe, limit)
    
    async def get_latest_price(self, symbol: str) -> float:
        """Get the latest price for a symbol"""
        try:
            ticker = await self.kraken_client.fetch_ticker(symbol)
            return ticker['last']
        except Exception as e:
            logger.error(f"Error fetching latest price for {symbol}: {e}")
            return 0.0
    
    async def get_market_data(self, symbols: List[str]) -> Dict[str, Dict]:
        """Get market data for multiple symbols"""
        market_data = {}
        
        for symbol in symbols:
            try:
                ticker = await self.kraken_client.fetch_ticker(symbol)
                market_data[symbol] = {
                    'price': ticker['last'],
                    'bid': ticker['bid'],
                    'ask': ticker['ask'],
                    'high': ticker['high'],
                    'low': ticker['low'],
                    'volume': ticker['baseVolume'],
                    'change': ticker['percentage'],
                    'timestamp': ticker['timestamp']
                }
            except Exception as e:
                logger.error(f"Error fetching market data for {symbol}: {e}")
                market_data[symbol] = {}
        
        return market_data
    
    async def _save_to_storage(self, symbol: str, timeframe: str, data: List[List]):
        """Save data to local storage"""
        try:
            filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
            filepath = os.path.join(self.storage_path, filename)
            
            # Convert to serializable format
            serializable_data = []
            for row in data:
                serializable_data.append({
                    'timestamp': row[0],
                    'open': row[1],
                    'high': row[2],
                    'low': row[3],
                    'close': row[4],
                    'volume': row[5]
                })
            
            with open(filepath, 'w') as f:
                json.dump(serializable_data, f)
                
        except Exception as e:
            logger.error(f"Error saving data to storage: {e}")
    
    async def _load_from_storage(self, symbol: str, timeframe: str, limit: int) -> List[List]:
        """Load data from local storage"""
        try:
            filename = f"{symbol.replace('/', '_')}_{timeframe}.json"
            filepath = os.path.join(self.storage_path, filename)
            
            if not os.path.exists(filepath):
                return []
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Convert back to OHLCV format
            ohlcv = []
            for row in data[-limit:]:
                ohlcv.append([
                    row['timestamp'],
                    row['open'],
                    row['high'],
                    row['low'],
                    row['close'],
                    row['volume']
                ])
            
            return ohlcv
            
        except Exception as e:
            logger.error(f"Error loading data from storage: {e}")
            return []
    
    async def update_all_data(self, symbols: List[str], timeframe: str = '1h'):
        """Update cached data for all symbols"""
        for symbol in symbols:
            try:
                await self.get_historical_data(symbol, timeframe, limit=500)
            except Exception as e:
                logger.error(f"Error updating data for {symbol}: {e}")
    
    def get_cached_data(self, symbol: str, timeframe: str = '1h') -> Optional[List[List]]:
        """Get cached data without fetching"""
        cache_key = f"{symbol}_{timeframe}_500"
        if cache_key in self.cache:
            return self.cache[cache_key][0]
        return None
    
    def clear_cache(self):
        """Clear all cached data"""
        self.cache.clear()
        logger.info("Data cache cleared")

# Data preprocessing utilities
class DataPreprocessor:
    @staticmethod
    def clean_ohlcv_data(data: List[List]) -> List[List]:
        """Clean OHLCV data by removing invalid entries"""
        cleaned = []
        for row in data:
            # Check for valid numeric values
            if all(isinstance(v, (int, float)) and not np.isnan(v) for v in row[1:]):
                cleaned.append(row)
        return cleaned
    
    @staticmethod
    def resample_data(data: List[List], target_timeframe: str) -> List[List]:
        """Resample OHLCV data to a different timeframe"""
        # This would use pandas resample functionality
        # Placeholder implementation
        return data
    
    @staticmethod
    def calculate_returns(data: List[List]) -> List[float]:
        """Calculate returns from OHLCV data"""
        returns = []
        for i in range(1, len(data)):
            prev_close = data[i-1][4]
            curr_close = data[i][4]
            if prev_close > 0:
                returns.append((curr_close - prev_close) / prev_close)
            else:
                returns.append(0.0)
        return returns
    
    @staticmethod
    def calculate_volatility(data: List[List], window: int = 20) -> List[float]:
        """Calculate rolling volatility"""
        returns = DataPreprocessor.calculate_returns(data)
        volatility = []
        
        for i in range(len(returns)):
            if i < window:
                volatility.append(0.0)
            else:
                window_returns = returns[i-window:i]
                volatility.append(np.std(window_returns))
        
        return volatility