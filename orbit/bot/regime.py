"""
MarketRegime — verbatim from orb_bot.py (Clayton).
All strategy constants that other bot modules depend on live here.
"""

from __future__ import annotations

import datetime
from typing import Optional
from zoneinfo import ZoneInfo

import pandas as pd

# ─── NYSE HOLIDAYS ────────────────────────────────────────────────────────────
US_MARKET_HOLIDAYS: set[datetime.date] = {
    datetime.date(2025, 1, 1),  datetime.date(2025, 1, 20),
    datetime.date(2025, 2, 17), datetime.date(2025, 4, 18),
    datetime.date(2025, 5, 26), datetime.date(2025, 6, 19),
    datetime.date(2025, 7, 4),  datetime.date(2025, 9, 1),
    datetime.date(2025, 11, 27),datetime.date(2025, 12, 25),
    datetime.date(2026, 1, 1),  datetime.date(2026, 1, 19),
    datetime.date(2026, 2, 16), datetime.date(2026, 4, 3),
    datetime.date(2026, 5, 25), datetime.date(2026, 6, 19),
    datetime.date(2026, 7, 3),  datetime.date(2026, 9, 7),
    datetime.date(2026, 11, 26),datetime.date(2026, 12, 25),
    datetime.date(2027, 1, 1),  datetime.date(2027, 1, 18),
    datetime.date(2027, 2, 15), datetime.date(2027, 4, 2),
    datetime.date(2027, 5, 31), datetime.date(2027, 6, 19),
    datetime.date(2027, 7, 5),  datetime.date(2027, 9, 6),
    datetime.date(2027, 11, 25),datetime.date(2027, 12, 24),
}

# Session times use US/Eastern regardless of server timezone.
TZ_ET = ZoneInfo("America/New_York")

# ─── STRATEGY CONFIG ──────────────────────────────────────────────────────────
STRATEGY_CAPITAL = 1_000_000    # paper account allocation ($)

SYMBOLS = ["SPY", "QQQ", "NVDA"]

# VIX tiers — match backtest
VIX_SKIP           = 14
VIX_HALF_MAX       = 16
VIX_NORMAL_MAX     = 20
VIX_AGGRESSIVE_MAX = 28

# Risk per trade — % of STRATEGY_CAPITAL (match backtest)
RISK_PCT_FULL = 0.20
RISK_PCT_HALF = 0.10
RISK_PCT_MAX  = 0.20

# Gap filter — match backtest
GAP_SKIP_PCT   = 3.0
GAP_RETEST_PCT = 1.5

# OR quality — match locked backtest baseline
OR_SKIP_PCT_ATR   = 8
OR_NORMAL_MIN_ATR = 15
OR_WIDE_PCT_ATR   = 60

# EMA gap → exit timeframe
EMA_GAP_TIGHT = 0.05
EMA_GAP_WIDE  = 0.15

# Entry execution
ENTRY_MAX_ATTEMPTS  = 5
ENTRY_FILL_WAIT_SEC = 60
SIGNAL_END_HOUR     = 14

# Revised strategy flags
SKIP_COUNTER_TREND = True
NVDA_OR_CAP        = True

# Hard stop
HARD_STOP_LOSS_PCT = 0.50
ATR_STOP_MULT      = 2.0

# Profit trimming
TRIM_MULTIPLE = 2.0
TRIM_PCT      = 0.50

# Circuit breakers — match backtest
CB_DAILY_LOSS_PCT  = 0.02
CB_MAX_TRADES      = 3
CB_MAX_LOSS_STREAK = 3
CB_MAX_OPEN_POS    = 3
CB_DD_HALVE_PCT    = 0.30
CB_DD_RESUME_PCT   = 0.15

# ─── HELPERS ──────────────────────────────────────────────────────────────────
def ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()

def compute_atr(df: pd.DataFrame, period: int = 14) -> float:
    h, l, c = df["high"], df["low"], df["close"]
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()],
                   axis=1).max(axis=1)
    return float(tr.ewm(span=period, adjust=False).mean().iloc[-1])

