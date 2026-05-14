"""Moomoo push callback handlers (Phase 2 — ORBIT_NORTHSTAR_BUILD)."""

from __future__ import annotations

import asyncio
import datetime

from moomoo import CurKlineHandlerBase, RET_OK

__all__ = ["FiveMinBarHandler", "ThreeMinBarHandler", "DailyBarHandler"]


class FiveMinBarHandler(CurKlineHandlerBase):
    """Called when each 5-min bar closes; drives signal detection."""

    def __init__(self, bot, loop):
        super().__init__()
        self.bot = bot
        self.loop = loop

    def on_recv_rsp(self, rsp_pb):
        ret, data = super().on_recv_rsp(rsp_pb)
        if ret != RET_OK or data.empty:
            return
        now = datetime.datetime.now()
        or_close = now.replace(hour=9, minute=45, second=0, microsecond=0)
        signal_end = now.replace(hour=14, minute=0, second=0, microsecond=0)
        if not (or_close <= now <= signal_end):
            return
        symbol = data["code"].iloc[-1].replace("US.", "")
        asyncio.run_coroutine_threadsafe(
            self.bot.on_5min_bar_close(symbol),
            self.loop,
        )


class ThreeMinBarHandler(CurKlineHandlerBase):
    """Called at every 3-min bar close; drives exit logic."""

    def __init__(self, bot, loop):
        super().__init__()
        self.bot = bot
        self.loop = loop

    def on_recv_rsp(self, rsp_pb):
        ret, data = super().on_recv_rsp(rsp_pb)
        if ret != RET_OK or data.empty:
            return
        symbol = data["code"].iloc[-1].replace("US.", "")
        if symbol not in self.bot.signals:
            return
        asyncio.run_coroutine_threadsafe(
            self.bot.on_3min_bar_close(symbol),
            self.loop,
        )


class DailyBarHandler(CurKlineHandlerBase):
    """Called when today's daily bar appears; refresh ATR / trend context."""

    def __init__(self, bot, loop):
        super().__init__()
        self.bot = bot
        self.loop = loop

    def on_recv_rsp(self, rsp_pb):
        ret, data = super().on_recv_rsp(rsp_pb)
        if ret != RET_OK or data.empty:
            return
        symbol = data["code"].iloc[-1].replace("US.", "")
        asyncio.run_coroutine_threadsafe(
            self.bot.on_daily_bar(symbol, data),
            self.loop,
        )
