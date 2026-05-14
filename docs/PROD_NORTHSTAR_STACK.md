# Northstar production stack (`192.168.1.116`)

**This document removes ambiguity:** production for the options / Northstar product runs on **`ncs@192.168.1.116`**. That host must run **Moomoo OpenD**, the **trading bot** (Moomoo Python API), and the **web frontend**, together with backing services (**PostgreSQL**, **Redis**, reverse proxy) as actually deployed.

**Phase 1 as-run (2026-05-14):** see **[PHASE1_DISCOVERY_AS_RUN.md](PHASE1_DISCOVERY_AS_RUN.md)** — live inventory (Docker services, ports **`5434`/`6380`**, Caddy **in container**, `/opt/orbit` vs `/opt/optionsbot`).

**Change safety (frozen containers, paths, prune rules):** **[NORTHSTAR_SAFE_CHANGES.md](NORTHSTAR_SAFE_CHANGES.md)** — **mandatory** before teardown, compose edits, or API replacement.

Companion references on your machine (not shipped inside FabioOrb):

- Moomoo / OpenD / SDK SSOT: `/Users/donnaile/dev/ORB/docs/MOOMOO_COMMAND_LANGUAGE_SSOT.md`
- Bot bootstrap (venv, `moomoo-api`, OpenD logged in): `/Users/donnaile/dev/ORB/README.md`
- Legacy deploy one-liner (same host/path): `/Users/donnaile/dev/CAL/cal-app/.cursor/rules/build_app.md` (search for `192.168.1.116`)

---

## SSH

```bash
ssh ncs@192.168.1.116
```

**Phase 1 discovery (read-only):** run [`scripts/phase1-discovery.sh`](../scripts/phase1-discovery.sh) on the server — see [`scripts/README.md`](../scripts/README.md). Save output under `reports/` (gitignored as `*.txt`) and use it before any teardown.

---

## 1. Moomoo OpenD (required)

OpenD is the **local gateway** between Moomoo’s network and your code. The bot’s Python SDK talks to OpenD (commonly **`127.0.0.1:11111`** on the same machine; confirm ports in OpenD settings if yours differ).

**Operational requirements**

- OpenD **installed** (visualization / GUI build is typical for operators who need the status indicator).
- OpenD **running** and **logged in** (Moomoo account; paper vs live per your policy).
- If the bot runs **inside Docker**, the compose file must still allow the bot process to reach OpenD (e.g. `network_mode: host`, published ports, or `extra_hosts` / `host.docker.internal` — **wrong networking here is the #1 reason “the bot can’t see Moomoo”**). Validate against the real `docker-compose.yml` on the server.

Official and local doc pointers are in the ORB SSOT file above.

---

## 2. Deploy roots on disk (Docker)

**As of Phase 1 discovery:** the running stack (`orbit-api`, `orbit-caddy`, `orbit-postgres`, `orbit-redis`, `orbit-ovtlyr-browser`) is consistent with a compose project under **`/opt/orbit`**. **`/opt/optionsbot`** still exists (legacy CAL note); **`/opt/Orbit`** also present — confirm which repo owns which before editing.

```bash
cd /opt/orbit
docker compose ps
docker compose up -d --build   # Don-initiated only; align with team policy
```

Legacy path (only if your release still uses it):

```bash
cd /opt/optionsbot
docker compose ps
docker compose up -d --build
```

After deploy: `docker compose logs -f <service>` using names from `docker compose ps`.

**Postgres from the host:** `127.0.0.1:5434` → container `5432` (not port 5432 on the host). **Redis:** `127.0.0.1:6380`.

---

## 3. Web frontend and TLS

**As observed:** **Caddy runs in Docker** (`orbit-caddy-1`), not as a host `systemd` unit. Public ports **80** and **443** are bound from that container.

Public URL (per [ORBIT_CURSOR_SETUP](ORBIT_CURSOR_SETUP)): **`https://trading.clermontitstore.com`** — confirm DNS points at this host and that Caddy’s config inside the compose project matches that hostname.

**Browser automation / VNC-style UI:** `orbit-ovtlyr-browser-1` exposes **`0.0.0.0:6080`** (treat as sensitive; firewall accordingly).

---

## 4. PostgreSQL and Redis (Docker)

**Postgres:** `orbit-postgres-1`, image `postgres:16-alpine`, **healthy**, **`127.0.0.1:5434:5432`**. Align `.env` / SSH tunnels with **port 5434**, not 5432.

**Redis:** `orbit-redis-1`, **`127.0.0.1:6380:6379`**.

Ensure compose **volumes** and credentials match application `.env` on the server.

---

## 5. Host baseline (still required)

Docker Engine, disk space, time sync, and firewall/LAN rules must allow:

- Outbound from this host to Moomoo / markets (per OpenD requirements).
- Inbound to the **frontend** and **API** ports from your LAN or VPN as intended.

---

## 6. FabioOrb mobile app

The iOS app in this repo calls **your HTTP API** using the **PROD** base URL you place in [ENVIRONMENT.md](ENVIRONMENT.md). It does **not** embed OpenD; OpenD stays on the server (or wherever you deliberately run it).

---

## First-time or “is prod actually complete?” checklist

On `192.168.1.116` after SSH:

1. OpenD GUI shows **logged in / green** (or equivalent healthy state).  
2. `cd /opt/orbit && docker compose ps` — **`orbit-api`**, **`orbit-caddy`**, **`orbit-postgres`**, **`orbit-redis`** (and siblings you expect) **Up / healthy**.  
3. `docker ps` — decide whether **`project-go-mcp-stack-*`** on **:8080** is still required before any global teardown.  
4. From a browser on the LAN: **frontend** loads (e.g. **`https://trading.clermontitstore.com`** if DNS is correct).  
5. Hit **API health** (e.g. `/api/health` per ORBIT doc) through Caddy.  
6. Bot log shows **quote/trade context** connected (no “cannot open quote context” loop — see ORB README troubleshooting).

If any step fails, fix that layer before treating prod as “ready for Claude / Cursor to extend the app against.”
