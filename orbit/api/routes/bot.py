"""Bot session control (DB only; process runner comes later)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict

from api.db import pool
from api.users import UserMe, get_current_user

router = APIRouter(tags=["bot"])


class BotSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    strategy: str
    status: str
    symbols: list[str]
    trd_env: str
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None


def _row_to_session(row: Any) -> BotSessionOut:
    return BotSessionOut(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        strategy=row["strategy"],
        status=row["status"],
        symbols=list(row["symbols"]) if row["symbols"] is not None else [],
        trd_env=row["trd_env"],
        started_at=row["started_at"],
        stopped_at=row["stopped_at"],
    )


@router.post("/start", response_model=BotSessionOut)
async def bot_start(
    user: Annotated[UserMe, Depends(get_current_user)],
) -> BotSessionOut:
    uid = uuid.UUID(user.id)
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO bot_sessions (user_id, status, started_at, stopped_at)
            VALUES ($1, 'running', now(), NULL)
            ON CONFLICT (user_id) DO UPDATE SET
                status = 'running',
                started_at = now(),
                stopped_at = NULL
            RETURNING id, user_id, strategy, status, symbols, trd_env, started_at, stopped_at
            """,
            uid,
        )
    assert row is not None
    return _row_to_session(row)


@router.post("/stop", response_model=BotSessionOut)
async def bot_stop(
    user: Annotated[UserMe, Depends(get_current_user)],
) -> BotSessionOut:
    uid = uuid.UUID(user.id)
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            UPDATE bot_sessions
            SET status = 'stopped', stopped_at = now()
            WHERE user_id = $1
            RETURNING id, user_id, strategy, status, symbols, trd_env, started_at, stopped_at
            """,
            uid,
        )
    if row is None:
        raise HTTPException(404, "No bot session for user")
    return _row_to_session(row)


@router.get("/status", response_model=None)
async def bot_status(
    user: Annotated[UserMe, Depends(get_current_user)],
) -> dict[str, Any]:
    uid = uuid.UUID(user.id)
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, user_id, strategy, status, symbols, trd_env, started_at, stopped_at
            FROM bot_sessions
            WHERE user_id = $1
            """,
            uid,
        )
    if row is None:
        return {"status": "idle"}
    return _row_to_session(row).model_dump(mode="json")
