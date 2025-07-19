# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-12-19

### Added
- GUI configuration editor (`config_editor.py`)
- Enhanced Discord bot integration with more commands
- Comprehensive logging system with rotation
- Auto restart functionality for long-term operation
- Performance monitoring and health checks
- Backup system for configuration and data
- Position monitoring with automatic closure
- Volume limits per symbol
- Jitter timing to prevent order clustering
- Risk management features (stop-loss, take-profit)
- Auto lot calculation with safety margin

### Changed
- Improved error handling and recovery mechanisms
- Enhanced configuration validation
- Better memory management with garbage collection
- Updated documentation with English README.md
- Added MIT License
- Improved security with input validation

### Fixed
- Memory leak issues in long-running operations
- API rate limiting improvements
- Configuration file validation errors
- Discord webhook integration issues

## [1.0.0] - 2024-07-19

### Added
- Initial release of GMO Coin Automated Trading Bot
- Basic automated trading functionality
- Discord notifications via webhook
- CSV-based trading schedules
- API integration with GMO Coin
- Basic risk management features

### Features
- Automated order execution
- Spread threshold control
- Basic position monitoring
- Discord integration for notifications
- Configuration file support 