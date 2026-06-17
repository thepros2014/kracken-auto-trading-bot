"""
Trading Engine Module
Core trading logic, strategy execution, and order management
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class TradingEngine:
    def __init__(self, kraken_client, config: Dict):
        self.kraken_client = kraken_client
        self.config = config
        self.is_running = False
        self.positions = {}
        self.orders = {}
        self.balance = {}
        self.strategies = {}
        self.risk_manager = None
        self.data_manager = None
        
        # Trading parameters
        self.default_pair = config.get('trading', {}).get('default_pair', 'XBT/USD')
        self.timeframe = config.get('trading', {}).get('timeframe', '1h')
        self.max_positions = config.get('trading', {}).get('max_positions', 5)
        self.position_size_percent = config.get('trading', {}).get('position_size_percent', 2.0)
        
        logger.info("Trading engine initialized")
    
    def set_risk_manager(self, risk_manager):
        """Set risk manager"""
        self.risk_manager = risk_manager
    
    def set_data_manager(self, data_manager):
        """Set data manager"""
        self.data_manager = data_manager
    
    def add_strategy(self, name: str, strategy):
        """Add a trading strategy"""
        self.strategies[name] = strategy
        logger.info(f"Strategy added: {name}")
    
    async def start(self):
        """Start the trading engine"""
        if self.is_running:
            logger.warning("Trading engine already running")
            return
        
        self.is_running = True
        logger.info("Starting trading engine...")
        
        # Start main trading loop
        asyncio.create_task(self._trading_loop())
        
        # Start position monitoring
        asyncio.create_task(self._monitor_positions())
        
        # Start order monitoring
        asyncio.create_task(self._monitor_orders())
    
    async def stop(self):
        """Stop the trading engine"""
        self.is_running = False
        logger.info("Stopping trading engine...")
        
        # Cancel all open orders
        await self._cancel_all_orders()
    
    async def _trading_loop(self):
        """Main trading loop"""
        while self.is_running:
            try:
                # Update market data
                await self._update_market_data()
                
                # Check risk limits
                if self.risk_manager:
                    if not await self.risk_manager.check_limits():
                        logger.warning("Risk limits exceeded, pausing trading")
                        await asyncio.sleep(60)
                        continue
                
                # Execute strategies
                for name, strategy in self.strategies.items():
                    try:
                        signals = await strategy.generate_signals()
                        await self._process_signals(name, signals)
                    except Exception as e:
                        logger.error(f"Error in strategy {name}: {e}")
                
                # Wait before next iteration
                await asyncio.sleep(30)  # 30 seconds between cycles
                
            except Exception as e:
                logger.error(f"Error in trading loop: {e}")
                await asyncio.sleep(10)
    
    async def _update_market_data(self):
        """Update market data for all tracked pairs"""
        # This would fetch latest OHLCV data and update indicators
        pass
    
    async def _process_signals(self, strategy_name: str, signals: Dict):
        """Process trading signals from strategies"""
        for symbol, signal in signals.items():
            if signal['action'] == 'BUY' and len(self.positions) < self.max_positions:
                await self._open_position(symbol, signal)
            elif signal['action'] == 'SELL' and symbol in self.positions:
                await self._close_position(symbol, signal)
    
    async def _open_position(self, symbol: str, signal: Dict):
        """Open a new position"""
        try:
            # Calculate position size
            balance = await self.kraken_client.fetch_balance()
            usd_balance = balance.get('USDT', {}).get('free', 0) or balance.get('USD', {}).get('free', 0)
            position_value = usd_balance * (self.position_size_percent / 100)
            
            # Get current price
            ticker = await self.kraken_client.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # Calculate amount
            amount = position_value / current_price
            
            # Apply precision
            precision = self.kraken_client.get_precision(symbol)
            amount = round(amount, precision['amount'])
            
            # Check risk limits
            if self.risk_manager and not await self.risk_manager.check_position_risk(symbol, amount, current_price):
                logger.warning(f"Position risk check failed for {symbol}")
                return
            
            # Create buy order
            order = await self.kraken_client.create_order(
                symbol=symbol,
                order_type='market',
                side='buy',
                amount=amount
            )
            
            # Store position
            self.positions[symbol] = {
                'amount': amount,
                'entry_price': current_price,
                'order_id': order['id'],
                'timestamp': datetime.now(),
                'strategy': signal.get('strategy', 'unknown'),
                'stop_loss': current_price * (1 - self.config.get('trading', {}).get('stop_loss_percent', 3.0) / 100),
                'take_profit': current_price * (1 + self.config.get('trading', {}).get('take_profit_percent', 6.0) / 100)
            }
            
            logger.info(f"Opened position: {symbol} {amount} @ {current_price}")
            
        except Exception as e:
            logger.error(f"Error opening position for {symbol}: {e}")
    
    async def _close_position(self, symbol: str, signal: Dict):
        """Close an existing position"""
        try:
            if symbol not in self.positions:
                return
            
            position = self.positions[symbol]
            
            # Create sell order
            order = await self.kraken_client.create_order(
                symbol=symbol,
                order_type='market',
                side='sell',
                amount=position['amount']
            )
            
            # Calculate P&L
            ticker = await self.kraken_client.fetch_ticker(symbol)
            current_price = ticker['last']
            pnl = (current_price - position['entry_price']) * position['amount']
            pnl_percent = (current_price / position['entry_price'] - 1) * 100
            
            # Remove position
            del self.positions[symbol]
            
            logger.info(f"Closed position: {symbol} {position['amount']} @ {current_price} (P&L: {pnl:.2f} USD, {pnl_percent:.2f}%)")
            
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
    
    async def _monitor_positions(self):
        """Monitor open positions for stop-loss/take-profit"""
        while self.is_running:
            try:
                for symbol, position in list(self.positions.items()):
                    ticker = await self.kraken_client.fetch_ticker(symbol)
                    current_price = ticker['last']
                    
                    # Check stop-loss
                    if current_price <= position['stop_loss']:
                        logger.info(f"Stop-loss triggered for {symbol} @ {current_price}")
                        await self._close_position(symbol, {'action': 'SELL', 'reason': 'stop_loss'})
                    
                    # Check take-profit
                    elif current_price >= position['take_profit']:
                        logger.info(f"Take-profit triggered for {symbol} @ {current_price}")
                        await self._close_position(symbol, {'action': 'SELL', 'reason': 'take_profit'})
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logger.error(f"Error monitoring positions: {e}")
                await asyncio.sleep(5)
    
    async def _monitor_orders(self):
        """Monitor order status"""
        while self.is_running:
            try:
                # Update order statuses
                for symbol in list(self.orders.keys()):
                    # Check if order is filled/cancelled
                    pass
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Error monitoring orders: {e}")
                await asyncio.sleep(5)
    
    async def _cancel_all_orders(self):
        """Cancel all open orders"""
        try:
            open_orders = await self.kraken_client.fetch_open_orders()
            for order in open_orders:
                await self.kraken_client.cancel_order(order['id'], order['symbol'])
            logger.info("All open orders cancelled")
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
    
    # Public API methods
    async def get_status(self) -> str:
        """Get bot status"""
        status = "🟢 *Running*" if self.is_running else "🔴 *Stopped*"
        pairs = list(self.positions.keys()) if self.positions else ["None"]
        
        return f"""
{status}

