# Cash-and-Carry Arbitrage Bot

A professional-grade automated trading bot that identifies and executes cash-and-carry arbitrage opportunities in futures markets.

## Overview

Cash-and-carry arbitrage is a market-neutral strategy that exploits mispricings between spot and futures prices. When a futures contract trades at a price significantly higher than its theoretical fair value (Spot Price + Cost of Carry), the bot:

1. **Buys the physical asset** at the spot price
2. **Shorts the futures contract** at the inflated price
3. **Holds until expiration**, then delivers the asset to close the futures position
4. **Locks in risk-free profit** from the price differential

## Features

- **Real-time Market Monitoring**: Continuously fetches spot and futures prices from configurable data sources
- **Cost of Carry Calculator**: Accurately calculates theoretical futures prices accounting for:
  - Interest/financing costs
  - Storage costs
  - Dividend/convenience yields
- **Arbitrage Detection**: Identifies profitable opportunities that exceed configurable thresholds
- **Risk Management**:
  - Position size limits per commodity
  - Total exposure caps
  - Emergency stop-loss protection
- **Trade Execution**: Automated execution of both legs (spot buy + futures short)
- **Position Tracking**: Maintains state of all open positions
- **Alerting System**: Notifications for opportunities, trades, and errors
- **Comprehensive Logging**: Detailed logs for monitoring and debugging
- **Dry-Run Mode**: Test strategies without real capital

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd cashandcary

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or install as package
pip install -e .
```

## Quick Start

### 1. Initialize Configuration

```bash
python main.py --init-config
```

This creates:
- `config/commodities.json`: Commodity-specific settings
- `.env.example`: Environment variables template

### 2. Configure Your Settings

Copy and edit the environment file:

```bash
cp .env.example .env
```

Edit `.env` with your API credentials:

```env
ARBITRAGE_API_KEY=your_api_key_here
ARBITRAGE_BROKER_API_KEY=your_broker_key
ARBITRAGE_DRY_RUN=true
ARBITRAGE_MAX_TOTAL_EXPOSURE=1000000
```

### 3. Run the Bot

**Dry Run with Mock Data (Recommended for Testing):**
```bash
python main.py --mock --dry-run
```

**Single Monitoring Cycle:**
```bash
python main.py --once --mock
```

**Continuous Monitoring:**
```bash
python main.py --dry-run
```

**Production Mode (Use with extreme caution):**
```bash
python main.py
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ARBITRAGE_API_KEY` | API key for data feeds | - |
| `ARBITRAGE_BROKER_API_KEY` | Broker API key | - |
| `ARBITRAGE_DRY_RUN` | Simulate trades | `true` |
| `ARBITRAGE_MONITORING_INTERVAL_SECONDS` | Check interval | `60` |
| `ARBITRAGE_MAX_TOTAL_EXPOSURE` | Max capital at risk | `1000000` |
| `ARBITRAGE_LOG_LEVEL` | Logging verbosity | `INFO` |
| `ARBITRAGE_ALERT_EMAIL` | Email for alerts | - |

### Commodity Configuration

Edit `config/commodities.json`:

```json
[
  {
    "symbol": "GOLD",
    "spot_api_url": "https://api.metals.live/v1/spot/gold",
    "futures_api_url": "https://api.cmegroup.com/v1/futures/gold",
    "annual_interest_rate": "0.05",
    "annual_storage_cost_rate": "0.005",
    "annual_dividend_yield": "0.0",
    "contract_size": "100",
    "min_profit_threshold": "0.005",
    "max_position_size": 10
  }
]
```

**Parameters:**
- `symbol`: Commodity identifier
- `spot_api_url`: Endpoint for spot prices
- `futures_api_url`: Endpoint for futures data
- `annual_interest_rate`: Risk-free rate (e.g., 0.05 = 5%)
- `annual_storage_cost_rate`: Storage as % of spot
- `annual_dividend_yield`: Convenience yield
- `contract_size`: Units per futures contract
- `min_profit_threshold`: Minimum profit % to trade
- `max_position_size`: Max contracts for this commodity

## Architecture

```
cashandcary/
├── src/cashandcary/
│   ├── __init__.py       # Package initialization
│   ├── config.py         # Configuration management
│   ├── models.py         # Data models (Pydantic)
│   ├── data_feeds.py     # Market data fetching
│   ├── calculator.py     # Cost of carry calculations
│   ├── executor.py       # Trade execution engine
│   ├── bot.py            # Main orchestration
│   └── alerts.py         # Alerting and logging
├── tests/                # Unit tests
├── config/               # Configuration files
├── main.py              # Entry point
└── requirements.txt      # Dependencies
```

### Core Components

1. **Data Feed Module** (`data_feeds.py`)
   - Fetches real-time spot and futures prices
   - Supports multiple data sources
   - Mock feed for testing

2. **Calculator** (`calculator.py`)
   - Cost of carry computation
   - Theoretical futures pricing
   - Arbitrage opportunity analysis

3. **Executor** (`executor.py`)
   - Risk validation
   - Position sizing
   - Trade execution (both legs)
   - Position management

4. **Bot Orchestrator** (`bot.py`)
   - Main monitoring loop
   - Opportunity detection
   - Trade coordination
   - State persistence

## How It Works

### The Cash-and-Carry Formula

```
Theoretical Futures Price = Spot Price × (1 + (r + s - y) × T)

