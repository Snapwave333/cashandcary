"""
Main Arbitrage Bot - Orchestrates the cash-and-carry arbitrage strategy.
"""

import asyncio
import signal
from datetime import datetime
from decimal import Decimal
import logging
from typing import Optional

from .config import BotSettings, CommodityConfig, load_commodity_configs
from .data_feeds import CombinedDataFeed, DataFeedError
from .calculator import ArbitrageAnalyzer
from .executor import TradeExecutor, PositionManager, ExecutionError, RiskLimitExceeded
from .models import ArbitrageOpportunity, MarketData


logger = logging.getLogger(__name__)


class ArbitrageBot:
    """
    Main arbitrage bot that monitors markets and executes trades.

    The bot continuously:
    1. Fetches spot and futures prices
    2. Calculates cost of carry
    3. Identifies arbitrage opportunities
    4. Executes profitable trades
    """

    def __init__(
        self,
        settings: BotSettings = None,
        commodity_configs: list[CommodityConfig] = None,
        use_mock_data: bool = False
    ):
        """
        Initialize the arbitrage bot.

        Args:
            settings: Bot settings (loads from env if None)
            commodity_configs: List of commodity configurations
            use_mock_data: Use mock data feeds for testing
        """
        self.settings = settings or BotSettings()
        self.commodity_configs = commodity_configs or load_commodity_configs()

        self.data_feed = CombinedDataFeed(self.settings, use_mock=use_mock_data)
        self.analyzer = ArbitrageAnalyzer()
        self.position_manager = PositionManager()
        self.executor = TradeExecutor(self.settings, self.position_manager)

        self._running = False
        self._shutdown_event = asyncio.Event()

        # Statistics
        self.stats = {
            "iterations": 0,
            "opportunities_found": 0,
            "trades_executed": 0,
            "total_profit_potential": Decimal("0"),
            "errors": 0,
            "start_time": None,
        }

        logger.info(f"Initialized ArbitrageBot with {len(self.commodity_configs)} commodities")
        logger.info(f"Dry run mode: {self.settings.dry_run}")

    def _setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating shutdown...")
            self._running = False
            self._shutdown_event.set()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    async def monitor_cycle(self) -> list[ArbitrageOpportunity]:
        """
        Execute one monitoring cycle.

        Returns:
            List of identified arbitrage opportunities
        """
        all_opportunities = []

        logger.debug("Starting monitoring cycle...")

        # Fetch market data for all commodities
        try:
            market_data_list = await self.data_feed.fetch_all_commodities(
                self.commodity_configs
            )
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            self.stats["errors"] += 1
            return []

        # Analyze each commodity
        for market_data, config in zip(market_data_list, self.commodity_configs):
            try:
                opportunities = self._analyze_commodity(market_data, config)
                all_opportunities.extend(opportunities)
            except Exception as e:
                logger.error(f"Error analyzing {config.symbol}: {e}")
                self.stats["errors"] += 1

        return all_opportunities

    def _analyze_commodity(
        self, market_data: MarketData, config: CommodityConfig
    ) -> list[ArbitrageOpportunity]:
        """
        Analyze a single commodity for arbitrage opportunities.

        Args:
            market_data: Current market data
            config: Commodity configuration

        Returns:
            List of profitable opportunities
        """
        opportunities = self.analyzer.analyze_all_opportunities(
            market_data.spot, market_data.futures, config
        )

        profitable = [opp for opp in opportunities if opp.is_profitable]

        if profitable:
            logger.info(
                f"{config.symbol}: Found {len(profitable)} profitable opportunities"
            )
            for opp in profitable:
                logger.info(
                    f"  {opp.futures_contract.contract_code}: "
                    f"Profit: {opp.profit_percentage:.4%} "
                    f"(${opp.expected_profit_per_contract}/contract)"
                )

        return profitable

    async def execute_opportunities(
        self, opportunities: list[ArbitrageOpportunity]
    ) -> int:
        """
        Execute trades for profitable opportunities.

        Args:
            opportunities: List of opportunities to execute

        Returns:
            Number of successful trades
        """
        if not opportunities:
            return 0

        successful_trades = 0

        # Sort by profit percentage to prioritize best opportunities
        opportunities.sort(key=lambda x: x.profit_percentage, reverse=True)

        for opportunity in opportunities:
            # Find the config for this commodity
            config = next(
                (c for c in self.commodity_configs if c.symbol == opportunity.symbol),
                None
            )

            if not config:
                logger.error(f"No config found for {opportunity.symbol}")
                continue

            try:
                trade = await self.executor.execute_arbitrage(opportunity, config)
                if trade.status.value == "FILLED":
                    successful_trades += 1
                    self.stats["total_profit_potential"] += trade.expected_profit
                    logger.info(f"Successfully executed trade {trade.trade_id}")
            except RiskLimitExceeded as e:
                logger.warning(f"Skipping {opportunity.symbol}: {e}")
            except ExecutionError as e:
                logger.error(f"Failed to execute {opportunity.symbol}: {e}")
                self.stats["errors"] += 1
            except Exception as e:
                logger.error(f"Unexpected error executing trade: {e}")
                self.stats["errors"] += 1

        return successful_trades

    async def run(self):
        """
        Main bot loop - continuously monitor and trade.
        """
        self._setup_signal_handlers()
        self._running = True
        self.stats["start_time"] = datetime.utcnow()

        logger.info("=" * 60)
        logger.info("Cash-and-Carry Arbitrage Bot Starting")
        logger.info(f"Monitoring interval: {self.settings.monitoring_interval_seconds}s")
        logger.info(f"Max total exposure: ${self.settings.max_total_exposure}")
        logger.info(f"Commodities: {[c.symbol for c in self.commodity_configs]}")
        logger.info("=" * 60)

        # Load previous state if exists
        try:
            self.position_manager.load_state("state/positions.json")
        except Exception as e:
            logger.warning(f"Could not load previous state: {e}")

        while self._running:
            try:
                self.stats["iterations"] += 1
                logger.info(f"\n--- Cycle {self.stats['iterations']} ---")

                # Monitor for opportunities
                opportunities = await self.monitor_cycle()
                self.stats["opportunities_found"] += len(opportunities)

                # Execute trades
                if opportunities:
                    trades = await self.execute_opportunities(opportunities)
                    self.stats["trades_executed"] += trades
                else:
                    logger.debug("No profitable opportunities found")

                # Save state
                try:
                    import os
                    os.makedirs("state", exist_ok=True)
                    self.position_manager.save_state("state/positions.json")
                except Exception as e:
                    logger.error(f"Failed to save state: {e}")

                # Print periodic summary
                if self.stats["iterations"] % 10 == 0:
                    self._print_summary()

                # Wait for next cycle or shutdown
                try:
                    await asyncio.wait_for(
                        self._shutdown_event.wait(),
                        timeout=self.settings.monitoring_interval_seconds
                    )
                    break  # Shutdown requested
                except asyncio.TimeoutError:
                    pass  # Normal timeout, continue loop

            except Exception as e:
                logger.error(f"Error in monitoring cycle: {e}")
                self.stats["errors"] += 1
                await asyncio.sleep(5)  # Brief pause before retry

        # Cleanup
        logger.info("Shutting down...")
        self._print_summary()
        self.position_manager.save_state("state/positions.json")
        logger.info("Arbitrage bot stopped")

    def _print_summary(self):
        """Print bot statistics summary."""
        runtime = datetime.utcnow() - self.stats["start_time"] if self.stats["start_time"] else "N/A"

        logger.info("\n" + "=" * 60)
        logger.info("BOT STATISTICS")
        logger.info("=" * 60)
        logger.info(f"Runtime: {runtime}")
        logger.info(f"Total iterations: {self.stats['iterations']}")
        logger.info(f"Opportunities found: {self.stats['opportunities_found']}")
        logger.info(f"Trades executed: {self.stats['trades_executed']}")
        logger.info(f"Total profit potential: ${self.stats['total_profit_potential']:.2f}")
        logger.info(f"Active positions: {len(self.position_manager.get_active_positions())}")
        logger.info(f"Total exposure: ${self.position_manager.get_total_exposure():.2f}")
        logger.info(f"Errors: {self.stats['errors']}")
        logger.info("=" * 60 + "\n")

    async def run_once(self) -> dict:
        """
        Run a single monitoring and execution cycle.

        Useful for testing or manual operation.

        Returns:
            Summary of the cycle results
        """
        opportunities = await self.monitor_cycle()
        trades = await self.execute_opportunities(opportunities)

        return {
            "opportunities": len(opportunities),
            "trades_executed": trades,
            "opportunities_data": [opp.model_dump() for opp in opportunities],
        }

    def stop(self):
        """Stop the bot gracefully."""
        logger.info("Stop requested")
        self._running = False
        self._shutdown_event.set()


async def main():
    """Main entry point for the bot."""
    import sys

    # Setup basic logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler("arbitrage_bot.log"),
        ],
    )

    # Load configuration
    settings = BotSettings()
    commodities = load_commodity_configs()

    # Determine if using mock data
    use_mock = settings.dry_run or "--mock" in sys.argv

    # Create and run bot
    bot = ArbitrageBot(
        settings=settings,
        commodity_configs=commodities,
        use_mock_data=use_mock
    )

    if "--once" in sys.argv:
        # Run single cycle
        result = await bot.run_once()
        print(f"Results: {result}")
    else:
        # Run continuous monitoring
        await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
