# Agent instructions — OrbitFabio

Use this file when implementing or verifying builds. Human-oriented details live in [docs/ENVIRONMENT.md](docs/ENVIRONMENT.md).

**Northstar (`192.168.1.116`):** Before SSH, Docker, or teardown, read [docs/NORTHSTAR_SAFE_CHANGES.md](docs/NORTHSTAR_SAFE_CHANGES.md). Do **not** run `docker system prune`, remove all containers, or touch frozen services listed there.

## Layout

| Path | Role |
|------|------|
| `apps/mobile/` | Expo SDK 54 + React Native (TypeScript). |
| `apps/mobile/ios/` | Native iOS — open **`OrbitFabio.xcworkspace`** (not the `.xcodeproj`). |
| `docs/ENVIRONMENT.md` | DEV/PROD hosts, Apple Team ID, GitHub, deploy commands. |
| `docs/PROD_NORTHSTAR_STACK.md` | **Prod on 192.168.1.116:** OpenD + Moomoo bot + frontend + Docker/Postgres expectations. |
| `docs/NORTHSTAR_SAFE_CHANGES.md` | **Frozen containers / paths** and what is safe to replace (FABIO API, compose, Caddy config, Python code). |

## Fresh clone — install

```bash
cd apps/mobile
npm ci   # or npm install
cd ios && pod install && cd ..
```

`ios/Pods/` is gitignored; CocoaPods must run after clone.

## Run (development)

- **Metro + dev client:** `npm run start` (from `apps/mobile`).
- **Build and run default simulator:** `npm run ios` (runs `expo run:ios`).

## Build only (CI / verification)

Pick a simulator that exists on the machine (`xcrun simctl list devices available`).

```bash
cd apps/mobile
xcodebuild -workspace ios/OrbitFabio.xcworkspace \
  -scheme OrbitFabio \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 17' \
  build
```

Adjust the simulator **name** to match an installed runtime. Use **Release** + a **device** destination only when signing for device or TestFlight is set up in Xcode.

## Xcode (local archive / TestFlight)

1. `open ios/OrbitFabio.xcworkspace`
2. Select a **real device** or **Any iOS Device (arm64)** for archive.
3. **Product → Archive** → distribute via Organizer to TestFlight.

Signing: **Team `9JJV6C7LD4`**, bundle **`com.ncs.orbitfabio`** (set from `app.json` via Expo prebuild).

## Regenerate `ios/` after native config changes

From `apps/mobile`:

```bash
npm run prebuild:clean   # destructive; re-run pod install afterward
# or
npm run prebuild:ios
```

Then `cd ios && pod install`.

## Distribution policy

- **Development / internal:** local Xcode + TestFlight (see ENVIRONMENT).
- **App Store (public):** EAS only if/when needed — do not add EAS unless asked.

## Android

Android native is not prebuilt in this repo yet. If Android is required, run `npx expo prebuild --platform android` from `apps/mobile` and mirror the iOS gitignore pattern (`android/` tracked, Gradle caches ignored as appropriate).