Where:
- r = Annual interest rate
- s = Annual storage cost rate
- y = Annual convenience yield
- T = Time to expiration (years)
```

### Profit Calculation

```
Profit = (Actual Futures Price - Theoretical Price) × Contract Size

If Actual > Theoretical by more than threshold → Execute arbitrage
```

### Example

```
Gold Spot Price: $2,000/oz
3-Month Future Price: $2,050/oz (actual)
Interest Rate: 5%
Storage Cost: 1%
Contract Size: 100 oz

Theoretical Price = $2,000 × (1 + 0.06 × 0.25) = $2,030
Price Difference = $2,050 - $2,030 = $20/oz
Profit Per Contract = $20 × 100 oz = $2,000
Profit Percentage = $20 / $2,030 = 0.99%

If min_profit_threshold = 0.5%, this is profitable!
```

## Testing

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_calculator.py

# Run with verbose output
pytest -v tests/

# Run with coverage
pytest --cov=src/cashandcary tests/
```

## Monitoring & Logs

- **Main Log**: `arbitrage_bot.log` - All bot activity
- **Error Log**: `errors.log` - Errors only
- **Alert Log**: `alerts.log` - JSON-formatted alerts
- **State File**: `state/positions.json` - Current positions

## Risk Warnings

**IMPORTANT**: This bot is designed for educational and research purposes. Real arbitrage trading involves significant risks:

1. **Execution Risk**: Slippage and partial fills can eliminate profits
2. **Counterparty Risk**: Broker/exchange failures
3. **Liquidity Risk**: May not be able to exit positions
4. **Regulatory Risk**: Different jurisdictions have different rules
5. **Capital Requirements**: Physical delivery requires substantial capital
6. **Storage Costs**: Real storage costs may exceed estimates
7. **Interest Rate Risk**: Financing costs can change

**Always:**
- Start with dry-run mode
- Use small position sizes initially
- Understand all costs involved
- Have sufficient capital reserves
- Monitor positions actively
- Consult with financial professionals

## API Integration

To use with real APIs, implement specific parsers in `data_feeds.py`:

```python
class CMEDataFeed(FuturesPriceFeed):
    def _parse_futures_response(self, config, data):
        # Parse CME-specific response format
        pass

class MetalsLiveFeed(SpotPriceFeed):
    def _parse_spot_response(self, symbol, data):
        # Parse metals.live response format
        pass
```

## Extending the Bot

### Adding New Commodities

1. Add configuration in `config/commodities.json`
2. Implement API parser if needed
3. Adjust storage costs appropriately

### Custom Alert Channels

```python
class SlackAlertManager(AlertManager):
    def _send_slack_alert(self, alert):
        # Implement Slack webhook integration
        pass
```

### Different Compounding Methods

```python
calculator = CostOfCarryCalculator(use_continuous_compounding=True)
```

## License

MIT License - See LICENSE file for details.

## Disclaimer

This software is provided "as is" without warranty of any kind. The authors are not responsible for any financial losses incurred through the use of this software. Trading futures and commodities involves substantial risk of loss and is not suitable for all investors.

Always consult with qualified financial advisors before engaging in real trading activities.
