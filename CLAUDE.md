# CLAUDE.md — ORBit FABIO
**Complete Context for Claude Code | nailecompsys-coder/ORBitFabio**

---

## WHO YOU ARE TALKING TO
Don Naile — solo MSP operator, NCS (Naile Computer Systems), Inverness FL.
This is a trading platform project with three users: Don, Clayton, Chris.
Don communicates directly, moves fast, low tolerance for verbose explanations.
Do the work, don't explain what you're about to do — just do it.

---

## REPO
```
git@github.com:nailecompsys-coder/ORBitFabio.git
Local Mac:  /Users/donnaile/dev/FabioOrb
Server:     ncs@192.168.1.116 (Northstar, Ubuntu 24.04)
Project:    /opt/orbit
Domain:     trading.clermontitstore.com
```

---

## WHAT THIS IS
ORBit FABIO is a multi-user options day trading platform running the
FABIO strategy (Focused Adaptive Breakout Intraday Options) on SPY, QQQ, NVDA.
Strategy logic is in `orb_bot_fabio.py` (Clayton's original, in repo root).
**This is the source of truth. DO NOT modify strategy logic ever.**
Three users trade independently with isolated paper accounts:
```
Clayton — Moomoo OpenD port 11111
Don     — Moomoo OpenD port 11112
Chris   — Moomoo OpenD port 11113
```

---

## FULL TECH STACK
```
Backend:        FastAPI (Python 3.11) in Docker
Database:       PostgreSQL 16 in Docker
Cache/Events:   Redis 7 in Docker
Reverse Proxy:  Caddy 2 in Docker (handles TLS automatically)
Broker Paper:   Moomoo OpenAPI (OpenD daemon, runs on HOST not Docker)
Broker Live:    Tradier (Phase 2, not now)
Market Data:    Moomoo real-time (Clayton's account, shared quote_ctx)
Auth:           TextBelt SMS OTP + JWT (30-day expiry)
Trade Log:      Google Sheets (OVTLYR dependency, never remove)
Web Portal:     React + Vite (built, served via Caddy from /opt/orbit/ui/)
iOS App:        React Native + Expo (local Xcode builds, TestFlight)
Apple:          Team ID 9JJV6C7LD4, Bundle ID com.ncs.orbitfabio
```

---

## SERVER — WHAT IS RUNNING RIGHT NOW
```
SSH: ssh ncs@192.168.1.116
```

Docker containers (ALL healthy, **DO NOT touch**):
```
orbit-postgres-1        PostgreSQL 16-alpine
                        host port: 127.0.0.1:5434 → container 5432
                        credentials: orbit / ${ORBIT_POSTGRES_PASSWORD}
                        data: /opt/orbit/data/postgres/

orbit-redis-1           Redis 7-alpine
                        host port: 127.0.0.1:6380 → container 6379

orbit-caddy-1           Caddy 2-alpine
                        ports: 0.0.0.0:80, 0.0.0.0:443
                        config: /opt/orbit/Caddyfile (mounted)
                        static: /opt/orbit/ui/ → /srv (mounted)

orbit-api-1             FastAPI Python 3.11
                        internal port 8000 (Caddy proxies)
                        built from orbit/api/Dockerfile

orbit-ovtlyr-browser-1  OVTLYR browser automation
                        port 6080 — DO NOT TOUCH
```

Other Docker (different project — **DO NOT TOUCH**):
```
project-go-mcp-stack-api-1
project-go-mcp-stack-worker-1
```

Active cron (**DO NOT DELETE** `/opt/orbit/scripts/`):
```
5 9 * * 1-5  /opt/orbit/scripts/cron_ovtlyr_morning.sh
TZ: America/New_York
```

**NEVER DELETE:**
```
/opt/orbit/data/          postgres data volumes
/opt/orbit/scripts/       cron jobs
/opt/orbit/caddy/         caddy TLS certs
```

---

## WHAT IS BUILT AND WORKING (Gates 1–4 passed)

**Gate 1 — API Health ✅**
```
GET https://trading.clermontitstore.com/health
→ {"status":"ok","database":true,"redis":true}
```

**Gate 2 — Auth OTP ✅**
```
POST https://trading.clermontitstore.com/auth/request-otp
POST https://trading.clermontitstore.com/auth/verify-otp
→ returns JWT token
```

**Gate 3 — Bot Control ✅**
```
GET  https://trading.clermontitstore.com/bot/status   (JWT required)
POST https://trading.clermontitstore.com/bot/start    (JWT required)
POST https://trading.clermontitstore.com/bot/stop     (JWT required)
→ {"status":"idle"} before start
```

**Gate 4 — WebSocket ✅**
```
wss://trading.clermontitstore.com/ws/{user_id}?token={JWT}
→ heartbeat {"type":"ping"} every 30s
→ streams bot_events rows in real-time
```

**Database schema deployed ✅**
```
users, otp_codes, user_credentials, bot_sessions,
trades, bot_events, daily_summaries
```

---

## REPO STRUCTURE
```
ORBitFabio/
├── CLAUDE.md                   ← this file
├── orb_bot_fabio.py            ← Clayton's original bot (SOURCE OF TRUTH)
├── orbit/                      ← mirrors /opt/orbit on server
│   ├── api/                    ← FastAPI app (built, working)
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── db.py
│   │   ├── deps.py
│   │   ├── users.py
│   │   ├── routes/
│   │   │   ├── bot.py
│   │   │   ├── ws.py
│   │   │   └── trades.py
│   │   ├── Dockerfile
│   │   ├── entrypoint.sh
│   │   └── requirements.txt
│   ├── bot/                    ← BUILT (Phase 5 complete)
│   ├── ui/                     ← NEEDS BUILDING (Phase 6)
│   ├── mobile/                 ← NEEDS BUILDING (Phase 7)
│   ├── migrations/
│   │   └── 001_initial.sql
│   ├── scripts/
│   │   └── deploy-api.sh
│   ├── docker-compose.yml
│   ├── Caddyfile
│   └── .env
└── docs/
```

---

## CADDYFILE — CURRENT STATE
Located at `/opt/orbit/Caddyfile` AND `orbit/Caddyfile` in repo.
Always keep both in sync. After editing locally, deploy with `deploy-api.sh`
then `docker restart orbit-caddy-1`.

Current routes:
```
/auth/*    → api:8000 (no prefix strip)
/bot/*     → api:8000 (no prefix strip)
/users/*   → api:8000 (no prefix strip)
/ws/*      → api:8000 (no prefix strip, WebSocket upgrade auto)
/trades/*  → api:8000 (no prefix strip)
/api/*     → api:8000 (strips /api prefix)
/novnc/*   → ovtlyr-browser:6080
/          → /srv static files (orbit/ui/dist)
```

---

## DATABASE CONNECTION

Inside Docker containers:
```
host: postgres
port: 5432
DATABASE_URL=postgresql://orbit:PASSWORD@postgres:5432/orbit
```

From host (bot, scripts):
```
host: localhost
port: 5434
DATABASE_URL=postgresql://orbit:PASSWORD@localhost:5434/orbit
```

From Mac dev (SSH tunnel):
```bash
ssh -L 5434:localhost:5434 ncs@192.168.1.116 -N
DATABASE_URL=postgresql://orbit:PASSWORD@localhost:5434/orbit
```

---

## DEPLOY WORKFLOW

Deploy API:
```bash
cd /Users/donnaile/dev/FabioOrb
rsync -av orbit/api/ ncs@192.168.1.116:/opt/orbit/api/
ssh ncs@192.168.1.116 'cd /opt/orbit && docker compose up -d --build api'
```

Deploy UI (after build):
```bash
cd orbit/ui && npm run build
rsync -av dist/ ncs@192.168.1.116:/opt/orbit/ui/
ssh ncs@192.168.1.116 'docker restart orbit-caddy-1'
```

Check logs:
```bash
ssh ncs@192.168.1.116 'docker logs orbit-api-1 --tail 30'
ssh ncs@192.168.1.116 'docker logs orbit-caddy-1 --tail 20'
```

---

## PHASE 5 — FABIO BOT CORE (COMPLETE)

Bot is built in `orbit/bot/` and deployed to `/opt/orbit/bot/`.
Deps installed in `/opt/orbit/.venv-bot/`.
Service file at `/opt/orbit/bot/systemd/orbit-bot-don.service`.
Env file at `/opt/orbit/.env.bot-don`.

To activate (requires sudo once):
```bash
sudo /opt/orbit/install-bot-services.sh
sudo systemctl status orbit-bot-don.service
sudo journalctl -u orbit-bot-don.service -f
```

**Bot rules (never violate):**
- `quote_ctx` always port 11111 (Clayton's OpenD, shared real-time options data)
- `trade_ctx` uses each user's own `opend_port`
- Bot runs as systemd on HOST, not Docker
- `orb_bot_fabio.py` is the strategy source of truth — copy verbatim, zero changes
- Keep ALL `self.sheets.log_*()` calls; add `push_event()` alongside, never instead of

---

## PHASE 6 — MOOMOO OPEND ON NORTHSTAR

OpenD runs on the HOST, not Docker. Three instances, one per user.

Install:
```bash
ssh ncs@192.168.1.116
mkdir -p /opt/orbit/opend/{clayton,don,chris}
# Download Ubuntu build from:
# https://www.moomoo.com/download/OpenAPI
# Extract into each directory — needs: OpenD binary + Appdata.dat
```

OpenD.xml for each user (Clayton example):
```xml
<?xml version="1.0" encoding="utf-8"?>
<config>
    <ip>127.0.0.1</ip>
    <api_port>11111</api_port>
    <login_account>CLAYTON_MOOMOO_ID</login_account>
    <login_pwd_md5>MD5_OF_PASSWORD</login_pwd_md5>
    <lang>en</lang>
    <log_level>info</log_level>
    <push_proto_type>1</push_proto_type>
    <pdt_protection>0</pdt_protection>
    <telnet_ip>127.0.0.1</telnet_ip>
    <telnet_port>22221</telnet_port>
</config>
```
Don: `api_port=11112`, `telnet_port=22222`
Chris: `api_port=11113`, `telnet_port=22223`

Generate MD5 password:
```python
import hashlib
print(hashlib.md5('your_password'.encode()).hexdigest())
```

First login (interactive, run once per account):
```bash
cd /opt/orbit/opend/clayton
./OpenD -cfg_file=./OpenD.xml
# Complete any questionnaire, then Ctrl+C
```

**Critical OpenD config notes:**
- `pdt_protection=0` — REQUIRED or bot locks after 3 day trades
- `push_proto_type=1` — JSON format
- `quote_ctx` always uses port 11111 (Clayton's — has options quote rights)
- `trade_ctx` uses each user's own port

Gate:
```python
from moomoo import OpenQuoteContext, RET_OK
for port in [11111, 11112, 11113]:
    ctx = OpenQuoteContext(host='127.0.0.1', port=port)
    ret, data = ctx.get_market_snapshot(['US.SPY'])
    print(f'{port}: {"OK" if ret == RET_OK else "FAIL"}')
    ctx.close()
```

---

## PHASE 7 — REACT WEB PORTAL

Setup:
```bash
cd orbit
npm create vite@latest ui -- --template react
cd ui
npm install axios react-router-dom recharts tailwindcss
```

Design — SpaceX Dragon palette:
```css
--bg-primary:   #0a0a0f;
--bg-card:      #12121a;
--accent-green: #00ff87;
--accent-red:   #ff3b5c;
--accent-blue:  #3d9eff;
--text-primary: #e8e8f0;
--text-muted:   #6b6b80;
--font-mono:    'Share Tech Mono', monospace;
--font-display: 'Barlow Condensed', sans-serif;
```

Screens:
```
/login       Phone entry → OTP → JWT stored in localStorage
/dashboard   P&L card, equity curve (Recharts), today's stats
/positions   Live open positions via WebSocket
/bot         Start/stop/pause, regime display, live event feed
/history     Trade history table, filters
/settings    Paper/live toggle (admin only)
```

WebSocket hook:
```javascript
export function useWebSocket(userId, token) {
    const [events, setEvents] = useState([]);
    useEffect(() => {
        if (!userId || !token) return;
        const ws = new WebSocket(
            `wss://trading.clermontitstore.com/ws/${userId}?token=${token}`
        );
        ws.onmessage = (e) => {
            setEvents(prev => [JSON.parse(e.data), ...prev].slice(0, 500));
        };
        return () => ws.close();
    }, [userId, token]);
    return events;
}
```

Build and deploy:
```bash
cd orbit/ui
npm run build
rsync -av dist/ ncs@192.168.1.116:/opt/orbit/ui/
ssh ncs@192.168.1.116 'docker restart orbit-caddy-1'
```

---

## PHASE 8 — REACT NATIVE iOS APP

Setup (on Mac with Xcode):
```bash
cd orbit
npx create-expo-app mobile --template blank-typescript
cd mobile
npx expo install expo-secure-store expo-notifications
npx expo install @react-navigation/native @react-navigation/bottom-tabs
npm install axios
```

`app.json` key fields:
```json
{
  "expo": {
    "name": "ORBit",
    "slug": "orbit-fabio",
    "ios": {
      "bundleIdentifier": "com.ncs.orbitfabio",
      "buildNumber": "1"
    },
    "extra": {
      "apiUrl": "https://trading.clermontitstore.com"
    }
  }
}
```

Apple credentials:
```
Team ID:       9JJV6C7LD4
Bundle ID:     com.ncs.orbitfabio
Distribution:  local Xcode builds → TestFlight (NOT EAS cloud builds)
```

JWT storage (iOS, encrypted):
```javascript
import * as SecureStore from 'expo-secure-store';
await SecureStore.setItemAsync('orbit_token', token);
const token = await SecureStore.getItemAsync('orbit_token');
```

Local Xcode build:
```bash
cd orbit/mobile
npx expo run:ios
# For TestFlight: Xcode → Product → Archive → Distribute
```

---

## PHASE 9 — TRADIER LIVE (future, not now)
When paper testing is complete, Tradier replaces Moomoo for live trading.
Single env flag swap — do not build this now.

---

## ENVIRONMENT FILE
`/opt/orbit/.env` on server, `orbit/.env` in repo (gitignored).
```bash
# Postgres
ORBIT_POSTGRES_PASSWORD=STRONG_PASSWORD_HERE

