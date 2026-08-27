# User Manual & SaaS Engineering Workflows 📖

Learn how to build single-page apps, complex multi-service microservices, and full-stack SaaS applications using the **Local Coding Agent (`coder`)**.

---

## 🎯 Basic Usage

### Mode 1: Interactive REPL (Recommended)
Open any directory and run `coder`:
```bash
cd ~/my-new-project
coder
```
You will enter the interactive prompt:
```text
ncoder > Build a complete TypeScript REST API with Express and Prisma
```

### Mode 2: Direct Command Line Goal
Execute a goal and exit when done:
```bash
coder "Initialize a full Next.js 14 landing page with Tailwind CSS and dark mode"
```

---

## ⚡ Interactive Slash Commands

| Command | Action |
| :--- | :--- |
| **`/map`** | Scans the whole directory tree, package manifests (`package.json`, `Cargo.toml`, etc.), and prints an architectural blueprint. |
| **`/clear`** | Clears conversation context and thinking history to start a fresh feature. |
| **`/help`** | Displays available commands and usage guide. |
| **`/exit`** | Exits the agent session. |

---

## 🏗️ Real-World SaaS Workflows

### 1. Bootstrapping a Complete Full-Stack SaaS Product

To build a complete product from scratch, give `coder` a high-level roadmap prompt:

```text
Build a complete B2B SaaS platform for Team Task Tracking:
1. Backend: Node.js/Express in TypeScript with routes for auth, tasks, and teams.
2. Database: Prisma schema for User, Team, Task, and Subscription.
3. Frontend: Modern responsive dashboard in src/public with dark mode, kanban boards, and task filtering.
4. Testing: Add Jest unit tests and a health check endpoint.
```

**What the Agent Does:**
1. Calls `update_task_plan` to render a live checklist in your terminal.
2. Calls `write_file` to create `package.json`, `tsconfig.json`, `prisma/schema.prisma`, `src/server.ts`, and frontend assets.
3. Calls `run_command` to run `npm install` and verify build syntax.
4. Marks tasks as `[DONE]` as it progresses.

---

### 2. Exploring & Refactoring Large Existing Codebases

When opening a large or unfamiliar repository:

```bash
cd ~/legacy-backend
coder
```

Prompt:
```text
/map
Find all authentication middleware and refactor token verification to use modern asymmetric JWT keys.
```

**What the Agent Does:**
1. Scans the directory using `get_codebase_map`.
2. Searches for auth middleware across all files with `search_code("jwt.verify")`.
3. Reads the exact files with `read_file`.
4. Surgically refactors the middleware using `edit_file`.
5. Runs test suites with `run_command("npm test")` to ensure nothing broke.

---

### 3. Working Across Windows & WSL Workspaces

You can use `coder` to work on code located on your native Windows drives (`C:\`, `D:\`):

```bash
# In your WSL terminal:
cd /mnt/c/Users/<your-username>/Projects/my-app
coder
```

All file edits are written directly to your Windows drive in real-time, allowing you to edit in VS Code on Windows while the local agent works in your terminal.

---

## 💡 Best Prompting Practices for Local Models

1. **Be Specific About Tech Stack**:
   - ✅ *"Use Next.js 14 App Router, Tailwind CSS, and Zod validation."*
   - ❌ *"Make a modern web app."*

2. **Instruct It to Write Complete Code**:
   - The agent is instructed to avoid placeholder comments (`// TODO`), but specifying *"Write 100% complete, working code with all functions implemented"* produces the cleanest output.

3. **Use `/clear` Between Distinct Features**:
   - After completing a major subsystem (e.g. database schema & migrations), type `/clear` before moving to UI styling to keep context usage optimal and generation speeds high.
