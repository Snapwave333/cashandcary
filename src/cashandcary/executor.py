"""
Trade Executor for Cash-and-Carry Arbitrage.

Handles the execution of arbitrage trades:
1. Buy physical asset at spot price
2. Short the corresponding futures contract
"""

import uuid
import asyncio
from datetime import datetime
from decimal import Decimal, ROUND_DOWN
from typing import Optional
import logging
import json

from .models import (
    ArbitrageOpportunity,
    Trade,
    Position,
    OrderSide,
    OrderStatus,
)
from .config import BotSettings, CommodityConfig


logger = logging.getLogger(__name__)


class ExecutionError(Exception):
    """Exception raised when trade execution fails."""
    pass


class RiskLimitExceeded(Exception):
    """Exception raised when trade would exceed risk limits."""
    pass


class PositionManager:
    """Manages open arbitrage positions."""

    def __init__(self):
        self.positions: dict[str, Position] = {}
        self.trades: list[Trade] = []

    def add_position(self, position: Position) -> None:
        """Add a new position."""
        self.positions[position.position_id] = position
        logger.info(f"Added position {position.position_id} for {position.symbol}")

    def close_position(self, position_id: str, actual_profit: Decimal) -> None:
        """Close a position."""
        if position_id in self.positions:
            self.positions[position_id].is_active = False
            logger.info(f"Closed position {position_id} with profit: {actual_profit}")

    def get_active_positions(self) -> list[Position]:
        """Get all active positions."""
        return [p for p in self.positions.values() if p.is_active]

    def get_total_exposure(self) -> Decimal:
        """Calculate total capital exposure across all positions."""
        total = Decimal("0")
        for position in self.get_active_positions():
            total += position.spot_quantity * position.spot_entry_price
        return total

    def get_symbol_exposure(self, symbol: str) -> Decimal:
        """Get exposure for a specific symbol."""
        total = Decimal("0")
        for position in self.get_active_positions():
            if position.symbol == symbol:
                total += position.spot_quantity * position.spot_entry_price
        return total

    def get_contract_count(self, symbol: str) -> int:
        """Get number of contracts held for a symbol."""
        count = 0
        for position in self.get_active_positions():
            if position.symbol == symbol:
                count += position.futures_quantity
        return count

    def add_trade(self, trade: Trade) -> None:
        """Record a trade."""
        self.trades.append(trade)

    def get_trade_history(self) -> list[Trade]:
        """Get all trade history."""
        return self.trades

    def save_state(self, filepath: str) -> None:
        """Save current state to file."""
        state = {
            "positions": [p.model_dump(mode="json") for p in self.positions.values()],
            "trades": [t.model_dump(mode="json") for t in self.trades],
        }
        with open(filepath, "w") as f:
            json.dump(state, f, indent=2, default=str)

    def load_state(self, filepath: str) -> None:
        """Load state from file."""
        try:
            with open(filepath, "r") as f:
                state = json.load(f)

            self.positions = {
                p["position_id"]: Position(**p) for p in state.get("positions", [])
            }
            self.trades = [Trade(**t) for t in state.get("trades", [])]
            logger.info(f"Loaded {len(self.positions)} positions and {len(self.trades)} trades")
        except FileNotFoundError:
            logger.info("No previous state file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading state: {e}")


