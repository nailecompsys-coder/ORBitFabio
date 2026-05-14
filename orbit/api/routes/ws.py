"""WebSocket: live bot_events feed + heartbeat."""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, status

from api.auth import decode_token
from api.db import pool

router = APIRouter(tags=["ws"])

POLL_INTERVAL_S = 0.5
HEARTBEAT_INTERVAL_S = 30.0


def _event_payload(row: Any) -> dict[str, Any]:
    created = row["created_at"]
    return {
        "id": row["id"],
        "user_id": str(row["user_id"]),
        "event_type": row["event_type"],
        "payload": row["payload"],
        "created_at": created.isoformat() if created is not None else None,
    }


@router.websocket("/{user_id}")
async def bot_event_stream(
    websocket: WebSocket,
    user_id: str,
    token: str | None = Query(None, description="JWT (same as Bearer for HTTP)"),
) -> None:
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return
    if token.startswith("Bearer "):
        token = token[7:].strip()
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        path_uid = uuid.UUID(user_id)
    except ValueError:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        sub = decode_token(token)
    except HTTPException:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    if sub != path_uid:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    await websocket.accept()

    async with pool().acquire() as conn:
        last_seen_id = await conn.fetchval(
            "SELECT COALESCE(MAX(id), 0) FROM bot_events WHERE user_id = $1",
            path_uid,
        )
    last_seen: int = int(last_seen_id or 0)

    stop = asyncio.Event()

    async def poll_loop() -> None:
        nonlocal last_seen
        try:
            while not stop.is_set():
                async with pool().acquire() as conn:
                    rows = await conn.fetch(
                        """
                        SELECT id, user_id, event_type, payload, created_at
                        FROM bot_events
                        WHERE user_id = $1 AND id > $2
                        ORDER BY id ASC
                        """,
                        path_uid,
                        last_seen,
                    )
                for row in rows:
                    if stop.is_set():
                        return
                    last_seen = int(row["id"])
                    try:
                        await websocket.send_json(_event_payload(row))
                    except Exception:
                        stop.set()
                        return
                try:
                    await asyncio.wait_for(stop.wait(), timeout=POLL_INTERVAL_S)
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, RuntimeError, OSError):
            stop.set()

    async def heartbeat_loop() -> None:
        try:
            while not stop.is_set():
                try:
                    await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_INTERVAL_S)
                except asyncio.TimeoutError:
                    pass
                if stop.is_set():
                    return
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    stop.set()
                    return
        except (WebSocketDisconnect, RuntimeError, OSError):
            stop.set()

    async def read_loop() -> None:
        try:
            while True:
                await websocket.receive()
        except WebSocketDisconnect:
            pass
        finally:
            stop.set()

    tasks = [
        asyncio.create_task(poll_loop()),
        asyncio.create_task(heartbeat_loop()),
        asyncio.create_task(read_loop()),
    ]
    try:
        await asyncio.gather(*tasks)
    finally:
        stop.set()
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        try:
            await websocket.close()
        except Exception:
            pass
