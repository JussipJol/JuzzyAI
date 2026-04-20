"""
/onecommand — Multi-agent pipeline
────────────────────────────────────
prompt → router → [agent_1..N] (parallel + iterative) → final_tune → output

Logging: workspace/logs/onecommand_YYYYMMDD_HHMMSS/
  run.json        — full run metadata (prompt, tasks, timing)
  agent_N.md      — each agent's final result
  final.md        — merged final result
  ops.log         — file creation and command execution log
"""

import json
import threading
import time
import subprocess
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from core.client import AIClient

DEFAULT_ITERATIONS = 2
MAX_TASKS = 5

ROUTER_PROMPT = """You are a task orchestrator. Break the user's request into 2-5 parallel subtasks.
Each subtask must cover a distinct aspect (architecture, implementation, tests, docs, security, UX, etc).

Respond ONLY with valid JSON, no markdown fences:
{{
  "tasks": [
    {{"id": 1, "name": "Short name", "role": "You are an expert in X.", "prompt": "Specific subtask"}},
    {{"id": 2, "name": "Short name", "role": "You are an expert in Y.", "prompt": "Specific subtask"}}
  ]
}}

User request: {user_prompt}"""

REFINE_PROMPT = """You are improving your solution based on peer feedback.

Your task: {task_prompt}
Your role: {role}

Peer agent "{peer_name}" produced:
{peer_result}

Your previous result:
{own_result}

Synthesize the best parts of both, fix any issues, fill gaps. Be concrete and complete."""

MERGE_PROMPT = """You are a senior engineer doing final integration.

Original request: {user_prompt}

Results from {n} specialized agents:
{agent_results}

Synthesize into one complete, production-ready response.

IMPORTANT — when creating files use EXACTLY this format:
<create_file><path>relative/path/file.py</path><content>
file content here
</content></create_file>

When running terminal commands (install deps, mkdir, git init, etc):
<run_cmd>command here</run_cmd>

Remove redundancy, resolve conflicts, ensure consistency."""


# ─── Logging ──────────────────────────────────────────────────────────────────

def _make_log_dir() -> str:
    workspace = os.environ.get("JUZZY_CWD", os.getcwd())
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_dir = os.path.join(workspace, "logs", f"onecommand_{stamp}")
    os.makedirs(log_dir, exist_ok=True)
    return log_dir


def _write(path: str, content: str):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


def _append(path: str, line: str):
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


# ─── File & command ops ───────────────────────────────────────────────────────

def _get_workspace() -> str:
    return os.environ.get("JUZZY_CWD", os.getcwd())


def _is_safe_path(path: str) -> bool:
    workspace = os.path.realpath(_get_workspace())
    target = os.path.realpath(os.path.join(_get_workspace(), path))
    return target.startswith(workspace + os.sep) or target == workspace



TEXT_EXTENSIONS = {
    '.txt', '.md', '.py', '.js', '.ts', '.jsx', '.tsx', '.json', '.yaml', '.yml',
    '.toml', '.env', '.sh', '.html', '.css', '.sql', '.rs', '.go', '.java',
    '.c', '.cpp', '.h', '.cs', '.rb', '.php', '.swift', '.kt', '.csv'
}
MAX_FILE_SIZE  = 50 * 1024   # 50KB per file
MAX_TOTAL_SIZE = 200 * 1024  # 200KB total injected


