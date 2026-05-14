# STRATEGY SOURCE: Replace with SignalEngine verbatim from orb_bot_fabio.py.

from __future__ import annotations

from typing import Any, Optional

import pandas as pd

from bot.regime import MarketRegime


class SignalEngine:
    """Placeholder until verbatim SignalEngine is pasted from orb_bot_fabio.py."""

    def __init__(self, regime: MarketRegime) -> None:
        self.regime = regime

    def check_breakout(self, df_5m: pd.DataFrame) -> Optional[str]:
        if df_5m is None or df_5m.empty:
            return None
        return None

    def is_counter_trend(self, direction: str) -> bool:
        _ = direction
        return False

    def exit_timeframe(self, df_5m: pd.DataFrame) -> Any:
        _ = df_5m
        return "3m"
