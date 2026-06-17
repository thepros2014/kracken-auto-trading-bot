"""
Backtesting Engine Module
Main backtesting orchestrator for the Kraken trading bot
"""

import asyncio
import logging
import yaml
import os
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd

from .data_handler import BacktestDataHandler
from .simulator import BacktestSimulator
from .analyzer import PerformanceAnalyzer

logger = logging.getLogger(__name__)

class BacktestEngine:
    def __init__(self, config_path: str = "config/config.yaml"):
        """
        Initialize the backtesting engine
        
        Args:
            config_path: Path to the configuration file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.data_handler = BacktestDataHandler(self.config)
        self.simulator = BacktestSimulator(self.config)
        self.analyzer = PerformanceAnalyzer(self.config)
        
        logger.info("Backtesting engine initialized")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        try:
            with open(self.config_path, 'r') as file:
                config = yaml.safe_load(file)
            return config
        except FileNotFoundError:
            logger.warning(f"Config file {self.config_path} not found, using defaults")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return self._get_default_config()
    
    def _get_default_config() -> Dict[str, Any]:
        """Return default configuration if file not found"""
        return {
            'backtest': {
                'initial_balance': 10000.0,
                'commission_percent': 0.26,
                'slippage_percent': 0.1,
                'max_trades_per_day': 100
            },
            'trading': {
                'default_pair': 'XBT/USD',
                'timeframe': '1h',
                'max_positions': 5,
                'position_size_percent': 2.0,
                'stop_loss_percent': 3.0,
                'take_profit_percent': 6.0
            }
        }
    
    async def run_backtest(self, 
                          symbol: str, 
                          start_date: str, 
                          end_date: str,
                          initial_balance: Optional[float] = None) -> Dict[str, Any]:
        """
        Run a backtest for a given symbol and date range
        
        Args:
            symbol: Trading pair symbol (e.g., 'XBT/USD')
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            initial_balance: Optional initial balance (overrides config)
            
        Returns:
            Dictionary containing backtest results
        """
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")
        
        try:
            # Override initial balance if provided
            if initial_balance is not None:
                self.config['backtest']['initial_balance'] = initial_balance
            
            # Load historical data
            logger.info("Loading historical data...")
            historical_data = await self.data_handler.load_historical_data(
                symbol, start_date, end_date
            )
            
            if not historical_data:
                raise ValueError(f"No historical data available for {symbol}")
            
            logger.info(f"Loaded {len(historical_data)} data points")
            
            # Run simulation
            logger.info("Running simulation...")
            trades, portfolio_history = await self.simulator.simulate(
                historical_data, symbol
            )
            
            # Analyze performance
            logger.info("Analyzing performance...")
            performance_metrics = self.analyzer.analyze(
                trades, portfolio_history, self.config['backtest']['initial_balance']
            )
            
            # Compile results
            results = {
                'symbol': symbol,
                'start_date': start_date,
                'end_date': end_date,
                'initial_balance': self.config['backtest']['initial_balance'],
                'final_balance': performance_metrics['final_balance'],
                'total_return': performance_metrics['total_return'],
                'total_return_percent': performance_metrics['total_return_percent'],
                'sharpe_ratio': performance_metrics['sharpe_ratio'],
                'max_drawdown': performance_metrics['max_drawdown'],
                'max_drawdown_percent': performance_metrics['max_drawdown_percent'],
                'total_trades': performance_metrics['total_trades'],
                'winning_trades': performance_metrics['winning_trades'],
                'losing_trades': performance_metrics['losing_trades'],
                'win_rate': performance_metrics['win_rate'],
                'profit_factor': performance_metrics['profit_factor'],
                'avg_trade_return': performance_metrics['avg_trade_return'],
                'total_commission_paid': performance_metrics['total_commission_paid'],
                'total_slippage_cost': performance_metrics['total_slippage_cost'],
                'trades': trades,
                'portfolio_history': portfolio_history
            }
            
            logger.info(f"Backtest completed. Return: {performance_metrics['total_return_percent']:.2f}%")
            return results
            
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            raise
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration"""
        return self.config.copy()

# Convenience function for easy backtesting
async def run_backtest(symbol: str, start_date: str, end_date: str, 
                      initial_balance: Optional[float] = None,
                      config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """
    Convenience function to run a backtest
    
    Args:
        symbol: Trading pair symbol (e.g., 'XBT/USD')
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        initial_balance: Optional initial balance
        config_path: Path to configuration file
        
    Returns:
        Dictionary containing backtest results
    """
    engine = BacktestEngine(config_path)
    return await engine.run_backtest(symbol, start_date, end_date, initial_balance)