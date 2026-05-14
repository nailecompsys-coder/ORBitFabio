"""
FABIO ORB bot — push-based loop (Phase 5).

Strategy classes are imported from sibling modules; replace regime/signals/circuit/orders
with verbatim copies from orb_bot_fabio.py when that file is available.
"""

from __future__ import annotations

import asyncio
import datetime
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from moomoo import (
    KLType,
    OpenQuoteContext,
    OpenSecTradeContext,
    RET_OK,
    SecurityFirm,
    SubType,
    TrdEnv,
    TrdMarket,
)

from bot.circuit import RiskCircuitBreaker
from bot.handlers import DailyBarHandler, FiveMinBarHandler, ThreeMinBarHandler
from bot.notifications import push_event
from bot.orders import OrderManager
from bot.regime import MarketRegime
from bot.signals import SignalEngine

if TYPE_CHECKING:
    import asyncpg

# ── Strategy constants (replace with verbatim block from orb_bot_fabio.py) ──
SYMBOLS = ["SPY", "QQQ", "NVDA"]
ENTRY_SIGNAL_MAX_AGE_MIN = 10
VIX_HALF_MAX = 16.0
VIX_NORMAL_MAX = 22.0
VIX_AGGRESSIVE_MAX = 28.0
STRATEGY_CAPITAL = 250_000.0


def get_candles(quote_ctx: Any, symbol: str, kl_type: Any, n: int) -> pd.DataFrame:
    """Pull recent klines from OpenD; fall back to a tiny synthetic frame if unavailable."""
    code = symbol if str(symbol).startswith("US.") else f"US.{symbol}"
    try:
        ret, data, _ = quote_ctx.request_history_kline(
            code,
            start=None,
            end=None,
            ktype=kl_type,
            max_count=n,
        )
        if ret == RET_OK and isinstance(data, pd.DataFrame) and not data.empty:
            return data
    except Exception:
        pass
    ts = pd.Timestamp.now()
    return pd.DataFrame({"time_key": [ts], "close": [100.0]})


def get_vix(quote_ctx: Any) -> float:
    try:
        ret, snap = quote_ctx.get_market_snapshot(["US.VIX"])
        if ret == RET_OK and snap is not None and not snap.empty:
            return float(snap.iloc[0].get("last_price", 18.0))
    except Exception:
        pass
    return 18.0


def get_portfolio_value(trade_ctx: Any, trd_env: Any) -> float:
    try:
        ret, data = trade_ctx.accinfo_query(trd_env=trd_env)
        if ret == RET_OK and data is not None and not data.empty:
            return float(data.iloc[0].get("total_assets", STRATEGY_CAPITAL))
    except Exception:
        pass
    return float(STRATEGY_CAPITAL)


