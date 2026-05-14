#!/bin/bash
# Phase 1 — Northstar discovery (from docs/ORBIT_CURSOR_SETUP)
# Read-only. Safe to run anytime.

set -euo pipefail

echo "=== RUNNING SERVICES ==="
systemctl list-units --type=service --state=running

echo ""
echo "=== DOCKER CONTAINERS ==="
docker ps -a 2>/dev/null || echo "Docker not installed"

echo ""
echo "=== DOCKER VOLUMES ==="
docker volume ls 2>/dev/null || echo "Docker not installed"

echo ""
echo "=== LISTENING PORTS ==="
ss -tlnp 2>/dev/null || ss -tln 2>/dev/null || echo "ss not available"

echo ""
echo "=== /opt CONTENTS ==="
ls -la /opt/ 2>/dev/null || echo "Cannot list /opt"

echo ""
echo "=== EXISTING CADDY ==="
which caddy && caddy version || echo "Caddy not installed"
cat /etc/caddy/Caddyfile 2>/dev/null || echo "No Caddyfile found"

echo ""
echo "=== EXISTING NGINX ==="
which nginx && nginx -v || echo "Nginx not installed"
systemctl is-active nginx 2>/dev/null || true

echo ""
echo "=== EXISTING POSTGRES ==="
which psql && psql --version || echo "Postgres not installed"
systemctl is-active postgresql 2>/dev/null || true

echo ""
echo "=== EXISTING NODE/NPM ==="
which node && node --version || echo "Node not installed"
which npm && npm --version || echo "npm not installed"

echo ""
echo "=== EXISTING PYTHON ==="
which python3 && python3 --version || echo "python3 not found"

echo ""
echo "=== /etc/systemd/system CUSTOM SERVICES ==="
ls /etc/systemd/system/*.service 2>/dev/null | grep -v "snap\|getty\|multi\|network\|systemd" || echo "None or not readable"

echo ""
echo "=== CRONTABS ==="
crontab -l 2>/dev/null || echo "No crontab"
ls /etc/cron.d/ 2>/dev/null || true
