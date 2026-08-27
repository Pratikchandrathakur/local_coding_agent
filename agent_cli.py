#!/home/test/.local/share/local-coder-agent/bin/python3
import os
import sys
import json
import time
import re
import fnmatch
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.tree import Tree
from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory

console = Console()

API_BASE = os.environ.get("OPENAI_API_BASE", "http://127.0.0.1:8080/v1")
API_KEY = os.environ.get("OPENAI_API_KEY", "none")
MODEL_NAME = os.environ.get("MODEL_NAME", "local-coder")

client = OpenAI(base_url=API_BASE, api_key=API_KEY)

# Ignored directories for scanning
IGNORE_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".nuxt", "__pycache__",
    ".venv", "venv", ".cache", ".pytest_cache", ".idea", ".vscode", "target"
}

# ---------------------------------------------------------------------------
# Tools Definitions (SaaS & Large Codebase Grade)
# ---------------------------------------------------------------------------
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write complete content to a file. Automatically creates all parent directories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to the file"},
                    "content": {"type": "string", "description": "Full source code content"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Surgically replace target search text in an existing file with replacement text.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to edit"},
                    "search": {"type": "string", "description": "Exact text to find and replace"},
                    "replace": {"type": "string", "description": "Replacement text"}
                },
                "required": ["path", "search", "replace"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read file contents with line numbers. Use start_line/end_line for large files.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Path to the file to read"},
                    "start_line": {"type": "integer", "description": "Start line (1-indexed, optional)"},
                    "end_line": {"type": "integer", "description": "End line (inclusive, optional)"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List files and subdirectories. Supports recursive listing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path (defaults to .)"},
                    "recursive": {"type": "boolean", "description": "Whether to list recursively (default false)"},
                    "max_depth": {"type": "integer", "description": "Max depth for recursive listing (default 3)"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_code",
            "description": "Search for a keyword, function, class, or regex across the entire codebase.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search string or regex pattern"},
                    "path": {"type": "string", "description": "Directory to search in (default .)"},
                    "file_extension": {"type": "string", "description": "Filter by extension e.g. .ts, .py (optional)"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "find_files",
            "description": "Find files matching a glob pattern (e.g. '*.tsx', '**/api/*.ts').",
            "parameters": {
                "type": "object",
                "properties": {
                    "pattern": {"type": "string", "description": "Glob pattern to match"}
                },
                "required": ["pattern"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_codebase_map",
            "description": "Scan and summarize the whole codebase architecture, dependency files, and folder structure.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Execute a bash shell command (e.g. npm install, npm test, prisma migrate, python tests, docker).",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Bash command to execute"}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_task_plan",
            "description": "Update the roadmap/task plan checklist for building complex SaaS features.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "status": {"type": "string", "enum": ["todo", "in_progress", "done"]}
                            },
                            "required": ["title", "status"]
                        },
                        "description": "List of tasks with titles and statuses"
                    }
                },
                "required": ["tasks"]
            }
        }
    }
]

