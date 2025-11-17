<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=200&section=header&text=Cash%20%26%20Carry%20Arbitrage%20Bot&fontSize=40&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Automated%20Futures%20Arbitrage%20Trading%20System&descAlignY=55&descSize=18">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=200&section=header&text=Cash%20%26%20Carry%20Arbitrage%20Bot&fontSize=40&fontColor=ffffff&animation=fadeIn&fontAlignY=35&desc=Automated%20Futures%20Arbitrage%20Trading%20System&descAlignY=55&descSize=18" width="100%"/>
</picture>

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pydantic](https://img.shields.io/badge/Pydantic-V2-E92063?style=for-the-badge&logo=pydantic&logoColor=white)](https://pydantic.dev)
[![AsyncIO](https://img.shields.io/badge/AsyncIO-Enabled-00ADD8?style=for-the-badge&logo=python&logoColor=white)](https://docs.python.org/3/library/asyncio.html)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen?style=flat-square&logo=github-actions)](/)
[![Tests](https://img.shields.io/badge/Tests-20%20Passed-success?style=flat-square&logo=pytest)](/)
[![Code Style](https://img.shields.io/badge/Code%20Style-PEP8-blue?style=flat-square&logo=python)](/)
[![PRs Welcome](https://img.shields.io/badge/PRs-Welcome-brightgreen?style=flat-square&logo=github)](/)

**🎯 Identify • 📊 Calculate • ⚡ Execute • 💰 Profit**

[Features](#-features) •
[Quick Start](#-quick-start) •
[How It Works](#-how-it-works) •
[Configuration](#%EF%B8%8F-configuration) •
[Documentation](#-documentation)

</div>

---

## 🌟 What is Cash-and-Carry Arbitrage?

<div align="center">
<table>
<tr>
<td width="50%" align="center">

### 📈 The Strategy

When futures contracts trade **above** their fair value, we exploit the mispricing by:

1. **BUY** physical asset at spot
2. **SHORT** the overpriced futures
3. **HOLD** until expiration
4. **DELIVER** and lock in profit

</td>
<td width="50%" align="center">

### 💡 Risk-Free Profit

```
Fair Price = Spot + Cost of Carry

If Market Price > Fair Price
   → Arbitrage Opportunity! 🎯
```

**No market direction risk**
**Profit locked at entry**

</td>
</tr>
</table>
</div>

---

## ✨ Features

<div align="center">

| Feature | Description | Status |
|:-------:|:------------|:------:|
| 🔄 | **Real-Time Monitoring** | Continuous spot & futures price tracking | ✅ |
| 🧮 | **Cost of Carry Engine** | Interest, storage, dividends calculation | ✅ |
| 🎯 | **Opportunity Detection** | Automatic profitable trade identification | ✅ |
| ⚡ | **Auto Execution** | Buy spot + short futures simultaneously | ✅ |
| 🛡️ | **Risk Management** | Position limits, exposure caps, stop-loss | ✅ |
| 📊 | **Position Tracking** | Real-time portfolio monitoring | ✅ |
| 🚨 | **Alert System** | Email, log, and webhook notifications | ✅ |
| 🧪 | **Dry-Run Mode** | Test without real capital | ✅ |
| 📝 | **Comprehensive Logs** | Full audit trail | ✅ |

</div>

---

## 🚀 Quick Start

### Prerequisites

<div align="center">

![Python](https://img.shields.io/badge/python-3.9%2B-blue?style=for-the-badge&logo=python&logoColor=ffdd54)
![pip](https://img.shields.io/badge/pip-latest-green?style=for-the-badge&logo=pypi&logoColor=white)
![Git](https://img.shields.io/badge/git-latest-F05032?style=for-the-badge&logo=git&logoColor=white)

</div>

### ⚡ Installation

```bash
# Clone the repository
git clone https://github.com/Snapwave333/cashandcary.git
cd cashandcary

# Create & activate virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 🎮 First Run

<details>
<summary><b>1️⃣ Initialize Configuration</b></summary>

```bash
python main.py --init-config
```

Creates:
- 📁 `config/commodities.json` - Trading parameters
- 📄 `.env.example` - Environment template

</details>

<details>
<summary><b>2️⃣ Configure Settings</b></summary>

```bash
cp .env.example .env
```

Edit `.env`:
```env
ARBITRAGE_API_KEY=your_key_here
ARBITRAGE_BROKER_API_KEY=your_broker_key
ARBITRAGE_DRY_RUN=true
ARBITRAGE_MAX_TOTAL_EXPOSURE=1000000
```

</details>

<details>
<summary><b>3️⃣ Launch Bot</b></summary>

```bash
# 🧪 Test with mock data (RECOMMENDED)
python main.py --mock --dry-run

# 🔍 Single monitoring cycle
python main.py --once --mock

# 🔄 Continuous monitoring
python main.py --dry-run

# 🚀 Production (CAUTION!)
python main.py
```

</details>

---

## 🧠 How It Works

### 📐 The Math Behind It

<div align="center">

```
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   🎯 THEORETICAL FUTURES PRICE                         │
│                                                         │
│        F = S × (1 + (r + s - y) × T)                  │
│                                                         │
│   Where:                                                │
│   • S = Spot Price         💵                          │
│   • r = Interest Rate      📈 (annual)                 │
│   • s = Storage Cost       🏭 (annual)                 │
│   • y = Dividend Yield     💰 (annual)                 │
│   • T = Time to Expiry     ⏰ (years)                  │
│                                                         │
└─────────────────────────────────────────────────────────┘

         ⬇️ IF Actual Price > Theoretical Price ⬇️

┌─────────────────────────────────────────────────────────┐
│                                                         │
│   💎 PROFIT PER CONTRACT                                │
│                                                         │
│   Profit = (Actual - Theoretical) × Contract Size      │
│                                                         │
│   ✅ EXECUTE ARBITRAGE                                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

</div>

### 📊 Real Example

<div align="center">

| Parameter | Value |
|:----------|------:|
| 🥇 **Gold Spot Price** | $2,000/oz |
| 📅 **3-Month Futures** | $2,050/oz |
| 💰 **Interest Rate** | 5% |
| 🏭 **Storage Cost** | 1% |
| 📦 **Contract Size** | 100 oz |

</div>

```python
# Calculate theoretical price
T = 90 / 365  # 3 months in years
theoretical = 2000 * (1 + (0.05 + 0.01) * T)
# = $2,000 × 1.0148 = $2,029.59

# Profit calculation
price_diff = 2050 - 2029.59  # = $20.41/oz
profit = 20.41 * 100  # = $2,041 per contract! 🎉
profit_pct = 20.41 / 2029.59  # = 1.01% ✅
```

> 💡 **Result**: With `min_profit_threshold = 0.5%`, this **1.01% opportunity triggers a trade!**

---

## 🏗️ Architecture

<div align="center">

```
                    ┌──────────────────────┐
                    │     🎮 MAIN.PY       │
                    │   (Entry Point)      │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │      🤖 BOT.PY       │
                    │   (Orchestrator)     │
                    └──────────┬───────────┘
                               │
          ┌────────────────────┼────────────────────┐
          │                    │                    │
┌─────────▼──────────┐ ┌──────▼───────┐ ┌─────────▼─────────┐
│  📡 DATA_FEEDS.PY  │ │ 🧮 CALC.PY  │ │  ⚡ EXECUTOR.PY   │
│  (Market Data)     │ │ (Pricing)   │ │  (Trade Engine)   │
└────────────────────┘ └──────────────┘ └───────────────────┘
          │                    │                    │
          │            ┌───────▼───────┐           │
          │            │  📋 MODELS.PY │           │
          └────────────►  (Data Types) ◄───────────┘
                       └───────────────┘
                               │
                    ┌──────────▼───────────┐
                    │    ⚙️ CONFIG.PY      │
                    │   (Settings)         │
                    └──────────────────────┘
                               │
                    ┌──────────▼───────────┐
                    │    🚨 ALERTS.PY      │
                    │   (Notifications)    │
                    └──────────────────────┘
```

</div>

### 📁 Project Structure

```
cashandcary/
├── 📂 src/cashandcary/
│   ├── 🎯 __init__.py       # Package init
│   ├── ⚙️ config.py         # Configuration management
│   ├── 📋 models.py         # Pydantic data models
│   ├── 📡 data_feeds.py     # Market data fetching
│   ├── 🧮 calculator.py     # Cost of carry engine
│   ├── ⚡ executor.py       # Trade execution
│   ├── 🤖 bot.py            # Main orchestrator
│   └── 🚨 alerts.py         # Alerting system
├── 🧪 tests/                 # Unit tests
├── 📁 config/                # Configuration files
├── 🎮 main.py               # Entry point
└── 📦 requirements.txt       # Dependencies
```

---

## ⚙️ Configuration

### 🌍 Environment Variables

<div align="center">

| Variable | Description | Default | Required |
|:---------|:------------|:-------:|:--------:|
| `ARBITRAGE_API_KEY` | 🔑 Data feed API key | - | ⚠️ |
| `ARBITRAGE_BROKER_API_KEY` | 🏦 Broker API key | - | ⚠️ |
| `ARBITRAGE_DRY_RUN` | 🧪 Simulation mode | `true` | No |
| `ARBITRAGE_MONITORING_INTERVAL_SECONDS` | ⏱️ Check frequency | `60` | No |
| `ARBITRAGE_MAX_TOTAL_EXPOSURE` | 💰 Max capital at risk | `1000000` | No |
| `ARBITRAGE_LOG_LEVEL` | 📝 Verbosity | `INFO` | No |
| `ARBITRAGE_ALERT_EMAIL` | 📧 Alert recipient | - | No |

</div>

### 🥇 Commodity Configuration

```json
{
  "symbol": "GOLD",
  "spot_api_url": "https://api.metals.live/v1/spot/gold",
  "futures_api_url": "https://api.cmegroup.com/v1/futures/gold",
  "annual_interest_rate": "0.05",      // 5% risk-free rate
  "annual_storage_cost_rate": "0.005", // 0.5% storage
  "annual_dividend_yield": "0.0",       // No yield
  "contract_size": "100",               // 100 oz per contract
  "min_profit_threshold": "0.005",      // 0.5% minimum profit
  "max_position_size": 10               // Max 10 contracts
}
```

---

## 🧪 Testing

<div align="center">

![Pytest](https://img.shields.io/badge/pytest-7.4+-009688?style=for-the-badge&logo=pytest&logoColor=white)
![Coverage](https://img.shields.io/badge/Coverage-85%25-brightgreen?style=for-the-badge)

</div>

```bash
# 🧪 Run all tests
pytest tests/

# 📊 Run with verbose output
pytest -v tests/

# 📈 Generate coverage report
pytest --cov=src/cashandcary tests/

# 🎯 Test specific module
pytest tests/test_calculator.py
```

### Test Structure

- `test_calculator.py` - Cost of carry calculations
- `test_executor.py` - Trade execution logic
- `test_bot.py` - Bot orchestration

---

## 📈 Monitoring & Logs

<div align="center">

| File | Content | Purpose |
|:-----|:--------|:--------|
| 📜 `arbitrage_bot.log` | All bot activity | Main audit trail |
| ❌ `errors.log` | Errors only | Quick debugging |
| 🚨 `alerts.log` | JSON alerts | Machine-readable events |
| 💼 `state/positions.json` | Open positions | Portfolio state |

</div>

---

## ⚠️ Risk Warnings

<div align="center">

> **🔴 IMPORTANT: Educational & Research Purposes Only**

</div>

### 🎯 Key Risks

<div align="center">

| Risk Type | Description | Mitigation |
|:----------|:------------|:-----------|
| ⚡ **Execution** | Slippage, partial fills | Low-latency execution |
| 🏦 **Counterparty** | Broker/exchange failure | Multiple brokers |
| 💧 **Liquidity** | Can't exit positions | Liquid contracts only |
| ⚖️ **Regulatory** | Jurisdiction rules | Legal compliance |
| 💰 **Capital** | Large capital requirements | Proper funding |
| 🏭 **Storage** | Costs exceed estimates | Conservative estimates |
| 📈 **Interest Rate** | Financing cost changes | Fixed-rate financing |

</div>

### ✅ Best Practices

```diff
+ Start with dry-run mode
+ Use small position sizes initially
+ Understand all costs involved
+ Have sufficient capital reserves
+ Monitor positions actively
+ Consult with financial professionals
- Never trade with money you can't afford to lose
- Don't ignore risk management settings
- Don't use in production without thorough testing
```

---

## 🔌 API Integration

### Custom Data Feed Implementation

```python
from cashandcary.data_feeds import FuturesPriceFeed, SpotPriceFeed

class CMEDataFeed(FuturesPriceFeed):
    """Custom CME Group API parser."""

    def _parse_futures_response(self, config, data):
        # Parse CME-specific JSON response
        contracts = []
        for item in data['quotes']:
            contract = FuturesContract(
                symbol=config.symbol,
                contract_code=item['contractCode'],
                price=Decimal(str(item['lastPrice'])),
                # ... additional fields
            )
            contracts.append(contract)
        return contracts


class MetalsLiveFeed(SpotPriceFeed):
    """Custom metals.live API parser."""

    def _parse_spot_response(self, symbol, data):
        return SpotPrice(
            symbol=symbol,
            price=Decimal(str(data['spot']['price'])),
            # ... additional fields
        )
```

---

## 🛠️ Extending the Bot

<details>
<summary><b>📦 Adding New Commodities</b></summary>

1. Add to `config/commodities.json`
2. Implement API parser if needed
3. Set appropriate storage costs
4. Test with dry-run mode

</details>

<details>
<summary><b>🔔 Custom Alert Channels</b></summary>

```python
class SlackAlertManager(AlertManager):
    def _send_slack_alert(self, alert):
        webhook_url = "https://hooks.slack.com/..."
        payload = {
            "text": f"*{alert.level}*: {alert.title}\n{alert.message}"
        }
        requests.post(webhook_url, json=payload)
```

</details>

<details>
<summary><b>📈 Continuous Compounding</b></summary>

```python
# Use exponential formula: F = S × e^((r+s-y)×T)
calculator = CostOfCarryCalculator(use_continuous_compounding=True)
```

</details>

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📄 License

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

</div>

---

## ⚖️ Disclaimer

<div align="center">

> **This software is provided "AS IS" without warranty of any kind.**
>
> The authors are **NOT responsible** for any financial losses incurred through the use of this software.
>
> Trading futures and commodities involves **substantial risk of loss** and is **not suitable for all investors**.
>
> **Always consult with qualified financial advisors before engaging in real trading activities.**

</div>

---

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=100&section=footer">
  <img src="https://capsule-render.vercel.app/api?type=waving&color=0:667eea,100:764ba2&height=100&section=footer" width="100%"/>
</picture>

<div align="center">

**Made with ❤️ for the trading community**

⭐ Star this repo if you find it useful! ⭐

</div>
