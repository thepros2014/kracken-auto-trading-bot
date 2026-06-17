"""
Trade Simulator Module
Simulates trade execution with slippage and commission for backtesting
"""

import asyncio
import logging
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import pandas as pd

logger = logging.getLogger(__name__)

class BacktestSimulator:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the backtesting simulator
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.commission_percent = config.get('backtest', {}).get('commission_percent', 0.26)
        self.slippage_percent = config.get('backtest', {}).get('slippage_percent', 0.1)
        self.initial_balance = config.get('backtest', {}).get('initial_balance', 10000.0)
        self.max_trades_per_day = config.get('backtest', {}).get('max_trades_per_day', 100)
        
        logger.info("Backtesting simulator initialized")
    
    async def simulate(self, 
                      historical_data: List[List], 
                      symbol: str) -> Tuple[List[Dict], List[Dict]]:
        """
        Simulate trading on historical data
        
        Args:
            historical_data: List of OHLCV data [timestamp, open, high, low, close, volume]
            symbol: Trading pair symbol
            
        Returns:
            Tuple of (trades_list, portfolio_history_list)
        """
        logger.info(f"Starting simulation for {symbol} with {len(historical_data)} data points")
        
        if not historical_data:
            logger.warning("No historical data provided for simulation")
            return [], []
        
        # Initialize simulation state
        balance = self.initial_balance
        position = 0.0  # Current position size (positive = long, negative = short)
        entry_price = 0.0
        trades = []
        portfolio_history = []
        daily_trade_count = {}
        
        # Process each candle
        for i, candle in enumerate(historical_data):
            timestamp, open_price, high_price, low_price, close_price, volume = candle
            date_str = datetime.fromtimestamp(timestamp / 1000).strftime('%Y-%m-%d')
            
            # Update daily trade count
            if date_str not in daily_trade_count:
                daily_trade_count[date_str] = 0
            
            # Check max trades per day limit
            if daily_trade_count[date_str] >= self.max_trades_per_day:
                continue
            
            # Generate trading signal (simplified - in reality this would come from a strategy)
            signal = self._generate_signal(historical_data, i)
            
            # Execute trade based on signal
            if signal['action'] == 'BUY' and position <= 0:
                # Close any short position and go long
                if position < 0:
                    # Close short position
                    trade = self._execute_trade(
                        'SELL', symbol, abs(position), entry_price, 
                        close_price, timestamp, 'close_short'
                    )
                    if trade:
                        trades.append(trade)
                        balance += trade['pnl']
                        daily_trade_count[date_str] += 1
                
                # Open long position
                position_size = self._calculate_position_size(balance, close_price)
                if position_size > 0:
                    trade = self._execute_trade(
                        'BUY', symbol, position_size, close_price, 
                        close_price, timestamp, 'open_long'
                    )
                    if trade:
                        trades.append(trade)
                        position = position_size
                        entry_price = close_price
                        balance -= trade['commission']  # Deduct commission
                        daily_trade_count[date_str] += 1
            
            elif signal['action'] == 'SELL' and position >= 0:
                # Close any long position and go short
                if position > 0:
                    # Close long position
                    trade = self._execute_trade(
                        'SELL', symbol, position, entry_price, 
                        close_price, timestamp, 'close_long'
                    )
                    if trade:
                        trades.append(trade)
                        balance += trade['pnl'] - trade['commission']  # Add P&L, deduct commission
                        position = 0.0
                        entry_price = 0.0
                        daily_trade_count[date_str] += 1
                
                # Open short position
                position_size = self._calculate_position_size(balance, close_price)
                if position_size > 0:
                    trade = self._execute_trade(
                        'SELL', symbol, position_size, close_price, 
                        close_price, timestamp, 'open_short'
                    )
                    if trade:
                        trades.append(trade)
                        position = -position_size
                        entry_price = close_price
                        balance -= trade['commission']  # Deduct commission
                        daily_trade_count[date_str] += 1
            
            # Record portfolio state
            portfolio_value = self._calculate_portfolio_value(balance, position, close_price)
            portfolio_history.append({
                'timestamp': timestamp,
                'date': date_str,
                'balance': balance,
                'position': position,
                'position_value': position * close_price if position != 0 else 0,
                'portfolio_value': portfolio_value,
                'price': close_price
            })
        
        # Close any remaining position at the end
        if position != 0 and len(historical_data) > 0:
            last_candle = historical_data[-1]
            last_timestamp, _, _, _, last_close_price, _ = last_candle
            
            if position > 0:
                action = 'SELL'
                close_reason = 'end_of_backtest'
            else:
                action = 'BUY'
                close_reason = 'end_of_backtest'
            
            trade = self._execute_trade(
                action, symbol, abs(position), entry_price, 
                last_close_price, last_timestamp, close_reason
            )
            if trade:
                trades.append(trade)
                if position > 0:
                    balance += trade['pnl'] - trade['commission']
                else:
                    balance += abs(trade['pnl']) - trade['commission']
        
        logger.info(f"Simulation completed. Generated {len(trades)} trades")
        return trades, portfolio_history
    
    def _generate_signal(self, historical_data: List[List], index: int) -> Dict[str, Any]:
        """
        Generate a trading signal (simplified for demonstration)
        In a real implementation, this would use actual trading strategies
        
        Args:
            historical_data: Historical OHLCV data
            index: Current index in the data
            
        Returns:
            Dictionary with signal information
        """
        # Simple moving average crossover strategy for demonstration
        if index < 50:  # Need enough data for MA
            return {'action': 'HOLD'}
        
        # Calculate simple moving averages
        closes = [candle[4] for candle in historical_data[max(0, index-49):index+1]]
        if len(closes) < 50:
            return {'action': 'HOLD'}
        
        ma_10 = sum(closes[-10:]) / 10
        ma_30 = sum(closes[-30:]) / 30
        
        # Generate signal
        if ma_10 > ma_30 and len(closes) >= 2 and closes[-2] <= closes[-3]:  # Golden cross
            return {'action': 'BUY', 'strength': 'strong'}
        elif ma_10 < ma_30 and len(closes) >= 2 and closes[-2] >= closes[-3]:  # Death cross
            return {'action': 'SELL', 'strength': 'strong'}
        else:
            return {'action': 'HOLD'}
    
    def _calculate_position_size(self, balance: float, price: float) -> float:
        """
        Calculate position size based on risk management rules
        
        Args:
            balance: Current account balance
            price: Current asset price
            
        Returns:
            Position size in units of the asset
        """
        risk_percent = self.config.get('trading', {}).get('position_size_percent', 2.0)
        risk_amount = balance * (risk_percent / 100)
        position_size = risk_amount / price
        return position_size
    
    def _execute_trade(self, 
                      action: str, 
                      symbol: str, 
                      amount: float, 
                      intended_price: float,
                      execution_price: float,
                      timestamp: int,
                      trade_type: str) -> Optional[Dict[str, Any]]:
        """
        Execute a simulated trade with slippage and commission
        
        Args:
            action: 'BUY' or 'SELL'
            symbol: Trading pair symbol
            amount: Amount to trade
            intended_price: Intended execution price
            execution_price: Actual execution price (before slippage)
            timestamp: Trade timestamp
            trade_type: Type of trade (for logging)
            
        Returns:
            Dictionary with trade information or None if trade failed
        """
        try:
            # Apply slippage
            if action == 'BUY':
                # When buying, we pay slightly more
                slippage = execution_price * (self.slippage_percent / 100)
                actual_price = execution_price + slippage
            else:  # SELL
                # When selling, we receive slightly less
                slippage = execution_price * (self.slippage_percent / 100)
                actual_price = execution_price - slippage
            
            # Calculate trade value
            trade_value = amount * actual_price
            
            # Calculate commission
            commission = trade_value * (self.commission_percent / 100)
            
            # Calculate P&L (for closing trades)
            pnl = 0.0
            if trade_type in ['close_long', 'close_short']:
                # This would be calculated based on the original entry price
                # For simplicity, we'll estimate it here
                pass
            
            trade = {
                'id': f"{symbol}_{timestamp}_{trade_type}",
                'timestamp': timestamp,
                'symbol': symbol,
                'action': action,
                'amount': amount,
                'intended_price': intended_price,
                'execution_price': actual_price,
                'slippage': slippage,
                'trade_value': trade_value,
                'commission': commission,
                'pnl': pnl,  # Will be calculated when position is closed
                'trade_type': trade_type
            }
            
            return trade
            
        except Exception as e:
            logger.error(f"Error executing trade: {e}")
            return None
    
    def _calculate_portfolio_value(self, balance: float, position: float, price: float) -> float:
        """
        Calculate total portfolio value (cash + position value)
        
        Args:
            balance: Cash balance
            position: Position size (positive = long, negative = short)
            price: Current asset price
            
        Returns:
            Total portfolio value
        """
        position_value = position * price
        return balance + position_value