"""
Tests for the main arbitrage bot.
"""

import pytest
from decimal import Decimal
from datetime import datetime

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cashandcary.bot import ArbitrageBot
from cashandcary.config import BotSettings, CommodityConfig


class TestArbitrageBot:
    """Test cases for ArbitrageBot."""

    def setup_method(self):
        """Setup test fixtures."""
        self.settings = BotSettings(
            dry_run=True,
            monitoring_interval_seconds=1,
            max_total_exposure=Decimal("10000000")
        )

        self.commodities = [
            CommodityConfig(
                symbol="GOLD",
                spot_api_url="http://test/spot",
                futures_api_url="http://test/futures",
                annual_interest_rate=Decimal("0.05"),
                annual_storage_cost_rate=Decimal("0.01"),
                annual_dividend_yield=Decimal("0.0"),
                contract_size=Decimal("100"),
                min_profit_threshold=Decimal("0.005"),
                max_position_size=10
            )
        ]

    def test_bot_initialization(self):
        """Test bot initializes correctly."""
        bot = ArbitrageBot(
            settings=self.settings,
            commodity_configs=self.commodities,
            use_mock_data=True
        )

        assert bot.settings.dry_run is True
        assert len(bot.commodity_configs) == 1
        assert bot.stats["iterations"] == 0
        assert bot.stats["trades_executed"] == 0

    @pytest.mark.asyncio
    async def test_monitor_cycle_with_mock_data(self):
        """Test monitoring cycle with mock data."""
        bot = ArbitrageBot(
            settings=self.settings,
            commodity_configs=self.commodities,
            use_mock_data=True
        )

        opportunities = await bot.monitor_cycle()

        # Mock data may or may not produce opportunities
        assert isinstance(opportunities, list)

    @pytest.mark.asyncio
    async def test_run_once(self):
        """Test single cycle execution."""
        bot = ArbitrageBot(
            settings=self.settings,
            commodity_configs=self.commodities,
            use_mock_data=True
        )

        result = await bot.run_once()

        assert "opportunities" in result
        assert "trades_executed" in result
        assert "opportunities_data" in result
        assert isinstance(result["opportunities"], int)

    def test_bot_stats_initialization(self):
        """Test bot statistics are properly initialized."""
        bot = ArbitrageBot(
            settings=self.settings,
            commodity_configs=self.commodities,
            use_mock_data=True
        )

        assert bot.stats["iterations"] == 0
        assert bot.stats["opportunities_found"] == 0
        assert bot.stats["trades_executed"] == 0
        assert bot.stats["total_profit_potential"] == Decimal("0")
        assert bot.stats["errors"] == 0
        assert bot.stats["start_time"] is None

    def test_stop_bot(self):
        """Test bot can be stopped."""
        bot = ArbitrageBot(
            settings=self.settings,
            commodity_configs=self.commodities,
            use_mock_data=True
        )

        bot._running = True
        bot.stop()

        assert bot._running is False
        assert bot._shutdown_event.is_set() is True
