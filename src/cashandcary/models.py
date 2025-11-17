"""
Data models for the arbitrage bot.
"""

from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime, date
from typing import Optional
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


class SpotPrice(BaseModel):
    """Represents a spot price for a commodity."""

    symbol: str
    price: Decimal
    timestamp: datetime
    source: str
    currency: str = "USD"


class FuturesContract(BaseModel):
    """Represents a futures contract."""

    symbol: str
    contract_code: str  # e.g., "GCZ24" for December 2024 Gold
    expiration_date: date
    price: Decimal
    timestamp: datetime
    source: str
    contract_size: Decimal
    currency: str = "USD"
    open_interest: Optional[int] = None
    volume: Optional[int] = None


class CostOfCarry(BaseModel):
    """Cost of carry calculation breakdown."""

    spot_price: Decimal
    days_to_expiration: int
    interest_cost: Decimal
    storage_cost: Decimal
    dividend_yield: Decimal
    total_cost_of_carry: Decimal
    theoretical_futures_price: Decimal


class ArbitrageOpportunity(BaseModel):
    """Represents an identified arbitrage opportunity."""

    symbol: str
    spot_price: SpotPrice
    futures_contract: FuturesContract
    cost_of_carry: CostOfCarry
    actual_futures_price: Decimal
    theoretical_futures_price: Decimal
    price_difference: Decimal
    profit_percentage: Decimal
    expected_profit_per_contract: Decimal
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    is_profitable: bool = False


class Trade(BaseModel):
    """Represents a trade execution."""

    trade_id: str
    symbol: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Spot leg
    spot_side: OrderSide
    spot_quantity: Decimal
    spot_price: Decimal
    spot_order_id: Optional[str] = None

    # Futures leg
    futures_contract_code: str
    futures_side: OrderSide
    futures_quantity: int  # Number of contracts
    futures_price: Decimal
    futures_order_id: Optional[str] = None

    # Status
    status: OrderStatus = OrderStatus.PENDING
    expected_profit: Decimal = Decimal("0")
    actual_profit: Optional[Decimal] = None

    # Metadata
    dry_run: bool = True
    notes: str = ""


class Position(BaseModel):
    """Represents an open arbitrage position."""

    position_id: str
    symbol: str
    open_date: datetime

    # Spot position
    spot_quantity: Decimal
    spot_entry_price: Decimal
    spot_current_value: Optional[Decimal] = None

    # Futures position
    futures_contract_code: str
    futures_quantity: int
    futures_entry_price: Decimal
    futures_expiration: date

    # P&L
    expected_profit: Decimal
    unrealized_pnl: Decimal = Decimal("0")

    # Status
    is_active: bool = True


class MarketData(BaseModel):
    """Combined market data for a commodity."""

    symbol: str
    spot: SpotPrice
    futures: list[FuturesContract]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
