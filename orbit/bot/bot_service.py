#!/usr/bin/env python3
"""ORBit FABIO bot — host entry (systemd). Reads env; connects OpenD + Postgres."""

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv


async def _async_main() -> None:
    load_dotenv()

    import asyncpg
    from moomoo import TrdEnv

    from bot.fabio_bot import ORBBot

    user_id = os.environ.get("ORBIT_BOT_USER_ID", "").strip()
    opend_s = os.environ.get("ORBIT_BOT_OPEND_PORT", "").strip()
    dsn = (os.environ.get("DATABASE_URL") or os.environ.get("PG_DSN") or "").strip()
    if not user_id or not opend_s:
        print("ORBIT_BOT_USER_ID and ORBIT_BOT_OPEND_PORT are required", file=sys.stderr)
        sys.exit(1)
    if not dsn:
        print("DATABASE_URL (or PG_DSN) is required", file=sys.stderr)
        sys.exit(1)

    opend_port = int(opend_s)
    trd_env = (
        TrdEnv.REAL
        if os.getenv("ORBIT_BOT_TRD_ENV", "SIMULATE").upper() == "REAL"
        else TrdEnv.SIMULATE
    )

    pool = await asyncpg.create_pool(dsn)
    try:
        bot = ORBBot(
            user_id=user_id,
            opend_port=opend_port,
            trd_env=trd_env,
            db_session=pool,
            sheets_logger=None,
        )
        await bot.run()
    finally:
        await pool.close()


def main() -> None:
    asyncio.run(_async_main())


if __name__ == "__main__":
    main()