def _inject_workspace_files(user_prompt: str) -> str:
    """Read files mentioned in prompt + all small text files in workspace.
    Injects their content into the prompt so agents can see them."""
    workspace = _get_workspace()
    injected = {}
    total_size = 0

    # 1. Files explicitly mentioned in the prompt (by filename)
    words = re.findall(r'[\w./\\-]+\.[a-zA-Z]{1,10}', user_prompt)
    for word in words:
        # Try as relative path from workspace
        candidates = [
            os.path.join(workspace, word),
            os.path.join(workspace, os.path.basename(word)),
        ]
        for path in candidates:
            if os.path.isfile(path) and path not in injected:
                try:
                    size = os.path.getsize(path)
                    if size <= MAX_FILE_SIZE and total_size + size <= MAX_TOTAL_SIZE:
                        with open(path, 'r', encoding='utf-8', errors='replace') as f:
                            injected[path] = f.read()
                            total_size += size
                except Exception:
                    pass

    # 2. All text files in workspace root (not subfolders)
    try:
        for fname in os.listdir(workspace):
            fpath = os.path.join(workspace, fname)
            ext = os.path.splitext(fname)[1].lower()
            if (os.path.isfile(fpath) and ext in TEXT_EXTENSIONS
                    and fpath not in injected and not fname.startswith('.')):
                try:
                    size = os.path.getsize(fpath)
                    if size <= MAX_FILE_SIZE and total_size + size <= MAX_TOTAL_SIZE:
                        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
                            injected[fpath] = f.read()
                            total_size += size
                except Exception:
                    pass
    except Exception:
        pass

    if not injected:
        return user_prompt

    files_block = "\n\n--- WORKSPACE FILES ---\n"
    for path, content in injected.items():
        rel = os.path.relpath(path, workspace)
        files_block += f"\n### {rel}\n```\n{content}\n```\n"

    return user_prompt + files_block


def process_output(text: str, on_log=None, ops_log_path: str = None) -> str:
    """Parse and execute <create_file> and <run_cmd> tags from model output."""
    workspace = _get_workspace()

    def log(msg):
        if on_log:
            on_log(msg)
        else:
            print(msg)
        if ops_log_path:
            _append(ops_log_path, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

    create_new = re.compile(
        r'<create_file>\s*<path>([^<]+)</path>\s*<content>(.*?)</content>\s*</create_file>',
        re.DOTALL
    )
    create_old = re.compile(r'<create_file path="([^"]+)">(.*?)</create_file>', re.DOTALL)

    for pat in (create_new, create_old):
        for m in pat.finditer(text):
            fpath    = m.group(1).strip()
            fcontent = m.group(2).strip()
            if not _is_safe_path(fpath):
                log(f"⚠ Blocked: {fpath}")
                continue
            abs_path = os.path.join(workspace, fpath)
            try:
                os.makedirs(os.path.dirname(os.path.abspath(abs_path)), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fcontent)
                log(f"✓ Created: {fpath}")
            except Exception as e:
                log(f"✗ File error {fpath}: {e}")

    cmd_pattern = re.compile(r'<run_cmd>(.*?)</run_cmd>', re.DOTALL)
    for m in cmd_pattern.finditer(text):
        cmd = m.group(1).strip()
        if not cmd:
            continue
        log(f"$ {cmd}")
        try:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True,
                cwd=workspace, timeout=60
            )
            if result.stdout.strip():
                log(result.stdout.strip()[:500])
            if result.returncode != 0 and result.stderr.strip():
                log(f"stderr: {result.stderr.strip()[:300]}")
        except subprocess.TimeoutExpired:
            log(f"✗ Timed out: {cmd}")
        except Exception as e:
            log(f"✗ Command error: {e}")

    for pat in (create_new, create_old, cmd_pattern):
        text = pat.sub("", text)
    return text.strip()


# ─── Agent state ──────────────────────────────────────────────────────────────

@dataclass
class AgentState:
    task_id: int
    name: str
    role: str
    prompt: str
    status: str = "waiting"
    result: str = ""
    iteration: int = 0
    total_iterations: int = DEFAULT_ITERATIONS
    error: str = ""


# ─── Pipeline runner ──────────────────────────────────────────────────────────

