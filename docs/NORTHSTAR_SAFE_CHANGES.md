# Northstar (`192.168.1.116`) — safe change policy

**Status:** Operational guardrails after Phase 1 discovery. **Overrides** any generic “teardown / prune everything” language elsewhere (including [ORBIT_CURSOR_SETUP](ORBIT_CURSOR_SETUP) Phase 2) when they conflict.

---

## Do not run (global / destructive)

- **`docker system prune`** (any variant that wipes unused data broadly without naming resources).
- **Remove all containers** or **remove all images** in one shot.
- **`docker volume prune`** (or similar) if it could touch **Postgres** data volumes used by `orbit-postgres-1`.

---

## Do not stop, remove, or recreate (frozen)

Treat these as **production infrastructure** unless Don explicitly changes this file:

| Resource | Notes |
|----------|--------|
| **`orbit-postgres-1`** | Data bind-mount: compose **`./data/postgres`** → host **`/opt/orbit/data/postgres`** — **never delete** that directory. |
| **`orbit-redis-1`** | Session/cache stack dependency. |
| **`orbit-ovtlyr-browser-1`** | Exposes **6080**; required for current workflows. |
| **`orbit-caddy-1`** | TLS + reverse proxy on **80/443**. |
| **`project-go-mcp-stack-api`** | Listens on **8080** — separate project; do not touch. |
| **`project-go-mcp-stack-worker`** | Worker for same stack; do not touch. |

---

## Do not delete on disk

| Path | Reason |
|------|--------|
| **`/opt/orbit/scripts/`** | Active cron: e.g. `cron_ovtlyr_morning.sh` (see Phase 1 discovery). |
| **`/opt/orbit/data/postgres/`** | Postgres persistence (`./data/postgres` in [ORBIT_DOCKER_COMPOSE.server.yml](ORBIT_DOCKER_COMPOSE.server.yml)). |

---

## Safe to remove (after confirmation on server)

| Item | Precondition |
|------|----------------|
| **`orbit-api-1`** container **and its image** | Replacing with **FABIO API**; no other service should reference that image name without coordination. |
| **`/opt/Orbit`** (capital **O**) | **2026-05-14:** empty directory (only `.` / `..`). Safe to remove after redundant-check. |
| **`/opt/optionsbot`** | **2026-05-14:** only **`.claude/`** present; no `docker-compose` here on server. Still confirm no external backup/cron references before `rm -rf`. |

---

## Safe to rebuild / edit

- **`docker-compose.yml`** (or equivalent) **only** for the **orbit API service** definition — without changing frozen services above unless explicitly approved.
- **Host paths used by Caddy container:** **`/opt/orbit/Caddyfile`** (read-only mount to `/etc/caddy/Caddyfile`), **`/opt/orbit/ui`** → `/srv`, **`/opt/orbit/caddy/data`**, **`/opt/orbit/caddy/config`**. Edit **`Caddyfile`** / static **`ui/`** and reload Caddy — do **not** remove the **caddy** service definition without replacing TLS routing.
- **All Python / FastAPI application code** for the API being replaced (FABIO), in the repo path that deploys to the API container.

---

## Related docs

- [ORBIT_DOCKER_COMPOSE.server.yml](ORBIT_DOCKER_COMPOSE.server.yml) — snapshot of live **`/opt/orbit/docker-compose.yml`** (2026-05-14).
- [PHASE1_DISCOVERY_AS_RUN.md](PHASE1_DISCOVERY_AS_RUN.md) — what is actually running.
- [PROD_NORTHSTAR_STACK.md](PROD_NORTHSTAR_STACK.md) — prod checklist.
- [ENVIRONMENT.md](ENVIRONMENT.md) — SSH user, URLs.

When in doubt, **Phase 1 discovery** again and paste output before changing anything.
