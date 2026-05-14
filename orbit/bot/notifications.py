"""Postgres notifications: bot_events + trades (asyncpg)."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional

import asyncpg

__all__ = ["push_event", "push_trade_entry", "push_trade_exit"]


def _uid(user_id: str) -> uuid.UUID:
    return uuid.UUID(str(user_id))


async def push_event(
    pool: asyncpg.Pool,
    user_id: str,
    event_type: str,
    payload: Mapping[str, Any],
) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO bot_events (user_id, event_type, payload)
            VALUES ($1, $2, $3::jsonb)
            """,
            _uid(user_id),
            event_type,
            json.dumps(dict(payload)),
        )


async def push_trade_entry(
    pool: asyncpg.Pool,
    user_id: str,
    *,
    symbol: str,
    direction: str,
    session_id: Optional[uuid.UUID] = None,
    option_code: Optional[str] = None,
    strike: Optional[Decimal] = None,
    expiry: Optional[str] = None,
    contracts: Optional[int] = None,
    entry_price: Optional[Decimal] = None,
    entry_time: Optional[datetime] = None,
    extra: Optional[Mapping[str, Any]] = None,
) -> uuid.UUID:
    entry_time = entry_time or datetime.now(timezone.utc)
    extra = dict(extra or {})
    async with pool.acquire() as conn:
        tid = await conn.fetchval(
            """
            INSERT INTO trades (
                user_id, session_id, symbol, direction, option_code,
                strike, expiry, contracts, entry_price, entry_time,
                vix, or_atr_pct, vix_regime, day_color, trend, status
            )
            VALUES (
                $1, $2, $3, $4, $5,
                $6, $7::date, $8, $9, $10,
                $11, $12, $13, $14, $15, 'open'
            )
            RETURNING id
            """,
            _uid(user_id),
            session_id,
            symbol,
            direction,
            option_code,
            strike,
            expiry,
            contracts,
            entry_price,
            entry_time,
            extra.get("vix"),
            extra.get("or_atr_pct"),
            extra.get("vix_regime"),
            extra.get("day_color"),
            extra.get("trend"),
        )
    return tid


async def push_trade_exit(
    pool: asyncpg.Pool,
    user_id: str,
    *,
    trade_id: uuid.UUID,
    exit_price: Optional[Decimal] = None,
    exit_time: Optional[datetime] = None,
    exit_reason: Optional[str] = None,
    pnl: Optional[Decimal] = None,
    return_pct: Optional[Decimal] = None,
) -> None:
    exit_time = exit_time or datetime.now(timezone.utc)
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE trades
            SET exit_price = $1,
                exit_time = $2,
                exit_reason = $3,
                pnl = $4,
                return_pct = $5,
                status = 'closed'
            WHERE id = $6 AND user_id = $7
            """,
            exit_price,
            exit_time,
            exit_reason,
            pnl,
            return_pct,
            trade_id,
            _uid(user_id),
        )
