#!/usr/bin/env bash
# ==============================================================================
# Local Autonomous Coding Agent - Automated Installer
# Supported OS: Ubuntu, Debian, Kali Linux, WSL2 (Windows Subsystem for Linux)
# ==============================================================================
set -euo pipefail

info() { printf "\033[1;34m[*] %s\033[0m\n" "$*"; }
succ() { printf "\033[1;32m[✓] %s\033[0m\n" "$*"; }
warn() { printf "\033[1;33m[!] %s\033[0m\n" "$*" >&2; }
die()  { printf "\033[1;31m[x] %s\033[0m\n" "$*" >&2; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

info "Starting Local Coding Agent Installation..."

# ------------------------------------------------------------------------------
# 1. GPU Check
# ------------------------------------------------------------------------------
info "Checking NVIDIA GPU..."
if command -v nvidia-smi >/dev/null 2>&1; then
    gpu_name=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1 || echo "NVIDIA GPU")
    vram_mb=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 || echo "0")
    succ "Detected GPU: ${gpu_name} (${vram_mb} MB VRAM)"
else
    warn "nvidia-smi not found. If running on WSL2, ensure NVIDIA drivers are installed on Windows."
fi

# ------------------------------------------------------------------------------
# 2. Package Manager Prerequisites (Docker & NVIDIA Container Toolkit)
# ------------------------------------------------------------------------------
if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
    info "Installing Docker & Docker Compose..."
    if [ "$EUID" -ne 0 ]; then
        SUDO="sudo"
    else
        SUDO=""
    fi

    $SUDO apt-get update -y
    $SUDO apt-get install -y ca-certificates curl gnupg lsb-release

    if ! command -v docker >/dev/null 2>&1; then
        $SUDO apt-get install -y docker.io || true
    fi

    # Docker Compose Plugin
    if ! docker compose version >/dev/null 2>&1; then
        $SUDO mkdir -p /usr/local/lib/docker/cli-plugins
        arch=$(uname -m)
        [ "$arch" = "x86_64" ] && arch="x86_64"
        [ "$arch" = "aarch64" ] && arch="aarch64"
        $SUDO curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-${arch}" -o /usr/local/lib/docker/cli-plugins/docker-compose
        $SUDO chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
    fi

    # Docker group configuration
    if [ -n "${SUDO_USER:-}" ]; then
        $SUDO usermod -aG docker "$SUDO_USER" || true
    else
        $SUDO usermod -aG docker "$USER" || true
    fi
    succ "Docker & Compose installed."
else
    succ "Docker & Docker Compose are already installed."
fi

# ------------------------------------------------------------------------------
# 3. Python & uv Installation
# ------------------------------------------------------------------------------
info "Setting up Python & uv environment..."
mkdir -p "${HOME}/.local/bin"

if ! command -v uv >/dev/null 2>&1; then
    info "Installing uv (fast Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="${HOME}/.local/bin:${PATH}"
fi

succ "uv is ready: $(uv --version)"

# ------------------------------------------------------------------------------
# 4. Native Linux Node.js & npm (LTS v22)
# ------------------------------------------------------------------------------
if ! "${HOME}/.local/bin/node" --version >/dev/null 2>&1 && ! /usr/bin/node --version >/dev/null 2>&1; then
    info "Installing native Linux Node.js LTS v22..."
    mkdir -p "${HOME}/.local/share/node" "${HOME}/.local/bin"
    curl -fsSL https://nodejs.org/dist/v22.14.0/node-v22.14.0-linux-x64.tar.xz | tar -xJ --strip-components=1 -C "${HOME}/.local/share/node"
    ln -sf "${HOME}/.local/share/node/bin/node" "${HOME}/.local/bin/node"
    ln -sf "${HOME}/.local/share/node/bin/npm" "${HOME}/.local/bin/npm"
    ln -sf "${HOME}/.local/share/node/bin/npx" "${HOME}/.local/bin/npx"
    succ "Node.js v22 LTS installed."
else
    succ "Node.js is already installed."
fi

# ------------------------------------------------------------------------------
# 5. Virtual Environment & Agent Dependencies
# ------------------------------------------------------------------------------
VENV_DIR="${HOME}/.local/share/local-coder-agent"
info "Setting up agent virtual environment in ${VENV_DIR}..."
mkdir -p "$(dirname "$VENV_DIR")"

uv venv "$VENV_DIR" --quiet
uv pip install --python "${VENV_DIR}/bin/python" openai rich prompt_toolkit pydantic --quiet
succ "Agent dependencies installed in isolated virtual environment."

# ------------------------------------------------------------------------------
# 5. Global CLI Symlinks
# ------------------------------------------------------------------------------
info "Linking global CLI commands..."
chmod +x "${SCRIPT_DIR}/coder" "${SCRIPT_DIR}/agent_cli.py"
ln -sf "${SCRIPT_DIR}/coder" "${HOME}/.local/bin/coder"
ln -sf "${SCRIPT_DIR}/coder" "${HOME}/.local/bin/local-agent"

# Ensure ~/.local/bin is in PATH for bash and zsh
for rc in "${HOME}/.bashrc" "${HOME}/.zshrc"; do
    if [ -f "$rc" ]; then
        if ! grep -q 'HOME/.local/bin' "$rc" && ! grep -q '.local/bin' "$rc"; then
            echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$rc"
        fi
    fi
done

succ "Global commands 'coder' and 'local-agent' are installed in ~/.local/bin."

# ------------------------------------------------------------------------------
# 6. Summary
# ------------------------------------------------------------------------------
echo
echo "=========================================================================="
echo "  Local Autonomous Coding Agent Installation Complete!"
echo "=========================================================================="
echo "  1. Start the GPU Server:   cd ${SCRIPT_DIR} && ./start.sh"
echo "  2. Run the Agent Anywhere: cd /path/to/any/project && coder"
echo "=========================================================================="
echo