# ---------------------------------------------------------------------------
# Tool Execution Handlers
# ---------------------------------------------------------------------------
def execute_tool(name: str, args: Dict[str, Any]) -> str:
    cwd = Path.cwd()
    try:
        if name == "write_file":
            p = cwd / Path(args["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            content = args["content"]
            p.write_text(content, encoding="utf-8")
            line_count = len(content.splitlines())
            console.print(Panel(f"[bold green]✓ Created/Updated:[/] {args['path']} ([cyan]{line_count} lines[/], [dim]{len(content)} bytes[/])", border_style="green"))
            return f"Successfully wrote {line_count} lines ({len(content)} bytes) to {args['path']}"

        elif name == "edit_file":
            p = cwd / Path(args["path"])
            if not p.exists():
                return f"Error: File {args['path']} does not exist."
            text = p.read_text(encoding="utf-8")
            search = args["search"]
            replace = args["replace"]
            if search not in text:
                # Try whitespace-stripped fallback match
                s_strip = re.sub(r'\s+', ' ', search.strip())
                t_strip = re.sub(r'\s+', ' ', text)
                if s_strip not in t_strip:
                    return f"Error: Target search text not found in {args['path']}. Check exact text and indentation."
            text = text.replace(search, replace, 1)
            p.write_text(text, encoding="utf-8")
            console.print(Panel(f"[bold green]✓ Refactored:[/] {args['path']}", border_style="green"))
            return f"Successfully updated {args['path']}"

        elif name == "read_file":
            p = cwd / Path(args["path"])
            if not p.exists():
                return f"Error: File {args['path']} does not exist."
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            start = max(1, args.get("start_line", 1)) - 1
            end = args.get("end_line", len(lines))
            selected = lines[start:end]
            numbered = [f"{i+start+1:4d} | {line}" for i, line in enumerate(selected)]
            console.print(Panel(f"[bold cyan]Read:[/] {args['path']} (lines {start+1}-{min(end, len(lines))} of {len(lines)})", border_style="cyan"))
            return "\n".join(numbered)

        elif name == "list_directory":
            base = cwd / Path(args.get("path", "."))
            if not base.exists():
                return f"Error: Directory {args.get('path', '.')} does not exist."
            recursive = args.get("recursive", False)
            max_depth = args.get("max_depth", 3)
            
            items = []
            if not recursive:
                for item in sorted(base.iterdir()):
                    if item.name in IGNORE_DIRS:
                        continue
                    kind = "dir" if item.is_dir() else "file"
                    size = f" ({item.stat().st_size} B)" if item.is_file() else ""
                    items.append(f"[{kind}] {item.name}{size}")
            else:
                for root, dirs, files in os.walk(base):
                    dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                    rel_root = os.path.relpath(root, base)
                    depth = 0 if rel_root == "." else rel_root.count(os.sep) + 1
                    if depth > max_depth:
                        continue
                    indent = "  " * depth
                    folder_name = os.path.basename(root) if rel_root != "." else "."
                    items.append(f"{indent}[dir] {folder_name}/")
                    for f in sorted(files):
                        items.append(f"{indent}  [file] {f}")

            console.print(Panel(f"[bold cyan]Directory:[/] {args.get('path', '.')} ({len(items)} items)", border_style="cyan"))
            return "\n".join(items) if items else "(empty directory)"

        elif name == "search_code":
            query = args["query"]
            search_path = cwd / Path(args.get("path", "."))
            ext = args.get("file_extension")
            results = []
            pattern = re.compile(re.escape(query), re.IGNORECASE)

            for root, dirs, files in os.walk(search_path):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for file in files:
                    if ext and not file.endswith(ext):
                        continue
                    file_p = Path(root) / file
                    try:
                        lines = file_p.read_text(encoding="utf-8", errors="replace").splitlines()
                        for i, line in enumerate(lines):
                            if pattern.search(line):
                                rel = file_p.relative_to(cwd)
                                results.append(f"{rel}:{i+1}: {line.strip()}")
                                if len(results) >= 50:
                                    break
                    except Exception:
                        continue
                if len(results) >= 50:
                    results.append("... (matches truncated to 50 results)")
                    break

            console.print(Panel(f"[bold cyan]Search Query:[/] '{query}' found {len(results)} matches", border_style="cyan"))
            return "\n".join(results) if results else f"No matches found for '{query}'"

        elif name == "find_files":
            pat = args["pattern"]
            matches = []
            for root, dirs, files in os.walk(cwd):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                for file in files:
                    rel = os.path.relpath(os.path.join(root, file), cwd)
                    if fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(file, pat):
                        matches.append(rel)
                        if len(matches) >= 50:
                            break
            console.print(Panel(f"[bold cyan]Found Files:[/] {len(matches)} files matching '{pat}'", border_style="cyan"))
            return "\n".join(matches) if matches else f"No files matched pattern '{pat}'"

        elif name == "get_codebase_map":
            manifests = ["package.json", "pyproject.toml", "Cargo.toml", "requirements.txt", "docker-compose.yml", "Dockerfile", "tsconfig.json"]
            found_manifests = []
            for m in manifests:
                if (cwd / m).exists():
                    found_manifests.append(f"- {m}: {(cwd / m).read_text(errors='replace')[:400]}")

            tree_items = []
            for root, dirs, files in os.walk(cwd):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
                depth = os.path.relpath(root, cwd).count(os.sep)
                if depth > 2:
                    continue
                rel = os.path.relpath(root, cwd)
                indent = "  " * depth
                tree_items.append(f"{indent}{os.path.basename(root)}/ ({len(files)} files)")

            summary = (
                f"=== Codebase Map for {cwd.name} ===\n"
                "Manifests & Configs:\n" + "\n".join(found_manifests) + "\n\n"
                "Structure Overview:\n" + "\n".join(tree_items[:40])
            )
            console.print(Panel(f"[bold cyan]Codebase Map Generated[/]", border_style="cyan"))
            return summary

        elif name == "run_command":
            cmd = args["command"]
            console.print(Panel(f"[bold yellow]$ {cmd}[/]", border_style="yellow"))
            env = os.environ.copy()
            home_bin = str(Path.home() / ".local/bin")
            env["PATH"] = f"{home_bin}:/usr/local/bin:/usr/bin:/bin:{env.get('PATH', '')}"
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=180, env=env)
            out = proc.stdout.strip()
            err = proc.stderr.strip()
            res = []
            if out:
                lines = out.splitlines()
                preview = lines if len(lines) <= 60 else lines[:30] + [f"... [{len(lines)-60} lines omitted] ..."] + lines[-30:]
                res.append("STDOUT:\n" + "\n".join(preview))
            if err:
                res.append(f"STDERR:\n{err}")
            res.append(f"Exit Code: {proc.returncode}")
            return "\n".join(res)

        elif name == "update_task_plan":
            tasks = args["tasks"]
            table = Table(title="[bold cyan]SaaS Engineering Roadmap[/]", show_header=True, header_style="bold magenta")
            table.add_column("Status", width=12)
            table.add_column("Task Title")
            for t in tasks:
                st = t["status"]
                icon = "[green]✓ DONE[/]" if st == "done" else ("[yellow]▶ IN PROGRESS[/]" if st == "in_progress" else "[dim]○ TODO[/]")
                table.add_row(icon, t["title"])
            console.print(table)
            return "Task plan updated and displayed to user."

        else:
            return f"Error: Unknown tool {name}"

    except Exception as e:
        return f"Tool Execution Error: {str(e)}"

# ---------------------------------------------------------------------------
# Context & Memory Optimization
# ---------------------------------------------------------------------------
def prune_history(messages: List[Dict[str, Any]], max_chars: int = 140000) -> List[Dict[str, Any]]:
    cleaned = []
    for msg in messages:
        m = dict(msg)
        if m.get("role") == "assistant" and isinstance(m.get("content"), str):
            content = m["content"]
            if "<think>" in content and "</think>" in content:
                parts = content.split("</think>")
                m["content"] = parts[-1].strip()
        cleaned.append(m)

    total_len = sum(len(str(m.get("content", ""))) for m in cleaned)
    if total_len > max_chars and len(cleaned) > 6:
        system = cleaned[0] if cleaned[0]["role"] == "system" else None
        recent = cleaned[-8:]
        summarized = [system] if system else []
        summarized.append({"role": "user", "content": "(Continuing previous SaaS architecture phase. Focus on current active task.)"})
        summarized.extend(recent)
        return summarized
    return cleaned

# ---------------------------------------------------------------------------
# Autonomous Agent Loop
# ---------------------------------------------------------------------------
def run_autonomous_loop(history: List[Dict[str, Any]], max_steps: int = 40):
    step = 0
    while step < max_steps:
        step += 1
        history = prune_history(history)
        
        with console.status(f"[bold cyan]Engineering Task (Step {step})...[/]", spinner="dots"):
            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=history,
                    tools=TOOLS,
                    tool_choice="auto",
                    temperature=0.3
                )
            except Exception as e:
                console.print(f"[bold red]API Error:[/] {e}")
                break

        msg = response.choices[0].message
        tool_calls = msg.tool_calls

        if msg.content:
            text = msg.content
            if "<think>" in text:
                think_part = text.split("</think>")[0].replace("<think>", "").strip()
                ans_part = text.split("</think>")[-1].strip()
                if think_part:
                    console.print(Panel(think_part, title="[dim]Architectural Reasoning[/dim]", border_style="dim", expand=False))
                if ans_part:
                    console.print(Markdown(ans_part))
            else:
                console.print(Markdown(text))

        assistant_msg = {"role": "assistant"}
        if msg.content:
            assistant_msg["content"] = msg.content
        if tool_calls:
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments}
                }
                for tc in tool_calls
            ]
        history.append(assistant_msg)

        if not tool_calls:
            break

        for tc in tool_calls:
            fname = tc.function.name
            try:
                fargs = json.loads(tc.function.arguments) if isinstance(tc.function.arguments, str) else tc.function.arguments
            except Exception:
                fargs = {}
            
            result = execute_tool(fname, fargs)
            history.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": fname,
                "content": result
            })

    return history

