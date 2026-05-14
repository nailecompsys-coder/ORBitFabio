"""ORBit FABIO bot — push-based, multi-user (Phase 5).

Strategy logic is verbatim from orb_bot.py (Clayton).
Architecture changes:
  • time.sleep(60) poll → Moomoo SubType.K_5M / K_3M push callbacks
  • quote_ctx always port 11111 (shared); trade_ctx on opend_port param
  • Parallel push_event() alongside every Sheets log call
  • Postgres via asyncpg; no Telegram
"""

from __future__ import annotations

import asyncio
import datetime
import os
import threading
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Optional

import pandas as pd
from moomoo import (
    KLType, OpenQuoteContext, OpenSecTradeContext,
    RET_OK, SecurityFirm, SubType, TrdEnv, TrdMarket,
)
from moomoo.common.constant import Currency

from bot.circuit import RiskCircuitBreaker
from bot.handlers import DailyBarHandler, FiveMinBarHandler, ThreeMinBarHandler
from bot.notifications import push_event, push_trade_entry, push_trade_exit
from bot.orders import OrderManager
from bot.regime import (
    NVDA_OR_CAP, SIGNAL_END_HOUR, SKIP_COUNTER_TREND, STRATEGY_CAPITAL,
    SYMBOLS, TZ_ET, _full_us_code, _safe_float,
)
from bot.signals import SignalEngine

if TYPE_CHECKING:
    import asyncpg


# ── Helpers (verbatim from orb_bot.py) ────────────────────────────────────────

def _row_enum_name(value) -> str:
    if hasattr(value, "name"):
        return value.name
    return str(value)


def _row_has_us_auth(value) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return "US" in value.upper()
    try:
        return any(_row_enum_name(item).upper() == "US" for item in value)
    except TypeError:
        return _row_enum_name(value).upper() == "US"


def get_candles(quote_ctx, symbol: str, ktype: KLType, count: int = 100) -> pd.DataFrame:
    sub_map = {
        KLType.K_DAY: SubType.K_DAY, KLType.K_5M: SubType.K_5M,
        KLType.K_3M: SubType.K_3M, KLType.K_15M: SubType.K_15M,
    }
    moo_sym  = _full_us_code(symbol)
    sub_type = sub_map.get(ktype)
    if sub_type:
        quote_ctx.subscribe([moo_sym], [sub_type])
    ret, data = quote_ctx.get_cur_kline(moo_sym, count, ktype)
    if ret != 0:
        raise RuntimeError(f"Candle fetch failed {symbol}: {data}")
    df = data[["time_key", "open", "close", "high", "low", "volume"]].copy()
    df["time_key"] = pd.to_datetime(df["time_key"])
    return df.sort_values("time_key").reset_index(drop=True)


def get_vix(quote_ctx) -> float:
    ret, data = quote_ctx.get_market_snapshot(["US.VIX"])
    if ret != 0:
        return 20.0
    return float(data["last_price"].iloc[0])


def resolve_trade_acc_id(trade_ctx, trd_env: TrdEnv) -> int:
    """
    Resolve the exact account id used for orders/funds (verbatim from orb_bot.py,
    adapted to accept trd_env instead of reading PAPER_TRADING global).
    """
    env_var    = "MOOMOO_PAPER_ACC_ID" if trd_env == TrdEnv.SIMULATE else "MOOMOO_LIVE_ACC_ID"
    configured = int(os.environ.get(env_var, "0") or "0")
    if configured:
        return configured
    ret, data = trade_ctx.get_acc_list()
    if ret != RET_OK or data is None or data.empty:
        raise RuntimeError(f"get_acc_list failed while resolving account: {data}")
    matches = []
    for _, row in data.iterrows():
        if row.get("trd_env") != trd_env:
            continue
        if not _row_has_us_auth(row.get("trdmarket_auth")):
            continue
        if _row_enum_name(row.get("acc_status", "ACTIVE")).upper() == "DISABLED":
            continue
        matches.append(int(row["acc_id"]))
    if not matches:
        env_name = "SIMULATE" if trd_env == TrdEnv.SIMULATE else "REAL"
        raise RuntimeError(f"No active US {env_name} account found in OpenD")
    return matches[0]


