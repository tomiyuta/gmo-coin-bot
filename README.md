# GMO Coin Automated Trading Bot

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0.0-orange.svg)]()

## Overview

GMO Coin Automated Trading Bot is a sophisticated automated trading system designed for GMO Coin's cryptocurrency exchange. It features advanced risk management, Discord integration, and a user-friendly GUI configuration editor.

## Features

### 🚀 Core Features
- **Automated Trading**: Execute trades based on CSV schedule files
- **Risk Management**: Built-in stop-loss, take-profit, and position monitoring
- **Discord Integration**: Real-time notifications and bot commands
- **GUI Configuration**: Easy-to-use settings editor
- **Auto Restart**: Scheduled restarts for long-term operation
- **Performance Monitoring**: Comprehensive system health checks

### 📊 Trading Features
- **Spread Control**: Configurable spread thresholds
- **Auto Lot Calculation**: Intelligent position sizing based on account balance
- **Position Monitoring**: Automatic position closure at scheduled times
- **Volume Limits**: Daily trading volume restrictions per symbol
- **Jitter Timing**: Random delays to prevent order clustering

### 🔧 Management Features
- **Discord Bot Commands**: Status, health, performance monitoring
- **Backup System**: Automatic configuration and data backup
- **Logging**: Comprehensive logging with rotation
- **Error Handling**: Robust error recovery and retry mechanisms

## Quick Start

### Prerequisites
- Python 3.8 or higher
- GMO Coin API account
- Discord account (for notifications)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gmo-coin-bot.git
   cd gmo-coin-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the bot**
   ```bash
   # Windows
   setup.bat
   
   # Or run directly
   python config_editor.py
   ```

4. **Start trading**
   ```bash
   # Windows
   trade.bat
   
   # Or run directly
   python main.py
   ```

## Configuration

### GUI Configuration Editor (Recommended)

Run the GUI configuration editor for easy setup:
```bash
python config_editor.py
```

### Manual Configuration

Create `config.json` with the following structure:
```json
{
  "api_key": "your_gmo_api_key",
  "api_secret": "your_gmo_api_secret",
  "discord_webhook_url": "your_discord_webhook_url",
  "discord_bot_token": "your_discord_bot_token",
  "spread_threshold": 0.01,
  "jitter_seconds": 3,
  "leverage": 10,
  "risk_ratio": 1.0,
  "autolot": "TRUE",
  "stop_loss_pips": 0,
  "take_profit_pips": 0,
  "position_check_interval_minutes": 10,
  "auto_restart_hour": null
}
```

### Trading Schedule

Create `trades.csv` with your trading schedule:
```csv
有効,方向,通貨ペア,エントリー時刻,決済時刻,ロット数
TRUE,BUY,BTC_JPY,09:30:00,10:00:00,1.0
TRUE,SELL,ETH_JPY,14:00:00,14:30:00,1.0
```

## Discord Bot Commands

| Command | Description |
|---------|-------------|
| `status` | Show bot status and account information |
| `health` | System health check |
| `performance` | Performance metrics |
| `position` | Current positions |
| `backup` | Create backup of configuration and data |
| `restart` | Restart the bot |
| `stop` | Stop the bot |
| `kill` | Force stop the bot |

## Security Features

- **API Key Protection**: Secure storage of API credentials
- **Environment Variables**: Support for environment variable configuration
- **Input Validation**: Comprehensive configuration validation
- **Error Logging**: Detailed error tracking without exposing sensitive data

## Risk Management

### Built-in Protections
- **Spread Thresholds**: Prevent trading during high spread conditions
- **Volume Limits**: Daily trading volume restrictions
- **Position Monitoring**: Automatic position closure
- **Auto Restart**: Scheduled restarts to prevent memory leaks
- **Error Recovery**: Automatic retry mechanisms

### Configuration Options
- **Stop Loss**: Automatic stop-loss orders
- **Take Profit**: Automatic take-profit orders
- **Risk Ratio**: Configurable account balance usage
- **Leverage Control**: Adjustable leverage settings

## File Structure

```
gmo-coin-bot/
├── main.py              # Main trading bot
├── config_editor.py     # GUI configuration editor
├── bot_core.py          # Discord bot core functions
├── config.json          # Configuration file (create this)
├── trades.csv           # Trading schedule (create this)
├── requirements.txt     # Python dependencies
├── setup.bat           # Windows setup script
├── trade.bat           # Windows trading script
├── README.md           # This file
├── README.txt          # Japanese documentation
├── LICENSE             # MIT License
└── logs/               # Log files (auto-created)
```

## API Requirements

### GMO Coin API Permissions
- Account balance retrieval
- Order placement
- Position management
- Trade history access

### Discord Bot Permissions
- Send Messages
- Read Message History
- Use Slash Commands

## Troubleshooting

### Common Issues

1. **API Connection Errors**
   - Verify API key and secret
   - Check internet connection
   - Ensure API permissions are correct

2. **Discord Integration Issues**
   - Verify webhook URL
   - Check bot token and permissions
   - Ensure bot is invited to server

3. **Configuration Errors**
   - Use GUI editor for easier configuration
   - Check JSON syntax in config.json
   - Verify all required fields are set

### Log Files

Check the following log files for detailed information:
- `logs/main.log` - Main application log
- `logs/error.log` - Error-specific log
- `logs/discord.log` - Discord integration log

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Disclaimer

This software is for educational and research purposes only. Trading cryptocurrencies involves substantial risk of loss and is not suitable for all investors. The high degree of leverage can work against you as well as for you. Before deciding to trade cryptocurrencies, you should carefully consider your investment objectives, level of experience, and risk appetite. The possibility exists that you could sustain a loss of some or all of your initial investment and therefore you should not invest money that you cannot afford to lose.

## Support

For support and questions:
- Create an issue on GitHub
- Check the Japanese documentation in `README.txt`
- Review the Discord commands guide in `DISCORD_COMMANDS.txt`

## Version History

### v2.0.0 (Current)
- Added GUI configuration editor
- Enhanced Discord bot integration
- Improved risk management features
- Added comprehensive logging
- Enhanced error handling and recovery

### v1.0.0
- Initial release
- Basic automated trading functionality
- Discord notifications
- CSV-based trading schedules 