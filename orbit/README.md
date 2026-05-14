# ORBit stack — deploy root (mirror of `/opt/orbit` on Northstar)

The **full** `docker-compose.yml` in this folder includes `ovtlyr-browser`, which builds from **`./scripts/ovtlyr-browser`** on the server. This repo ships **`api/`** and **`migrations/`** for Phase 1; do **not** blindly `rsync --delete` the whole tree onto Northstar (see [NORTHSTAR_SAFE_CHANGES.md](../docs/NORTHSTAR_SAFE_CHANGES.md)).

## Deploy API skeleton to existing Northstar

From FabioOrb repo root on your Mac:

```bash
chmod +x orbit/scripts/deploy-api.sh
./orbit/scripts/deploy-api.sh ncs@192.168.1.116 /opt/orbit
```

SSH and rebuild **only** the `api` service:

```bash
ssh ncs@192.168.1.116
cd /opt/orbit
# Optional: add TEXTBELT_KEY=... to .env for real SMS
docker compose up -d --build api
docker compose exec api curl -sf http://127.0.0.1:8000/health
```

**Gate:** last command returns JSON with `"status":"ok"` and exit code **0** (HTTP **200**). The API is not on the host loopback; use `docker compose exec api …` as above.

Merge the **`api:`** block from `orbit/docker-compose.yml` into server `/opt/orbit/docker-compose.yml` if you need `TEXTBELT_KEY` or longer `start_period` (already set to **60s** here for migrations).

## Phase 1 API layout

- `api/` — FastAPI app, Dockerfile, `entrypoint.sh` (migrations + uvicorn)
- `migrations/001_initial.sql` — schema

If `TEXTBELT_KEY` is unset, `POST /auth/request-otp` logs the OTP to container stdout.
