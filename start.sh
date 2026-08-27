#!/usr/bin/env bash
# ==============================================================================
# Local Coding Agent - Start Server & Model Engine
# ==============================================================================
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

info() { printf "\033[1;34m[*] %s\033[0m\n" "$*"; }
succ() { printf "\033[1;32m[✓] %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m[!] %s\033[0m\n" "$*" >&2; }
die()  { printf "\033[1;31m[x] %s\033[0m\n" "$*" >&2; exit 1; }

# 1. Environment Setup
if [ ! -f .env ]; then
    info "Creating .env from .env.example..."
    cp .env.example .env
fi

set -a
# shellcheck disable=SC1091
. ./.env
set +a

: "${MODEL_REPO:?MODEL_REPO is not set in .env}"
: "${MODEL_FILE:?MODEL_FILE is not set in .env}"

# 2. Preflight Check
command -v docker >/dev/null 2>&1 || die "Docker not found. Run ./install.sh first."
docker compose version >/dev/null 2>&1 || die "'docker compose' v2 not found. Run ./install.sh."

if ! docker info >/dev/null 2>&1; then
    die "Cannot connect to Docker daemon. Run: sudo systemctl start docker"
fi

mkdir -p models

# 3. Model Weights Download (Resumable HTTPS)
fetch_model() {
    local f="$1" url part
    if [ -f "models/${f}" ]; then
        succ "Using existing weights in models/${f}"
        return 0
    fi
    url="https://huggingface.co/${MODEL_REPO}/resolve/main/${f}"
    part="models/${f}.part"

    info "Downloading ${f} from HuggingFace (${MODEL_REPO})..."
    local auth=()
    if [ -n "${HF_TOKEN:-}" ]; then
        auth=(-H "Authorization: Bearer ${HF_TOKEN}")
    fi

    if ! curl -fL -C - --retry 8 --retry-delay 5 --retry-all-errors \
              --progress-bar "${auth[@]}" -o "$part" "$url"; then
        die "Download failed. Check internet connection or disk space."
    fi
    mv "$part" "models/${f}"
    succ "Downloaded ${f} successfully."
}

fetch_model "${MODEL_FILE}"

# 4. Start Server via Docker Compose
info "Starting GPU Inference Server..."
docker compose up -d

info "Waiting for model to load into GPU memory (context: ${CONTEXT_SIZE:-131072} tokens)..."
ready=0
for _ in $(seq 1 120); do
    if curl -fsS "http://127.0.0.1:${PORT:-8080}/health" >/dev/null 2>&1; then
        ready=1
        break
    fi
    sleep 3
done

echo
echo "=========================================================================="
if [ "$ready" = "1" ]; then
    succ "Local Inference Server Ready on http://127.0.0.1:${PORT:-8080}/v1"
else
    warn "Server is still loading. Check status with: docker compose logs -f"
fi
echo " Model Alias:   ${MODEL_ALIAS:-local-coder}"
echo " Context Size:  ${CONTEXT_SIZE:-131072} tokens"
echo " Stop Server:   ./stop.sh"
echo
echo " Launch Agent:  coder"
echo "=========================================================================="
echo
