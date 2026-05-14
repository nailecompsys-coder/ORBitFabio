"""Trade history API."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, Query

from api.db import pool
from api.users import UserMe, get_current_user

router = APIRouter(tags=["trades"])


def _serialize_trade(row: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, val in dict(row).items():
        if val is None:
            out[key] = None
        elif isinstance(val, uuid.UUID):
            out[key] = str(val)
        elif isinstance(val, Decimal):
            out[key] = float(val)
        elif isinstance(val, (datetime, date)):
            out[key] = val.isoformat()
        else:
            out[key] = val
    return out


@router.post("/history")
async def trades_history(
    user: Annotated[UserMe, Depends(get_current_user)],
    symbol: Optional[str] = Query(None, max_length=10),
    status: Optional[str] = Query(None, max_length=20),
    limit: int = Query(100, ge=1, le=500),
) -> list[dict[str, Any]]:
    uid = uuid.UUID(user.id)
    async with pool().acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
                id, user_id, session_id, symbol, direction, option_code,
                strike, expiry, contracts, entry_price, exit_price,
                entry_time, exit_time, exit_reason, pnl, return_pct,
                vix, or_atr_pct, vix_regime, day_color, trend, status
            FROM trades
            WHERE user_id = $1
              AND ($2::varchar IS NULL OR symbol = $2)
              AND ($3::varchar IS NULL OR trades.status = $3)
            ORDER BY entry_time DESC NULLS LAST, id DESC
            LIMIT $4
            """,
            uid,
            symbol,
            status,
            limit,
        )
    return [_serialize_trade(r) for r in rows]