class PipelineRunner:
    def __init__(self, client: AIClient, user_prompt: str, iterations: int = DEFAULT_ITERATIONS):
        self.client        = client
        self.user_prompt   = user_prompt
        self.iterations    = iterations
        self.agents: list[AgentState] = []
        self.final_result  = ""
        self.router_done   = False
        self.pipeline_done = False
        self.ops_log: list[str] = []
        self.log_dir: str  = ""
        self.started_at    = datetime.now()
        self.lock          = threading.Lock()
        self._cb           = None
        self._stop         = False
        self._enriched_prompt = ""

    def stop(self):
        self._stop = True

    def on_update(self, cb):
        self._cb = cb

    def _notify(self):
        if self._cb:
            try:
                self._cb()
            except Exception:
                pass

    def _call(self, messages):
        if self._stop:
            raise InterruptedError("Pipeline stopped")
        return self.client.send(messages)

    def run_router(self):
        # Create log dir at start
        self.log_dir = _make_log_dir()
        _append(os.path.join(self.log_dir, "ops.log"),
                f"[{self.started_at.strftime('%H:%M:%S')}] Pipeline started: {self.user_prompt[:100]}")

        enriched_prompt = _inject_workspace_files(self.user_prompt)
        response = self._call([{"role": "user", "content": ROUTER_PROMPT.format(user_prompt=enriched_prompt)}])
        try:
            clean = response.strip()
            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) > 1 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
            tasks = json.loads(clean.strip()).get("tasks", [])[:MAX_TASKS]
            if not tasks:
                raise ValueError
        except Exception:
            tasks = [{"id": 1, "name": "Solution", "role": "You are an expert assistant.", "prompt": self.user_prompt}]

        # Store enriched prompt so agents also see workspace files
        self._enriched_prompt = enriched_prompt

        agents = [AgentState(
            task_id=t.get("id", i+1),
            name=t.get("name", f"Agent {i+1}"),
            role=t.get("role", "You are an expert assistant."),
            prompt=t.get("prompt", self.user_prompt),
            total_iterations=self.iterations,
        ) for i, t in enumerate(tasks)]

        with self.lock:
            self.agents = agents
            self.router_done = True

        # Log router result
        _write(os.path.join(self.log_dir, "run.json"), json.dumps({
            "prompt": self.user_prompt,
            "started_at": self.started_at.isoformat(),
            "iterations": self.iterations,
            "tasks": [{"id": a.task_id, "name": a.name, "prompt": a.prompt} for a in agents],
        }, ensure_ascii=False, indent=2))

        self._notify()

    def run_agent(self, agent: AgentState):
        if self._stop:
            return
        with self.lock:
            agent.status = "running"
        self._notify()
        try:
            # Use enriched prompt (with workspace files) for initial call
            enriched = self._enriched_prompt if self._enriched_prompt else agent.prompt
            result = self._call([
                {"role": "system", "content": agent.role},
                {"role": "user",   "content": agent.prompt + (
                    "\n\n" + enriched[len(self.user_prompt):] if self._enriched_prompt and
                    enriched != self.user_prompt else ""
                )},
            ])
            agent.result = result
            with self.lock:
                agent.iteration = 1
            self._notify()

            for i in range(1, self.iterations):
                if self._stop:
                    break
                peer = None
                for _ in range(40):
                    if self._stop:
                        break
                    with self.lock:
                        others = [a for a in self.agents if a.task_id != agent.task_id and a.result]
                    if others:
                        idx = agent.task_id % len(self.agents)
                        peer = self.agents[idx] if self.agents[idx].task_id != agent.task_id else others[0]
                        break
                    time.sleep(0.3)

                if peer and not self._stop:
                    result = self._call([
                        {"role": "system", "content": agent.role},
                        {"role": "user", "content": REFINE_PROMPT.format(
                            task_prompt=agent.prompt,
                            role=agent.role,
                            peer_name=peer.name,
                            peer_result=peer.result[:2000],
                            own_result=result[:2000],
                        )},
                    ])
                    agent.result = result

                with self.lock:
                    agent.iteration = i + 1
                self._notify()

            with self.lock:
                agent.status = "done"
            self._notify()

            # Log agent result
            if self.log_dir:
                safe_name = re.sub(r'[^\w]', '_', agent.name.lower())
                _write(os.path.join(self.log_dir, f"agent_{agent.task_id}_{safe_name}.md"),
                       f"# Agent {agent.task_id}: {agent.name}\n\n{agent.result}")

        except InterruptedError:
            with self.lock:
                agent.status = "error"
                agent.error = "stopped"
            self._notify()
        except Exception as e:
            with self.lock:
                agent.status = "error"
                agent.error = str(e)
            self._notify()

    def run_agents_parallel(self):
        threads = [threading.Thread(target=self.run_agent, args=(a,), daemon=True) for a in self.agents]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    def run_final_tune(self) -> str:
        if self._stop:
            return "Pipeline stopped by user."
        done = [a for a in self.agents if a.status == "done"]
        if not done:
            return "All agents failed."

        result = self._call([{"role": "user", "content": MERGE_PROMPT.format(
            user_prompt=self.user_prompt,
            n=len(done),
            agent_results="\n\n".join(f"### {a.name}\n{a.result}" for a in done),
        )}])

        # Process file creation and commands
        ops_log_path = os.path.join(self.log_dir, "ops.log") if self.log_dir else None
        ops_entries = []
        cleaned = process_output(result, on_log=lambda msg: ops_entries.append(msg),
                                  ops_log_path=ops_log_path)

        # Save logs
        if self.log_dir:
            _write(os.path.join(self.log_dir, "final.md"), cleaned)
            # Update run.json with timing and ops
            elapsed = (datetime.now() - self.started_at).total_seconds()
            _append(os.path.join(self.log_dir, "ops.log"),
                    f"[{datetime.now().strftime('%H:%M:%S')}] Pipeline finished in {elapsed:.1f}s")

        with self.lock:
            self.final_result  = cleaned
            self.ops_log       = ops_entries
            self.pipeline_done = True
        self._notify()
        return cleaned

    def run(self) -> str:
        self.run_router()
        self.run_agents_parallel()
        return self.run_final_tune()


