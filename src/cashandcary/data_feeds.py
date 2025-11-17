"""
Data feed module for fetching spot and futures prices.
"""

import aiohttp
import asyncio
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional
import logging

from .models import SpotPrice, FuturesContract, MarketData
from .config import CommodityConfig, BotSettings


logger = logging.getLogger(__name__)


class DataFeedError(Exception):
    """Exception raised when data feed fails."""
    pass


class BaseDataFeed:
    """Base class for data feeds."""

    def __init__(self, settings: BotSettings):
        self.settings = settings
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            headers=self._get_headers(),
            timeout=aiohttp.ClientTimeout(total=30)
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    def _get_headers(self) -> dict:
        """Get API headers with authentication."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers


class SpotPriceFeed(BaseDataFeed):
    """Fetches spot prices for commodities."""

    async def fetch_spot_price(self, config: CommodityConfig) -> SpotPrice:
        """
        Fetch current spot price for a commodity.

        Args:
            config: Commodity configuration

        Returns:
            SpotPrice object with current price data
        """
        if not self.session:
            raise DataFeedError("Session not initialized. Use async context manager.")

        try:
            logger.debug(f"Fetching spot price for {config.symbol}")
            async with self.session.get(config.spot_api_url) as response:
                if response.status != 200:
                    raise DataFeedError(
                        f"Failed to fetch spot price: HTTP {response.status}"
                    )
                data = await response.json()
                return self._parse_spot_response(config.symbol, data)
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching spot price: {e}")
            raise DataFeedError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error fetching spot price: {e}")
            raise DataFeedError(f"Failed to fetch spot price: {e}")

    def _parse_spot_response(self, symbol: str, data: dict) -> SpotPrice:
        """
        Parse spot price API response.

        Override this method for specific API formats.
        """
        # Generic parser - adjust based on actual API response format
        price = Decimal(str(data.get("price", data.get("spot", data.get("last", 0)))))
        timestamp_str = data.get("timestamp", data.get("time", datetime.utcnow().isoformat()))

        if isinstance(timestamp_str, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except ValueError:
                timestamp = datetime.utcnow()
        else:
            timestamp = datetime.utcnow()

        return SpotPrice(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
            source=data.get("source", "api"),
            currency=data.get("currency", "USD")
        )


class FuturesPriceFeed(BaseDataFeed):
    """Fetches futures contract prices."""

    async def fetch_futures_contracts(
        self, config: CommodityConfig
    ) -> list[FuturesContract]:
        """
        Fetch available futures contracts for a commodity.

        Args:
            config: Commodity configuration

        Returns:
            List of FuturesContract objects
        """
        if not self.session:
            raise DataFeedError("Session not initialized. Use async context manager.")

        try:
            logger.debug(f"Fetching futures contracts for {config.symbol}")
            async with self.session.get(config.futures_api_url) as response:
                if response.status != 200:
                    raise DataFeedError(
                        f"Failed to fetch futures: HTTP {response.status}"
                    )
                data = await response.json()
                return self._parse_futures_response(config, data)
        except aiohttp.ClientError as e:
            logger.error(f"Network error fetching futures: {e}")
            raise DataFeedError(f"Network error: {e}")
        except Exception as e:
            logger.error(f"Error fetching futures: {e}")
            raise DataFeedError(f"Failed to fetch futures: {e}")

    def _parse_futures_response(
        self, config: CommodityConfig, data: dict
    ) -> list[FuturesContract]:
        """
        Parse futures API response.

        Override this method for specific API formats.
        """
        contracts = []

        # Handle list of contracts
        contract_list = data.get("contracts", data.get("futures", [data]))
        if not isinstance(contract_list, list):
            contract_list = [contract_list]

        for contract_data in contract_list:
            try:
                price = Decimal(
                    str(contract_data.get("price", contract_data.get("last", 0)))
                )

                # Parse expiration date
                exp_str = contract_data.get("expiration", contract_data.get("expiry"))
                if isinstance(exp_str, str):
                    expiration = date.fromisoformat(exp_str[:10])
                else:
                    # Default to 3 months from now if not specified
                    expiration = (datetime.utcnow() + timedelta(days=90)).date()

                # Parse timestamp
                timestamp_str = contract_data.get(
                    "timestamp", datetime.utcnow().isoformat()
                )
                if isinstance(timestamp_str, str):
                    try:
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        )
                    except ValueError:
                        timestamp = datetime.utcnow()
                else:
                    timestamp = datetime.utcnow()

                contract = FuturesContract(
                    symbol=config.symbol,
                    contract_code=contract_data.get("code", f"{config.symbol}_FUT"),
                    expiration_date=expiration,
                    price=price,
                    timestamp=timestamp,
                    source=contract_data.get("source", "api"),
                    contract_size=config.contract_size,
                    currency=contract_data.get("currency", "USD"),
                    open_interest=contract_data.get("open_interest"),
                    volume=contract_data.get("volume")
                )
                contracts.append(contract)
            except Exception as e:
                logger.warning(f"Failed to parse contract: {e}")
                continue

        return contracts


class MockDataFeed(BaseDataFeed):
    """Mock data feed for testing and dry-run mode."""

    def __init__(self, settings: BotSettings):
        super().__init__(settings)
        self._mock_prices = {
            "GOLD": {
                "spot": Decimal("2000.00"),
                "futures_base": Decimal("2015.00")
            },
            "OIL": {
                "spot": Decimal("75.00"),
                "futures_base": Decimal("76.50")
            }
        }

    async def __aenter__(self):
        # Don't create actual session for mock
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

    async def fetch_spot_price(self, config: CommodityConfig) -> SpotPrice:
        """Generate mock spot price."""
        import random

        base_price = self._mock_prices.get(
            config.symbol, {"spot": Decimal("100.00")}
        )["spot"]

        # Add small random variation
        variation = Decimal(str(random.uniform(-0.01, 0.01)))
        price = base_price * (1 + variation)

        return SpotPrice(
            symbol=config.symbol,
            price=price.quantize(Decimal("0.01")),
            timestamp=datetime.utcnow(),
            source="mock",
            currency="USD"
        )

    async def fetch_futures_contracts(
        self, config: CommodityConfig
    ) -> list[FuturesContract]:
        """Generate mock futures contracts."""
        import random

        base_futures = self._mock_prices.get(
            config.symbol, {"futures_base": Decimal("101.00")}
        )["futures_base"]

        contracts = []
        now = datetime.utcnow()

        # Generate contracts for next 3 months
        for months_ahead in [1, 2, 3]:
            expiration = (now + timedelta(days=30 * months_ahead)).date()

            # Add premium for longer-dated contracts
            time_premium = Decimal(str(months_ahead * 0.002))
            variation = Decimal(str(random.uniform(-0.005, 0.01)))
            price = base_futures * (1 + time_premium + variation)

            contract = FuturesContract(
                symbol=config.symbol,
                contract_code=f"{config.symbol}_{expiration.strftime('%b%y').upper()}",
                expiration_date=expiration,
                price=price.quantize(Decimal("0.01")),
                timestamp=now,
                source="mock",
                contract_size=config.contract_size,
                currency="USD",
                open_interest=random.randint(10000, 100000),
                volume=random.randint(1000, 50000)
            )
            contracts.append(contract)

        return contracts


class CombinedDataFeed:
    """Combines spot and futures feeds to get complete market data."""

    def __init__(self, settings: BotSettings, use_mock: bool = False):
        self.settings = settings
        self.use_mock = use_mock

    async def fetch_market_data(self, config: CommodityConfig) -> MarketData:
        """
        Fetch complete market data for a commodity.

        Args:
            config: Commodity configuration

        Returns:
            MarketData object with spot and futures prices
        """
        if self.use_mock:
            feed = MockDataFeed(self.settings)
            async with feed:
                spot = await feed.fetch_spot_price(config)
                futures = await feed.fetch_futures_contracts(config)
        else:
            async with SpotPriceFeed(self.settings) as spot_feed:
                spot = await spot_feed.fetch_spot_price(config)

            async with FuturesPriceFeed(self.settings) as futures_feed:
                futures = await futures_feed.fetch_futures_contracts(config)

        return MarketData(
            symbol=config.symbol,
            spot=spot,
            futures=futures,
            timestamp=datetime.utcnow()
        )

    async def fetch_all_commodities(
        self, configs: list[CommodityConfig]
    ) -> list[MarketData]:
        """
        Fetch market data for all configured commodities concurrently.

        Args:
            configs: List of commodity configurations

        Returns:
            List of MarketData objects
        """
        tasks = [self.fetch_market_data(config) for config in configs]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        market_data = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    f"Failed to fetch data for {configs[i].symbol}: {result}"
                )
            else:
                market_data.append(result)

        return market_data
