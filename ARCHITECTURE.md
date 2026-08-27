# Architecture & System Design 🏗️

This document outlines the technical architecture of the **Local Coding Agent**, detailing how it balances GPU VRAM, system RAM, SSD storage, and context memory for autonomous software engineering.

---

## 🏛️ System Overview

```
                      ┌──────────────────────────────────────────────┐
                      │             Terminal Interface               │
                      │         (coder / local-agent CLI)            │
                      └──────────────────────┬───────────────────────┘
                                             │
                                             ▼
                      ┌──────────────────────────────────────────────┐
                      │          Autonomous ReAct Engine             │
                      │  - Context Manager & Token Pruner            │
                      │  - Task Plan Tracker                         │
                      │  - OpenAI Tool Calling Client                │
                      └──────────────┬────────────────┬──────────────┘
                                     │                │
          [Direct Tool Calls]        │                │  [JSON API]
          ┌──────────────────────────┘                └─────────────────────────┐
          ▼                                                                     ▼
┌──────────────────────────────┐                              ┌───────────────────────────────────┐
│     Local Execution Engine   │                              │     Inference Engine (llama.cpp)  │
│  - write_file                │                              │  - 35B MoE Model (IQ3_M)          │
│  - edit_file (Regex)         │                              │  - 128k Context Window (f16 KV)   │
│  - search_code (grep/walk)   │                              │  - Custom Jinja Tool Template     │
│  - run_command (bash subprocess)                            │  - FlashAttention-2               │
└──────────────┬───────────────┘                              └─────────────────┬─────────────────┘
               │                                                                │
               ▼                                                                ▼
┌──────────────────────────────┐                              ┌───────────────────────────────────┐
│   Host Filesystem & OS       │                              │        Hardware Allocation        │
│  - Real-time disk I/O        │                              │  - VRAM: 15.8 GB (Attention + KV) │
│  - Subprocess execution      │                              │  - RAM: 4.2 GB (MoE Experts)      │
└──────────────────────────────┘                              └───────────────────────────────────┘
```

---

## 💾 Hardware Memory Allocation (VRAM + RAM Strategy)

Modern Mixture-of-Experts (MoE) coding models (such as Ornith 35B-A3B) have a total footprint of ~17.4 GB, which can exceed single 16 GB consumer GPUs (RTX 4060 Ti, 4070, 4080, 5060 Ti).

### The Hybrid Solution:
1. **GPU VRAM (15.8 GB)**:
   - All attention matrices (`GPU_LAYERS=99`) remain entirely on the GPU for maximum inference speed.
   - The 128,000-token KV cache is allocated in VRAM (`KV_CACHE_QUANT=f16`) with FlashAttention enabled (`FLASH_ATTN=on`).
2. **System RAM (4.2 GB Offload)**:
   - Inactive MoE expert blocks are offloaded to system RAM using `--n-cpu-moe 12`.
   - Because only 8 of 256 experts fire per token, CPU offload for inactive experts introduces virtually zero latency while saving ~4.2 GB of GPU VRAM.

---

## 🧠 Jinja Native Tool Calling Engine

When running local models for agentic coding, many frameworks fail because the model outputs raw text (e.g. `<tool_call>`) that the client cannot parse.

`local_coding_agent` solves this via `models/chat_template.jinja`:
1. **Schema Injection**: Injects tool signatures in the `<tools>...</tools>` format expected by the base model.
2. **Multi-Turn System Support**: Overcomes default GGUF restrictions by permitting system messages at any turn in the conversation.
3. **Structured Tool Response**: The server automatically captures `<tool_call>` outputs from the model and translates them into standard OpenAI `tool_calls` JSON schemas.

---

## 🔄 Infinite-Length Context Management

As autonomous coding tasks progress across 20+ steps, chat histories can grow to tens of thousands of tokens.

### Memory Optimization Rules:
1. **Chain-of-Thought Pruning**: The agent preserves `<think>` tags during the active step, but strips them from older history turns once the tool call is executed.
2. **Rolling Architectural Summary**: If total prompt context approaches the limit, the agent compacts older tool outputs into a concise state summary while retaining the global system prompt and the current `update_task_plan` roadmap.
3. **Output Truncation**: High-volume terminal outputs (e.g. 500-line build logs) are automatically windowed to the head and tail error snippets.