*Trading Pair:* {self.default_pair}
*Timeframe:* {self.timeframe}
*Open Positions:* {len(self.positions)}
*Active Strategies:* {len(self.strategies)}

*Positions:*
{chr(10).join([f"• {sym}: {pos['amount']:.6f} @ {pos['entry_price']:.2f}" for sym, pos in self.positions.items()])}
"""
    
    async def get_balance(self) -> str:
        """Get account balance"""
        try:
            balance = await self.kraken_client.fetch_balance()
            usd_balance = balance.get('USDT', {}).get('total', 0) or balance.get('USD', {}).get('total', 0)
            
            return f"""
💰 *Account Balance*

*Total:* ${usd_balance:.2f}
*Available:* ${balance.get('USDT', {}).get('free', 0) or balance.get('USD', {}).get('free', 0):.2f}

*Assets:*
{chr(10).join([f"• {asset}: {info.get('total', 0):.6f}" for asset, info in balance.items() if isinstance(info, dict) and info.get('total', 0) > 0])}
"""
        except Exception as e:
            return f"❌ Error fetching balance: {e}"
    
    async def get_positions(self) -> str:
        """Get open positions"""
        if not self.positions:
            return "📭 *No open positions*"
        
        positions_text = "📊 *Open Positions*\n\n"
        for symbol, position in self.positions.items():
            try:
                ticker = await self.kraken_client.fetch_ticker(symbol)
                current_price = ticker['last']
                pnl = (current_price - position['entry_price']) * position['amount']
                pnl_percent = (current_price / position['entry_price'] - 1) * 100
                
                positions_text += (
                    f"*{symbol}*\n"
                    f"Amount: {position['amount']:.6f}\n"
                    f"Entry: ${position['entry_price']:.2f}\n"
                    f"Current: ${current_price:.2f}\n"
                    f"P&L: ${pnl:.2f} ({pnl_percent:+.2f}%)\n"
                    f"SL: ${position['stop_loss']:.2f} | TP: ${position['take_profit']:.2f}\n\n"
                )
            except Exception as e:
                positions_text += f"*{symbol}*: Error fetching data ({e})\n\n"
        
        return positions_text
    
    async def execute_manual_trade(self, side: str, symbol: str, amount: float, price: float = None) -> str:
        """Execute a manual trade"""
        try:
            order_type = 'limit' if price else 'market'
            order = await self.kraken_client.create_order(
                symbol=symbol,
                order_type=order_type,
                side=side.lower(),
                amount=amount,
                price=price
            )
            
            return f"""
