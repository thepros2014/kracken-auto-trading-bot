"""
Telegram Bot Module
Handles bot commands, notifications, and user interactions
"""
import logging
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import asyncio

logger = logging.getLogger(__name__)

class TradingBot:
    def __init__(self, token: str, admin_users: List[int] = None):
        self.token = token
        self.admin_users = admin_users or []
        self.application = None
        self.trading_engine = None
        self.notification_queue = asyncio.Queue()
        
    async def initialize(self):
        """Initialize the Telegram bot application"""
        self.application = Application.builder().token(self.token).build()
        self._register_handlers()
        await self.application.initialize()
        logger.info("Telegram bot initialized")
    
    def _register_handlers(self):
        """Register command and callback handlers"""
        # Command handlers
        self.application.add_handler(CommandHandler("start", self.cmd_start))
        self.application.add_handler(CommandHandler("help", self.cmd_help))
        self.application.add_handler(CommandHandler("status", self.cmd_status))
        self.application.add_handler(CommandHandler("balance", self.cmd_balance))
        self.application.add_handler(CommandHandler("positions", self.cmd_positions))
        self.application.add_handler(CommandHandler("trade", self.cmd_trade))
        self.application.add_handler(CommandHandler("stop", self.cmd_stop))
        self.application.add_handler(CommandHandler("config", self.cmd_config))
        self.application.add_handler(CommandHandler("stats", self.cmd_stats))
        
        # Callback query handler for inline keyboards
        self.application.add_handler(CallbackQueryHandler(self.handle_callback))
    
    def set_trading_engine(self, engine):
        """Set reference to trading engine"""
        self.trading_engine = engine
    
    # Command handlers
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        keyboard = [
            [InlineKeyboardButton("📊 Status", callback_data="status"),
             InlineKeyboardButton("💰 Balance", callback_data="balance")],
            [InlineKeyboardButton("📈 Positions", callback_data="positions"),
             InlineKeyboardButton("⚙️ Config", callback_data="config")],
            [InlineKeyboardButton("📊 Stats", callback_data="stats"),
             InlineKeyboardButton("🛑 Stop Bot", callback_data="stop_bot")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🤖 *Kraken Trading Bot*\n\nWelcome! Use the buttons below to control the bot.",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
🤖 *Kraken Trading Bot - Help*

*Commands:*
/start - Show main menu
/help - Show this help message
/status - Show bot status
/balance - Show account balance
/positions - Show open positions
/trade - Manual trade execution
/stop - Stop the bot
/config - Show current configuration
/stats - Show trading statistics

*Admin Commands:*
/reload - Reload configuration
/logs - Show recent logs
"""
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            status = self.trading_engine.get_status()
            await update.message.reply_text(status, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_balance(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /balance command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            balance = await self.trading_engine.get_balance()
            await update.message.reply_text(balance, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_positions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /positions command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            positions = await self.trading_engine.get_positions()
            await update.message.reply_text(positions, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_trade(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /trade command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        # Parse arguments: /trade BUY XBT/USD 0.01
        args = context.args
        if len(args) < 3:
            await update.message.reply_text(
                "Usage: /trade <BUY|SELL> <SYMBOL> <AMOUNT> [PRICE]\n"
                "Example: /trade BUY XBT/USD 0.01"
            )
            return
        
        side = args[0].upper()
        symbol = args[1].upper()
        amount = float(args[2])
        price = float(args[3]) if len(args) > 3 else None
        
        if self.trading_engine:
            result = await self.trading_engine.execute_manual_trade(side, symbol, amount, price)
            await update.message.reply_text(result, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_stop(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stop command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            await self.trading_engine.stop()
            await update.message.reply_text("🛑 Bot stopped")
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /config command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            config = self.trading_engine.get_config()
            await update.message.reply_text(config, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        if not self._is_authorized(update.effective_user.id):
            await update.message.reply_text("❌ Unauthorized access")
            return
        
        if self.trading_engine:
            stats = self.trading_engine.get_stats()
            await update.message.reply_text(stats, parse_mode='Markdown')
        else:
            await update.message.reply_text("⚠️ Trading engine not initialized")
    
    # Callback handler
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks"""
        query = update.callback_query
        await query.answer()
        
        if not self._is_authorized(query.from_user.id):
            await query.edit_message_text("❌ Unauthorized access")
            return
        
        data = query.data
        
        if data == "status":
            if self.trading_engine:
                status = self.trading_engine.get_status()
                await query.edit_message_text(status, parse_mode='Markdown')
        elif data == "balance":
            if self.trading_engine:
                balance = await self.trading_engine.get_balance()
                await query.edit_message_text(balance, parse_mode='Markdown')
        elif data == "positions":
            if self.trading_engine:
                positions = await self.trading_engine.get_positions()
                await query.edit_message_text(positions, parse_mode='Markdown')
        elif data == "config":
            if self.trading_engine:
                config = self.trading_engine.get_config()
                await query.edit_message_text(config, parse_mode='Markdown')
        elif data == "stats":
            if self.trading_engine:
                stats = self.trading_engine.get_stats()
                await query.edit_message_text(stats, parse_mode='Markdown')
        elif data == "stop_bot":
            if self.trading_engine:
                await self.trading_engine.stop()
                await query.edit_message_text("🛑 Bot stopped")
    
    def _is_authorized(self, user_id: int) -> bool:
        """Check if user is authorized"""
        return len(self.admin_users) == 0 or user_id in self.admin_users
    
    # Notification methods
    async def send_notification(self, message: str, parse_mode: str = 'Markdown'):
        """Send notification to all admin users"""
        for user_id in self.admin_users:
            try:
                await self.application.bot.send_message(
                    chat_id=user_id,
                    text=message,
                    parse_mode=parse_mode
                )
            except Exception as e:
                logger.error(f"Failed to send notification to {user_id}: {e}")
    
    async def send_trade_notification(self, trade_info: Dict):
        """Send trade execution notification"""
        message = (
            f"🔔 *Trade Executed*\n\n"
            f"Side: {trade_info['side']}\n"
            f"Symbol: {trade_info['symbol']}\n"
            f"Amount: {trade_info['amount']}\n"
            f"Price: {trade_info.get('price', 'Market')}\n"
            f"Order ID: {trade_info.get('order_id', 'N/A')}"
        )
        await self.send_notification(message)
    
    async def send_error_notification(self, error: str):
        """Send error notification"""
        message = f"⚠️ *Error*\n\n{error}"
        await self.send_notification(message)
    
    async def start_polling(self):
        """Start bot polling"""
        await self.application.start()
        await self.application.updater.start_polling()
        logger.info("Telegram bot started polling")
    
    async def stop(self):
        """Stop the bot"""
        await self.application.updater.stop()
        await self.application.stop()
        logger.info("Telegram bot stopped")