"""
Cost of Carry Calculator for futures pricing.

The theoretical futures price is calculated using the cost-of-carry model:
F = S * e^((r + s - y) * T)

Where:
- F = Theoretical futures price
- S = Spot price
- r = Risk-free interest rate (annualized)
- s = Storage cost rate (annualized)
- y = Convenience yield / dividend yield (annualized)
- T = Time to expiration (in years)

For simplicity, we use discrete compounding:
F = S * (1 + (r + s - y) * T)
"""

from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime, date
import math

from .models import SpotPrice, FuturesContract, CostOfCarry, ArbitrageOpportunity
from .config import CommodityConfig


class CostOfCarryCalculator:
    """Calculates the theoretical futures price and cost of carry."""

    def __init__(self, use_continuous_compounding: bool = False):
        """
        Initialize the calculator.

        Args:
            use_continuous_compounding: If True, use continuous compounding (e^rt).
                                       If False, use simple interest (1 + rt).
        """
        self.use_continuous_compounding = use_continuous_compounding

    def calculate_days_to_expiration(
        self, expiration_date: date, from_date: date = None
    ) -> int:
        """Calculate the number of days until contract expiration."""
        if from_date is None:
            from_date = datetime.utcnow().date()

        delta = expiration_date - from_date
        return max(0, delta.days)

    def calculate_time_to_expiration_years(
        self, expiration_date: date, from_date: date = None
    ) -> Decimal:
        """Calculate time to expiration in years."""
        days = self.calculate_days_to_expiration(expiration_date, from_date)
        return Decimal(str(days)) / Decimal("365")

    def calculate_cost_of_carry(
        self,
        spot_price: Decimal,
        expiration_date: date,
        annual_interest_rate: Decimal,
        annual_storage_cost_rate: Decimal,
        annual_dividend_yield: Decimal = Decimal("0"),
        from_date: date = None
    ) -> CostOfCarry:
        """
        Calculate the complete cost of carry breakdown.

        Args:
            spot_price: Current spot price
            expiration_date: Futures contract expiration date
            annual_interest_rate: Annual risk-free rate (e.g., 0.05 for 5%)
            annual_storage_cost_rate: Annual storage cost as fraction of spot
            annual_dividend_yield: Annual convenience/dividend yield
            from_date: Date to calculate from (defaults to today)

        Returns:
            CostOfCarry object with all components
        """
        days = self.calculate_days_to_expiration(expiration_date, from_date)
        T = self.calculate_time_to_expiration_years(expiration_date, from_date)

        # Calculate individual cost components
        interest_cost = spot_price * annual_interest_rate * T
        storage_cost = spot_price * annual_storage_cost_rate * T
        dividend_yield_amount = spot_price * annual_dividend_yield * T

        # Total cost of carry
        total_cost = interest_cost + storage_cost - dividend_yield_amount

        # Theoretical futures price
        if self.use_continuous_compounding:
            # F = S * e^((r + s - y) * T)
            net_rate = float(annual_interest_rate + annual_storage_cost_rate - annual_dividend_yield)
            time_years = float(T)
            multiplier = Decimal(str(math.exp(net_rate * time_years)))
            theoretical_price = spot_price * multiplier
        else:
            # F = S * (1 + (r + s - y) * T)
            theoretical_price = spot_price + total_cost

        # Round to 2 decimal places
        precision = Decimal("0.01")

        return CostOfCarry(
            spot_price=spot_price.quantize(precision, ROUND_HALF_UP),
            days_to_expiration=days,
            interest_cost=interest_cost.quantize(precision, ROUND_HALF_UP),
            storage_cost=storage_cost.quantize(precision, ROUND_HALF_UP),
            dividend_yield=dividend_yield_amount.quantize(precision, ROUND_HALF_UP),
            total_cost_of_carry=total_cost.quantize(precision, ROUND_HALF_UP),
            theoretical_futures_price=theoretical_price.quantize(precision, ROUND_HALF_UP)
        )

    def calculate_theoretical_price(
        self,
        spot_price: Decimal,
        days_to_expiration: int,
        annual_interest_rate: Decimal,
        annual_storage_cost_rate: Decimal,
        annual_dividend_yield: Decimal = Decimal("0")
    ) -> Decimal:
        """
        Quick calculation of theoretical futures price.

        Args:
            spot_price: Current spot price
            days_to_expiration: Days until expiration
            annual_interest_rate: Annual risk-free rate
            annual_storage_cost_rate: Annual storage cost rate
            annual_dividend_yield: Annual dividend/convenience yield

        Returns:
            Theoretical futures price
        """
        T = Decimal(str(days_to_expiration)) / Decimal("365")

        if self.use_continuous_compounding:
            net_rate = float(annual_interest_rate + annual_storage_cost_rate - annual_dividend_yield)
            time_years = float(T)
            multiplier = Decimal(str(math.exp(net_rate * time_years)))
            theoretical_price = spot_price * multiplier
        else:
            net_cost = spot_price * (annual_interest_rate + annual_storage_cost_rate - annual_dividend_yield) * T
            theoretical_price = spot_price + net_cost

        return theoretical_price.quantize(Decimal("0.01"), ROUND_HALF_UP)


