# Northstar Phase 1 — discovery

Read-only inventory. Source: `docs/ORBIT_CURSOR_SETUP` Phase 1.

**Before any Phase 2 / teardown / Docker cleanup:** [docs/NORTHSTAR_SAFE_CHANGES.md](../docs/NORTHSTAR_SAFE_CHANGES.md).

## Run (from your Mac, same LAN as Northstar)

Use the SSH user that actually works on your box (`ncs` or `ubuntu` per your server):

```bash
cd /Users/donnaile/dev/FabioOrb
ssh ncs@192.168.1.116 'bash -s' < scripts/phase1-discovery.sh | tee reports/phase1-discovery-$(date +%Y%m%d-%H%M).txt
```

If `ncs` fails, try:

```bash
ssh ubuntu@192.168.1.116 'bash -s' < scripts/phase1-discovery.sh | tee reports/phase1-discovery-$(date +%Y%m%d-%H%M).txt
```

Paste the transcript into chat (or commit the `reports/` file if you want it in Git — **review for secrets first**).

## Postgres tunnel (after Phase 1)

Live Postgres listens on the server at **`127.0.0.1:5434`** (not 5432). Example tunnel to local **5433**:

```bash
ssh -L 5433:127.0.0.1:5434 ncs@192.168.1.116 -N
```

## What failed here

Automated SSH from the agent returned `Permission denied (publickey,password)` for both `ncs@` and `ubuntu@`. You need an interactive session, SSH agent with the right key, or `ssh-copy-id` for the user you use on `192.168.1.116`.
