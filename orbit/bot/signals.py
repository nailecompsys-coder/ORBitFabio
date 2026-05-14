"""
SignalEngine — verbatim from orb_bot.py (Clayton).
"""

from __future__ import annotations

from typing import Optional

import pandas as pd
from moomoo import KLType

from bot.regime import EMA_GAP_TIGHT, EMA_GAP_WIDE, MarketRegime, ema

# ─── SIGNAL ENGINE ────────────────────────────────────────────────────────────
class SignalEngine:
    def __init__(self, regime: MarketRegime):
        self.regime = regime

    def check_breakout(self, df_5m: pd.DataFrame) -> Optional[str]:
        """Two consecutive 5-min closes outside OR."""
        if len(df_5m) < 3:
            return None
        c1, c2 = df_5m.iloc[-2], df_5m.iloc[-1]
        bull = (c1["close"] > self.regime.or_high) and (c2["close"] > self.regime.or_high)
        bear = (c1["close"] < self.regime.or_low)  and (c2["close"] < self.regime.or_low)

        if bull and c2["low"]  < self.regime.or_low:  return None
        if bear and c2["high"] > self.regime.or_high: return None

        if self.regime.retest_required and len(df_5m) >= 4:
            prev = df_5m.iloc[-3]
            TOL  = 0.005
            if bull and prev["low"]  > self.regime.or_high * (1 + TOL): return None
            if bear and prev["high"] < self.regime.or_low  * (1 - TOL): return None

        if bull: return "CALL"
        if bear: return "PUT"
        return None

    def is_counter_trend(self, direction: str) -> bool:
        return (direction == "CALL" and not self.regime.bullish) or \
               (direction == "PUT"  and self.regime.bullish)

    def exit_timeframe(self, df_5m: pd.DataFrame) -> KLType:
        """Dynamic exit TF from EMA 10/20 gap vs ATR."""
        c   = df_5m["close"]
        gap = abs(ema(c, 10).iloc[-1] - ema(c, 20).iloc[-1])
        r   = gap / self.regime.atr if self.regime.atr > 0 else 0
        if r < EMA_GAP_TIGHT: return KLType.K_15M
        if r > EMA_GAP_WIDE:  return KLType.K_3M
        return KLType.K_5M

    def check_ema_exit(self, df_exit: pd.DataFrame, direction: str) -> bool:
        c = df_exit["close"]
        last, ema10 = c.iloc[-1], ema(c, 10).iloc[-1]
        if direction == "CALL" and last < ema10: return True
        if direction == "PUT"  and last > ema10: return True
        return False

    def check_or_reentry(self, df_5m: pd.DataFrame, direction: str) -> bool:
        """Price closes back inside OR — breakout thesis failed."""
        last = df_5m["close"].iloc[-1]
        if direction == "CALL" and last < self.regime.or_high: return True
        if direction == "PUT"  and last > self.regime.or_low:  return True
        return False
