"""Authenticated user endpoints."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict

from api.auth import decode_token
from api.db import pool

router = APIRouter(tags=["users"])
security = HTTPBearer(auto_error=False)


class UserMe(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    phone: str
    display_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime


async def get_current_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
) -> UserMe:
    if credentials is None or not credentials.credentials:
        raise HTTPException(401, "Not authenticated")
    user_id = decode_token(credentials.credentials)
    async with pool().acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, phone, display_name, role, is_active, created_at
            FROM users
            WHERE id = $1
            """,
            user_id,
        )
    if row is None:
        raise HTTPException(404, "User not found")
    return UserMe(
        id=str(row["id"]),
        phone=row["phone"],
        display_name=row["display_name"],
        role=row["role"],
        is_active=row["is_active"],
        created_at=row["created_at"],
    )


@router.get("/me", response_model=UserMe)
async def read_users_me(user: Annotated[UserMe, Depends(get_current_user)]) -> UserMe:
    return user
