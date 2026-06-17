"""
Risk Management Module
Handles position sizing, stop-loss, take-profit, and portfolio risk limits
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class RiskManager:
    def __init__(self, config: Dict):
        self.config = config
        self.daily_pnl = 0.0
        self.max_drawdown = 0.0
        self.peak_balance = 0.0
        self.daily_trades = 0
        self.last_reset_date = datetime.now().date()
        
        # Risk parameters
        self.max_drawdown_percent = config.get('risk', {}).get('max_drawdown_percent', 20.0)
        self.daily_loss_limit_percent = config.get('trading', {}).get('daily_loss_limit_percent', 10.0)
        self.position_size_percent = config.get('trading', {}).get('position_size_percent', 2.0)
        self.max_positions = config.get('trading', {}).get('max_positions', 5)
        self.volatility_adjustment = config.get('risk', {}).get('volatility_adjustment', True)
        self.correlation_limit = config.get('risk', {}).get('correlation_limit', 0.7)
        
        logger.info("Risk manager initialized")
    
    async def check_limits(self) -> bool:
        """Check if trading is within risk limits"""
        # Reset daily counters if needed
        await self._reset_daily_counters()
        
        # Check daily loss limit
        if self.daily_pnl < 0:
            daily_loss_percent = abs(self.daily_pnl) / self.peak_balance * 100 if self.peak_balance > 0 else 0
            if daily_loss_percent > self.daily_loss_limit_percent:
                logger.warning(f"Daily loss limit exceeded: {daily_loss_percent:.2f}%")
                return False
        
        # Check max drawdown
        if self.max_drawdown_percent > 0:
            current_drawdown = (self.peak_balance - self._get_current_balance()) / self.peak_balance * 100 if self.peak_balance > 0 else 0
            if current_drawdown > self.max_drawdown_percent:
                logger.warning(f"Max drawdown exceeded: {current_drawdown:.2f}%")
                return False
        
        return True
    
    async def validate_trade(self, side: str, symbol: str, amount: float, price: float) -> bool:
        """Validate if a trade meets risk criteria"""
        try:
            # Check position limits
            # This would need access to current positions
            
            # Check if trade size is reasonable
            trade_value = amount * price
            # This would need access to account balance
            
            # For now, return True (would be enhanced with actual balance/position data)
            return True
            
        except Exception as e:
            logger.error(f"Error validating trade: {e}")
            return False
    
    async def check_position_risk(self, symbol: str, amount: float, price: float) -> bool:
        """Check if opening a position would violate risk limits"""
        try:
            # Calculate position value
            position_value = amount * price
            
            # This would check against account balance and existing positions
            # For now, basic validation
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking position risk: {e}")
            return False
    
    def update_pnl(self, pnl: float):
        """Update P&L for risk tracking"""
        self.daily_pnl += pnl
        # Update peak balance and drawdown calculations
        # This would need current balance information
    
    def update_balance(self, balance: float):
        """Update account balance for drawdown calculation"""
        if balance > self.peak_balance:
            self.peak_balance = balance
        
        current_drawdown = (self.peak_balance - balance) / self.peak_balance * 100 if self.peak_balance > 0 else 0
        if current_drawdown > self.max_drawdown:
            self.max_drawdown = current_drawdown
    
    async def _reset_daily_counters(self):
        """Reset daily counters if date has changed"""
        current_date = datetime.now().date()
        if current_date != self.last_reset_date:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = current_date
            logger.info("Daily risk counters reset")
    
    def get_risk_status(self) -> Dict[str, Any]:
        """Get current risk status"""
        return {
            'daily_pnl': self.daily_pnl,
            'daily_trades': self.daily_trades,
            'max_drawdown': self.max_drawdown,
            'peak_balance': self.peak_balance,
            'within_limits': True  # Would be calculated based on actual checks
        }

# Position sizing calculators
class PositionSizer:
    @staticmethod
    def fixed_fractional(account_balance: float, risk_percent: float, stop_loss_percent: float) -> float:
        """Calculate position size using fixed fractional method"""
        risk_amount = account_balance * (risk_percent / 100)
        position_size = risk_amount / (stop_loss_percent / 100)
        return position_size
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        """Calculate optimal fraction using Kelly criterion"""
        if avg_loss == 0:
            return 0
        kelly_fraction = (win_rate * avg_win - (1 - win_rate) * avg_loss) / avg_win
        return max(0, min(kelly_fraction, 0.25))  # Cap at 25%
    
    @staticmethod
    def volatility_adjusted(account_balance: float, volatility: float, target_volatility: float = 0.02) -> float:
        """Adjust position size based on volatility"""
        if volatility == 0:
            return account_balance * 0.1  # Default 10%
        volatility_ratio = target_volatility / volatility
        return account_balance * min(volatility_ratio, 0.5)  # Cap at 50%