def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _full_us_code(symbol: str) -> str:
    return symbol if "." in symbol else f"US.{symbol}"

def _round_us_option_limit_price(raw: float) -> float:
    """Moomoo rejects float noise (e.g. 7.209999); US options use cent ticks >= $3."""
    x = float(raw)
    if x <= 0:
        return 0.01
    if x < 3.0:
        return round(round(x / 0.05) * 0.05, 2) or 0.05
    return float(f"{x:.2f}")

# ─── MARKET REGIME ────────────────────────────────────────────────────────────
class MarketRegime:
    def __init__(self, symbol: str, df_daily: pd.DataFrame,
                 df_15m: pd.DataFrame, vix: float):
        self.symbol      = symbol
        self.vix         = vix
        self.atr         = compute_atr(df_daily)
        self.gap_pct     = self._gap(df_daily)
        self.or_high, self.or_low = self._opening_range(df_15m)
        self.or_width    = self.or_high - self.or_low
        self.or_atr_pct  = (self.or_width / self.atr * 100) if self.atr > 0 else 0

        c = df_daily["close"]
        self.bullish = (ema(c, 10).iloc[-1] > ema(c, 20).iloc[-1]) and \
                       (c.iloc[-1] > ema(c, 50).iloc[-1])

    def _gap(self, df: pd.DataFrame) -> float:
        if len(df) < 2:
            return 0.0
        return abs((float(df["open"].iloc[-1]) - float(df["close"].iloc[-2]))
                   / float(df["close"].iloc[-2])) * 100

    def _opening_range(self, df_15m: pd.DataFrame) -> tuple[float, float]:
        """First 15-min candle of the day (9:30-9:44)."""
        if df_15m.empty:
            return 0.0, 0.0
        session_date = datetime.datetime.now(TZ_ET).date()
        times = pd.to_datetime(df_15m["time_key"])
        # Moomoo labels 15-minute K-lines by bar close time, so the opening
        # 9:30-9:44 ET range is stamped 09:45.
        day_bars = df_15m[
            (times.dt.date == session_date)
            & (times.dt.time >= datetime.time(9, 45))
            & (times.dt.time < datetime.time(10, 0))
        ]
        if day_bars.empty:
            raise RuntimeError("Opening-range 9:30-9:44 ET bar not found")
        first = day_bars.iloc[0]
        return float(first["high"]), float(first["low"])

    @property
    def vix_risk_pct(self) -> float:
        if self.vix < VIX_SKIP:             return 0.0
        if self.vix <= VIX_HALF_MAX:        return RISK_PCT_HALF
        if self.vix <= VIX_NORMAL_MAX:      return RISK_PCT_FULL
        if self.vix <= VIX_AGGRESSIVE_MAX:  return min(RISK_PCT_FULL * 1.25, RISK_PCT_MAX)
        return RISK_PCT_HALF

    @property
    def or_size_factor(self) -> float:
        p = self.or_atr_pct
        if p < OR_SKIP_PCT_ATR:      return 0.0
        if p < OR_NORMAL_MIN_ATR:    return 0.75
        if p <= OR_WIDE_PCT_ATR:     return 1.0
        return 0.75

    @property
    def retest_required(self) -> bool:
        return GAP_RETEST_PCT <= self.gap_pct < GAP_SKIP_PCT

    @property
    def tradeable(self) -> bool:
        return self.vix_risk_pct > 0 and self.or_size_factor > 0 and self.gap_pct < GAP_SKIP_PCT

    def risk_multiplier(self, cb_mod: float = 1.0) -> float:
        return min(self.vix_risk_pct * self.or_size_factor * cb_mod, RISK_PCT_MAX)

    def summary(self) -> str:
        trend = "BULL" if self.bullish else "BEAR"
        retest = " | RETEST REQ" if self.retest_required else ""
        return (f"[{self.symbol}] VIX={self.vix:.1f} | "
                f"OR={self.or_width:.2f} ({self.or_atr_pct:.0f}%ATR) | "
                f"Gap={self.gap_pct:.2f}% | Trend={trend}"
                f" | Tradeable={'YES' if self.tradeable else 'NO'}{retest}")
