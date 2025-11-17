"""
Tests for cost of carry calculator.
"""

import pytest
from decimal import Decimal
from datetime import date, datetime, timedelta

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from cashandcary.calculator import CostOfCarryCalculator, ArbitrageAnalyzer
from cashandcary.models import SpotPrice, FuturesContract
from cashandcary.config import CommodityConfig


class TestCostOfCarryCalculator:
    """Test cases for CostOfCarryCalculator."""

    def setup_method(self):
        """Setup test fixtures."""
        self.calculator = CostOfCarryCalculator(use_continuous_compounding=False)

    def test_days_to_expiration(self):
        """Test days to expiration calculation."""
        today = date(2024, 1, 1)
        expiration = date(2024, 4, 1)

        days = self.calculator.calculate_days_to_expiration(expiration, today)
        assert days == 91

    def test_days_to_expiration_past(self):
        """Test days to expiration when date is past."""
        today = date(2024, 4, 1)
        expiration = date(2024, 1, 1)

        days = self.calculator.calculate_days_to_expiration(expiration, today)
        assert days == 0

    def test_time_to_expiration_years(self):
        """Test time to expiration in years."""
        today = date(2024, 1, 1)
        expiration = date(2024, 7, 1)  # 182 days

        years = self.calculator.calculate_time_to_expiration_years(expiration, today)
        expected = Decimal("182") / Decimal("365")
        assert years == expected

    def test_cost_of_carry_calculation(self):
        """Test complete cost of carry calculation."""
        spot_price = Decimal("2000.00")
        expiration = date(2024, 4, 1)
        today = date(2024, 1, 1)
        interest_rate = Decimal("0.05")
        storage_rate = Decimal("0.01")
        dividend_yield = Decimal("0.0")

        result = self.calculator.calculate_cost_of_carry(
            spot_price=spot_price,
            expiration_date=expiration,
            annual_interest_rate=interest_rate,
            annual_storage_cost_rate=storage_rate,
            annual_dividend_yield=dividend_yield,
            from_date=today
        )

        assert result.spot_price == spot_price
        assert result.days_to_expiration == 91

        # Expected: 2000 * (0.05 + 0.01) * (91/365) = 29.92
        expected_cost = spot_price * (interest_rate + storage_rate) * (Decimal("91") / Decimal("365"))
        assert result.total_cost_of_carry == expected_cost.quantize(Decimal("0.01"))

        # Theoretical price = spot + cost
        expected_price = spot_price + expected_cost
        assert result.theoretical_futures_price == expected_price.quantize(Decimal("0.01"))

    def test_cost_of_carry_with_dividend(self):
        """Test cost of carry with dividend yield."""
        spot_price = Decimal("100.00")
        expiration = date(2024, 7, 1)
        today = date(2024, 1, 1)
        interest_rate = Decimal("0.05")
        storage_rate = Decimal("0.0")
        dividend_yield = Decimal("0.02")

        result = self.calculator.calculate_cost_of_carry(
            spot_price=spot_price,
            expiration_date=expiration,
            annual_interest_rate=interest_rate,
            annual_storage_cost_rate=storage_rate,
            annual_dividend_yield=dividend_yield,
            from_date=today
        )

        # Net cost should be lower due to dividend yield
        days = 182
        T = Decimal(str(days)) / Decimal("365")
        expected_cost = spot_price * (interest_rate + storage_rate - dividend_yield) * T
        assert result.total_cost_of_carry == expected_cost.quantize(Decimal("0.01"))

    def test_theoretical_price_quick_calculation(self):
        """Test quick theoretical price calculation."""
        spot = Decimal("1500.00")
        days = 90
        rate = Decimal("0.05")
        storage = Decimal("0.005")

        price = self.calculator.calculate_theoretical_price(
            spot, days, rate, storage
        )

        # Expected: 1500 * (1 + (0.05 + 0.005) * 90/365) = 1520.34
        T = Decimal("90") / Decimal("365")
        expected = spot + spot * (rate + storage) * T
        assert price == expected.quantize(Decimal("0.01"))


