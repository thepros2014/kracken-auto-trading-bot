# 🚀 Live Trading Starter Script - Kraken Trading Bot
# 
# This script initializes and starts the Kraken Trading Bot in live trading mode
# 
# USAGE:
#   python live_trading/start_live_trading.py
#   python live_trading/start_live_trading.py --test-connection  # Test API connection only
#   python live_trading/start_live_trading.py --help            # Show help

import asyncio
import logging
import os
import sys
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add the src directory to the path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Load environment variables from .env file
load_dotenv()

# Import bot components
try:
    from telegram.bot import TradingBot
    from trading.engine import TradingEngine
    from data.manager import DataManager
    from kraken.client import KrakenClient
    import yaml
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("💡 Make sure you're running this from the project directory")
    print("💡 Install dependencies with: pip install -r live_trading/requirements_live.txt")
    sys.exit(1)

def setup_logging():
    """Configure logging for live trading"""
    # Create logs directory if it doesn't exist
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_dir / "live_trading.log"),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Reduce noise from some libraries
    logging.getLogger("ccxt").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)

def load_configuration():
    """Load and validate configuration"""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    
    if not config_path.exists():
        print(f"❌ Configuration file not found: {config_path}")
        print("💡 Copy live_trading/config_template.yaml to config/config.yaml and edit it")
        sys.exit(1)
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        print(f"❌ Error loading configuration: {e}")
        sys.exit(1)