✅ *Trade Executed*

*Order ID:* {order['id']}
*Symbol:* {symbol}
*Side:* {side.upper()}
*Amount:* {amount}
*Type:* {order_type.upper()}
*Price:* {price or 'Market'}
*Status:* {order.get('status', 'unknown')}
"""
        except Exception as e:
            return f"❌ Error executing trade: {e}"
    
    def get_config(self) -> str:
        """Get current configuration"""
        return f"""
⚙️ *Current Configuration*

*Trading:*
• Default Pair: {self.default_pair}
• Timeframe: {self.timeframe}
• Max Positions: {self.max_positions}
• Position Size: {self.position_size_percent}%
• Stop Loss: {self.config.get('trading', {}).get('stop_loss_percent', 3.0)}%
• Take Profit: {self.config.get('trading', {}).get('take_profit_percent', 6.0)}%

*Risk Management:*
• Max Drawdown: {self.config.get('risk', {}).get('max_drawdown_percent', 20.0)}%
• Daily Loss Limit: {self.config.get('trading', {}).get('daily_loss_limit_percent', 10.0)}%

*ML Settings:*
• Model Type: {self.config.get('ml', {}).get('model_type', 'ppo')}
• Retrain Frequency: {self.config.get('ml', {}).get('retrain_frequency_hours', 24)}h
"""
    
    async def get_stats(self) -> str:
        """Get trading statistics"""
        # This would calculate actual stats from trade history
        return f"""
📈 *Trading Statistics*

*Total Trades:* 0
*Win Rate:* 0%
*Profit Factor:* 0.0
*Sharpe Ratio:* 0.0
*Max Drawdown:* 0%
*Total P&L:* $0.00

*Note:* Statistics will be available after trades are executed
"""