class TestArbitrageAnalyzer:
    """Test cases for ArbitrageAnalyzer."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyzer = ArbitrageAnalyzer()

        self.spot = SpotPrice(
            symbol="GOLD",
            price=Decimal("2000.00"),
            timestamp=datetime.utcnow(),
            source="test"
        )

        self.config = CommodityConfig(
            symbol="GOLD",
            spot_api_url="http://test",
            futures_api_url="http://test",
            annual_interest_rate=Decimal("0.05"),
            annual_storage_cost_rate=Decimal("0.01"),
            annual_dividend_yield=Decimal("0.0"),
            contract_size=Decimal("100"),
            min_profit_threshold=Decimal("0.005"),  # 0.5%
            max_position_size=10
        )

    def test_analyze_profitable_opportunity(self):
        """Test identifying a profitable opportunity."""
        # Create overpriced futures contract
        expiration = (datetime.utcnow() + timedelta(days=90)).date()

        futures = FuturesContract(
            symbol="GOLD",
            contract_code="GCM24",
            expiration_date=expiration,
            price=Decimal("2050.00"),  # Overpriced
            timestamp=datetime.utcnow(),
            source="test",
            contract_size=Decimal("100")
        )

        opp = self.analyzer.analyze_opportunity(self.spot, futures, self.config)

        # Should be profitable (futures price > theoretical)
        assert opp.is_profitable is True
        assert opp.actual_futures_price > opp.theoretical_futures_price
        assert opp.price_difference > Decimal("0")
        assert opp.expected_profit_per_contract > Decimal("0")

    def test_analyze_unprofitable_opportunity(self):
        """Test identifying an unprofitable opportunity."""
        expiration = (datetime.utcnow() + timedelta(days=90)).date()

        # Underpriced futures (no arbitrage)
        futures = FuturesContract(
            symbol="GOLD",
            contract_code="GCM24",
            expiration_date=expiration,
            price=Decimal("2010.00"),  # Close to theoretical
            timestamp=datetime.utcnow(),
            source="test",
            contract_size=Decimal("100")
        )

        opp = self.analyzer.analyze_opportunity(self.spot, futures, self.config)

        # Should not meet minimum threshold
        assert opp.is_profitable is False

    def test_find_best_opportunity(self):
        """Test finding the best opportunity from multiple contracts."""
        now = datetime.utcnow()

        contracts = [
            FuturesContract(
                symbol="GOLD",
                contract_code="GCM24",
                expiration_date=(now + timedelta(days=30)).date(),
                price=Decimal("2020.00"),
                timestamp=now,
                source="test",
                contract_size=Decimal("100")
            ),
            FuturesContract(
                symbol="GOLD",
                contract_code="GCQ24",
                expiration_date=(now + timedelta(days=90)).date(),
                price=Decimal("2060.00"),  # Most overpriced
                timestamp=now,
                source="test",
                contract_size=Decimal("100")
            ),
            FuturesContract(
                symbol="GOLD",
                contract_code="GCZ24",
                expiration_date=(now + timedelta(days=180)).date(),
                price=Decimal("2050.00"),
                timestamp=now,
                source="test",
                contract_size=Decimal("100")
            ),
        ]

        best = self.analyzer.find_best_opportunity(self.spot, contracts, self.config)

        assert best is not None
        assert best.is_profitable is True
        # Should be one of the overpriced ones
        assert best.profit_percentage > Decimal("0")

    def test_analyze_all_opportunities(self):
        """Test analyzing all contracts and sorting by profit."""
        now = datetime.utcnow()

        contracts = [
            FuturesContract(
                symbol="GOLD",
                contract_code="GCM24",
                expiration_date=(now + timedelta(days=30)).date(),
                price=Decimal("2015.00"),
                timestamp=now,
                source="test",
                contract_size=Decimal("100")
            ),
            FuturesContract(
                symbol="GOLD",
                contract_code="GCQ24",
                expiration_date=(now + timedelta(days=90)).date(),
                price=Decimal("2050.00"),
                timestamp=now,
                source="test",
                contract_size=Decimal("100")
            ),
        ]

        opps = self.analyzer.analyze_all_opportunities(self.spot, contracts, self.config)

        assert len(opps) == 2
        # Should be sorted by profit percentage (descending)
        assert opps[0].profit_percentage >= opps[1].profit_percentage
