# Phase 1 discovery — Northstar as observed

**When:** 2026-05-14 (from `scripts/phase1-discovery.sh` run as `ncs@192.168.1.116`).  
**Purpose:** Ground truth before any teardown (see [ORBIT_CURSOR_SETUP](ORBIT_CURSOR_SETUP)).

## Summary

| Topic | Observation |
|--------|----------------|
| **SSH user** | `ncs` (password auth used from Mac) |
| **Systemd app stack** | No `optionsbot` / `northstar` / `opend-*` / `caddy` / `nginx` units in the **running** list — workload is mostly **Docker**. |
| **Caddy** | **Not** installed on the host OS; **Caddy runs in Docker** (`orbit-caddy-1`, image `caddy:2-alpine`), publishing **`:80` and `:443`**. |
| **Nginx** | Not installed; inactive. |
| **Postgres (system)** | Not installed; inactive. |
| **Postgres (Docker)** | `orbit-postgres-1` — `postgres:16-alpine`, **healthy**, bound **`127.0.0.1:5434` → container 5432** (not 5432 on the host). |
| **Redis** | `orbit-redis-1` — **`127.0.0.1:6380` → 6379**. |
| **API** | `orbit-api-1` — healthy, internal **8000/tcp** (likely reached via Caddy reverse proxy, not directly on discovery list). |
| **Browser / VNC** | `orbit-ovtlyr-browser-1` — **`0.0.0.0:6080`**. |
| **Other Docker** | `project-go-mcp-stack-api-1` on **`:8080`**, `project-go-mcp-stack-worker-1` — **separate project**; any global `docker prune` / Phase 2 teardown in ORBIT_CURSOR_SETUP would affect these unless scoped. |
| **`/opt` layout** | **`/opt/orbit`** (owned `ncs`), **`/opt/optionsbot`**, **`/opt/Orbit`** (capital O). |
| **Host Node** | `v18.19.1` / npm `9.2.0` (may be unused if Node work is only in CI or on Mac). |
| **Host Python** | `3.12.3` (containers may use other versions). |
| **Cron** | `CRON_TZ=America/New_York`; job **`5 9 * * 1-5 /opt/orbit/scripts/cron_ovtlyr_morning.sh`**. |

## Listening ports (high level)

- **22** — SSH  
- **80 / 443** — Docker Caddy  
- **5434** — Postgres (localhost only)  
- **6380** — Redis (localhost only)  
- **6080** — ovtlyr browser  
- **8080** — `project-go-mcp-stack` API  
- Several **127.0.0.1** high ports with **node** — local processes (inspect on server if needed).

## Implications for [ORBIT_CURSOR_SETUP](ORBIT_CURSOR_SETUP)

- The playbook assumes **host-installed Caddy** and **`/etc/caddy/Caddyfile`**. On this box, **Caddy is containerized** — do not expect a host `Caddyfile` until you align docs with compose.  
- Playbook Postgres example used **`127.0.0.1:5432`**; live DB is on **`127.0.0.1:5434`**. Any `.env` / tunnel commands must use **5434**.  
- **Phase 2 teardown** that removes **all** Docker containers/images will hit **`project-go-mcp-stack-*`** — confirm with owners before running.

## Next step

Phase 2 (teardown) only after an explicit decision: **target layout** (`/opt/orbit` only vs coexist with `optionsbot`) and **whether `project-go-mcp-stack` stays**.