class BrokerAPI:
    """Interface for broker API (abstract/mock implementation)."""

    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.api_url = settings.broker_api_url

    async def buy_spot(
        self, symbol: str, quantity: Decimal, price: Decimal
    ) -> dict:
        """
        Execute spot buy order.

        Returns:
            Order execution result
        """
        logger.info(f"BUY SPOT: {quantity} {symbol} @ ${price}")

        # In production, this would make actual API call
        # For now, return mock execution
        return {
            "order_id": f"SPOT_{uuid.uuid4().hex[:12]}",
            "status": "FILLED",
            "filled_quantity": float(quantity),
            "filled_price": float(price),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def short_futures(
        self, contract_code: str, quantity: int, price: Decimal
    ) -> dict:
        """
        Execute futures short order.

        Returns:
            Order execution result
        """
        logger.info(f"SHORT FUTURES: {quantity} contracts {contract_code} @ ${price}")

        # In production, this would make actual API call
        return {
            "order_id": f"FUT_{uuid.uuid4().hex[:12]}",
            "status": "FILLED",
            "filled_quantity": quantity,
            "filled_price": float(price),
            "timestamp": datetime.utcnow().isoformat(),
        }

    async def get_account_balance(self) -> Decimal:
        """Get available account balance."""
        # Mock implementation
        return Decimal("10000000")  # $10M


class TradeExecutor:
    """Executes cash-and-carry arbitrage trades."""

    def __init__(
        self,
        settings: BotSettings,
        position_manager: PositionManager = None,
        broker: BrokerAPI = None
    ):
        self.settings = settings
        self.position_manager = position_manager or PositionManager()
        self.broker = broker or BrokerAPI(settings)

    def validate_risk_limits(
        self, opportunity: ArbitrageOpportunity, num_contracts: int, config: CommodityConfig
    ) -> None:
        """
        Validate that trade doesn't exceed risk limits.

        Raises:
            RiskLimitExceeded: If trade would exceed limits
        """
        # Check max position size for this commodity
        current_contracts = self.position_manager.get_contract_count(opportunity.symbol)
        if current_contracts + num_contracts > config.max_position_size:
            raise RiskLimitExceeded(
                f"Would exceed max position size of {config.max_position_size} contracts"
            )

        # Check total exposure
        spot_value = opportunity.spot_price.price * config.contract_size * num_contracts
        current_exposure = self.position_manager.get_total_exposure()
        if current_exposure + spot_value > self.settings.max_total_exposure:
            raise RiskLimitExceeded(
                f"Would exceed max total exposure of ${self.settings.max_total_exposure}"
            )

    def calculate_position_size(
        self, opportunity: ArbitrageOpportunity, config: CommodityConfig
    ) -> int:
        """
        Calculate optimal number of contracts to trade.

        Returns:
            Number of contracts to trade
        """
        # Available capacity based on max position size
        current_contracts = self.position_manager.get_contract_count(opportunity.symbol)
        available_contracts = config.max_position_size - current_contracts

        # Available capacity based on total exposure
        current_exposure = self.position_manager.get_total_exposure()
        available_capital = self.settings.max_total_exposure - current_exposure
        spot_value_per_contract = opportunity.spot_price.price * config.contract_size

        if spot_value_per_contract > 0:
            capital_based_contracts = int(
                (available_capital / spot_value_per_contract).quantize(
                    Decimal("1"), ROUND_DOWN
                )
            )
        else:
            capital_based_contracts = 0

        # Take the minimum
        num_contracts = min(available_contracts, capital_based_contracts)

        # Ensure at least 1 contract if we have capacity
        return max(0, num_contracts)

    async def execute_arbitrage(
        self, opportunity: ArbitrageOpportunity, config: CommodityConfig, num_contracts: int = None
    ) -> Trade:
        """
        Execute a cash-and-carry arbitrage trade.

        Args:
            opportunity: Identified arbitrage opportunity
            config: Commodity configuration
            num_contracts: Number of contracts to trade (auto-calculated if None)

        Returns:
            Trade object with execution details
        """
        if num_contracts is None:
            num_contracts = self.calculate_position_size(opportunity, config)

        if num_contracts <= 0:
            raise ExecutionError("No capacity available for trade")

        # Validate risk limits
        self.validate_risk_limits(opportunity, num_contracts, config)

        # Calculate quantities
        spot_quantity = config.contract_size * num_contracts
        expected_profit = opportunity.expected_profit_per_contract * num_contracts

        # Create trade record
        trade = Trade(
            trade_id=f"ARB_{uuid.uuid4().hex[:12]}",
            symbol=opportunity.symbol,
            spot_side=OrderSide.BUY,
            spot_quantity=spot_quantity,
            spot_price=opportunity.spot_price.price,
            futures_contract_code=opportunity.futures_contract.contract_code,
            futures_side=OrderSide.SELL,
            futures_quantity=num_contracts,
            futures_price=opportunity.actual_futures_price,
            expected_profit=expected_profit,
            dry_run=self.settings.dry_run,
            status=OrderStatus.PENDING
        )

        if self.settings.dry_run:
            logger.info(f"DRY RUN: Would execute trade {trade.trade_id}")
            trade.status = OrderStatus.FILLED
            trade.spot_order_id = "DRY_RUN_SPOT"
            trade.futures_order_id = "DRY_RUN_FUTURES"
            trade.notes = "Dry run execution - no actual orders placed"
        else:
            # Execute both legs
            try:
                # Execute spot buy
                spot_result = await self.broker.buy_spot(
                    opportunity.symbol,
                    spot_quantity,
                    opportunity.spot_price.price
                )
                trade.spot_order_id = spot_result["order_id"]

                # Execute futures short
                futures_result = await self.broker.short_futures(
                    opportunity.futures_contract.contract_code,
                    num_contracts,
                    opportunity.actual_futures_price
                )
                trade.futures_order_id = futures_result["order_id"]

                trade.status = OrderStatus.FILLED
                trade.notes = "Successfully executed both legs"

            except Exception as e:
                logger.error(f"Execution failed: {e}")
                trade.status = OrderStatus.REJECTED
                trade.notes = f"Execution failed: {str(e)}"
                raise ExecutionError(f"Trade execution failed: {e}")

        # Record trade
        self.position_manager.add_trade(trade)

        # Create position if trade was successful
        if trade.status == OrderStatus.FILLED:
            position = Position(
                position_id=f"POS_{uuid.uuid4().hex[:12]}",
                symbol=opportunity.symbol,
                open_date=datetime.utcnow(),
                spot_quantity=spot_quantity,
                spot_entry_price=opportunity.spot_price.price,
                futures_contract_code=opportunity.futures_contract.contract_code,
                futures_quantity=num_contracts,
                futures_entry_price=opportunity.actual_futures_price,
                futures_expiration=opportunity.futures_contract.expiration_date,
                expected_profit=expected_profit,
                is_active=True
            )
            self.position_manager.add_position(position)

        logger.info(
            f"Trade {trade.trade_id}: {trade.status} - "
            f"Expected profit: ${expected_profit}"
        )

        return trade

    def get_execution_summary(self) -> dict:
        """Get summary of all executions."""
        trades = self.position_manager.get_trade_history()
        positions = self.position_manager.get_active_positions()

        total_expected_profit = sum(t.expected_profit for t in trades)
        total_exposure = self.position_manager.get_total_exposure()

        return {
            "total_trades": len(trades),
            "active_positions": len(positions),
            "total_exposure": float(total_exposure),
            "total_expected_profit": float(total_expected_profit),
            "trades": [t.model_dump() for t in trades[-10:]],  # Last 10 trades
        }
