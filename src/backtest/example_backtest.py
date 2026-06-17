"""
Example Backtesting Script
Demonstrates how to use the backtesting engine
"""

import asyncio
import logging
import sys
import os

# Add the src directory to the path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from src.backtest.engine import run_backtest
except ImportError:
    # Fallback for when src is not in path
    from backtest.engine import run_backtest

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def main():
    """Example usage of the backtesting engine"""
    print("Kraken Trading Bot - Backtesting Example")
    print("=" * 50)
    
    # Example backtest parameters
    symbol = "XBT/USD"  # Bitcoin/USD
    start_date = "2023-01-01"
    end_date = "2023-12-31"
    initial_balance = 10000.0
    
    print(f"Running backtest for {symbol}")
    print(f"Period: {start_date} to {end_date}")
    print(f"Initial Balance: ${initial_balance:,.2f}")
    print()
    
    try:
        # Run the backtest
        results = await run_backtest(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date,
            initial_balance=initial_balance
        )
        
        # Display results
        print("BACKTEST RESULTS")
        print("=" * 50)
        print(f"Symbol: {results['symbol']}")
        print(f"Period: {results['start_date']} to {results['end_date']}")
        print(f"Initial Balance: ${results['initial_balance']:,.2f}")
        print(f"Final Balance:   ${results['final_balance']:,.2f}")
        print(f"Total Return:    ${results['total_return']:,.2f} ({results['total_return_percent']:.2f}%)")
        print()
        print("Performance Metrics:")
        print(f"  Sharpe Ratio:    {results['sharpe_ratio']:.2f}")
        print(f"  Max Drawdown:    {results['max_drawdown_percent']:.2f}%")
        print(f"  Total Trades:    {results['total_trades']}")
        print(f"  Win Rate:        {results['win_rate']:.2f}%")
        print(f"  Profit Factor:   {results['profit_factor']:.2f}")
        print()
        print("Costs:")
        print(f"  Total Commission: ${results['total_commission_paid']:.2f}")
        print(f"  Total Slippage:   ${results['total_slippage_cost']:.2f}")
        
        # Show first few trades if any
        if results['trades']:
            print()
            print("Sample Trades (first 3):")
            print("-" * 30)
            for i, trade in enumerate(results['trades'][:3]):
                print(f"Trade {i+1}: {trade['action']} {trade['amount']:.6f} {trade['symbol']} "
                      f"@ ${trade['execution_price']:.2f}")
                if trade['pnl'] != 0:
                    print(f"  P&L: ${trade['pnl']:.2f}")
        else:
            print()
            print("No trades were executed during the backtest period.")
            
    except Exception as e:
        print(f"Error running backtest: {e}")
        logging.exception("Backtest failed")

if __name__ == "__main__":
    asyncio.run(main())