def validate_api_keys(config):
    """Validate that API keys are present and properly configured"""
    api_key = config.get('kraken', {}).get('api_key', '')
    api_secret = config.get('kraken', {}).get('api_secret', '')
    sandbox = config.get('kraken', {}).get('sandbox', True)
    
    # Check for environment variable overrides
    if not api_key or api_key.startswith("${") or "YOUR_" in api_key:
        api_key = os.getenv('KRAKEN_API_KEY', '')
    if not api_secret or api_secret.startswith("${") or "YOUR_" in api_secret:
        api_secret = os.getenv('KRAKEN_API_SECRET', '')
    
    if not api_key or not api_secret:
        print("❌ Kraken API keys not found or not properly configured!")
        print("💡 Set KRAKEN_API_KEY and KRAKEN_API_SECRET environment variables")
        print("💡 Or edit config/config.yaml with your actual keys")
        print("🔐 Get API keys from: https://www.kraken.com/features/api")
        return False, None, None
    
    if sandbox:
        print("⚠️  WARNING: Sandbox mode is enabled!")
        print("💡 For live trading, set 'sandbox: false' in config/config.yaml")
        print("💡 Or set KRAKEN_SANDBOX=false in your environment")
        response = input("Do you want to continue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(0)
    
    return True, api_key, api_secret

async def test_kraken_connection(kraken_client):
    """Test connection to Kraken exchange"""
    print("🔗 Testing connection to Kraken exchange...")
    try:
        # Test basic connectivity
        server_time = await kraken_client.get_server_time()
        print(f"✅ Connected to Kraken! Server time: {server_time}")
        
        # Test account access (balance)
        balance = await kraken_client.get_balance()
        total_currencies = len([k for k, v in balance.items() if float(v) > 0])
        print(f"💰 Account access verified! Found {total_currencies} currencies with balance")
        
        # Show non-zero balances
        if total_currencies > 0:
            print("💰 Non-zero balances:")
            for currency, amount in balance.items():
                if float(amount) > 0:
                    print(f"   {currency}: {amount}")
        
        return True
    except Exception as e:
        print(f"❌ Failed to connect to Kraken: {e}")
        print("💡 Check your API keys, internet connection, and Kraken status")
        return False

async def main():
    """Main function to start the live trading bot"""
    parser = argparse.ArgumentParser(description="Kraken Trading Bot - Live Trading Starter")
    parser.add_argument("--test-connection", action="store_true", 
                       help="Test Kraken connection and exit")
    parser.add_argument("--skip-telegram", action="store_true",
                       help="Start without Telegram bot (for debugging)")
    args = parser.parse_args()
    
    # Setup logging
    setup_logging()
    logger = logging.getLogger(__name__)
    
    print("🚀 Kraken Trading Bot - Live Trading Starter")
    print("=" * 50)
    
    # Load configuration
    config = load_configuration()
    print("📋 Configuration loaded successfully")
    
    # Validate API keys
    keys_valid, api_key, api_secret = validate_api_keys(config)
    if not keys_valid:
        sys.exit(1)
    
    print("🔐 API keys validated")
    
    # Show important warnings
    print("\n⚠️  IMPORTANT WARNINGS:")
    print("   • You are about to start LIVE TRADING with REAL MONEY")
    print("   • Losses are possible and you could lose your entire investment")
    print("   • Start with small amounts you can afford to lose")
    print("   • Consider testing with backtesting first")
    print("   • Never leave the bot unattended for extended periods initially")
    
    if args.test_connection:
        print("\n🔧 Connection test mode - will not start trading")
    else:
        confirm = input("\n❓ Do you want to continue and start live trading? (yes/NO): ")
        if confirm.lower() != 'yes':
            print("🛑 Live trading startup cancelled by user")
            sys.exit(0)
    
    # Initialize Kraken client for LIVE trading
    print("\n🔌 Initializing Kraken client...")
    try:
        kraken_client = KrakenClient(
            api_key=api_key,
            api_secret=api_secret,
            sandbox=config.get('kraken', {}).get('sandbox', False)
        )
        logger.info("Kraken client initialized")
    except Exception as e:
        logger.error(f"Failed to initialize Kraken client: {e}")
        print(f"❌ Failed to initialize Kraken client: {e}")
        sys.exit(1)
    
    # Test connection if requested
    if args.test_connection:
        success = await test_kraken_connection(kraken_client)
        if success:
            print("\n✅ Connection test PASSED")
            print("💡 Your API keys and connection are working correctly")
        else:
            print("\n❌ Connection test FAILED")
            print("💡 Fix the issues above before attempting live trading")
        return
    
    # Test connection before starting
    print("\n🔗 Testing Kraken connection before startup...")
    connection_ok = await test_kraken_connection(kraken_client)
    if not connection_ok:
        print("\n❌ Cannot start live trading due to connection issues")
        print("💡 Fix connection problems before attempting to start the bot")
        sys.exit(1)
    
    # Initialize data manager
    print("\n📊 Initializing data manager...")
    try:
        data_manager = DataManager(kraken_client, config)
        logger.info("Data manager initialized")
    except Exception as e:
        logger.error(f"Failed to initialize data manager: {e}")
        print(f"❌ Failed to initialize data manager: {e}")
        sys.exit(1)
    
    # Initialize trading engine
    print("⚙️  Initializing trading engine...")
    try:
        trading_engine = TradingEngine(config, data_manager, kraken_client)
        logger.info("Trading engine initialized")
    except Exception as e:
        logger.error(f"Failed to initialize trading engine: {e}")
        print(f"❌ Failed to initialize trading engine: {e}")
        sys.exit(1)
    
    # Initialize Telegram bot (optional)
    telegram_bot = None
    if not args.skip_telegram:
        telegram_token = os.getenv('TELEGRAM_BOT_TOKEN')
        if telegram_token and telegram_token != "YOUR_TELEGRAM_BOT_TOKEN_HERE":
            try:
                admin_users_str = os.getenv('TELEGRAM_ADMIN_USERS', '')
                admin_users = [int(uid.strip()) for uid in admin_users_str.split(',') if uid.strip()]
                
                print("💬 Initializing Telegram bot...")
                telegram_bot = TradingBot(
                    token=telegram_token,
                    admin_users=admin_users
                )
                telegram_bot.set_trading_engine(trading_engine)
                await telegram_bot.initialize()
                await telegram_bot.start_polling()
                logger.info("Telegram bot started and linked to trading engine")
                print("💬 Telegram bot started - use Telegram to monitor and control")
            except Exception as e:
                logger.warning(f"Failed to initialize Telegram bot: {e}")
                print(f"⚠️  Telegram bot initialization failed: {e}")
                print("💡 Continuing without Telegram notifications")
        else:
            print("💬 Telegram bot not configured (optional)")
            print("💡 Set TELEGRAM_BOT_TOKEN and TELEGRAM_ADMIN_USERS in .env for notifications")
    else:
        print("💬 Telegram bot skipped (--skip-telegram flag used)")
    
    # Start the trading engine
    print("\n⚡ Starting trading engine...")
    try:
        await trading_engine.start()
        logger.info("Trading engine started successfully")
        print("✅ Live trading bot is now RUNNING")
        
        # Show startup summary
        print("\n📊 STARTUP SUMMARY:")
        print(f"   Trading Pair: {config.get('trading', {}).get('default_pair', 'XBT/USD')}")
        print(f"   Timeframe: {config.get('trading', {}).get('timeframe', '1h')}")
        print(f"   Position Size: {config.get('trading', {}).get('position_size_percent', 5.0)}% per trade")
        print(f"   Max Positions: {config.get('trading', {}).get('max_positions', 3)}")
        print(f"   Stop Loss: {config.get('trading', {}).get('stop_loss_percent', 3.0)}%")
        print(f"   Take Profit: {config.get('trading', {}).get('take_profit_percent', 6.0)}%")
        print(f"   Daily Loss Limit: {config.get('risk', {}).get('max_daily_loss_percent', 10.0)}%")
        print(f"   Telegram: {'Enabled' if telegram_bot else 'Disabled'}")
        print(f"   Logs: Check logs/ directory for detailed output")
        
        print("\n💡 NEXT STEPS:")
        print("   • Monitor performance via Telegram or logs")
        print("   • Check logs/ directory for detailed output")
        print("   • Use Telegram commands: /status, /balance, /positions, /stats")
        print("   • Use /stop to halt trading if needed")
        print("   • Review performance regularly and adjust as needed")
        print("   • START SMALL and increase only as confidence builds")
        
        print("\n🔴 LIVE TRADING IS NOW ACTIVE")
        print("   Press Ctrl+C to initiate graceful shutdown")
        print("   Or use /stop command via Telegram")
        
        # Keep the bot running until interrupted
        try:
            while True:
                await asyncio.sleep(30)  # Check every 30 seconds
                # Optional: Add periodic health checks here
                
        except KeyboardInterrupt:
            print("\n🛑 Received shutdown signal (Ctrl+C)...")
            logger.info("Received shutdown signal from user")
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            print(f"\n❌ Unexpected error: {e}")
        finally:
            # Graceful shutdown
            print("\n🔄 Shutting down gracefully...")
            logger.info("Starting graceful shutdown...")
            
            try:
                await trading_engine.stop()
                logger.info("Trading engine stopped")
            except Exception as e:
                logger.error(f"Error stopping trading engine: {e}")
            
            if telegram_bot:
                try:
                    await telegram_bot.stop()
                    logger.info("Telegram bot stopped")
                except Exception as e:
                    logger.error(f"Error stopping Telegram bot: {e}")
            
            print("✅ Live trading bot stopped successfully")
            logger.info("Live trading bot shutdown complete")
    
    except Exception as e:
        logger.error(f"Failed to start live trading bot: {e}")
        print(f"❌ Failed to start live trading bot: {e}")
        print("💡 Check the logs/ directory for detailed error information")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Startup cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Fatal error during startup: {e}")
        sys.exit(1)