def get_account_value(trade_ctx, trd_env: TrdEnv, acc_id: int) -> float:
    ret, data = trade_ctx.accinfo_query(
        trd_env=trd_env, acc_id=acc_id,
        currency=Currency.USD, refresh_cache=True,
    )
    if ret != 0 or data is None or data.empty:
        return float(STRATEGY_CAPITAL)
    return float(_safe_float(data.iloc[0]["total_assets"], STRATEGY_CAPITAL))


# ── ORBBot ────────────────────────────────────────────────────────────────────

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
        self.db      = db_session
        self._sheets = sheets_logger

        # quote_ctx always port 11111 (shared real-time options data)
        self.quote_ctx = OpenQuoteContext(host="127.0.0.1", port=11111)
        # trade_ctx on per-user opend_port
        self.trade_ctx = OpenSecTradeContext(
            filter_trdmarket=TrdMarket.US,
            host="127.0.0.1",
            port=opend_port,
            security_firm=SecurityFirm.FUTUINC,
        )

        trade_pwd = os.environ.get("MOOMOO_TRADE_PWD", "")
        if trade_pwd:
            ret, msg = self.trade_ctx.unlock_trade(trade_pwd)
            if ret != 0:
                print(f"  ⚠  Trade unlock FAILED: {msg}")
                m = str(msg)
                if "Unlock button" in m or "GUI version" in m:
                    print("      GUI OpenD: click Unlock (top-right) — API unlock disabled.")
                else:
                    print("      Check MOOMOO_TRADE_PWD in .env vs Moomoo Settings.")
            else:
                print(f"  ✓ Trade unlocked ({'PAPER' if trd_env == TrdEnv.SIMULATE else 'LIVE'})")
        else:
            print("  ⚠  MOOMOO_TRADE_PWD not set — order placement will fail")

        self.trade_acc_id = resolve_trade_acc_id(self.trade_ctx, trd_env)
        print(f"  ✓ Using trade account {self.trade_acc_id} "
              f"({'PAPER' if trd_env == TrdEnv.SIMULATE else 'LIVE'})")

        self.om           = OrderManager(self.trade_ctx, self.quote_ctx, trd_env,
                                         acc_id=self.trade_acc_id)
        self.cb           = RiskCircuitBreaker()
        self.regimes:    dict[str, Any] = {}
        self.signals:    dict[str, str] = {}
        self.exit_tfs:   dict[str, Any] = {}
        self.paused        = False
        self.stopped       = False
        self.options_ready = False
        self.live_syms     = SYMBOLS.copy()
        self._trade_ids:  dict[str, Any] = {}

        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.get_event_loop()

    # ── Day initialisation ────────────────────────────────────────────────────

    def _validate_option_access(self) -> bool:
        for sym in self.live_syms:
            base = _full_us_code(sym)
            try:
                ret, exps = self.quote_ctx.get_option_expiration_date(base)
                if ret == RET_OK and exps is not None and not exps.empty:
                    return True
                print(f"  ⚠  [{sym}] option expirations unavailable: {exps}")
            except Exception as e:
                print(f"  ⚠  [{sym}] option permission check failed: {e}")
        print("  ✗ US option chain access is not available. Entries are disabled.")
        print("    Enable US options quote permissions in Moomoo/OpenD, then restart.")
        return False

    def initialize_day(self) -> None:
        print("\n" + "=" * 64)
        print(f"  ORB BOT [{self.user_id}]  |  "
              f"{datetime.datetime.now(TZ_ET):%Y-%m-%d %H:%M} ET")
        print("=" * 64)

        self.options_ready = self._validate_option_access()

        vix      = get_vix(self.quote_ctx)
        acct_val = get_account_value(self.trade_ctx, self.trd_env, self.trade_acc_id)
        self.cb.set_open(acct_val)
        self.cb.update_peak(acct_val)
        print(f"  VIX={vix:.1f}  |  Account=${acct_val:,.0f}")

        from bot.regime import MarketRegime
        for sym in self.live_syms:
            try:
                df_d   = get_candles(self.quote_ctx, sym, KLType.K_DAY,  60)
                df_15m = get_candles(self.quote_ctx, sym, KLType.K_15M, 100)
                regime = MarketRegime(sym, df_d, df_15m, vix)
                self.regimes[sym] = regime
                print(f"  {regime.summary()}")
            except Exception as e:
                print(f"  ⚠  [{sym}] Regime init failed: {e}")

        if self._sheets is not None and hasattr(self._sheets, "log_session"):
            try:
                self._sheets.log_session(self.live_syms, vix, acct_val)
            except Exception:
                pass
        asyncio.run_coroutine_threadsafe(
            push_event(self.db, self.user_id, "day_init", {
                "vix": vix, "account": acct_val, "symbols": self.live_syms,
            }),
            self._loop,
        )

    def _subscribe_push(self) -> None:
        codes = [_full_us_code(sym) for sym in self.live_syms]
        self.quote_ctx.subscribe(
            codes,
            [SubType.K_5M, SubType.K_3M, SubType.K_15M, SubType.K_DAY],
            subscribe_push=True,
        )
        self.quote_ctx.set_handler(FiveMinBarHandler(self, self._loop))
        self.quote_ctx.set_handler(ThreeMinBarHandler(self, self._loop))
        self.quote_ctx.set_handler(DailyBarHandler(self, self._loop))
        self.quote_ctx.start()

    # ── Push callbacks ────────────────────────────────────────────────────────

    async def on_5min_bar_close(self, symbol: str) -> None:
        """Entry logic only — exit logic handled by on_3min_bar_close."""
        if self.om.has_position(symbol):
            return
        if self.paused or not self.options_ready:
            return

        regime = self.regimes.get(symbol)
        if not regime or not regime.tradeable:
            return

        ok, reason = self.cb.can_enter(self.om.open_count())
        if not ok:
            print(f"  🚫 [{symbol}] Blocked — {reason}")
            return

        if any(t.name == f"enter-{symbol}" and t.is_alive()
               for t in threading.enumerate()):
            return

        try:
            df_5m  = get_candles(self.quote_ctx, symbol, KLType.K_5M, 20)
            engine = SignalEngine(regime)
            sig    = engine.check_breakout(df_5m)
        except Exception as e:
            print(f"  ⚠  [{symbol}] Signal check error: {e}")
            return

        if not sig:
            return

        # Revised: skip counter-trend entirely (LOCKED)
        if SKIP_COUNTER_TREND and engine.is_counter_trend(sig):
            print(f"  [{symbol}] Skipping counter-trend {sig}")
            return

        cb_mod   = self.cb.size_mod()
        risk_pct = regime.risk_multiplier(cb_mod=cb_mod)
        last_px  = float(df_5m["close"].iloc[-1])
        exit_tf  = engine.exit_timeframe(df_5m)

        # Revised: NVDA OR-width cap (LOCKED)
        if NVDA_OR_CAP and symbol == "NVDA" and regime.or_atr_pct > 30:
            risk_pct *= 0.50
            print(f"  [{symbol}] NVDA OR cap applied "
                  f"(OR={regime.or_atr_pct:.0f}%ATR > 30%) → risk×0.5")

        tf_label = {KLType.K_3M: "3-min", KLType.K_5M: "5-min", KLType.K_15M: "15-min"}
        print(f"\n  [{symbol}] {sig} | Risk={risk_pct*100:.1f}% | "
              f"Exit TF={tf_label.get(exit_tf, '?')}")

        loop = self._loop

        def _on_fill(s=symbol, d=sig, tf=exit_tf, r=regime, rp=risk_pct):
            if self.om.has_position(s):
                self.signals[s]  = d
                self.exit_tfs[s] = tf
                pos = self.om.positions[s]
                asyncio.run_coroutine_threadsafe(
                    self._on_fill_async(s, d, tf, r, rp, dict(pos)),
                    loop,
                )
            else:
                print(f"  [{s}] ✗ No fill")

        self.om.enter_async(symbol, sig, last_px, risk_pct, on_complete=_on_fill)

    async def _on_fill_async(
        self,
        symbol: str,
        direction: str,
        exit_tf: Any,
        regime: Any,
        risk_pct: float,
        pos: dict,
    ) -> None:
        if self._sheets is not None and hasattr(self._sheets, "log_entry"):
            try:
                self._sheets.log_entry(symbol, direction, regime, risk_pct)
            except Exception:
                pass
        try:
            tid = await push_trade_entry(
                self.db, self.user_id,
                symbol=symbol,
                direction=direction,
                option_code=pos.get("code"),
                contracts=pos.get("original_qty"),
                entry_price=Decimal(str(pos.get("entry_option_price", 0))),
                extra={
                    "vix": regime.vix,
                    "or_atr_pct": regime.or_atr_pct,
                    "vix_regime": (
                        "aggressive" if regime.vix > 20
                        else "normal" if regime.vix > 16
                        else "half"
                    ),
                    "trend": "BULL" if regime.bullish else "BEAR",
                },
            )
            self._trade_ids[symbol] = tid
        except Exception as e:
            print(f"  ⚠  push_trade_entry failed: {e}")
        await push_event(
            self.db, self.user_id, "entry",
            {
                "symbol": symbol,
                "direction": direction,
                "vix": regime.vix,
                "risk_pct": risk_pct,
                "option_code": pos.get("code"),
                "entry_price": pos.get("entry_option_price", 0),
            },
        )

    async def on_3min_bar_close(self, symbol: str) -> None:
        """Exit loop on every 3-min bar for open positions."""
        await self._run_exit(symbol)
        await push_event(
            self.db, self.user_id, "bar_3m",
            {"symbol": symbol, "has_signal": symbol in self.signals},
        )

    async def on_daily_bar(self, symbol: str, data: Any) -> None:
        await push_event(
            self.db, self.user_id, "daily_bar",
            {"symbol": symbol, "rows": int(len(data)) if hasattr(data, "__len__") else 0},
        )

    # ── Exit loop (verbatim logic from orb_bot.py run_exit_loop) ─────────────

    async def _run_exit(self, symbol: str) -> None:
        # Include open positions even if signals were dropped (state desync)
        if not self.om.has_position(symbol):
            self.signals.pop(symbol, None)
            self.exit_tfs.pop(symbol, None)
            return

        direction = self.signals.get(symbol)
        if direction is None:
            direction = self.om.positions[symbol]["direction"]
            self.signals[symbol] = direction
            self.exit_tfs.setdefault(symbol, KLType.K_5M)

        exit_tf = self.exit_tfs.get(symbol, KLType.K_5M)
        regime  = self.regimes.get(symbol)
        if not regime:
            return
        engine = SignalEngine(regime)

        # 1. Profit trim
        trim_pnl = self.om.check_trim(symbol)
        if trim_pnl > 0:
            if self._sheets is not None and hasattr(self._sheets, "log_trim"):
                try:
                    self._sheets.log_trim(symbol, trim_pnl)
                except Exception:
                    pass
            await push_event(
                self.db, self.user_id, "trim",
                {"symbol": symbol, "pnl": trim_pnl},
            )
        if not self.om.has_position(symbol):
            self.cb.record(trim_pnl)
            self.signals.pop(symbol, None)
            self.exit_tfs.pop(symbol, None)
            return

        try:
            df_5m  = get_candles(self.quote_ctx, symbol, KLType.K_5M, 20)
            cur_px = float(df_5m["close"].iloc[-1])
        except Exception:
            return

        # Update ATR for stop calc
        if symbol in self.om.positions:
            self.om.positions[symbol]["atr"] = regime.atr

        # 2. Hard stop
        if self.om.check_hard_stop(symbol, cur_px):
            await self._safe_exit(symbol, reason="Hard stop")
            return

        # 3. OR re-entry
        if engine.check_or_reentry(df_5m, direction):
            await self._safe_exit(symbol, reason="OR re-entry")
            return

        # 4. EMA exit on dynamic timeframe
        tf_label = {KLType.K_3M: "3-min", KLType.K_5M: "5-min", KLType.K_15M: "15-min"}
        try:
            df_exit = get_candles(self.quote_ctx, symbol, exit_tf, 20)
            if engine.check_ema_exit(df_exit, direction):
                await self._safe_exit(symbol, reason=f"EMA {tf_label.get(exit_tf, '?')}")
        except Exception:
            pass

    async def _safe_exit(self, symbol: str, reason: str) -> float:
        if not self.om.has_position(symbol):
            self.signals.pop(symbol, None)
            self.exit_tfs.pop(symbol, None)
            return 0.0

        pnl = self.om.exit(symbol, reason=reason)
        if self.om.has_position(symbol):
            print(f"  ⚠  [{symbol}] Sell not confirmed — position still open; will retry")
            return 0.0

        self.cb.record(pnl)
        trade_id = self._trade_ids.pop(symbol, None)
        self.signals.pop(symbol, None)
        self.exit_tfs.pop(symbol, None)

        if self._sheets is not None and hasattr(self._sheets, "log_exit"):
            try:
                self._sheets.log_exit(symbol, reason, pnl)
            except Exception:
                pass
        if trade_id is not None:
            try:
                await push_trade_exit(
                    self.db, self.user_id,
                    trade_id=trade_id,
                    pnl=Decimal(str(round(pnl, 2))),
                    exit_reason=reason,
                )
            except Exception as e:
                print(f"  ⚠  push_trade_exit failed: {e}")
        await push_event(
            self.db, self.user_id, "exit",
            {
                "symbol": symbol,
                "reason": reason,
                "pnl": pnl,
                "cb": self.cb.summary(),
            },
        )
        return pnl

    # ── EOD ───────────────────────────────────────────────────────────────────

    async def eod_close_all(self) -> None:
        print("\n  [EOD] Closing all positions...")
        to_close = set(self.signals.keys()) | set(self.om.positions.keys())

        # Wait for any in-flight entry threads
        for t in threading.enumerate():
            if t.name.startswith("enter-") and t.is_alive():
                t.join(timeout=10)

        for sym in sorted(to_close):
            if self.om.has_position(sym):
                await self._safe_exit(sym, reason="EOD")

        if self._sheets is not None and hasattr(self._sheets, "log_eod"):
            try:
                self._sheets.log_eod(self.cb.summary())
            except Exception:
                pass
        await push_event(
            self.db, self.user_id, "eod",
            {"action": "close_all", "cb": self.cb.summary()},
        )
        self.regimes.clear()
        self.signals.clear()
        self.exit_tfs.clear()
        self.cb.reset()

    # ── Main loop ─────────────────────────────────────────────────────────────

    async def run(self) -> None:
        print(f"  [{self.user_id}] Session times use US/Eastern. "
              "Waiting for OR close at 9:45 AM ET...")

        or_close = datetime.datetime.now(TZ_ET).replace(
            hour=9, minute=45, second=0, microsecond=0
        )
        while datetime.datetime.now(TZ_ET) < or_close:
            await asyncio.sleep(30)

        self.initialize_day()
        self._subscribe_push()

        eod_time = datetime.datetime.now(TZ_ET).replace(
            hour=15, minute=45, second=0, microsecond=0
        )
        while datetime.datetime.now(TZ_ET) < eod_time:
            if self.stopped:
                break
            await asyncio.sleep(10)

        await self.eod_close_all()
        self.quote_ctx.close()
        self.trade_ctx.close()
