# Northstar production stack (`192.168.1.116`)

**This document removes ambiguity:** production for the options / Northstar product runs on **`ncs@192.168.1.116`**. That host must run **Moomoo OpenD**, the **trading bot** (Moomoo Python API), and the **web frontend**, together with whatever backing services your live `docker-compose` defines (for example **PostgreSQL**). Development stays on your Mac; this is the **prod** story only.

Companion references on your machine (not shipped inside FabioOrb):

- Moomoo / OpenD / SDK SSOT: `/Users/donnaile/dev/ORB/docs/MOOMOO_COMMAND_LANGUAGE_SSOT.md`
- Bot bootstrap (venv, `moomoo-api`, OpenD logged in): `/Users/donnaile/dev/ORB/README.md`
- Legacy deploy one-liner (same host/path): `/Users/donnaile/dev/CAL/cal-app/.cursor/rules/build_app.md` (search for `192.168.1.116`)

---

## SSH

```bash
ssh ncs@192.168.1.116
```

---

## 1. Moomoo OpenD (required)

OpenD is the **local gateway** between Moomoo’s network and your code. The bot’s Python SDK talks to OpenD (commonly **`127.0.0.1:11111`** on the same machine; confirm ports in OpenD settings if yours differ).

**Operational requirements**

- OpenD **installed** (visualization / GUI build is typical for operators who need the status indicator).
- OpenD **running** and **logged in** (Moomoo account; paper vs live per your policy).
- If the bot runs **inside Docker**, the compose file must still allow the bot process to reach OpenD (e.g. `network_mode: host`, published ports, or `extra_hosts` / `host.docker.internal` — **wrong networking here is the #1 reason “the bot can’t see Moomoo”**). Validate against the real `docker-compose.yml` on the server.

Official and local doc pointers are in the ORB SSOT file above.

---

## 2. Bot stack under `/opt/optionsbot` (required)

```bash
cd /opt/optionsbot
docker compose up -d --build
```

This directory is the **deploy root** for the trading bot and its **Docker** services. It is **not** optional for prod: compose brings up whatever images you ship (bot worker, API, etc.).

After deploy: `docker compose ps`, `docker compose logs -f` (use the service names defined on the box).

---

## 3. Web frontend (required for “full stack” prod)

The **browser UI** for operators/traders is part of the same product story as the bot. In practice it is usually:

- A **`web` / `portal` / `nginx`** service in the same compose project, or  
- Static assets behind nginx on the host.

**You must record** the HTTPS or HTTP URL (and port if not 443/80) in [ENVIRONMENT.md](ENVIRONMENT.md) under **API base URLs → PROD** (or a dedicated row for “Web UI”) once you read it off the live server.

---

## 4. PostgreSQL (if your compose defines it)

Many stacks use **Postgres** for orders, state, or user data. If `docker-compose.yml` on `192.168.1.116` includes a `postgres` (or equivalent) service:

- Ensure **volumes** survive restarts.
- Align **credentials** with bot/API `.env` on the server.

If there is **no** Postgres service, document what you use instead (SQLite path, external DB host, etc.) when you discover it on the box.

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
2. `cd /opt/optionsbot && docker compose ps` — expected services **Up**.  
3. From a browser on the LAN: **frontend** loads.  
4. Hit **API health** (or one read-only endpoint) if you have one.  
5. Bot log shows **quote/trade context** connected (no “cannot open quote context” loop — see ORB README troubleshooting).

If any step fails, fix that layer before treating prod as “ready for Claude / Cursor to extend the app against.”
