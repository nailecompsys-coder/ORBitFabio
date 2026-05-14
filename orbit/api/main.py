"""ORBit FABIO API — Phase 1 skeleton (health, CORS, auth)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import auth
from api.db import close_db, health_check_db, health_check_redis, init_db

ALLOWED_ORIGINS = [
    "https://trading.clermontitstore.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(title="ORBit FABIO API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth")


@app.get("/health", response_model=None)
async def health():
    ok_db = await health_check_db()
    ok_redis = await health_check_redis()
    if ok_db and ok_redis:
        return {"status": "ok", "database": True, "redis": True}
    return JSONResponse(
        status_code=503,
        content={
            "status": "unhealthy",
            "database": ok_db,
            "redis": ok_redis,
        },
    )