class ORBBot:
    def __init__(
        self,
        user_id: str,
        opend_port: int,
        trd_env: TrdEnv,
        db_session: "asyncpg.Pool",
        sheets_logger: Any = None,
    ) -> None:
        self.user_id = user_id
        self.trd_env = trd_env
        self.db = db_session
        self._sheets = sheets_logger

        self.quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        self.trade_ctx = OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US,
            host="127.0.0.1",
            port=opend_port,
            security_firm=SecurityFirm.FUTUINC,
        )

        self.cb = RiskCircuitBreaker()
        self.regimes: dict[str, MarketRegime] = {}
        self.signals: dict[str, str] = {}
        self.exit_tfs: dict[str, Any] = {}
        self.order_mgr = OrderManager(self.trade_ctx, self.quote_ctx, trd_env)
        self._trades_today: list[Any] = []
        self._trade_entries: dict[str, Any] = {}
        self._capital_at_open = 0.0
        self._cb_logged: set[str] = set()
        self._prefetched = False
        self._prefetch_vix: Optional[float] = None
        self._prefetch_portfolio: Optional[float] = None
        self._prefetch_daily: dict[str, Any] = {}
        self.paused = False
        self.stopped = False

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

    def _subscribe_push(self) -> None:
        codes = [f"US.{sym}" for sym in SYMBOLS]
        self.quote_ctx.subscribe(
            codes,
            [SubType.K_5M, SubType.K_3M, SubType.K_15M, SubType.K_DAY],
            subscribe_push=True,
        )
        self.quote_ctx.set_handler(FiveMinBarHandler(self, self._loop))
        self.quote_ctx.set_handler(ThreeMinBarHandler(self, self._loop))
        self.quote_ctx.set_handler(DailyBarHandler(self, self._loop))
        self.quote_ctx.start()

    async def prefetch_or_window(self) -> None:
        self._prefetch_vix = get_vix(self.quote_ctx)
        self._prefetch_portfolio = get_portfolio_value(self.trade_ctx, self.trd_env)
        await push_event(
            self.db,
            self.user_id,
            "prefetch",
            {"vix": self._prefetch_vix, "portfolio": self._prefetch_portfolio},
        )

    def initialize_day(self) -> None:
        vix = self._prefetch_vix if self._prefetch_vix is not None else get_vix(self.quote_ctx)
        self.regimes = {
            sym: MarketRegime(symbol=sym, tradeable=True, vix=float(vix)) for sym in SYMBOLS
        }
        self._capital_at_open = float(self._prefetch_portfolio or STRATEGY_CAPITAL)
        self._prefetched = True

    async def on_5min_bar_close(self, symbol: str) -> None:
        if symbol not in self.regimes:
            return
        regime = self.regimes[symbol]
        if not regime.tradeable:
            return
        if self.order_mgr.has_position(symbol):
            return
        if self.paused:
            return
        allowed, _reason = self.cb.can_enter(self.order_mgr.open_count())
        if not allowed:
            return

        df_5m = get_candles(self.quote_ctx, symbol, KLType.K_5M, 30)
        engine = SignalEngine(regime)
        direction = engine.check_breakout(df_5m)
        if not direction:
            return

        signal_candle_time = df_5m["time_key"].iloc[-1]
        age_min = (pd.Timestamp.now() - pd.Timestamp(signal_candle_time)).total_seconds() / 60
        if age_min > ENTRY_SIGNAL_MAX_AGE_MIN:
            return

        if engine.is_counter_trend(direction):
            return
        if regime.vix < (VIX_HALF_MAX + 0.1):
            return
        if direction == "CALL" and VIX_NORMAL_MAX < regime.vix <= VIX_AGGRESSIVE_MAX:
            return

        cb_mod = self.cb.size_modifier()
        risk_mult = regime.risk_multiplier(counter_trend=False, cb_modifier=cb_mod)
        port_val = min(get_portfolio_value(self.trade_ctx, self.trd_env), STRATEGY_CAPITAL)
        last_price = float(df_5m["close"].iloc[-1])

        self.order_mgr.enter(symbol, direction, last_price, risk_mult, port_val)

        if self.order_mgr.has_position(symbol):
            self.signals[symbol] = direction
            self.exit_tfs[symbol] = engine.exit_timeframe(df_5m)
            await self._log_entry(symbol, direction, regime, risk_mult, port_val)

    async def on_3min_bar_close(self, symbol: str) -> None:
        await push_event(
            self.db,
            self.user_id,
            "bar_3m",
            {"symbol": symbol, "has_signal": symbol in self.signals},
        )

    async def on_daily_bar(self, symbol: str, data: Any) -> None:
        self._prefetch_daily[symbol] = data
        await push_event(
            self.db,
            self.user_id,
            "daily_bar",
            {"symbol": symbol, "rows": int(len(data)) if hasattr(data, "__len__") else 0},
        )

    async def _log_entry(
        self,
        symbol: str,
        direction: str,
        regime: MarketRegime,
        risk_mult: float,
        port_val: float,
    ) -> None:
        if self._sheets is not None and hasattr(self._sheets, "log_entry"):
            try:
                self._sheets.log_entry(symbol, direction, regime, risk_mult, port_val)
            except Exception:
                pass
        await push_event(
            self.db,
            self.user_id,
            "entry",
            {
                "symbol": symbol,
                "direction": direction,
                "vix": regime.vix,
                "risk_mult": risk_mult,
                "portfolio": port_val,
            },
        )

    async def eod_close_all(self) -> None:
        await push_event(self.db, self.user_id, "eod", {"action": "close_all"})
        self.signals.clear()

    async def run(self) -> None:
        now = datetime.datetime.now()
        or_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        eod = now.replace(hour=15, minute=45, second=0, microsecond=0)

        while datetime.datetime.now() < or_open:
            await asyncio.sleep(30)

        await self.prefetch_or_window()
        self.initialize_day()
        self._subscribe_push()

        while datetime.datetime.now() < eod:
            if self.stopped:
                break
            await asyncio.sleep(10)

        await self.eod_close_all()
        self.quote_ctx.close()
        self.trade_ctx.close()
