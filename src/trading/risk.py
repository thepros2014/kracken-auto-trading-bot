"""
Risk Management Module
Handles position sizing, stop-loss, take-profit, and risk limits
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, kraken_client, config: Dict):
        self.kraken_client = kraken_client
        self.config = config
        
        # Risk parameters
        self.max_drawdown_percent = config.get('risk', {}).get('max_drawdown_percent', 20.0)
        self.daily_loss_limit_percent = config.get('trading', {}).get('daily_loss_limit_percent', 10.0)
        self.max_position_size_percent = config.get('trading', {}).get('position_size_percent', 2.0)
        self.max_positions = config.get('trading', {}).get('max_positions', 5)
        self.volatility_adjustment = config.get('risk', {}).get('volatility_adjustment', True)
        
        # Tracking
        self.daily_pnl = 0.0
        self.max_equity = 0.0
        self.current_drawdown = 0.0
        self.last_reset_date = None
        
        logger.info("Risk manager initialized")
    
    async def check_limits(self) -> bool:
        """Check if trading should continue based on risk limits"""
        try:
            # Reset daily P&L if needed
            await self._reset_daily_if_needed()
            
            # Check daily loss limit
            if abs(self.daily_pnl) >= (self.max_equity * self.daily_loss_limit_percent / 100):
                logger.warning(f"Daily loss limit exceeded: {self.daily_pnl:.2f}")
                return False
            
            # Check max drawdown
            if self.current_drawdown >= self.max_drawdown_percent:
                logger.warning(f"Max drawdown exceeded: {self.current_drawdown:.2f}%")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking risk limits: {e}")
            return True  # Fail safe - allow trading if we can't check
    
    async def validate_trade(self, side: str, symbol: str, amount: float, price: float) -> bool:
        """Validate a proposed trade against risk parameters"""
        try:
            # Check position limits
            balance = await self.kraken_client.fetch_balance()
            usd_balance = balance.get('USDT', {}).get('total', 0) or balance.get('USD', {}).get('total', 0)
            
            # Calculate position value
            position_value = amount * price
            position_percent = (position_value / usd_balance) * 100 if usd_balance > 0 else 0
            
            if position_percent > self.max_position_size_percent:
                logger.warning(f"Position size too large: {position_percent:.2f}% > {self.max_position_size_percent}%")
                return False
            
            # Check volatility adjustment
            if self.volatility_adjustment:
                volatility_factor = await self._get_volatility_factor(symbol)
                adjusted_size = position_percent * volatility_factor
                if adjusted_size > self.max_position_size_percent:
                    logger.warning(f"Adjusted position size too large: {adjusted_size:.2f}%")
                    return False
            
            # Check correlation risk
            if not await self._check_correlation_risk(symbol, amount, price):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return True  # Fail safe
    
    async def check_position_risk(self, symbol: str, amount: float, price: float) -> bool:
        """Check risk for an existing or proposed position"""
        return await self.validate_trade('BUY', symbol, amount, price)
    
    async def _reset_daily_if_needed(self):
        """Reset daily P&L tracking if it's a new day"""
        from datetime import date
        today = date.today()
        
        if self.last_reset_date != today:
            self.daily_pnl = 0.0
            self.last_reset_date = today
            logger.info("Daily P&L reset")
    
    async def _get_volatility_factor(self, symbol: str) -> float:
        """Get volatility adjustment factor for a symbol"""
        try:
            # Fetch recent OHLCV data
            ohlcv = await self.kraken_client.fetch_ohlcv(symbol, '1h', 24)
            if len(ohlcv) < 10:
                return 1.0
            
            # Calculate volatility (standard deviation of returns)
            df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['returns'] = df['close'].pct_change()
            volatility = df['returns'].std()
            
            # Normalize volatility (lower volatility = higher factor)
            # Typical crypto daily volatility is around 2-5%
            if volatility > 0.05:  # High volatility
                return 0.5
            elif volatility > 0.02:  # Medium volatility
                return 0.75
            else:  # Low volatility
                return 1.0
                
        except Exception as e:
            logger.error(f"Error calculating volatility for {symbol}: {e}")
            return 1.0  # Neutral factor
    
    async def _check_correlation_risk(self, symbol: str, amount: float, price: float) -> bool:
        """Check if adding this position would create too much correlation risk"""
        try:
            # For simplicity, we'll just check if we already have too many positions
            # A more sophisticated implementation would check actual correlation
            open_orders = await self.kraken_client.fetch_open_orders()
            current_positions = len(open_orders)
            
            if current_positions >= self.max_positions:
                logger.warning(f"Max positions reached: {current_positions}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking correlation risk: {e}")
            return True  # Fail safe
    
    def update_pnl(self, pnl: float):
        """Update P&L tracking"""
        self.daily_pnl += pnl
        # Update max equity for drawdown calculation
        # This would be more sophisticated in a real implementation
    
    def get_risk_metrics(self) -> Dict[str, float]:
        """Get current risk metrics"""
        return {
            'daily_pnl': self.daily_pnl,
            'current_drawdown': self.current_drawdown,
            'max_drawdown_limit': self.max_drawdown_percent,
            'daily_loss_limit': self.daily_loss_limit_percent
        }

# Position sizing calculators
class PositionSizer:
    @staticmethod
    def fixed_fractional(equity: float, risk_percent: float, stop_loss_percent: float) -> float:
        """Calculate position size using fixed fractional method"""
        risk_amount = equity * (risk_percent / 100)
        position_size = risk_amount / (stop_loss_percent / 100)
        return position_size
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate optimal fraction using Kelly criterion"""
        if avg_loss == 0:
            return 0
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        return max(0, min(kelly_fraction, 0.25))  # Cap at 25% for safety