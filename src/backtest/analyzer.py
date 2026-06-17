"""
Performance Analyzer Module
Analyzes backtest performance and calculates metrics
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

class PerformanceAnalyzer:
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the performance analyzer
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.risk_free_rate = 0.02  # 2% annual risk-free rate
        
        logger.info("Performance analyzer initialized")
    
    def analyze(self, 
               trades: List[Dict], 
               portfolio_history: List[Dict],
               initial_balance: float) -> Dict[str, Any]:
        """
        Analyze backtest performance and calculate metrics
        
        Args:
            trades: List of executed trades
            portfolio_history: List of portfolio snapshots over time
            initial_balance: Initial account balance
            
        Returns:
            Dictionary containing performance metrics
        """
        logger.info(f"Analyzing performance of {len(trades)} trades")
        
        if not trades or not portfolio_history:
            return self._get_empty_metrics(initial_balance)
        
        try:
            # Convert portfolio history to DataFrame for easier analysis
            df = pd.DataFrame(portfolio_history)
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            # Calculate returns
            df['returns'] = df['portfolio_value'].pct_change()
            df['returns'] = df['returns'].fillna(0)
            
            # Calculate cumulative returns
            df['cumulative_returns'] = (1 + df['returns']).cumprod() - 1
            
            # Calculate final balance
            final_balance = df['portfolio_value'].iloc[-1] if len(df) > 0 else initial_balance
            
            # Calculate total return
            total_return = final_balance - initial_balance
            total_return_percent = (total_return / initial_balance) * 100 if initial_balance > 0 else 0
            
            # Calculate Sharpe ratio (annualized)
            if df['returns'].std() > 0:
                excess_returns = df['returns'] - (self.risk_free_rate / 365)  # Daily risk-free rate
                sharpe_ratio = np.sqrt(365) * excess_returns.mean() / excess_returns.std()
            else:
                sharpe_ratio = 0.0
            
            # Calculate maximum drawdown
            rolling_max = df['portfolio_value'].expanding().max()
            drawdown = (df['portfolio_value'] - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            max_drawdown_percent = max_drawdown * 100
            
            # Calculate trade statistics
            winning_trades = [t for t in trades if t.get('pnl', 0) > 0]
            losing_trades = [t for t in trades if t.get('pnl', 0) < 0]
            
            total_trades = len(trades)
            win_count = len(winning_trades)
            loss_count = len(losing_trades)
            win_rate = (win_count / total_trades) * 100 if total_trades > 0 else 0
            
            # Calculate profit factor
            gross_profit = sum(t.get('pnl', 0) for t in winning_trades)
            gross_loss = abs(sum(t.get('pnl', 0) for t in losing_trades))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf') if gross_profit > 0 else 0
            
            # Calculate average trade return
            avg_trade_return = np.mean([t.get('pnl', 0) for t in trades]) if trades else 0
            
            # Calculate total costs
            total_commission_paid = sum(t.get('commission', 0) for t in trades)
            total_slippage_cost = sum(abs(t.get('slippage', 0) * t.get('amount', 0)) for t in trades)
            
            # Calculate trade duration statistics (if we have entry/exit times)
            trade_durations = []
            # This would require tracking entry and exit times for each trade
            
            metrics = {
                'final_balance': final_balance,
                'total_return': total_return,
                'total_return_percent': total_return_percent,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'max_drawdown_percent': max_drawdown_percent,
                'total_trades': total_trades,
                'winning_trades': win_count,
                'losing_trades': loss_count,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'avg_trade_return': avg_trade_return,
                'total_commission_paid': total_commission_paid,
                'total_slippage_cost': total_slippage_cost,
                'gross_profit': gross_profit,
                'gross_loss': gross_loss
            }
            
            logger.info(f"Performance analysis complete. Return: {total_return_percent:.2f}%, Sharpe: {sharpe_ratio:.2f}")
            return metrics
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {e}")
            return self._get_empty_metrics(initial_balance)
    
    def _get_empty_metrics(self, initial_balance: float) -> Dict[str, Any]:
        """Return empty/default metrics when analysis fails"""
        return {
            'final_balance': initial_balance,
            'total_return': 0.0,
            'total_return_percent': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown': 0.0,
            'max_drawdown_percent': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'avg_trade_return': 0.0,
            'total_commission_paid': 0.0,
            'total_slippage_cost': 0.0,
            'gross_profit': 0.0,
            'gross_loss': 0.0
        }
    
    def generate_report(self, metrics: Dict[str, Any]) -> str:
        """
        Generate a formatted performance report
        
        Args:
            metrics: Performance metrics dictionary
            
        Returns:
            Formatted report string
        """
        report = f"""
BACKTESTING PERFORMANCE REPORT
{'='*50}

Initial Balance: ${metrics.get('initial_balance', 0):,.2f}
Final Balance:   ${metrics.get('final_balance', 0):,.2f}
Total Return:    ${metrics.get('total_return', 0):,.2f} ({metrics.get('total_return_percent', 0):.2f}%)

RISK METRICS
{'-'*30}
Sharpe Ratio:    {metrics.get('sharpe_ratio', 0):.2f}
Max Drawdown:    {metrics.get('max_drawdown_percent', 0):.2f}%

TRADE STATISTICS
{'-'*30}
Total Trades:    {metrics.get('total_trades', 0)}
Winning Trades:  {metrics.get('winning_trades', 0)}
Losing Trades:   {metrics.get('losing_trades', 0)}
Win Rate:        {metrics.get('win_rate', 0):.2f}%
Profit Factor:   {metrics.get('profit_factor', 0):.2f}

AVG TRADE RETURN: ${metrics.get('avg_trade_return', 0):.2f}

COSTS
{'-'*30}
Total Commission: ${metrics.get('total_commission_paid', 0):.2f}
Total Slippage:   ${metrics.get('total_slippage_cost', 0):.2f}
"""
        return report.strip()