# ---------------------------------------------------------------------------
# Interactive Shell
# ---------------------------------------------------------------------------
def main():
    console.print(Panel.fit(
        "[bold cyan]Production SaaS Autonomous Coding Engine[/]\n"
        "[dim]Multi-file codebase architecture, automated tests, full filesystem tools[/]\n"
        f"[green]Working Directory:[/] {Path.cwd()}\n"
        f"[green]GPU Server:[/] {API_BASE} | [green]Model:[/] {MODEL_NAME} (128k Context)",
        border_style="cyan"
    ))

    system_prompt = (
        f"You are a Senior Principal Software Architect and Full-Stack SaaS Engineer working directly in: {Path.cwd()}.\n"
        "You have full autonomy and direct access to tools:\n"
        "- write_file: Write complete source code files (creates parent dirs automatically).\n"
        "- edit_file: Surgical search/replace edits.\n"
        "- read_file: Read files with exact line numbers.\n"
        "- list_directory / find_files: Explore project structure.\n"
        "- search_code: Search code, symbols, endpoints across the entire codebase.\n"
        "- get_codebase_map: Get an architectural overview of all files and manifests.\n"
        "- run_command: Execute terminal commands (npm, cargo, python, pip, tests, docker).\n"
        "- update_task_plan: Maintain a structured roadmap checklist for large multi-file projects.\n\n"
        "SaaS Engineering Guidelines:\n"
        "1. For multi-file or SaaS applications, create an initial task plan using update_task_plan.\n"
        "2. Follow production best practices: clean separation of concerns, secure environment variables (.env.example), type safety (TypeScript / Pydantic), robust error handling, and modular component architecture.\n"
        "3. Write 100% complete, fully implemented code. Never use placeholder comments like '// TODO' or '/* add logic here */'.\n"
        "4. Use run_command to verify syntax, install packages, and ensure everything builds.\n"
        "5. Keep responses concise and focused on execution."
    )

    history = [{"role": "system", "content": system_prompt}]
    hist_file = Path.home() / ".local_coder_history"

    if len(sys.argv) > 1:
        initial_prompt = " ".join(sys.argv[1:])
        console.print(f"[bold green]Goal:[/] {initial_prompt}")
        history.append({"role": "user", "content": initial_prompt})
        run_autonomous_loop(history)
        return

    while True:
        try:
            user_input = prompt(
                "\ncoder > ",
                history=FileHistory(str(hist_file)),
                auto_suggest=AutoSuggestFromHistory(),
                enable_cpr=False
            ).strip()

            if not user_input:
                continue

            if user_input.lower() in ("/exit", "/quit", "exit", "quit"):
                console.print("[yellow]Goodbye![/]")
                break
            elif user_input.lower() in ("/clear", "clear"):
                history = [{"role": "system", "content": system_prompt}]
                console.print("[green]Context & memory cleared for fresh project.[/]")
                continue
            elif user_input.lower() in ("/map", "map"):
                history.append({"role": "user", "content": "Analyze the project structure and give a codebase map."})
                history = run_autonomous_loop(history)
                continue
            elif user_input.lower() in ("/help", "help"):
                console.print(
                    "[bold]Available Commands:[/]\n"
                    "  /map    - Scan and display project codebase architecture\n"
                    "  /clear  - Clear conversation context\n"
                    "  /exit   - Exit the agent\n"
                    "  Just type any goal (e.g. 'Build a complete Next.js SaaS with auth and billing')"
                )
                continue

            history.append({"role": "user", "content": user_input})
            history = run_autonomous_loop(history)

        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Exiting...[/]")
            break

if __name__ == "__main__":
    main()


