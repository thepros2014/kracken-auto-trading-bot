# Kraken Telegram Trading Bot

An automated trading bot for Kraken.com with Telegram integration and self-learning machine learning capabilities.

## Features

- **Kraken API Integration**: Real-time market data, order execution, portfolio management
- **Telegram Bot Interface**: Commands, notifications, inline keyboards for control
- **Machine Learning**: Self-learning models that improve from trade outcomes
- **Risk Management**: Position sizing, stop-loss, take-profit, daily limits
- **Multi-pair Support**: Configurable strategies per trading pair
- **Backtesting**: Validate strategies before live deployment
- **Docker Ready**: Easy deployment with containerization

## Project Structure

```
kracken-bot/
├── config/
│   ├── config.yaml
│   └── secrets.yaml.example
├── src/
│   ├── kraken/          # API client, websocket, auth
│   ├── telegram/        # Bot handlers, commands, notifications
│   ├── trading/         # Strategy engine, risk manager, order executor
│   ├── ml/              # Models, features, training, inference
│   ├── data/            # Data fetching, storage, preprocessing
│   ├── backtest/        # Backtesting engine
│   └── utils/           # Config, logging, helpers
├── tests/
├── docker/
├── requirements.txt
└── README.md
```

## Quick Start

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd kracken-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   - Copy `config/secrets.yaml.example` to `config/secrets.yaml`
   - Fill in your Kraken API keys and Telegram bot token
   - Adjust `config/config.yaml` for your preferences

4. **Run the bot**
   ```bash
   python -m src.main
   ```

## Configuration

### Kraken API
Get your API keys from [Kraken API Settings](https://www.kraken.com/features/api)

### Telegram Bot
1. Talk to [@BotFather](https://t.me/BotFather) on Telegram
2. Create a new bot and get the token
3. Get your user ID by messaging [@userinfobot](https://t.me/userinfobot)

## Machine Learning

The bot includes self-learning capabilities using:
- Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- Reinforcement learning (PPO/DQN) or supervised learning approaches
- Online learning from trade outcomes
- Model persistence and versioning

## Risk Management

- Configurable position sizing (% of portfolio)
- Stop-loss and take-profit levels
- Daily loss limits
- Maximum concurrent positions
- Volatility-based adjustments

## Development

### Running Tests
```bash
pytest tests/
```

### Code Style
```bash
black src/
flake8 src/
```

## Deployment

### Manual Deployment
Ensure Python 3.9+ is installed, then:
```bash
pip install -r requirements.txt
python -m src.main
```

## Security Notes

- Never commit your `secrets.yaml` file
- Use environment variables for production secrets
- The bot operates in test mode by default - enable live trading carefully
- Consider using a dedicated trading account with limited funds

## License

MIT License - see LICENSE file for details.

## Disclaimer

Trading cryptocurrencies involves significant risk. This bot is for educational purposes only. Past performance does not guarantee future results. Use at your own risk.
