"""
Configuration management for the Cash-and-Carry Arbitrage Bot.
"""

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from typing import Optional
from decimal import Decimal
import os


class CommodityConfig(BaseModel):
    """Configuration for a specific commodity."""

    symbol: str = Field(..., description="Commodity symbol (e.g., 'GOLD', 'OIL')")
    spot_api_url: str = Field(..., description="API endpoint for spot prices")
    futures_api_url: str = Field(..., description="API endpoint for futures prices")

    # Cost of carry parameters
    annual_interest_rate: Decimal = Field(
        default=Decimal("0.05"),
        description="Annual risk-free interest rate (e.g., 0.05 for 5%)"
    )
    annual_storage_cost_rate: Decimal = Field(
        default=Decimal("0.01"),
        description="Annual storage cost as percentage of spot price"
    )
    annual_dividend_yield: Decimal = Field(
        default=Decimal("0.0"),
        description="Annual dividend/convenience yield"
    )

    # Trading parameters
    contract_size: Decimal = Field(
        default=Decimal("100"),
        description="Size of one futures contract (e.g., 100 oz for gold)"
    )
    min_profit_threshold: Decimal = Field(
        default=Decimal("0.005"),
        description="Minimum profit percentage to trigger trade (0.5%)"
    )
    max_position_size: int = Field(
        default=10,
        description="Maximum number of contracts to hold"
    )


class BotSettings(BaseSettings):
    """Main bot configuration settings."""

    # API Configuration
    api_key: str = Field(default="", description="API key for data feeds")
    api_secret: str = Field(default="", description="API secret for authentication")

    # Broker/Exchange Configuration
    broker_api_url: str = Field(
        default="https://api.example.com",
        description="Broker API endpoint for trade execution"
    )
    broker_api_key: str = Field(default="", description="Broker API key")
    broker_api_secret: str = Field(default="", description="Broker API secret")

    # Bot Behavior
    monitoring_interval_seconds: int = Field(
        default=60,
        description="How often to check for arbitrage opportunities (seconds)"
    )
    dry_run: bool = Field(
        default=True,
        description="If True, simulate trades without executing"
    )

    # Risk Management
    max_total_exposure: Decimal = Field(
        default=Decimal("1000000"),
        description="Maximum total capital exposure"
    )
    emergency_stop_loss_pct: Decimal = Field(
        default=Decimal("0.10"),
        description="Emergency stop loss percentage"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(
        default="arbitrage_bot.log",
        description="Log file path"
    )

    # Alerts
    alert_email: Optional[str] = Field(
        default=None,
        description="Email for alerts"
    )
    alert_on_opportunity: bool = Field(
        default=True,
        description="Send alert when opportunity found"
    )
    alert_on_trade: bool = Field(
        default=True,
        description="Send alert when trade executed"
    )

    model_config = {
        "env_prefix": "ARBITRAGE_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v.upper()


def load_commodity_configs(config_file: str = "config/commodities.json") -> list[CommodityConfig]:
    """Load commodity configurations from a JSON file."""
    import json

    if not os.path.exists(config_file):
        # Return default gold configuration if no config file exists
        return [
            CommodityConfig(
                symbol="GOLD",
                spot_api_url="https://api.metals.live/v1/spot/gold",
                futures_api_url="https://api.cmegroup.com/v1/futures/gold",
                annual_interest_rate=Decimal("0.05"),
                annual_storage_cost_rate=Decimal("0.005"),
                annual_dividend_yield=Decimal("0.0"),
                contract_size=Decimal("100"),
                min_profit_threshold=Decimal("0.005"),
                max_position_size=10
            )
        ]

    with open(config_file, "r") as f:
        data = json.load(f)

    return [CommodityConfig(**item) for item in data]


def create_sample_config():
    """Create a sample configuration file."""
    import json

    sample_commodities = [
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
        },
        {
            "symbol": "OIL",
            "spot_api_url": "https://api.oilprice.com/v1/spot/wti",
            "futures_api_url": "https://api.cmegroup.com/v1/futures/cl",
            "annual_interest_rate": "0.05",
            "annual_storage_cost_rate": "0.03",
            "annual_dividend_yield": "0.0",
            "contract_size": "1000",
            "min_profit_threshold": "0.008",
            "max_position_size": 5
        }
    ]

    os.makedirs("config", exist_ok=True)
    with open("config/commodities.json", "w") as f:
        json.dump(sample_commodities, f, indent=2)

    # Create sample .env file
    env_content = """# Arbitrage Bot Configuration
ARBITRAGE_API_KEY=your_api_key_here
ARBITRAGE_API_SECRET=your_api_secret_here
ARBITRAGE_BROKER_API_URL=https://api.broker.com
ARBITRAGE_BROKER_API_KEY=your_broker_key
ARBITRAGE_BROKER_API_SECRET=your_broker_secret
ARBITRAGE_MONITORING_INTERVAL_SECONDS=60
ARBITRAGE_DRY_RUN=true
ARBITRAGE_MAX_TOTAL_EXPOSURE=1000000
ARBITRAGE_LOG_LEVEL=INFO
ARBITRAGE_ALERT_EMAIL=your_email@example.com
"""
    with open(".env.example", "w") as f:
        f.write(env_content)

    return "config/commodities.json", ".env.example"
