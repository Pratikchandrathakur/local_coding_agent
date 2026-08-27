# Complete Installation Guide 🛠️

This guide walks you through setting up the **Local Coding Agent** on any machine from scratch.

---

## 📋 Table of Contents
1. [Prerequisites](#1-prerequisites)
2. [Automated 1-Click Installation (Recommended)](#2-automated-1-click-installation-recommended)
3. [Windows 10/11 (WSL2) Setup Guide](#3-windows-1011-wsl2-setup-guide)
4. [Native Linux Setup Guide](#4-native-linux-setup-guide)
5. [Manual Step-by-Step Installation](#5-manual-step-by-step-installation)
6. [Troubleshooting & Verification](#6-troubleshooting--verification)

---

## 1. Prerequisites

- **NVIDIA GPU**: RTX 3060, 4060, 4070, 4080, 4090, 5060 Ti, or datacenter cards (A10G, A100, L4).
- **GPU Drivers**: Modern NVIDIA Game Ready or Studio Driver installed on the host.
- **Disk Space**: At least 30 GB free space (model weights are ~17-18 GB).

---

## 2. Automated 1-Click Installation (Recommended)

Run the automated installer script:

```bash
git clone https://github.com/Pratikchandrathakur/local_coding_agent.git
cd local_coding_agent
./install.sh
```

The script will automatically:
1. Detect your GPU and check VRAM.
2. Install Docker and Docker Compose v2.
3. Configure the NVIDIA Container Toolkit.
4. Install `uv` and create the isolated Python virtual environment.
5. Symlink the `coder` binary globally into `~/.local/bin`.
6. Add `~/.local/bin` to your `.bashrc` and `.zshrc`.

---

## 3. Windows 10/11 (WSL2) Setup Guide

### Step 1: Enable WSL2 & Install a Linux Distribution
Open PowerShell as Administrator:
```powershell
wsl --install -d Ubuntu
# or for Kali Linux:
wsl --install -d kali-linux
```
Restart your computer if prompted.

### Step 2: GPU Passthrough (Crucial Rule)
> [!IMPORTANT]
> **Do NOT install NVIDIA Linux drivers inside WSL2.**  
> The Windows host driver is automatically projected into WSL2 via `/dev/dxg`. Installing Linux drivers inside WSL will break CUDA.

Verify GPU access inside your WSL terminal:
```bash
nvidia-smi
```
If your GPU and VRAM are listed, GPU passthrough is working!

### Step 3: Run the Installer
```bash
git clone https://github.com/Pratikchandrathakur/local_coding_agent.git
cd local_coding_agent
./install.sh
```

---

## 4. Native Linux Setup Guide (Ubuntu / Debian / Arch)

1. Ensure the official proprietary NVIDIA drivers are installed:
   ```bash
   sudo apt update && sudo apt install -y nvidia-driver-535 nvidia-utils-535
   ```
2. Clone the repository and run `./install.sh`.

---

## 5. Manual Step-by-Step Installation

If you prefer to configure everything manually:

### 1. Install Docker & NVIDIA Container Toolkit
```bash
sudo apt update
sudo apt install -y docker.io curl
sudo usermod -aG docker $USER
```

Install NVIDIA Container Toolkit:
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### 2. Setup Python Environment with uv
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"

uv venv ~/.local/share/local-coder-agent
uv pip install --python ~/.local/share/local-coder-agent/bin/python openai rich prompt_toolkit pydantic
```

### 3. Create Global Symlink
```bash
chmod +x coder agent_cli.py
ln -sf $(pwd)/coder ~/.local/bin/coder
ln -sf $(pwd)/coder ~/.local/bin/local-agent
```

---

## 6. Troubleshooting & Verification

### Test 1: Verify Server Health
After starting the server with `./start.sh`, run:
```bash
curl http://127.0.0.1:8080/health
# Expected: {"status":"ok"}
```

### Test 2: Check Model Capabilities
```bash
curl http://127.0.0.1:8080/props
# Verify: supports_tools: true, supports_tool_calls: true
```

### Test 3: Check CLI Lookup
```bash
which coder
# Expected: /home/<user>/.local/bin/coder
```

### Issue: "permission denied while trying to connect to the Docker daemon socket"
Run:
```bash
newgrp docker
# Or restart your shell session
```

### Issue: "CUDA out of memory (OOM)"
Edit `.env` and increase CPU MoE offloading:
```bash
EXTRA_ARGS="--n-cpu-moe 16"
```
Then restart with `./start.sh`.
