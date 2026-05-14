# STRATEGY SOURCE: Replace with RiskCircuitBreaker verbatim from orb_bot_fabio.py.

from __future__ import annotations

from typing import Tuple


class RiskCircuitBreaker:
    """Placeholder until verbatim RiskCircuitBreaker is pasted from orb_bot_fabio.py."""

    def can_enter(self, open_count: int) -> Tuple[bool, str]:
        if open_count >= 6:
            return False, "max_positions"
        return True, ""

    def size_modifier(self) -> float:
        return 1.0
