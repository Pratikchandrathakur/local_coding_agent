#!/usr/bin/env bash
# ==============================================================================
# Local Coding Agent - Stop Server
# ==============================================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"
echo "[*] Stopping local GPU inference server..."
docker compose down
echo "[✓] Server stopped."
