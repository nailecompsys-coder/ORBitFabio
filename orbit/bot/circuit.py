"""
RiskCircuitBreaker — verbatim from orb_bot.py (Clayton).
"""

from __future__ import annotations

from bot.regime import (
    CB_DAILY_LOSS_PCT,
    CB_DD_HALVE_PCT,
    CB_DD_RESUME_PCT,
    CB_MAX_LOSS_STREAK,
    CB_MAX_OPEN_POS,
    CB_MAX_TRADES,
)

# ─── CIRCUIT BREAKER ─────────────────────────────────────────────────────────
class RiskCircuitBreaker:
    def __init__(self):
        self.open_value   = 0.0
        self.day_pnl      = 0.0
        self.trade_count  = 0
        self.loss_streak  = 0
        self.peak_equity  = 0.0
        self.dd_halved    = False

    def set_open(self, value: float):
        self.open_value = value

    def update_peak(self, equity: float):
        self.peak_equity = max(self.peak_equity, equity)
        if self.peak_equity > 0:
            dd = (equity - self.peak_equity) / self.peak_equity
            if dd <= -CB_DD_HALVE_PCT and not self.dd_halved:
                print(f"  ⚠  DD CB: {dd*100:.1f}% from peak — risk halved")
                self.dd_halved = True
            elif self.dd_halved and dd >= -CB_DD_RESUME_PCT:
                print(f"  ✓  DD CB recovered to {dd*100:.1f}% — full size resumed")
                self.dd_halved = False

    def can_enter(self, n_open: int) -> tuple[bool, str]:
        if self.open_value > 0 and self.day_pnl / self.open_value <= -CB_DAILY_LOSS_PCT:
            return False, f"Daily loss limit hit ({self.day_pnl/self.open_value*100:.1f}%)"
        if self.trade_count >= CB_MAX_TRADES:
            return False, f"Daily trade cap ({self.trade_count}/{CB_MAX_TRADES})"
        if n_open >= CB_MAX_OPEN_POS:
            return False, f"Max open positions ({n_open}/{CB_MAX_OPEN_POS})"
        return True, ""

    def size_mod(self) -> float:
        streak = 0.5 if self.loss_streak >= CB_MAX_LOSS_STREAK else 1.0
        dd     = 0.5 if self.dd_halved else 1.0
        return streak * dd

    def record(self, pnl: float):
        self.day_pnl     += pnl
        self.trade_count += 1
        self.loss_streak  = (self.loss_streak + 1) if pnl < 0 else 0

    def reset(self):
        self.open_value  = 0.0
        self.day_pnl     = 0.0
        self.trade_count = 0
        self.loss_streak = 0
        # peak_equity and dd_halved persist across days

    def summary(self) -> str:
        return (f"CB | DayPnL=${self.day_pnl:+,.0f} | "
                f"Trades={self.trade_count}/{CB_MAX_TRADES} | "
                f"Streak={self.loss_streak}"
                + (" | DD-PROTECTED" if self.dd_halved else ""))
