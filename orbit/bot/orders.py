"""
OrderManager — verbatim from orb_bot.py (Clayton).
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from moomoo import (
    KLType, ModifyOrderOp, OpenQuoteContext, OpenSecTradeContext,
    OrderStatus, OrderType, RET_OK, SubType, TimeInForce, TrdSide,
)
from moomoo.common.constant import OptionType

from bot.regime import (
    ATR_STOP_MULT,
    ENTRY_FILL_WAIT_SEC,
    ENTRY_MAX_ATTEMPTS,
    HARD_STOP_LOSS_PCT,
    STRATEGY_CAPITAL,
    TRIM_MULTIPLE,
    TRIM_PCT,
    US_MARKET_HOLIDAYS,
    _full_us_code,
    _round_us_option_limit_price,
    _safe_float,
)
import datetime

# ─── ORDER MANAGER ────────────────────────────────────────────────────────────
class OrderManager:
    def __init__(self, trade_ctx, quote_ctx, trd_env, acc_id: int):
        self.ctx       = trade_ctx
        self.quote_ctx = quote_ctx
        self.trd_env   = trd_env
        self.acc_id    = acc_id
        self.positions = {}

    def _try_option_code_from_chain(
        self, symbol: str, direction: str, price: float
    ) -> Optional[str]:
        """Use exact `code` from get_option_chain — avoids invalid homemade OCC strings."""
        base = _full_us_code(symbol)
        exp_compact = self._next_expiry()
        try:
            yy = int(exp_compact[0:2])
            mm = int(exp_compact[2:4])
            dd = int(exp_compact[4:6])
            y = 2000 + yy if yy < 70 else 1900 + yy
            exp_iso = datetime.date(y, mm, dd).isoformat()
        except (ValueError, IndexError):
            return None
        ot = OptionType.CALL if direction == "CALL" else OptionType.PUT
        ret, chain = self.quote_ctx.get_option_chain(
            base, start=exp_iso, end=exp_iso, option_type=ot
        )
        if ret != RET_OK:
            print(f"   ⚠  get_option_chain({base}, {exp_iso}) — {chain}")
            return None
        if chain is None or getattr(chain, "empty", True):
            return None
        if "strike_price" not in chain.columns or "code" not in chain.columns:
            return None
        tgt = float(round(price))
        work = chain.dropna(subset=["strike_price", "code"]).copy()
        if work.empty:
            return None
        work["_strike_dist"] = (work["strike_price"] - tgt).abs()
        row = work.sort_values("_strike_dist").iloc[0]
        code = str(row["code"]).strip()
        return code or None

    def _option_code(self, symbol: str, direction: str, price: float) -> Optional[str]:
        resolved = self._try_option_code_from_chain(symbol, direction, price)
        if resolved:
            return resolved
        print("   ✗ Option chain lookup failed — entry skipped. "
              "Enable US options quote permissions in Moomoo/OpenD.")
        return None

    def _next_expiry(self) -> str:
        """Next valid trading day (1DTE). Compact YYMMDD for OCC-style codes."""
        d = datetime.date.today() + datetime.timedelta(days=1)
        while d.weekday() >= 5 or d in US_MARKET_HOLIDAYS:
            d += datetime.timedelta(days=1)
        return d.strftime("%y%m%d")

    def _next_expiry_yyyymmdd(self) -> str:
        """Same expiry as _next_expiry, YYYYMMDD (some APIs require full year)."""
        d = datetime.date.today() + datetime.timedelta(days=1)
        while d.weekday() >= 5 or d in US_MARKET_HOLIDAYS:
            d += datetime.timedelta(days=1)
        return d.strftime("%Y%m%d")

    def _ask(self, code: str, fallback: float) -> float:
        self.quote_ctx.subscribe([code], [SubType.QUOTE])
        ret, data = self.quote_ctx.get_market_snapshot([code])
        if ret != 0 or data.empty:
            return fallback
        ask = float(data["ask_price"].iloc[0])
        return ask if ask > 0 else fallback

    def _last(self, code: str) -> float:
        ret, data = self.quote_ctx.get_market_snapshot([code])
        if ret != 0 or data.empty:
            return 0.0
        bid  = float(data["bid_price"].iloc[0])
        last = float(data["last_price"].iloc[0])
        return bid if bid > 0 else last

    def _cancel(self, order_id: str) -> bool:
        # moomoo-api: use modify_order — there is no cancel_order on OpenSecTradeContext
        ret, data = self.ctx.modify_order(
            ModifyOrderOp.CANCEL, str(order_id), 0, 0,
            trd_env=self.trd_env, acc_id=self.acc_id,
        )
        if ret != 0:
            print(f"   ✗ Cancel order {order_id}: {data}")
            return False
        return True

    def _sell(self, code: str, qty: int, label: str = "") -> bool:
        ret, data = self.ctx.place_order(
            price=0, qty=qty, code=code,
            trd_side=TrdSide.SELL, order_type=OrderType.MARKET,
            trd_env=self.trd_env, time_in_force=TimeInForce.DAY,
            acc_id=self.acc_id,
        )
        if ret == 0:
            print(f"   ✓ Market sell {qty} {label}: OK")
            return True
        # Fallback: limit at bid (some routes reject market on options)
        bid = self._last(code)
        if bid > 0:
            lp = _round_us_option_limit_price(bid * 0.99)
            ret2, data2 = self.ctx.place_order(
                price=lp, qty=qty, code=code,
                trd_side=TrdSide.SELL, order_type=OrderType.NORMAL,
                trd_env=self.trd_env, time_in_force=TimeInForce.DAY,
                acc_id=self.acc_id,
            )
            ok = ret2 == 0
            print(f"   {'✓' if ok else '✗'} Limit sell {qty} @ ${lp:.2f} {label}: "
                  f"{'OK' if ok else data2}")
            return ok
        print(f"   ✗ Sell {qty} {label}: {data}")
        return False

    # ── Entry (async) ─────────────────────────────────────────────────────────
    def enter_async(self, symbol: str, direction: str, price: float,
                    risk_pct: float, on_complete=None):
        t = threading.Thread(
            target=self._enter_thread,
            args=(symbol, direction, price, risk_pct, on_complete),
            daemon=True, name=f"enter-{symbol}"
        )
        t.start()
        return t

    def _enter_thread(self, symbol, direction, price, risk_pct, on_complete):
        self.enter(symbol, direction, price, risk_pct)
        filled = self.has_position(symbol)
        if on_complete:
            try:
                on_complete(symbol, filled)
            except Exception as e:
                print(f"  ⚠  on_complete error: {e}")

    def enter(self, symbol: str, direction: str, price: float, risk_pct: float):
        risk_dollars = STRATEGY_CAPITAL * risk_pct
        opt_code     = self._option_code(symbol, direction, price)
        if not opt_code:
            return
        total_filled = 0
        entry_price  = 0.0

        print(f"\n → [{symbol}] ENTER {direction} | {opt_code} | ${risk_dollars:,.0f}")

        for attempt in range(1, ENTRY_MAX_ATTEMPTS + 1):
            ask      = _round_us_option_limit_price(
                self._ask(opt_code, fallback=price * 0.01)
            )
            need     = max(1, int(risk_dollars / (ask * 100)))
            rem      = need - total_filled
            if rem <= 0:
                break

            print(f"   Attempt {attempt}/{ENTRY_MAX_ATTEMPTS} | ask=${ask:.2f} | "
                  f"need {rem} more ({total_filled}/{need} filled)")

            ret, data = self.ctx.place_order(
                price=ask, qty=rem, code=opt_code,
                trd_side=TrdSide.BUY, order_type=OrderType.NORMAL,
                trd_env=self.trd_env, time_in_force=TimeInForce.DAY,
                acc_id=self.acc_id,
            )
            if ret != 0:
                print(f"   ✗ Order failed: {data}")
                break

            order_id = data["order_id"].iloc[0]
            print(f"   ✓ Limit {order_id} @ ${ask:.2f} — waiting {ENTRY_FILL_WAIT_SEC}s...")
            time.sleep(ENTRY_FILL_WAIT_SEC)

            dealt, avg_price, status = self._order_fill_state(order_id)
            if dealt <= total_filled:
                _ = self._cancel(order_id)
                continue

            if dealt > 0 and entry_price == 0.0:
                entry_price = avg_price if avg_price > 0 else ask
            total_filled = dealt

            if status == OrderStatus.FILLED_ALL:
                break
            _ = self._cancel(order_id)

        if total_filled > 0:
            self.positions[symbol] = {
                "direction"           : direction,
                "code"                : opt_code,
                "original_qty"        : total_filled,
                "remaining_qty"       : total_filled,
                "entry_option_price"  : entry_price,
                "entry_stock_price"   : price,
                "atr"                 : 0.0,
                "trim_level"          : 0,
                "trim_pnl"            : 0.0,
            }
            print(f"   ✓ Position: {symbol} {direction} ×{total_filled} @ ${entry_price:.2f}")
        else:
            print(f"   ✗ [{symbol}] No fill after {ENTRY_MAX_ATTEMPTS} attempts")

    def _order_fill_state(self, order_id: str) -> tuple[int, float, object]:
        """
        Return cumulative filled qty, average fill price, and status.

        `order_list_query` can be empty after a full fill because the official
        API describes it as an open-order query. Deals are the reliable source
        for today's fills.
        """
        ret, od = self.ctx.order_list_query(
            order_id=order_id, trd_env=self.trd_env, acc_id=self.acc_id,
            refresh_cache=True,
        )
        if ret == RET_OK and od is not None and not od.empty:
            row = od.iloc[0]
            return (
                int(_safe_float(row.get("dealt_qty"), 0)),
                _safe_float(row.get("dealt_avg_price"), 0),
                row.get("order_status"),
            )
        ret, deals = self.ctx.deal_list_query(
            trd_env=self.trd_env, acc_id=self.acc_id, refresh_cache=True
        )
        if ret != RET_OK or deals is None or deals.empty or "order_id" not in deals.columns:
            return 0, 0.0, None
        fills = deals[deals["order_id"].astype(str) == str(order_id)]
        if fills.empty:
            return 0, 0.0, None
        qty = int(fills["qty"].astype(float).sum())
        if "price" in fills.columns and qty > 0:
            avg = float((fills["price"].astype(float) * fills["qty"].astype(float)).sum() / qty)
        else:
            avg = 0.0
        return qty, avg, OrderStatus.FILLED_ALL

    # ── Hard stop ─────────────────────────────────────────────────────────────
    def check_hard_stop(self, symbol: str, current_px: float) -> bool:
        if symbol not in self.positions:
            return False
        pos = self.positions[symbol]
        opt_px = self._last(pos["code"])
        if opt_px > 0 and pos["entry_option_price"] > 0:
            loss = (pos["entry_option_price"] - opt_px) / pos["entry_option_price"]
            if loss >= HARD_STOP_LOSS_PCT:
                print(f"  🛑 [{symbol}] HARD STOP — option down {loss*100:.0f}%")
                return True
        entry_px = pos.get("entry_stock_price", 0)
        if entry_px > 0 and current_px > 0:
            move = current_px - entry_px
            if pos["direction"] == "PUT":
                move = -move
            atr_stop = ATR_STOP_MULT * pos.get("atr", 0)
            if atr_stop > 0 and move < -atr_stop:
                print(f"  🛑 [{symbol}] ATR STOP — move {move:.2f} vs -{atr_stop:.2f}")
                return True
        return False

    # ── Profit trim ───────────────────────────────────────────────────────────
    def check_trim(self, symbol: str) -> float:
        if symbol not in self.positions:
            return 0.0
        pos = self.positions[symbol]
        if pos["remaining_qty"] < 2:
            return 0.0
        cur = self._last(pos["code"])
        if cur <= 0:
            return 0.0
        target = pos["entry_option_price"] * (TRIM_MULTIPLE ** (pos["trim_level"] + 1))
        if cur < target:
            return 0.0
        qty = max(1, int(pos["remaining_qty"] * TRIM_PCT))
        print(f"  [{symbol}] TRIM lvl {pos['trim_level']+1} | "
              f"${cur:.2f} >= ${target:.2f} | selling {qty}")
        if self._sell(pos["code"], qty, label="trim"):
            pnl = (cur - pos["entry_option_price"]) * qty * 100
            pos["trim_pnl"]      += pnl
            pos["remaining_qty"] -= qty
            pos["trim_level"]    += 1
            return pnl
        return 0.0

    # ── Exit ──────────────────────────────────────────────────────────────────
    def exit(self, symbol: str, reason: str = "") -> float:
        if symbol not in self.positions:
            return 0.0
        pos = self.positions[symbol]
        print(f"\n → EXIT [{reason}] {pos['direction']} {symbol} ×{pos['remaining_qty']}")
        exit_px = self._last(pos["code"])
        if self._sell(pos["code"], pos["remaining_qty"], label=reason):
            pnl = (exit_px - pos["entry_option_price"]) * pos["remaining_qty"] * 100
            total = pos["trim_pnl"] + pnl
            print(f"   Trade P&L: ${total:+,.0f}")
            del self.positions[symbol]
            return total
        print(f"   ✗ EXIT FAILED — position still open; check OpenD unlock & option permissions")
        return 0.0

    def has_position(self, symbol: str) -> bool:
        return symbol in self.positions

    def open_count(self) -> int:
        return len(self.positions)
