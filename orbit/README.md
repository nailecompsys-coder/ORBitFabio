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

Auth routes are **`/auth/*`**. **`/api/*`** uses **`uri strip_prefix /api`** in **`orbit/Caddyfile`**, so **`GET https://…/api/users/me`** hits the app as **`GET /users/me`**. **`/auth/*`**, **`/bot/*`**, **`/users/*`**, **`/ws/*`**, and **`/trades/*`** are proxied **without** stripping.

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

## Phase 3 — Auth completion + bot (DB layer)

### 1. Verify OTP end-to-end (dev: OTP in logs)

```bash
curl -sS -X POST "https://trading.clermontitstore.com/auth/request-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOUR_PHONE"}'
```

On the server, read the code from API logs (container name may be `orbit-api-1` or use `docker compose logs api`):

```bash
docker logs orbit-api-1 --tail 30 2>&1 | grep -E '\[auth\]|OTP'
# or: cd /opt/orbit && docker compose logs api --tail 40
```

Verify and capture the JWT:

```bash
curl -sS -X POST "https://trading.clermontitstore.com/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+1YOUR_PHONE","code":"123456"}'
# Expect: {"token":"...","user_id":"..."}
```

### 2. Current user (JWT required)

Same as Phase 2: **`GET …/api/users/me`** with **`Authorization: Bearer`**.

### 3–4. Bot session control (JWT required)

**`bot_sessions`** is one row per user (`UNIQUE(user_id)`): **start** upserts `status=running`; **stop** sets `status=stopped`; **status** returns **`{"status":"idle"}`** when there is no row, otherwise session fields (including **`status`**).

```bash
export JWT=...   # from verify-otp

curl -sS -X POST "https://trading.clermontitstore.com/bot/start" \
  -H "Authorization: Bearer $JWT"

curl -sS "https://trading.clermontitstore.com/bot/status" \
  -H "Authorization: Bearer $JWT"

curl -sS -X POST "https://trading.clermontitstore.com/bot/stop" \
  -H "Authorization: Bearer $JWT"
```

**Gate:** `GET /bot/status` with a valid Bearer token returns **`{"status":"idle"}`** (no session yet) or a JSON object with **`"status"`** and session metadata after **start**.

## Phase 4 — WebSocket feed + trade history

### WebSocket (`/ws/{user_id}`)

Requires a JWT whose **`sub`** matches **`user_id`**. Pass the token as a query parameter (browsers and **`wscat`** do not send HTTP `Authorization` on the WS handshake):

```text
wss://trading.clermontitstore.com/ws/YOUR_USER_UUID?token=YOUR_JWT
```

The server polls **`bot_events`** every **500ms** for new rows after connect (cursor = max existing id at connect), pushes each row as JSON, and sends **`{"type":"ping"}`** every **30s**.

**Gate (wscat):** within **30s** you should see a ping (install **`wscat`** globally if needed: `npm install -g wscat`):

```bash
wscat -c "wss://trading.clermontitstore.com/ws/YOUR_USER_UUID?token=YOUR_JWT"
# expect: {"type":"ping"}
```

### Trade history (`POST /trades/history`)

JWT **`Authorization: Bearer`**. Optional query: **`symbol`**, **`status`**, **`limit`** (default **100**, max **500**). Returns up to **`limit`** rows for the current user, newest first.

```bash
curl -sS -X POST "https://trading.clermontitstore.com/trades/history?symbol=SPY&limit=50" \
  -H "Authorization: Bearer $JWT"
```

### Caddy

**`/ws/*`** uses **`reverse_proxy api:8000`** with no URI rewrite. Caddy **v2 forwards `Connection` and `Upgrade` automatically** for WebSocket upgrades; no extra `header_up` is required for the typical upgrade case.

Merge the **`api:`** block from `orbit/docker-compose.yml` into server `/opt/orbit/docker-compose.yml` if you need `TEXTBELT_KEY` or longer `start_period` (already set to **60s** here for migrations).

## Phase 1 API layout

- `api/` — FastAPI app, Dockerfile, `entrypoint.sh` (migrations + uvicorn)
- `migrations/001_initial.sql` — schema

If `TEXTBELT_KEY` is unset, `POST /auth/request-otp` logs the OTP to container stdout.
