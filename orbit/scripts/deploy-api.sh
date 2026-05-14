# Partial deploy — API + migrations only (keeps server `./scripts/`, Caddyfile, `ui/`, etc.)

set -euo pipefail
HOST="${1:-ncs@192.168.1.116}"
REMOTE_ROOT="${2:-/opt/orbit}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORBIT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "Sync api/ -> ${HOST}:${REMOTE_ROOT}/api/"
rsync -avz --delete "${ORBIT_DIR}/api/" "${HOST}:${REMOTE_ROOT}/api/"

echo "Sync migrations/ -> ${HOST}:${REMOTE_ROOT}/migrations/"
rsync -avz --delete "${ORBIT_DIR}/migrations/" "${HOST}:${REMOTE_ROOT}/migrations/"

echo "On server, run: cd ${REMOTE_ROOT} && docker compose up -d --build api"
echo "Gate: docker compose exec api curl -sf -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/health"
