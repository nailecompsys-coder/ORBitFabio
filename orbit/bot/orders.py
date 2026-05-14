# STRATEGY SOURCE: Replace with OrderManager verbatim from orb_bot_fabio.py.

from __future__ import annotations

from typing import Any


class OrderManager:
    """Placeholder until verbatim OrderManager is pasted from orb_bot_fabio.py."""

    def __init__(self, trade_ctx: Any, quote_ctx: Any, trd_env: Any) -> None:
        self.trade_ctx = trade_ctx
        self.quote_ctx = quote_ctx
        self.trd_env = trd_env
        self._positions: set[str] = set()

    def has_position(self, symbol: str) -> bool:
        return symbol in self._positions

    def open_count(self) -> int:
        return len(self._positions)

    def enter(
        self,
        symbol: str,
        direction: str,
        last_price: float,
        risk_mult: float,
        port_val: float,
    ) -> None:
        _ = (direction, last_price, risk_mult, port_val)
        self._positions.add(symbol)