# Auth
JWT_SECRET=generate_with_openssl_rand_hex_32
TEXTBELT_KEY=your_textbelt_api_key

# Moomoo
MOOMOO_QUOTE_PORT=11111

# Google Sheets (Clayton's setup)
GOOGLE_SHEETS_CREDENTIALS=/opt/orbit/secrets/google_credentials.json
GOOGLE_SHEETS_ID=sheet_id_here

# App
ENVIRONMENT=production
ORBIT_ADMIN_PASSWORD=admin_password
```

---

## CRITICAL RULES — NEVER VIOLATE

1. Never touch `orbit-postgres-1`, `orbit-redis-1`, `orbit-caddy-1`,
   `orbit-ovtlyr-browser-1`, or the `go-mcp-stack` containers.
2. Never delete `/opt/orbit/data/`, `/opt/orbit/scripts/`, `/opt/orbit/caddy/`
3. Never modify strategy logic in `regime.py`, `signals.py`, `circuit.py`,
   `orders.py`. Copy verbatim from `orb_bot_fabio.py`.
4. Never remove Google Sheets logging calls. Add `push_event()` alongside,
   never instead of.
5. `uvicorn --workers 1` always. Bot tasks are in-process asyncio.
6. OpenD runs on HOST not Docker. Never put OpenD in a container.
7. Bot systemd services run on HOST not Docker.
8. `quote_ctx` always port 11111 (Clayton's OpenD, shared).
9. `trade_ctx` uses each user's own port.
10. `pdt_protection=0` in all OpenD.xml files.
11. Caddyfile changes: edit `orbit/Caddyfile` locally, rsync to server,
    restart caddy container. Never edit the server file directly
    without syncing back to repo.

---

## CURRENT BUILD STATUS
```
✅ Phase 1 — System update + Docker stack verified
✅ Phase 2 — PostgreSQL schema deployed
✅ Phase 3 — FastAPI skeleton + /health endpoint
✅ Phase 4 — Auth (OTP + JWT) endpoints live
✅ Phase 5 — Bot control endpoints (start/stop/status)
✅ Phase 6 — WebSocket event feed live
✅ Phase 7 — FABIO bot core (orbit/bot/) — deployed to Northstar
⬜ Phase 8 — OpenD on Northstar (3 instances)
⬜ Phase 9 — React web portal (orbit/ui/)
⬜ Phase 10 — React Native iOS (orbit/mobile/)
⬜ Phase 11 — Tradier live (future)
```

**Next: Phase 8 — Install OpenD on Northstar for each user.**
