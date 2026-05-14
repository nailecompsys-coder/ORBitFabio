"""Async Postgres (asyncpg) + Redis clients for the API."""

from __future__ import annotations

import os
from typing import Optional

import asyncpg
import redis.asyncio as redis

_pool: Optional[asyncpg.Pool] = None
_redis: Optional[redis.Redis] = None


def _pg_dsn() -> str:
    url = os.environ.get("DATABASE_URL")
    if url:
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        return url
    return "postgresql://{user}:{password}@{host}:{port}/{db}".format(
        user=os.environ.get("PGUSER", "orbit"),
        password=os.environ.get("PGPASSWORD", ""),
        host=os.environ.get("PGHOST", "postgres"),
        port=os.environ.get("PGPORT", "5432"),
        db=os.environ.get("PGDATABASE", "orbit"),
    )


async def init_db() -> None:
    global _pool, _redis
    _pool = await asyncpg.create_pool(_pg_dsn(), min_size=1, max_size=10)
    url = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    _redis = redis.from_url(url, decode_responses=True)


async def close_db() -> None:
    global _pool, _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
    if _pool is not None:
        await _pool.close()
        _pool = None


def pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("Database pool not initialized")
    return _pool


def redis_client() -> redis.Redis:
    if _redis is None:
        raise RuntimeError("Redis client not initialized")
    return _redis


async def health_check_db() -> bool:
    async with pool().acquire() as conn:
        v = await conn.fetchval("SELECT 1")
        return v == 1


async def health_check_redis() -> bool:
    try:
        return await redis_client().ping()
    except Exception:
        return False
