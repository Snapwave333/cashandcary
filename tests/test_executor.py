"""
Tests for trade executor.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cashandcary.executor import (
    TradeExecutor,
    PositionManager,
    RiskLimitExceeded,
    ExecutionError,
)
from cashandcary.models import (
    ArbitrageOpportunity,
    SpotPrice,
    FuturesContract,
    CostOfCarry,
    Position,
    OrderStatus,
)
from cashandcary.config import BotSettings, CommodityConfig


class TestPositionManager:
    """Test cases for PositionManager."""

    def setup_method(self):
        """Setup test fixtures."""
        self.manager = PositionManager()

    def test_add_position(self):
        """Test adding a position."""
        position = Position(
            position_id="POS_001",
            symbol="GOLD",
            open_date=datetime.utcnow(),
            spot_quantity=Decimal("100"),
            spot_entry_price=Decimal("2000"),
            futures_contract_code="GCM24",
            futures_quantity=1,
            futures_entry_price=Decimal("2050"),
            futures_expiration=(datetime.utcnow() + timedelta(days=90)).date(),
            expected_profit=Decimal("5000"),
            is_active=True
        )

        self.manager.add_position(position)

        assert len(self.manager.get_active_positions()) == 1
        assert position.position_id in self.manager.positions

    def test_get_total_exposure(self):
        """Test calculating total exposure."""
        # Add two positions
        for i in range(2):
            position = Position(
                position_id=f"POS_{i}",
                symbol="GOLD",
                open_date=datetime.utcnow(),
                spot_quantity=Decimal("100"),
                spot_entry_price=Decimal("2000"),
                futures_contract_code="GCM24",
                futures_quantity=1,
                futures_entry_price=Decimal("2050"),
                futures_expiration=(datetime.utcnow() + timedelta(days=90)).date(),
                expected_profit=Decimal("5000"),
                is_active=True
            )
            self.manager.add_position(position)

        exposure = self.manager.get_total_exposure()
        # 2 * 100 * 2000 = 400,000
        assert exposure == Decimal("400000")

    def test_get_contract_count(self):
        """Test getting contract count for a symbol."""
        position = Position(
            position_id="POS_001",
            symbol="GOLD",
            open_date=datetime.utcnow(),
            spot_quantity=Decimal("100"),
            spot_entry_price=Decimal("2000"),
            futures_contract_code="GCM24",
            futures_quantity=3,
            futures_entry_price=Decimal("2050"),
            futures_expiration=(datetime.utcnow() + timedelta(days=90)).date(),
            expected_profit=Decimal("5000"),
            is_active=True
        )
        self.manager.add_position(position)

        count = self.manager.get_contract_count("GOLD")
        assert count == 3

        # Different symbol should be 0
        assert self.manager.get_contract_count("OIL") == 0

    def test_close_position(self):
        """Test closing a position."""
        position = Position(
            position_id="POS_001",
            symbol="GOLD",
            open_date=datetime.utcnow(),
            spot_quantity=Decimal("100"),
            spot_entry_price=Decimal("2000"),
            futures_contract_code="GCM24",
            futures_quantity=1,
            futures_entry_price=Decimal("2050"),
            futures_expiration=(datetime.utcnow() + timedelta(days=90)).date(),
            expected_profit=Decimal("5000"),
            is_active=True
        )
        self.manager.add_position(position)

        self.manager.close_position("POS_001", Decimal("5200"))

        assert len(self.manager.get_active_positions()) == 0
        assert self.manager.positions["POS_001"].is_active is False


class TestTradeExecutor:
    """Test cases for TradeExecutor."""

    def setup_method(self):
        """Setup test fixtures."""
        self.settings = BotSettings(
            dry_run=True,
            max_total_exposure=Decimal("1000000")
        )
        self.executor = TradeExecutor(self.settings)

        self.config = CommodityConfig(
            symbol="GOLD",
            spot_api_url="http://test",
            futures_api_url="http://test",
            annual_interest_rate=Decimal("0.05"),
            annual_storage_cost_rate=Decimal("0.01"),
            annual_dividend_yield=Decimal("0.0"),
            contract_size=Decimal("100"),
            min_profit_threshold=Decimal("0.005"),
            max_position_size=10
        )

        # Create a sample opportunity
        self.opportunity = ArbitrageOpportunity(
            symbol="GOLD",
            spot_price=SpotPrice(
                symbol="GOLD",
                price=Decimal("2000.00"),
                timestamp=datetime.utcnow(),
                source="test"
            ),
            futures_contract=FuturesContract(
                symbol="GOLD",
                contract_code="GCM24",
                expiration_date=(datetime.utcnow() + timedelta(days=90)).date(),
                price=Decimal("2050.00"),
                timestamp=datetime.utcnow(),
                source="test",
                contract_size=Decimal("100")
            ),
            cost_of_carry=CostOfCarry(
                spot_price=Decimal("2000.00"),
                days_to_expiration=90,
                interest_cost=Decimal("24.66"),
                storage_cost=Decimal("4.93"),
                dividend_yield=Decimal("0"),
                total_cost_of_carry=Decimal("29.59"),
                theoretical_futures_price=Decimal("2029.59")
            ),
            actual_futures_price=Decimal("2050.00"),
            theoretical_futures_price=Decimal("2029.59"),
            price_difference=Decimal("20.41"),
            profit_percentage=Decimal("0.0101"),
            expected_profit_per_contract=Decimal("2041.00"),
            is_profitable=True
        )

    def test_calculate_position_size(self):
        """Test position size calculation."""
        size = self.executor.calculate_position_size(self.opportunity, self.config)

        # Should be limited by max_position_size (10 contracts)
        assert size > 0
        assert size <= self.config.max_position_size

    def test_calculate_position_size_capital_limited(self):
        """Test position size when limited by capital."""
        self.settings.max_total_exposure = Decimal("100000")
        executor = TradeExecutor(self.settings)

        size = executor.calculate_position_size(self.opportunity, self.config)

        # Should be limited by capital (100000 / (2000 * 100) = 0.5)
        # But we need at least 1 contract value (200000), so 0 contracts
        assert size == 0

    def test_validate_risk_limits_within_limits(self):
        """Test risk validation passes when within limits."""
        # Should not raise exception
        self.executor.validate_risk_limits(self.opportunity, 5, self.config)

    def test_validate_risk_limits_exceeds_position_size(self):
        """Test risk validation fails when exceeding position size."""
        with pytest.raises(RiskLimitExceeded):
            self.executor.validate_risk_limits(self.opportunity, 15, self.config)

    def test_validate_risk_limits_exceeds_exposure(self):
        """Test risk validation fails when exceeding total exposure."""
        self.settings.max_total_exposure = Decimal("100000")
        executor = TradeExecutor(self.settings)

        with pytest.raises(RiskLimitExceeded):
            executor.validate_risk_limits(self.opportunity, 5, self.config)

    @pytest.mark.asyncio
    async def test_execute_arbitrage_dry_run(self):
        """Test trade execution in dry run mode."""
        trade = await self.executor.execute_arbitrage(
            self.opportunity, self.config, num_contracts=1
        )

        assert trade.status == OrderStatus.FILLED
        assert trade.dry_run is True
        assert trade.spot_quantity == Decimal("100")
        assert trade.futures_quantity == 1
        assert trade.expected_profit == Decimal("2041.00")
        assert "DRY_RUN" in trade.notes

    @pytest.mark.asyncio
    async def test_execute_arbitrage_creates_position(self):
        """Test that execution creates a position."""
        await self.executor.execute_arbitrage(
            self.opportunity, self.config, num_contracts=1
        )

        positions = self.executor.position_manager.get_active_positions()
        assert len(positions) == 1

        position = positions[0]
        assert position.symbol == "GOLD"
        assert position.spot_quantity == Decimal("100")
        assert position.futures_quantity == 1

    @pytest.mark.asyncio
    async def test_execute_arbitrage_no_capacity(self):
        """Test execution fails when no capacity available."""
        with pytest.raises(ExecutionError):
            await self.executor.execute_arbitrage(
                self.opportunity, self.config, num_contracts=0
            )

    def test_get_execution_summary(self):
        """Test execution summary generation."""
        summary = self.executor.get_execution_summary()

        assert "total_trades" in summary
        assert "active_positions" in summary
        assert "total_exposure" in summary
        assert "total_expected_profit" in summary
