# ORBit stack — deploy root (mirror of `/opt/orbit` on Northstar)

The **full** `docker-compose.yml` in this folder includes `ovtlyr-browser`, which builds from **`./scripts/ovtlyr-browser`** on the server. This repo ships **`api/`** and **`migrations/`** for Phase 1; do **not** blindly `rsync --delete` the whole tree onto Northstar (see [NORTHSTAR_SAFE_CHANGES.md](../docs/NORTHSTAR_SAFE_CHANGES.md)).

## Deploy API skeleton to existing Northstar

From FabioOrb repo root on your Mac:

```bash
chmod +x orbit/scripts/deploy-api.sh
./orbit/scripts/deploy-api.sh ncs@192.168.1.116 /opt/orbit
```

Copy or merge **`orbit/Caddyfile`** into **`/opt/orbit/Caddyfile`** on the server when routing changes (the API-only deploy script does not rsync it). Then run **`docker compose restart caddy`** (or **`up -d`**) so the proxy reloads.

SSH to Northstar, then rebuild **only** the `api` service (paths like `/opt/orbit` exist **on the server**, not on your Mac):

```bash
ssh ncs@192.168.1.116
cd /opt/orbit
# Optional: add TEXTBELT_KEY=... to .env for real SMS
docker compose up -d --build api
docker compose exec api curl -sf http://127.0.0.1:8000/health
```

**Gate (health):** last command returns JSON with `"status":"ok"` and exit code **0** (HTTP **200**). The API is not on the host loopback; use `docker compose exec api …` as above.

## Phase 2 — Auth (public URL + curl)

Auth routes are **`/auth/*`** on the API. User profile stays under **`/api/users/*`**. The repo **`orbit/Caddyfile`** proxies **`/auth/*`** and **`/ws/*`** to `api:8000` without stripping; **`/api/*`** uses `uri strip_prefix /api` before the same upstream.

**Gate — request OTP** (replace phone; use `-k` only if TLS is self-signed):

```bash
curl -sS -X POST "https://trading.clermontitstore.com/auth/request-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOUR_PHONE"}'
# Expect: {"sent":true}
# SMS via TextBelt if TEXTBELT_KEY is set; else OTP in: docker compose logs api --tail 20
```

**Verify OTP** (use code from SMS or logs):

```bash
curl -sS -X POST "https://trading.clermontitstore.com/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOUR_PHONE","code":"123456"}'
# Expect: {"token":"...","user_id":"..."}
```

**Current user** (Bearer JWT from verify step):

```bash
curl -sS "https://trading.clermontitstore.com/api/users/me" \
  -H "Authorization: Bearer YOUR_JWT"
```

Merge the **`api:`** block from `orbit/docker-compose.yml` into server `/opt/orbit/docker-compose.yml` if you need `TEXTBELT_KEY` or longer `start_period` (already set to **60s** here for migrations).

## Phase 1 API layout

- `api/` — FastAPI app, Dockerfile, `entrypoint.sh` (migrations + uvicorn)
- `migrations/001_initial.sql` — schema

If `TEXTBELT_KEY` is unset, `POST /auth/request-otp` logs the OTP to container stdout.
