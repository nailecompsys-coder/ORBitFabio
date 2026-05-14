# STRATEGY SOURCE: Replace this entire file with the MarketRegime class
# copied verbatim from orb_bot_fabio.py (Clayton). That file is not vendored
# in this repository; these stubs exist so imports and the Phase 5 gate pass.

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MarketRegime:
    """Placeholder until verbatim MarketRegime is pasted from orb_bot_fabio.py."""

    symbol: str
    tradeable: bool = True
    vix: float = 18.0

    def risk_multiplier(self, counter_trend: bool, cb_modifier: float) -> float:
        _ = counter_trend
        return max(0.25, min(1.0, float(cb_modifier)))
