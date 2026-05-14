"""Phone OTP (TextBelt) + JWT auth."""

from __future__ import annotations

import os
import random
import string
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException
from jose import JWTError, jwt
from pydantic import BaseModel, Field

from api.db import pool

router = APIRouter(tags=["auth"])

JWT_SECRET = os.environ.get("JWT_SECRET", "change-me-in-production")
JWT_ALGO = "HS256"
TEXTBELT_KEY = os.environ.get("TEXTBELT_KEY", "")


class OtpRequest(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)


class OtpVerify(BaseModel):
    phone: str = Field(..., min_length=10, max_length=20)
    code: str = Field(..., min_length=4, max_length=10)


async def get_or_create_user(conn: Any, phone: str) -> uuid.UUID:
    row = await conn.fetchrow("SELECT id FROM users WHERE phone = $1", phone)
    if row:
        return row["id"]
    uid = await conn.fetchval(
        "INSERT INTO users (phone) VALUES ($1) RETURNING id",
        phone,
    )
    return uid


@router.post("/request-otp")
async def request_otp(body: OtpRequest) -> dict[str, bool]:
    code = "".join(random.choices(string.digits, k=6))
    expires = datetime.now(timezone.utc) + timedelta(minutes=10)

    async with pool().acquire() as conn:
        await conn.execute(
            """
            INSERT INTO otp_codes (phone, code, expires_at)
            VALUES ($1, $2, $3)
            """,
            body.phone,
            code,
            expires,
        )

    if not TEXTBELT_KEY:
        # Dev: no SMS provider — still store OTP; operator reads logs if needed.
        print(f"[auth] TEXTBELT_KEY unset; OTP for {body.phone}: {code}", flush=True)
    else:
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(
                "https://textbelt.com/text",
                data={
                    "phone": body.phone,
                    "message": f"ORBit code: {code}. Expires in 10 min.",
                    "key": TEXTBELT_KEY,
                },
            )
            if r.status_code != 200:
                raise HTTPException(502, "SMS provider error")
            data = r.json()
            if not data.get("success") and data.get("quotaRemaining") is None:
                raise HTTPException(502, f"SMS rejected: {data}")

    return {"sent": True}


@router.post("/verify-otp")
async def verify_otp(body: OtpVerify) -> dict[str, str]:
    async with pool().acquire() as conn:
        async with conn.transaction():
            row = await conn.fetchrow(
                """
                SELECT id FROM otp_codes
                WHERE phone = $1 AND code = $2 AND used = false AND expires_at > now()
                ORDER BY created_at DESC
                LIMIT 1
                """,
                body.phone,
                body.code,
            )
            if not row:
                raise HTTPException(401, "Invalid or expired code")

            await conn.execute(
                "UPDATE otp_codes SET used = true WHERE id = $1",
                row["id"],
            )

            user_id = await get_or_create_user(conn, body.phone)

    token = jwt.encode(
        {
            "sub": str(user_id),
            "exp": datetime.now(timezone.utc) + timedelta(days=30),
        },
        JWT_SECRET,
        algorithm=JWT_ALGO,
    )

    return {"token": token, "user_id": str(user_id)}


def decode_token(token: str) -> uuid.UUID:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGO])
        sub: Optional[str] = payload.get("sub")
        if not sub:
            raise JWTError("missing sub")
        return uuid.UUID(sub)
    except (JWTError, ValueError) as e:
        raise HTTPException(401, "Invalid token") from e