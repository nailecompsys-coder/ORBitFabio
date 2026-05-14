# FabioOrb — environments and setup

Single source of truth for where things run, how prod is deployed, and how iOS builds are produced. Update this file when decisions change.

## DEV vs PROD

| Layer | Where |
|--------|--------|
| **DEV** | This Mac (local Xcode, iOS Simulator, Cursor). Day-to-day development and TestFlight archive prep happen here. |
| **PROD** | **`192.168.1.116`** only — SSH as **`ncs@192.168.1.116`**. Server workload for this product lives under **`/opt/optionsbot`** (Docker Compose). |

**Scope on `192.168.1.116`:** Document and operate **only this product’s stack** plus the **host baseline** (OS, Docker engine, disk, SSH, LAN/firewall as needed). Other services on the same machine are out of scope for this project’s runbook.

## Apple Developer and iOS app identity

| Field | Value |
|--------|--------|
| **Apple Team ID** | `9JJV6C7LD4` (same team as CAL Native on this Mac) |
| **Bundle ID (intended)** | `com.ncs.orbitfabio` — create/register the App ID in [Apple Developer](https://developer.apple.com/account) if it does not exist yet. |

Xcode: set **Signing & Capabilities** to this team; use **Automatic** signing unless you have a reason to use manual profiles.

## Mobile builds and distribution

- **Development and internal testing:** Build and archive with **local Xcode** on this Mac; distribute via **TestFlight** (e.g. Don, Clayton, Chris as testers).
- **App Store (production store listing):** Use **EAS** only if/when you need Expo’s store submission pipeline. Until then, prefer local Xcode for all builds.

## PROD server (Northstar)

**Access**

```bash
ssh ncs@192.168.1.116
```

**Deploy this product** (Don-initiated or explicit release only — align with your team policy):

```bash
cd /opt/optionsbot
docker compose up -d --build
```

**Optional host baseline** (confirms the machine can run this stack; does not imply owning other tenants):

```bash
# On 192.168.1.116 after SSH
uname -a
docker version
docker compose version
df -h
```

Cross-reference: sibling project notes in `CAL/cal-app/.cursor/rules/build_app.md` (Northstar section).

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

**First-time local setup** (from this project root, if `origin` is not set yet):

```bash
git init
git remote add origin git@github.com:nailecompsys-coder/ORBitFabio.git
git branch -M main
git add .
git commit -m "Initial commit: environment doc and README"
git push -u origin main
```

If GitHub already has a README or license from the empty repo, use `git pull origin main --rebase` after the first `git remote add` (or merge) before pushing.

If the [GitHub CLI](https://cli.github.com/) is installed, `gh repo clone nailecompsys-coder/ORBitFabio` elsewhere is equivalent to cloning by HTTPS/SSH.

## API base URLs (fill when wired)

| Environment | Base URL / notes |
|-------------|------------------|
| DEV | `________________` (localhost, LAN IP of this Mac, or tunnel) |
| PROD | `________________` (service on `192.168.1.116` or front URL) |