class ArbitrageAnalyzer:
    """Analyzes market data to identify arbitrage opportunities."""

    def __init__(self, calculator: CostOfCarryCalculator = None):
        """
        Initialize the analyzer.

        Args:
            calculator: CostOfCarryCalculator instance (creates default if None)
        """
        self.calculator = calculator or CostOfCarryCalculator()

    def analyze_opportunity(
        self,
        spot: SpotPrice,
        futures: FuturesContract,
        config: CommodityConfig
    ) -> ArbitrageOpportunity:
        """
        Analyze a specific spot/futures pair for arbitrage opportunity.

        Args:
            spot: Current spot price
            futures: Futures contract to analyze
            config: Commodity configuration with cost parameters

        Returns:
            ArbitrageOpportunity object with analysis results
        """
        # Calculate cost of carry
        cost_of_carry = self.calculator.calculate_cost_of_carry(
            spot_price=spot.price,
            expiration_date=futures.expiration_date,
            annual_interest_rate=config.annual_interest_rate,
            annual_storage_cost_rate=config.annual_storage_cost_rate,
            annual_dividend_yield=config.annual_dividend_yield
        )

        # Compare actual vs theoretical price
        actual_price = futures.price
        theoretical_price = cost_of_carry.theoretical_futures_price

        price_difference = actual_price - theoretical_price

        # Calculate profit percentage
        if theoretical_price > 0:
            profit_percentage = (price_difference / theoretical_price).quantize(
                Decimal("0.0001"), ROUND_HALF_UP
            )
        else:
            profit_percentage = Decimal("0")

        # Calculate expected profit per contract
        # Profit = (Actual Futures Price - Theoretical Price) * Contract Size
        expected_profit_per_contract = price_difference * config.contract_size

        # Determine if profitable (exceeds minimum threshold)
        is_profitable = profit_percentage >= config.min_profit_threshold

        return ArbitrageOpportunity(
            symbol=spot.symbol,
            spot_price=spot,
            futures_contract=futures,
            cost_of_carry=cost_of_carry,
            actual_futures_price=actual_price,
            theoretical_futures_price=theoretical_price,
            price_difference=price_difference.quantize(Decimal("0.01")),
            profit_percentage=profit_percentage,
            expected_profit_per_contract=expected_profit_per_contract.quantize(
                Decimal("0.01")
            ),
            timestamp=datetime.utcnow(),
            is_profitable=is_profitable
        )

    def find_best_opportunity(
        self,
        spot: SpotPrice,
        futures_contracts: list[FuturesContract],
        config: CommodityConfig
    ) -> ArbitrageOpportunity | None:
        """
        Find the best arbitrage opportunity from multiple futures contracts.

        Args:
            spot: Current spot price
            futures_contracts: List of available futures contracts
            config: Commodity configuration

        Returns:
            Best profitable opportunity, or None if no profitable opportunity exists
        """
        best_opportunity = None
        best_profit = Decimal("-1")

        for futures in futures_contracts:
            opportunity = self.analyze_opportunity(spot, futures, config)

            if opportunity.is_profitable and opportunity.profit_percentage > best_profit:
                best_profit = opportunity.profit_percentage
                best_opportunity = opportunity

        return best_opportunity

    def analyze_all_opportunities(
        self,
        spot: SpotPrice,
        futures_contracts: list[FuturesContract],
        config: CommodityConfig
    ) -> list[ArbitrageOpportunity]:
        """
        Analyze all futures contracts for arbitrage opportunities.

        Args:
            spot: Current spot price
            futures_contracts: List of available futures contracts
            config: Commodity configuration

        Returns:
            List of all opportunities sorted by profit percentage (descending)
        """
        opportunities = []

        for futures in futures_contracts:
            opportunity = self.analyze_opportunity(spot, futures, config)
            opportunities.append(opportunity)

        # Sort by profit percentage (highest first)
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)

        return opportunities


def calculate_breakeven_threshold(
    transaction_costs: Decimal,
    contract_size: Decimal,
    spot_price: Decimal
) -> Decimal:
    """
    Calculate the minimum profit percentage needed to cover transaction costs.

    Args:
        transaction_costs: Total round-trip transaction costs (both legs)
        contract_size: Size of one futures contract
        spot_price: Current spot price

    Returns:
        Minimum profit percentage needed to break even
    """
    total_position_value = contract_size * spot_price
    breakeven_pct = transaction_costs / total_position_value
    return breakeven_pct.quantize(Decimal("0.0001"), ROUND_HALF_UP)