# ─── TUI ──────────────────────────────────────────────────────────────────────

def run_onecommand_tui(client, user_prompt, iterations, s):
    from textual.app import App, ComposeResult
    from textual.widgets import Static, RichLog
    from textual.containers import Vertical, Horizontal
    from textual.binding import Binding
    from textual import work
    from rich.text import Text
    from rich.markdown import Markdown

    runner = PipelineRunner(client, user_prompt, iterations)

    class OneCommandApp(App):
        CSS = """
        Screen { layout: vertical; background: #0b0b12; }
        #header { height: 3; padding: 0 2; border-bottom: solid #1f1f2e; background: #0b0b12; }
        #title { color: #8b7cff; text-style: bold; }
        #agents { height: auto; margin: 1 2 0 2; }
        .agent-row         { height: 3; padding: 0 1; border: round #202030; margin-bottom: 1; background: #0c0c14; }
        .agent-row.running { border: round #8b7cff; }
        .agent-row.done    { border: round #00cc88; }
        .agent-row.error   { border: round #cc3333; }
        #ops    { height: 5; margin: 0 2; padding: 0 1; border: round #1a1a2e; background: #080810; }
        #result { height: 1fr; margin: 1 2; padding: 1 2; border: round #202030; background: #0c0c14; }
        #status { height: 1; padding: 0 2; color: #4a4a66; border-top: solid #1f1f2e; }
        """
        BINDINGS = [
            Binding("q", "quit", "Quit"),
            Binding("ctrl+c", "quit", show=False),
            Binding("escape", "quit", show=False),
        ]

        def compose(self) -> ComposeResult:
            with Vertical():
                with Horizontal(id="header"):
                    yield Static("JuzzyAI  /onecommand", id="title")
                yield Vertical(id="agents")
                yield RichLog(id="ops", wrap=True, markup=False)
                yield RichLog(id="result", wrap=True, markup=False)
                yield Static("  Initializing...  [Q/Esc] stop & quit", id="status")

        def on_mount(self):
            self._widgets: dict[int, Static] = {}
            self.start_pipeline()

        def _label(self, a: AgentState) -> str:
            icons  = {"waiting": "○", "running": "◉", "done": "✓", "error": "✗"}
            colors = {"waiting": "#4a4a66", "running": "#8b7cff", "done": "#00cc88", "error": "#cc3333"}
            icon  = icons.get(a.status, "○")
            color = colors.get(a.status, "#4a4a66")
            bar = ""
            if a.status == "running":
                filled = int(10 * a.iteration / max(a.total_iterations, 1))
                bar = f"  [{'█'*filled}{'░'*(10-filled)}] {a.iteration}/{a.total_iterations}"
            return f"[bold {color}]{icon}  {a.name}[/bold {color}]{bar}"

        def _refresh(self):
            panel   = self.query_one("#agents", Vertical)
            ops_log = self.query_one("#ops", RichLog)
            with runner.lock:
                agents      = list(runner.agents)
                router_done = runner.router_done
                done        = runner.pipeline_done
                ops         = list(runner.ops_log)
                log_dir     = runner.log_dir

            for a in agents:
                if a.task_id not in self._widgets:
                    w = Static(self._label(a), classes=f"agent-row {a.status}")
                    self._widgets[a.task_id] = w
                    panel.mount(w)
                else:
                    w = self._widgets[a.task_id]
                    w.update(self._label(a))
                    w.set_classes(f"agent-row {a.status}")

            if ops:
                ops_log.clear()
                for line in ops[-8:]:
                    ops_log.write(Text(line))

            if not router_done:
                st = "  Analyzing task...  [Q] stop"
            elif not done:
                running  = sum(1 for a in agents if a.status == "running")
                finished = sum(1 for a in agents if a.status == "done")
                st = f"  {finished}/{len(agents)} done  ·  {running} running  ·  [Q] stop"
            else:
                log_hint = f"  ·  log: {log_dir}" if log_dir else ""
                st = f"  Complete{log_hint}  ·  [Q] quit"
            self.query_one("#status", Static).update(st)

        @work(thread=True)
        def start_pipeline(self):
            runner.on_update(lambda: self.call_from_thread(self._refresh))
            final = runner.run()

            def show():
                self.query_one("#result", RichLog).write(Markdown(final))
                if runner.ops_log:
                    ops_log = self.query_one("#ops", RichLog)
                    ops_log.clear()
                    for line in runner.ops_log:
                        ops_log.write(Text(line))
                log_hint = f"  ·  log: {runner.log_dir}" if runner.log_dir else ""
                self.query_one("#status", Static).update(f"  Complete{log_hint}  ·  [Q] quit")

            self.call_from_thread(show)

        def action_quit(self):
            runner.stop()
            self.exit()

    OneCommandApp().run()


