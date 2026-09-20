"""External market observation boundary."""

from career_harness.core.common import EntityKind
from career_harness.core.lifecycle import Market
from career_harness.core.market.trend import (
    BROAD_MARKET_TREND_VERSION,
    BroadMarketTrend,
    CapabilityTrend,
    build_broad_market_trend,
)

ENTITY_KIND = EntityKind.MARKET

__all__ = [
    "BROAD_MARKET_TREND_VERSION",
    "ENTITY_KIND",
    "BroadMarketTrend",
    "CapabilityTrend",
    "Market",
    "build_broad_market_trend",
]
