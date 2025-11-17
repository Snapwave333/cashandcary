#!/usr/bin/env python3
"""
Cash-and-Carry Arbitrage Bot - Main Entry Point

This bot monitors spot and futures prices to identify and execute
cash-and-carry arbitrage opportunities.
"""

import asyncio
import argparse
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from cashandcary.config import BotSettings, load_commodity_configs, create_sample_config
from cashandcary.bot import ArbitrageBot
from cashandcary.alerts import setup_logging, AlertManager


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Cash-and-Carry Futures Arbitrage Bot"
    )

    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock data feeds for testing"
    )

    parser.add_argument(
        "--once",
        action="store_true",
        help="Run single monitoring cycle and exit"
    )

    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Create sample configuration files"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simulate trades without executing"
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Monitoring interval in seconds"
    )

    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default=None,
        help="Logging level"
    )

    return parser.parse_args()


async def run_bot(args):
    """Run the arbitrage bot."""
    # Load settings
    settings = BotSettings()

    # Override with command line arguments
    if args.dry_run:
        settings.dry_run = True
    if args.interval:
        settings.monitoring_interval_seconds = args.interval
    if args.log_level:
        settings.log_level = args.log_level

    # Setup logging
    setup_logging(settings)

    # Load commodity configurations
    commodities = load_commodity_configs()

    # Determine if using mock data
    use_mock = args.mock or settings.dry_run

    # Create alert manager
    alert_manager = AlertManager(settings)

    # Create bot
    bot = ArbitrageBot(
        settings=settings,
        commodity_configs=commodities,
        use_mock_data=use_mock
    )

    # Run
    if args.once:
        print("Running single monitoring cycle...")
        result = await bot.run_once()
        print(f"\nResults:")
        print(f"  Opportunities found: {result['opportunities']}")
        print(f"  Trades executed: {result['trades_executed']}")

        if result['opportunities_data']:
            print("\nOpportunities:")
            for opp in result['opportunities_data']:
                print(f"  - {opp['symbol']} ({opp['futures_contract']['contract_code']})")
                print(f"    Profit: {opp['profit_percentage']:.4%}")
                print(f"    Expected: ${opp['expected_profit_per_contract']}/contract")
    else:
        print("Starting continuous monitoring...")
        await bot.run()


def main():
    """Main entry point."""
    args = parse_args()

    if args.init_config:
        print("Creating sample configuration files...")
        config_file, env_file = create_sample_config()
        print(f"Created: {config_file}")
        print(f"Created: {env_file}")
        print("\nEdit these files with your actual API credentials and parameters.")
        print("Copy .env.example to .env and fill in your values.")
        return

    # Run the bot
    try:
        asyncio.run(run_bot(args))
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error: {e}")
        raise


if __name__ == "__main__":
    main()
