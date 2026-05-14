# FabioOrb — environments and setup

Single source of truth for where things run, how prod is deployed, and how iOS builds are produced. Update this file when decisions change.

## DEV vs PROD

| Layer | Where |
|--------|--------|
| **DEV** | This Mac (local Xcode, iOS Simulator, Cursor). Day-to-day development and TestFlight archive prep happen here. |
| **PROD** | **`192.168.1.116`** — SSH **`ncs@192.168.1.116`**. Primary Docker stack under **`/opt/orbit`**. **Safety policy (do not prune / frozen containers):** [NORTHSTAR_SAFE_CHANGES.md](NORTHSTAR_SAFE_CHANGES.md). Inventory: [PHASE1_DISCOVERY_AS_RUN.md](PHASE1_DISCOVERY_AS_RUN.md); checklist: [PROD_NORTHSTAR_STACK.md](PROD_NORTHSTAR_STACK.md). |

**Scope on `192.168.1.116`:** In scope = **this product’s Northstar stack** (OpenD + bot + frontend + DB/API as deployed). Out of scope = unrelated apps or machines you do not treat as part of this product’s prod.

## Apple Developer and iOS app identity

| Field | Value |
|--------|--------|
| **Apple Team ID** | `9JJV6C7LD4` (same team as CAL Native on this Mac) |
| **Bundle ID (intended)** | `com.ncs.orbitfabio` — create/register the App ID in [Apple Developer](https://developer.apple.com/account) if it does not exist yet. |

Xcode: set **Signing & Capabilities** to this team; use **Automatic** signing unless you have a reason to use manual profiles.

## Mobile builds and distribution

- **Development and internal testing:** Build and archive with **local Xcode** on this Mac; distribute via **TestFlight** (e.g. Don, Clayton, Chris as testers).
- **App Store (production store listing):** Use **EAS** only if/when you need Expo’s store submission pipeline. Until then, prefer local Xcode for all builds.

## Mobile codebase (Expo + native iOS)

| Item | Location / value |
|------|------------------|
| App sources | [`apps/mobile/`](apps/mobile/) |
| Expo config | [`apps/mobile/app.json`](apps/mobile/app.json) — `slug` `orbitfabio`, display name **OrbitFabio** |
| Xcode workspace | `apps/mobile/ios/OrbitFabio.xcworkspace` |
| **Agent / automation commands** | Repo root [`AGENTS.md`](../AGENTS.md) |

**After clone:** `cd apps/mobile && npm install && cd ios && pod install`

**Scripts** (from `apps/mobile`): `npm run start` (Metro), `npm run ios` (`expo run:ios`), `npm run prebuild:ios` (regenerate native from config).

## PROD server (Northstar)

**Read first:** [PROD_NORTHSTAR_STACK.md](PROD_NORTHSTAR_STACK.md) — OpenD + bot + frontend + Postgres (if present). This section is the short operational slice.

**Access**

```bash
ssh ncs@192.168.1.116
```

**Deploy (pick the tree that matches your change)** — only after you confirm which compose project owns the service:

```bash
# Primary ORBit stack (observed running containers from this tree)
cd /opt/orbit && docker compose ps && docker compose up -d --build

# Legacy optionsbot tree (still present on disk)
cd /opt/optionsbot && docker compose ps && docker compose up -d --build
```

**Host baseline** (Docker, disk, OS):

```bash
# On 192.168.1.116 after SSH
uname -a
docker version
docker compose version
df -h
```

**Cross-references:** `/Users/donnaile/dev/CAL/cal-app/.cursor/rules/build_app.md` (Northstar one-liner); Moomoo/OpenD: `/Users/donnaile/dev/ORB/README.md`, `/Users/donnaile/dev/ORB/docs/MOOMOO_COMMAND_LANGUAGE_SSOT.md`.

## Mac dev machine checklist

Run on **this** Mac when onboarding or after Xcode updates:

```bash
xcodebuild -version
xcrun simctl list devices available
pod --version          # if the iOS project uses CocoaPods
```

Install missing **Simulator runtimes** from **Xcode → Settings → Platforms**.

## GitHub and repo layout

**Remote:** [nailecompsys-coder/ORBitFabio](https://github.com/nailecompsys-coder/ORBitFabio) (GitHub repo name `ORBitFabio`; local folder may stay `FabioOrb`).

| Clone | URL |
|--------|-----|
| HTTPS | `https://github.com/nailecompsys-coder/ORBitFabio.git` |
| SSH | `git@github.com:nailecompsys-coder/ORBitFabio.git` |

**Default branch:** `main`.

**This workspace:** Git is initialized with `origin` → `git@github.com:nailecompsys-coder/ORBitFabio.git` and `main` is tracking `origin/main`.

**Another machine:** clone with SSH or HTTPS:

```bash
git clone git@github.com:nailecompsys-coder/ORBitFabio.git
cd ORBitFabio   # or rename checkout folder to FabioOrb if you prefer
```

**Empty folder, no `.git` yet** (rare): `git init`, `git remote add origin …`, `git branch -M main`, add/commit, then `git push -u origin main`. If the remote already has commits (e.g. GitHub-added README), run `git pull origin main --rebase` before the first push.

## API base URLs (fill when wired)

| Environment | Base URL / notes |
|-------------|------------------|
| DEV | `________________` (localhost, LAN IP of this Mac, or tunnel) |
| PROD | **`https://trading.clermontitstore.com`** (per [ORBIT_CURSOR_SETUP](ORBIT_CURSOR_SETUP); Caddy in Docker listens on **:443** — confirm DNS/LAN). API paths likely `/api/*` as in that doc. Postgres from host/tunnel: **`127.0.0.1:5434`** (not 5432). |