# ─── Classic ──────────────────────────────────────────────────────────────────

def run_onecommand_classic(client, user_prompt, iterations, s):
    from utils.markdown import print_markdown
    C="\033[36m"; G="\033[32m"; R="\033[31m"; D="\033[90m"; X="\033[0m"
    print(f"\n{C}⚡ /onecommand{X}  (Ctrl+C to stop)\n")

    runner = PipelineRunner(client, user_prompt, iterations)
    drawn = [0]

    def on_update():
        with runner.lock:
            agents = list(runner.agents)
            if not runner.router_done:
                return
        lines = []
        for a in agents:
            if   a.status == "waiting": icon = f"{D}○{X}"
            elif a.status == "running":
                f = int(10 * a.iteration / max(a.total_iterations, 1))
                icon = f"{C}◉{X} [{'█'*f}{'░'*(10-f)}] {a.iteration}/{a.total_iterations}"
            elif a.status == "done":    icon = f"{G}✓{X}"
            else:                       icon = f"{R}✗ {a.error[:40]}{X}"
            lines.append(f"  {icon}  {a.name}")
        if drawn[0]:
            print(f"\033[{drawn[0]}A", end="")
        print("\n".join(lines), flush=True)
        drawn[0] = len(lines)

    runner.on_update(on_update)
    box = {}
    t = threading.Thread(target=lambda: box.update(r=runner.run()), daemon=True)
    t.start()
    try:
        t.join()
    except KeyboardInterrupt:
        print(f"\n{R}Stopping...{X}")
        runner.stop()
        t.join(timeout=3)

    print(f"\n\n{G}{'━'*50} Final Result {'━'*50}{X}\n")
    final = box.get("r", "No result.")
    print_markdown(final)

    if runner.ops_log:
        print(f"\n{C}Files & Commands:{X}")
        for line in runner.ops_log:
            print(f"  {line}")

    if runner.log_dir:
        print(f"\n{D}Log saved: {runner.log_dir}{X}")


# ─── Entry ────────────────────────────────────────────────────────────────────

def run_onecommand(client: AIClient, user_prompt: str, iterations: int = DEFAULT_ITERATIONS,
                   lang: str = "en", s: dict = None):
    s = s or {}
    try:
        from textual.app import App
        run_onecommand_tui(client, user_prompt, iterations, s)
    except Exception:
        run_onecommand_classic(client, user_prompt, iterations, s)