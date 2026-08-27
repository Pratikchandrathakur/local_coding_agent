# Local Coding Agent 🚀

> **Autonomous, GPU-accelerated software engineering agent running 100% offline on your own machine.**  
> Built for full-stack SaaS development, multi-file refactoring, live terminal verification, and infinite-length codebases.

---

## 🌟 Key Capabilities

- **100% Local & Private**: Runs completely on your GPU/RAM via `llama.cpp` CUDA server. Zero data leaves your machine, zero API fees.
- **Native Tool Calling**: Equipped with real filesystem and terminal tools:
  - `write_file`: Writes source code and auto-creates nested directories.
  - `edit_file`: Surgical string replacement for precise refactoring.
  - `read_file`: Windowed file reader with exact line numbering.
  - `search_code`: Fast cross-codebase symbol/regex search.
  - `find_files`: Deep glob search across project trees.
  - `get_codebase_map`: Architectural scanner for `package.json`, `prisma`, `docker-compose`, etc.
  - `run_command`: Executes `npm`, `cargo`, `pytest`, `prisma`, and verifies server builds.
  - `update_task_plan`: Live engineering roadmap with visual `[TODO]`, `[IN PROGRESS]`, `[DONE]` task tracking.
- **Infinite Codebase Memory**: Context pruning and rolling summary engine ensures you never hit `ContextWindowExceeded` errors.
- **Universal Workspaces**: Run `coder` in **any** folder in WSL or Windows (via `/mnt/c/`).

---

## ⚡ Quickstart (3 Commands)

### 1. Install (One-time setup)
```bash
git clone https://github.com/Pratikchandrathakur/local_coding_agent.git
cd local_coding_agent
./install.sh
```

### 2. Start the Inference Engine
```bash
./start.sh
```
*(Automatically downloads GGUF weights, checks VRAM, and boots the GPU server on port 8080)*

### 3. Code from ANY Directory
```bash
cd /path/to/your/project
coder
```

---

## 🖥️ System Requirements

| Component | Minimum | Recommended |
| :--- | :--- | :--- |
| **GPU** | NVIDIA RTX 3060 / 4060 (8-12 GB VRAM) | NVIDIA RTX 4070 / 4080 / 5060 Ti / 5090 (16+ GB VRAM) |
| **System RAM** | 16 GB | 32 GB (Allows offloading inactive MoE experts) |
| **Storage** | 30 GB SSD space | Fast NVMe SSD |
| **OS** | Windows 10/11 (WSL2) or Linux | Ubuntu 22.04+ / Kali Linux / Debian |

---

## 📚 Documentation Index

- **[INSTALL.md](INSTALL.md)**: Zero-to-hero installation guide for fresh machines & WSL2 setup.
- **[MANUAL.md](MANUAL.md)**: Complete user manual with SaaS workflows, prompt engineering, and command reference.
- **[ARCHITECTURE.md](ARCHITECTURE.md)**: Deep dive into VRAM/RAM MoE offloading, Jinja template parsing, and memory optimization.

---

## 🛠️ Comparison: Why `coder`?

| Feature | Aider | Claude Code | **Local Coding Agent (`coder`)** |
| :--- | :--- | :--- | :--- |
| **Connection** | OpenAI API | Anthropic API (Needs Proxy) | **Native Direct OpenAI API** |
| **Editing Style** | Git Diff (Fails on mismatch) | Tool Calling | **Direct File Tooling + Regex Refactoring** |
| **Multi-File Autonomy** | Partial | High (Cloud-focused) | **High (Optimized for Local GPUs)** |
| **Context Overhead** | Minimal | ~30k tokens system prompt | **~400 tokens high-adherence prompt** |
| **Cost** | Free (Local) | Cloud tokens | **100% Free & Unlimited** |

---

## 📜 License

MIT License. Crafted with ❤️ for local autonomous software development.
