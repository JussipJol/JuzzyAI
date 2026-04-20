import uuid
import time
import os
import re
import shutil
import random
from datetime import datetime

from core.client import AIClient
from core.history import save_message, load_session, list_sessions
from core.project import index_project, get_project_summary
from core.plugin_loader import load_plugins, get_plugin_help
from utils.display import print_error, print_info
from utils.markdown import print_markdown, console

from rich.text import Text
from rich.markdown import Markdown

from commands.onecommand import run_onecommand

MAX_HISTORY = 20

SPINNERS = [
    ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"],
    ["◐","◓","◑","◒"],
    ["▁","▂","▃","▄","▅","▆","▇","█","▇","▆","▅","▄","▃","▂"],
    ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"],
    ["◢","◣","◤","◥"],
    ["⊙","⊚","⊛","⊝"],
]

STRINGS = {
    "en": {
        "help_title": "JuzzyAI commands",
        "cmd_col": "Command",
        "desc_col": "Description",
        "commands": [
            ("/exit", "Exit chat"),
            ("/new", "Start a new session"),
            ("/help", "Show this menu"),
            ("/model", "Switch model"),
            ("/plugins", "List installed plugins"),
            ("/history", "Show current session ID"),
            ("/sessions", "List all sessions"),
            ("/clear", "Clear screen"),
            ("/copy", "Copy last response"),
            ("/project <path>", "Load project context"),
            ("/project off", "Unload project context"),
            ("/reset", "Reset profile and re-register"),
            ("/onecommand <task>", "Multi-agent pipeline"),
        ],
        "greeting": "Hey, {}! How can I help?",
        "loaded": "Loaded {} messages from history",
        "last_active": "Last activity: {}",
        "session_info": "Session: {} | {}@{} | /help — commands",
        "new_session": "New session: {}",
        "model_info": "Provider: {} | Model: {}",
        "current_session": "Current session: {}",
        "sessions_title": "Sessions",
        "sessions_id": "ID",
        "sessions_last": "Last message",
        "no_history": "History is empty",
        "copied": "Copied to clipboard!",
        "copy_fail": "Could not copy. Install xclip (Linux), pbcopy is built-in on macOS.",
        "nothing_to_copy": "No response to copy",
        "profile_reset": "Profile deleted. Restart the app to re-register.",
        "system_prompt": "You are an experienced programmer and JuzzyAI assistant. Address the user by name {}.",
        "system_goal": " The user is using you for: {}.",
        "system_suffix": " Help write, analyze and improve code. Be clear and concise. When you need to create or edit a file, use EXACTLY these XML tags.\n\nTo CREATE a file:\n<create_file><path>filename.py</path><content>\nfile content here\n</content></create_file>\n\nTo EDIT a file:\n<edit_file><path>filename.py</path><old>exact old text to replace</old><new>new text</new></edit_file>\n\nAlways tell the user which files you created or edited.",
        "tokens": "[{} | {}+{} tokens | {:.1f}s]",
        "elapsed": "[{} | {:.1f}s]",
        "file_created": "Created: {}",
        "file_edited": "Edited: {}",
        "file_error": "File error {}: {}",
        "file_not_found": "File not found for editing: {}",
        "file_blocked": "Blocked: path outside working directory: {}",
        "project_loaded": "Project loaded: {}",
        "project_unloaded": "Project context removed",
        "project_error": "Project error: {}",
        "interrupted": "Interrupted",
        "thinking": "thinking...",
        "plugins_title": "Installed plugins",
        "no_plugins": "No plugins installed. Add folders to plugins/",
        "plugin_error": "Plugin error: {}",
    },
    "ru": {
        "help_title": "JuzzyAI команды",
        "cmd_col": "Команда",
        "desc_col": "Описание",
        "commands": [
            ("/exit", "Выйти из чата"),
            ("/new", "Начать новую сессию"),
            ("/help", "Показать это меню"),
            ("/model", "Сменить модель"),
            ("/plugins", "Список установленных плагинов"),
            ("/history", "Показать ID текущей сессии"),
            ("/sessions", "Список всех сессий"),
            ("/clear", "Очистить экран"),
            ("/copy", "Скопировать последний ответ"),
            ("/project <путь>", "Загрузить контекст проекта"),
            ("/project off", "Выгрузить контекст проекта"),
            ("/reset", "Сбросить профиль и пройти регистрацию заново"),
            ("/onecommand <задача>", "Мульти-агентный пайплайн"),
        ],
        "greeting": "Привет, {}! Чем могу помочь?",
        "loaded": "Загружено {} сообщений из истории",
        "last_active": "Последняя активность: {}",
        "session_info": "Сессия: {} | {}@{} | /help — команды",
        "new_session": "Новая сессия: {}",
        "model_info": "Провайдер: {} | Модель: {}",
        "current_session": "Текущая сессия: {}",
        "sessions_title": "Сессии",
        "sessions_id": "ID",
        "sessions_last": "Последнее сообщение",
        "no_history": "История пуста",
        "copied": "Скопировано в буфер обмена!",
        "copy_fail": "Не удалось скопировать. Установи xclip (Linux), на macOS pbcopy встроен.",
        "nothing_to_copy": "Нет ответа для копирования",
        "profile_reset": "Профиль удалён. Перезапусти приложение для регистрации.",
        "system_prompt": "Ты — опытный программист и ассистент JuzzyAI. Обращайся к пользователю по имени {}.",
        "system_goal": " Пользователь использует тебя для: {}.",
        "system_suffix": " Помогай писать, анализировать и улучшать код. Отвечай чётко и по делу. Когда нужно создать или изменить файл, используй ТОЧНО эти XML теги.\n\nДля СОЗДАНИЯ файла:\n<create_file><path>filename.py</path><content>\nсодержимое файла\n</content></create_file>\n\nДля РЕДАКТИРОВАНИЯ файла:\n<edit_file><path>filename.py</path><old>точный старый текст</old><new>новый текст</new></edit_file>\n\nВсегда сообщай пользователю какие файлы создал или изменил.",
        "tokens": "[{} | {}+{} токенов | {:.1f}с]",
        "elapsed": "[{} | {:.1f}с]",
        "file_created": "Создан: {}",
        "file_edited": "Изменён: {}",
        "file_error": "Ошибка файла {}: {}",
        "file_not_found": "Файл не найден для редактирования: {}",
        "file_blocked": "Заблокировано: путь вне рабочей директории: {}",
        "project_loaded": "Проект загружен: {}",
        "project_unloaded": "Контекст проекта удалён",
        "project_error": "Ошибка проекта: {}",
        "interrupted": "Прервано",
        "thinking": "думаю...",
        "plugins_title": "Установленные плагины",
        "no_plugins": "Нет плагинов. Добавь папки в plugins/",
        "plugin_error": "Ошибка плагина: {}",
    }
}


def _get_workspace_root():
    return os.environ.get("JUZZY_CWD", os.getcwd())


def _is_safe_path(path: str) -> bool:
    workspace = os.path.realpath(_get_workspace_root())
    target = os.path.realpath(os.path.abspath(path))
    return target.startswith(workspace + os.sep) or target == workspace


def _copy_to_clipboard(text: str) -> bool:
    import subprocess
    try:
        if os.name == "nt":
            subprocess.run("clip", input=text.encode("utf-8"), check=True)
        elif shutil.which("pbcopy"):
            subprocess.run("pbcopy", input=text.encode("utf-8"), check=True)
        elif shutil.which("xclip"):
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode("utf-8"), check=True)
        elif shutil.which("xsel"):
            subprocess.run(["xsel", "--clipboard", "--input"], input=text.encode("utf-8"), check=True)
        else:
            return False
        return True
    except Exception:
        return False


def process_file_ops(response: str, s: dict, log=None) -> str:
    workspace = _get_workspace_root()

    def resolve(path):
        return path if os.path.isabs(path) else os.path.join(workspace, path)

    def output(msg):
        if log is not None:
            log.write(Text.from_markup(msg))
        else:
            console.print(msg)

    create_pattern_new = re.compile(
        r'<create_file>\s*<path>([^<]+)</path>\s*<content>(.*?)</content>\s*</create_file>',
        re.DOTALL
    )
    create_pattern_old = re.compile(r'<create_file path="([^"]+)">(.*?)</create_file>', re.DOTALL)

    for pat in (create_pattern_new, create_pattern_old):
        for match in pat.finditer(response):
            fpath    = match.group(1).strip()
            fcontent = match.group(2).strip()
            if not _is_safe_path(fpath):
                output(f"[bold red]{s['file_blocked'].format(fpath)}[/bold red]")
                continue
            try:
                abs_path = resolve(fpath)
                os.makedirs(os.path.dirname(os.path.abspath(abs_path)), exist_ok=True)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fcontent)
                output(f"[bold green]{s['file_created'].format(fpath)}[/bold green]")
            except Exception as e:
                output(f"[bold red]{s['file_error'].format(fpath, e)}[/bold red]")

    edit_pattern_new = re.compile(
        r'<edit_file>\s*<path>([^<]+)</path>\s*<old>(.*?)</old>\s*<new>(.*?)</new>\s*</edit_file>',
        re.DOTALL
    )
    edit_pattern_old = re.compile(
        r'<edit_file path="([^"]+)" old="(.*?)" new="(.*?)"></edit_file>',
        re.DOTALL
    )

    for pat in (edit_pattern_new, edit_pattern_old):
        for match in pat.finditer(response):
            fpath = match.group(1).strip()
            old   = match.group(2)
            new   = match.group(3)
            if not _is_safe_path(fpath):
                output(f"[bold red]{s['file_blocked'].format(fpath)}[/bold red]")
                continue
            try:
                abs_path = resolve(fpath)
                if not os.path.exists(abs_path):
                    output(f"[bold red]{s['file_not_found'].format(fpath)}[/bold red]")
                    continue
                with open(abs_path, "r", encoding="utf-8") as f:
                    fcontent = f.read()
                if old not in fcontent:
                    output(f"[bold yellow]Warning: old text not found in {fpath}[/bold yellow]")
                    continue
                fcontent = fcontent.replace(old, new, 1)
                with open(abs_path, "w", encoding="utf-8") as f:
                    f.write(fcontent)
                output(f"[bold green]{s['file_edited'].format(fpath)}[/bold green]")
            except Exception as e:
                output(f"[bold red]{s['file_error'].format(fpath, e)}[/bold red]")

    for pat in (create_pattern_new, create_pattern_old, edit_pattern_new, edit_pattern_old):
        response = pat.sub("", response)
    return response.strip()


def build_system_prompt(s, name, goal, project_context):
    sp = s["system_prompt"].format(name)
    if goal:
        sp += s["system_goal"].format(goal)
    sp += s["system_suffix"]
    if project_context:
        sp += f"\n\n{project_context}"
    return sp


def stream_with_tokens(client, messages, system_prompt):
    trimmed = messages[-MAX_HISTORY:] if len(messages) > MAX_HISTORY else messages
    return client.stream_tokens(trimmed, system_prompt)


def _build_plugin_context(lang, profile, session_id, project_context):
    return {
        "lang": lang,
        "profile": profile,
        "session_id": session_id,
        "project_context": project_context,
    }


def _try_textual():
    try:
        import textual
        from textual.app import App
        return True
    except Exception:
        return False


def run_chat(client: AIClient, session_id: str = None, profile: dict = None, project_context: str = ""):
    if _try_textual():
        _run_chat_tui(client, session_id, profile, project_context)
    else:
        _run_chat_classic(client, session_id, profile, project_context)


def _run_chat_tui(client: AIClient, session_id: str = None, profile: dict = None, project_context: str = ""):
    from textual.app import App, ComposeResult
    from textual.widgets import Input, RichLog, Static, ListView, ListItem, Label
    from textual.containers import Horizontal, Vertical
    from textual.binding import Binding
    from textual import work

    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    lang = profile.get("lang", "en") if profile else "en"
    s = STRINGS[lang]
    name = profile.get("name", "friend") if profile else "friend"
    goal = profile.get("goal", "") if profile else ""

    state = {
        "session_id": session_id,
        "messages": load_session(session_id),
        "project_context": project_context,
        "system_prompt": build_system_prompt(s, name, goal, project_context),
        "last_response": "",
        "total_tokens": 0,
        "input_history": [],
        "history_idx": -1,
    }

    class JuzzyApp(App):
        CSS = """
        Screen { layout: vertical; background: #0b0b12; }
        #header { height: 3; padding: 0 2; border-bottom: solid #1f1f2e; background: #0b0b12; }
        #title { color: #8b7cff; text-style: bold; }
        #meta { width: 1fr; text-align: right; color: #4a4a66; }
        #chat { height: 1fr; margin: 1 2; padding: 1 2; border: round #202030; background: #0c0c14; }
        #status { height: 1; padding: 0 2; border-top: solid #1f1f2e; color: #8b7cff; }
        #autocomplete { margin: 0 2; background: #12121a; border: round #2b2b44; height: auto; max-height: 6; display: none; }
        #autocomplete.visible { display: block; }
        #autocomplete > ListItem { padding: 0 1; }
        #autocomplete > ListItem:hover { background: #1e1e2e; }
        #autocomplete > ListItem.--highlight { background: #2b2b44; }
        #input-box { margin: 0 2 1 2; height: 3; padding: 0 1; border: round #2b2b44; background: #12121a; }
        #input-box:focus-within { border: round #8b7cff; }
        Input { border: none; background: #12121a; color: #e6e6f0; width: 1fr; }
        """

        BINDINGS = [
            Binding("ctrl+c", "quit", show=False),
            Binding("ctrl+n", "new_session", show=False),
        ]

        def compose(self) -> ComposeResult:
            with Vertical():
                with Horizontal(id="header"):
                    yield Static("JuzzyAI", id="title")
                    yield Static("", id="meta")
                yield RichLog(id="chat", wrap=True, markup=False)
                yield Static("", id="status")
                yield ListView(id="autocomplete")
                with Horizontal(id="input-box"):
                    yield Input(placeholder=f"{name} › ask anything...", id="input")

        def on_mount(self):
            self._awaiting_model_pick = False
            self._model_list = []
            self._plugins = load_plugins()
            self._all_commands = (
                [c for c, _ in s["commands"]] +
                list(self._plugins.keys()) +
                ["/onecommand"]
            )
            self._is_spinning = False
            self._spinner_frames = random.choice(SPINNERS)
            self.update_header()
            self.bg_spinner()
            log = self.query_one("#chat", RichLog)
            log.write(Text.from_markup(f"[bold cyan]{s['greeting'].format(name)}[/bold cyan]"))
            if state["messages"]:
                log.write(Text.from_markup(f"[dim]{s['loaded'].format(len(state['messages']))}[/dim]"))
                for msg in state["messages"][-10:]:
                    if msg["role"] == "user":
                        log.write(Text.from_markup(f"[bold #b26cff]{name}:[/bold #b26cff] {msg['content']}"))
                    else:
                        log.write(Text.from_markup(f"[bold #8b7cff]JuzzyAI:[/bold #8b7cff]"))
                        log.write(Markdown(msg["content"]))
            self.query_one("#input", Input).focus()

        def update_header(self, spinner_char: str = ""):
            full_model = f"{client.provider}/{client.model}"
            if len(full_model) > 50:
                full_model = full_model[:47] + "..."
            proj = "P " if state["project_context"] else ""
            now = datetime.now().strftime("%H:%M")
            tok = f" {state['total_tokens']}t"
            self.query_one("#meta", Static).update(
                f"{proj}{full_model} {state['session_id']} {now}{tok}"
            )
            if spinner_char:
                color = "#ff7cff" if self._is_spinning else "#8b7cff"
                self.query_one("#title", Static).update(
                    f"[bold {color}]{spinner_char}[/bold {color}] [bold #8b7cff]JuzzyAI[/bold #8b7cff]"
                )

        def update_status(self, text: str):
            self.query_one("#status", Static).update(text)

        def _show_autocomplete(self, matches: list):
            ac = self.query_one("#autocomplete", ListView)
            ac.clear()
            if matches:
                for m in matches[:5]:
                    ac.append(ListItem(Label(m)))
                ac.add_class("visible")
            else:
                ac.remove_class("visible")

        def _hide_autocomplete(self):
            ac = self.query_one("#autocomplete", ListView)
            ac.remove_class("visible")
            ac.clear()

        def on_input_changed(self, event: Input.Changed):
            text = event.value
            if text.startswith("/") and " " not in text:
                matches = [c for c in self._all_commands if c.startswith(text) and c != text]
                self._show_autocomplete(matches)
            else:
                self._hide_autocomplete()

        def on_list_view_selected(self, event: ListView.Selected):
            label = event.item.query_one(Label)
            inp = self.query_one("#input", Input)
            inp.value = label.renderable
            inp.cursor_position = len(inp.value)
            self._hide_autocomplete()
            inp.focus()

        def on_key(self, event) -> None:
            inp = self.query_one("#input", Input)
            ac = self.query_one("#autocomplete", ListView)

            if event.key == "tab":
                if "visible" in ac.classes and len(ac.children) > 0:
                    first = ac.children[0].query_one(Label)
                    inp.value = first.renderable
                    inp.cursor_position = len(inp.value)
                    self._hide_autocomplete()
                    event.prevent_default()
                return

            if event.key == "up":
                if "visible" in ac.classes:
                    ac.focus()
                    event.prevent_default()
                    return
                history = state["input_history"]
                if history:
                    if state["history_idx"] < len(history) - 1:
                        state["history_idx"] += 1
                    inp.value = history[-(state["history_idx"] + 1)]
                    inp.cursor_position = len(inp.value)
                event.prevent_default()
                return

            if event.key == "down":
                history = state["input_history"]
                if state["history_idx"] > 0:
                    state["history_idx"] -= 1
                    inp.value = history[-(state["history_idx"] + 1)]
                elif state["history_idx"] == 0:
                    state["history_idx"] = -1
                    inp.value = ""
                inp.cursor_position = len(inp.value)
                event.prevent_default()
                return

            if event.key == "escape":
                self._hide_autocomplete()

        def action_quit(self):
            self.exit()

        def action_new_session(self):
            state["session_id"] = str(uuid.uuid4())[:8]
            state["messages"] = []
            log = self.query_one("#chat", RichLog)
            log.clear()
            log.write(Text.from_markup(f"[dim]{s['new_session'].format(state['session_id'])}[/dim]"))
            self.update_header()

        def on_input_submitted(self, event: Input.Submitted):
            text = event.value.strip()
            if not text:
                return
            event.input.clear()
            self._hide_autocomplete()

            if self._awaiting_model_pick:
                self._awaiting_model_pick = False
                self.update_status("")
                self._pick_model(text)
                return

            if not state["input_history"] or state["input_history"][-1] != text:
                state["input_history"].append(text)
                if len(state["input_history"]) > 100:
                    state["input_history"].pop(0)
            state["history_idx"] = -1

            self.handle_message(text)

        def handle_message(self, text: str):
            if text.startswith("/"):
                cmd_word = text.split()[0]
                if cmd_word in self._plugins:
                    self._run_plugin_tui(cmd_word, text[len(cmd_word):].strip())
                    return
                self.handle_command(text)
                return
            log = self.query_one("#chat", RichLog)
            log.write(Text.from_markup(f"[bold #b26cff]{name}:[/bold #b26cff] {text}"))
            state["messages"].append({"role": "user", "content": text})
            save_message(state["session_id"], "user", text)
            self._is_spinning = True
            self._spinner_frames = random.choice(SPINNERS)
            self.spin_status()
            self.stream_reply()

        def _run_plugin_tui(self, cmd: str, message: str):
            log = self.query_one("#chat", RichLog)
            plugin = self._plugins[cmd]
            self._is_spinning = True
            self._spinner_frames = random.choice(SPINNERS)
            self.spin_status()

            @work(thread=True)
            def _exec(self):
                try:
                    ctx = _build_plugin_context(lang, profile, state["session_id"], state["project_context"])
                    result = plugin.run(client, message, ctx)
                    def render():
                        self._is_spinning = False
                        self.update_status("")
                        log.write(Text.from_markup(f"[bold #8b7cff]{plugin.name}:[/bold #8b7cff]"))
                        log.write(Markdown(result) if result else Text("(no output)"))
                        log.scroll_end()
                    self.call_from_thread(render)
                except Exception as e:
                    def err():
                        self._is_spinning = False
                        log.write(Text(f"Plugin error: {e}"))
                        self.update_status("")
                    self.call_from_thread(err)
            _exec(self)

        @work(thread=True)
        def bg_spinner(self):
            idle_frames = ["·", "·", "·", "∘", "∘", "○", "∘", "∘"]
            busy_frames = ["⣾","⣽","⣻","⢿","⡿","⣟","⣯","⣷"]
            i = 0
            while True:
                frames = busy_frames if self._is_spinning else idle_frames
                delay  = 0.08 if self._is_spinning else 0.3
                frame  = frames[i % len(frames)]
                def _upd(f=frame):
                    self.update_header(spinner_char=f)
                self.call_from_thread(_upd)
                time.sleep(delay)
                i += 1

        @work(thread=True)
        def spin_status(self):
            i = 0
            label = s["thinking"]
            while self._is_spinning:
                frame = self._spinner_frames[i % len(self._spinner_frames)]
                def _upd(f=frame):
                    self.query_one("#status", Static).update(f"  {f}  {label}")
                self.call_from_thread(_upd)
                time.sleep(0.1)
                i += 1

        def handle_command(self, cmd: str):
            log = self.query_one("#chat", RichLog)
            if cmd == "/exit":
                self.exit(); return
            if cmd == "/new":
                self.action_new_session(); return
            if cmd.startswith("/onecommand"):
                prompt = cmd[len("/onecommand"):].strip()
                self.handle_onecommand(prompt)
                return
            if cmd == "/clear":
                log.clear(); return
            if cmd == "/help":
                from rich.table import Table
                table = Table(title=s["help_title"], header_style="bold cyan", border_style="dim")
                table.add_column(s["cmd_col"], style="green")
                table.add_column(s["desc_col"])
                for c, desc in s["commands"]:
                    table.add_row(c, desc)
                for c, desc in get_plugin_help(self._plugins):
                    table.add_row(c, f"plugin: {desc}")
                log.write(table); return
            if cmd == "/plugins":
                from rich.table import Table
                if self._plugins:
                    table = Table(title=s["plugins_title"], header_style="bold cyan", border_style="dim")
                    table.add_column("Command", style="green")
                    table.add_column("Name")
                    table.add_column("Ver", style="dim")
                    table.add_column("Description")
                    for p in self._plugins.values():
                        table.add_row(p.command, p.name, p.version, p.description)
                    log.write(table)
                else:
                    log.write(Text(s["no_plugins"]))
                return
            if cmd == "/model":
                self._show_model_picker(); return
            if cmd == "/history":
                log.write(Text(s["current_session"].format(state["session_id"]))); return
            if cmd == "/sessions":
                sessions = list_sessions()
                if sessions:
                    from rich.table import Table
                    table = Table(title=s["sessions_title"], header_style="bold cyan", border_style="dim")
                    table.add_column(s["sessions_id"], style="green")
                    table.add_column(s["sessions_last"])
                    for x in sessions:
                        table.add_row(x["session_id"], x["last_message"])
                    log.write(table)
                else:
                    log.write(Text(s["no_history"]))
                return
            if cmd == "/copy":
                if state["last_response"]:
                    ok = _copy_to_clipboard(state["last_response"])
                    log.write(Text(s["copied"] if ok else s["copy_fail"]))
                else:
                    log.write(Text(s["nothing_to_copy"]))
                return
            if cmd == "/reset":
                profile_path = os.path.expanduser("~/.juzzyai/profile.json")
                if os.path.exists(profile_path):
                    os.remove(profile_path)
                log.write(Text(s["profile_reset"]))
                self.exit(); return
            if cmd.startswith("/project"):
                parts = cmd.split(maxsplit=1)
                arg = parts[1].strip() if len(parts) > 1 else ""
                if arg == "off":
                    state["project_context"] = ""
                    state["system_prompt"] = build_system_prompt(s, name, goal, "")
                    log.write(Text(s["project_unloaded"]))
                elif arg == "":
                    status = "active" if state["project_context"] else "none"
                    log.write(Text(f"Project: {status}"))
                else:
                    try:
                        summary = get_project_summary(arg)
                        state["project_context"] = index_project(arg)
                        state["system_prompt"] = build_system_prompt(s, name, goal, state["project_context"])
                        log.write(Text(s["project_loaded"].format(summary)))
                        self.update_header()
                    except Exception as e:
                        log.write(Text(s["project_error"].format(e)))
                return
            log.write(Text(f"Unknown command: {cmd}. Type /help"))

        def handle_onecommand(self, prompt: str):
            """Launch /onecommand — opens dedicated TUI pipeline app."""
            log = self.query_one("#chat", RichLog)
            if not prompt:
                log.write(Text("Usage: /onecommand <task description>"))
                return

            @work(thread=True)
            def _exec(self):
                try:
                    # run_onecommand открывает отдельный TUI — выходим из JuzzyApp
                    # и запускаем OneCommandApp, затем возвращаемся
                    def launch():
                        self.exit()
                    self.call_from_thread(launch)
                    time.sleep(0.1)
                    run_onecommand(client, prompt, iterations=2, lang=lang)
                except Exception as e:
                    def err():
                        log.write(Text(f"/onecommand error: {e}"))
                    self.call_from_thread(err)
            _exec(self)

        def _show_model_picker(self):
            from core.config import GROQ_MODELS, OPENROUTER_MODELS, HF_MODELS
            from rich.table import Table
            log = self.query_one("#chat", RichLog)
            if client.provider == "ollama":
                from core.profile import get_ollama_models
                ollama_models = get_ollama_models()
                if not ollama_models:
                    log.write(Text("No Ollama models found"))
                    return
                models = [(m, "local") for m in ollama_models]
            else:
                models_map = {"groq": GROQ_MODELS, "openrouter": OPENROUTER_MODELS, "huggingface": HF_MODELS}
                models = models_map.get(client.provider)
                if not models:
                    log.write(Text(f"Model switching not supported for {client.provider}"))
                    return
            table = Table(title=f"Models — {client.provider}", header_style="bold cyan", border_style="dim")
            table.add_column("#", style="dim", width=3)
            table.add_column("Model", style="green")
            table.add_column("Description")
            for i, (m, desc) in enumerate(models, 1):
                current = " *" if m == client.model else ""
                table.add_row(str(i), m.split("/")[-1] + current, desc)
            log.write(table)
            self._model_list = models
            self._awaiting_model_pick = True
            self.update_status("  Enter model number to switch ->")

        def _pick_model(self, choice: str):
            log = self.query_one("#chat", RichLog)
            try:
                new_model = self._model_list[int(choice) - 1][0]
                client.model = new_model
                log.write(Text(f"Switched to {new_model.split('/')[-1]}"))
                self.update_header()
            except (ValueError, IndexError):
                log.write(Text("Cancelled"))

        @work(thread=True)
        def stream_reply(self):
            log = self.query_one("#chat", RichLog)
            start = time.time()
            try:
                full, pt, gt = stream_with_tokens(client, state["messages"], state["system_prompt"])
                elapsed = time.time() - start
                cleaned = process_file_ops(full, s, log=log)
                state["last_response"] = cleaned
                state["messages"].append({"role": "assistant", "content": full})
                save_message(state["session_id"], "assistant", full)
                if pt or gt:
                    state["total_tokens"] += (pt or 0) + (gt or 0)

                def render():
                    self._is_spinning = False
                    self.update_status("")
                    log.write(Text.from_markup("[bold #8b7cff]JuzzyAI:[/bold #8b7cff]"))
                    log.write(Markdown(cleaned))
                    if pt or gt:
                        log.write(Text(f"[{client.model.split('/')[-1]} | {pt}+{gt} tokens | {elapsed:.1f}s]"))
                    else:
                        log.write(Text(f"[{client.model.split('/')[-1]} | {elapsed:.1f}s]"))
                    self.update_header()
                    log.scroll_end()

                self.call_from_thread(render)

            except Exception as e:
                def err():
                    self._is_spinning = False
                    log.write(Text(f"Error: {e}"))
                    self.update_status("")
                self.call_from_thread(err)

    JuzzyApp().run()


# ─── Классический fallback ────────────────────────────────────────────────────

def print_help(lang="en", plugins=None):
    from rich.table import Table
    s = STRINGS[lang]
    table = Table(title=s["help_title"], show_header=True, header_style="bold cyan")
    table.add_column(s["cmd_col"], style="green")
    table.add_column(s["desc_col"])
    for cmd, desc in s["commands"]:
        table.add_row(cmd, desc)
    if plugins:
        for cmd, desc in get_plugin_help(plugins):
            table.add_row(cmd, f"plugin: {desc}")
    console.print(table)


def _show_model_picker_classic(client, lang):
    from core.config import GROQ_MODELS, OPENROUTER_MODELS, HF_MODELS
    from rich.table import Table

    if client.provider == "ollama":
        from core.profile import get_ollama_models
        models_list = get_ollama_models()
        if not models_list:
            print_info("No Ollama models found")
            return
        models = [(m, "local") for m in models_list]
    else:
        models_map = {"groq": GROQ_MODELS, "openrouter": OPENROUTER_MODELS, "huggingface": HF_MODELS}
        models = models_map.get(client.provider)
        if not models:
            print_info(f"Model switching not supported for {client.provider}")
            return

    table = Table(title=f"Models — {client.provider}", header_style="bold cyan")
    table.add_column("#", style="dim", width=3)
    table.add_column("Model", style="green")
    table.add_column("Description")
    for i, (m, desc) in enumerate(models, 1):
        current = " *" if m == client.model else ""
        table.add_row(str(i), m.split("/")[-1] + current, desc)
    console.print(table)

    try:
        choice = input("  Enter number → ").strip()
        new_model = models[int(choice) - 1][0]
        client.model = new_model
        print_info(f"Switched to {new_model.split('/')[-1]}")
    except (ValueError, IndexError, KeyboardInterrupt, EOFError):
        print_info("Cancelled")


def _run_chat_classic(client: AIClient, session_id: str = None, profile: dict = None, project_context: str = ""):
    if not session_id:
        session_id = str(uuid.uuid4())[:8]

    lang = profile.get("lang", "en") if profile else "en"
    s = STRINGS[lang]
    name = profile.get("name", "friend") if profile else "friend"
    goal = profile.get("goal", "") if profile else ""

    plugins = load_plugins()
    system_prompt = build_system_prompt(s, name, goal, project_context)

    console.print(f"\n[bold cyan]{s['greeting'].format(name)}[/bold cyan]")
    messages = load_session(session_id)
    if messages:
        print_info(s["loaded"].format(len(messages)))
        sessions = list_sessions()
        current = next((x for x in sessions if x["session_id"] == session_id), None)
        if current:
            print_info(s["last_active"].format(current["last_message"]))
    print_info(s["session_info"].format(session_id, name, client.model))
    last_response = ""

    while True:
        try:
            user_input = input(f"\n\033[35m{name}@{client.model.split(':')[0]} >\033[0m ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd_word = user_input.split()[0]
            if cmd_word in plugins:
                plugin = plugins[cmd_word]
                message = user_input[len(cmd_word):].strip()
                try:
                    ctx = _build_plugin_context(lang, profile, session_id, project_context)
                    result = plugin.run(client, message, ctx)
                    if result:
                        console.print(f"\n[bold green]{plugin.name}:[/bold green]")
                        print_markdown(result)
                except Exception as e:
                    print_error(s["plugin_error"].format(e))
                continue

        if user_input == "/exit":
            break
        if user_input == "/new":
            session_id = str(uuid.uuid4())[:8]
            messages = []
            print_info(s["new_session"].format(session_id))
            continue
        if user_input == "/help":
            print_help(lang, plugins)
            continue
        if user_input == "/model":
            _show_model_picker_classic(client, lang)
            system_prompt = build_system_prompt(s, name, goal, project_context)
            continue
        if user_input == "/plugins":
            if plugins:
                from rich.table import Table
                table = Table(title=s["plugins_title"], header_style="bold cyan")
                table.add_column("Command", style="green")
                table.add_column("Name")
                table.add_column("Ver", style="dim")
                table.add_column("Description")
                for p in plugins.values():
                    table.add_row(p.command, p.name, p.version, p.description)
                console.print(table)
            else:
                print_info(s["no_plugins"])
            continue
        if user_input == "/history":
            print_info(s["current_session"].format(session_id))
            continue
        if user_input == "/sessions":
            sessions = list_sessions()
            if sessions:
                from rich.table import Table
                table = Table(title=s["sessions_title"], header_style="bold cyan")
                table.add_column(s["sessions_id"], style="green")
                table.add_column(s["sessions_last"])
                for x in sessions:
                    table.add_row(x["session_id"], x["last_message"])
                console.print(table)
            else:
                print_info(s["no_history"])
            continue
        if user_input == "/clear":
            os.system("cls" if os.name == "nt" else "clear")
            continue
        if user_input.startswith("/onecommand"):
            prompt = user_input[len("/onecommand"):].strip()
            if not prompt:
                print_info("Usage: /onecommand <task description>")
            else:
                run_onecommand(client, prompt, iterations=2, lang=lang)
            continue
        if user_input.startswith("/project"):
            parts = user_input.split(maxsplit=1)
            arg = parts[1].strip() if len(parts) > 1 else ""
            if arg == "off":
                project_context = ""
                system_prompt = build_system_prompt(s, name, goal, project_context)
                print_info(s["project_unloaded"])
            elif arg == "":
                print_info("Project: " + ("active" if project_context else "none"))
            else:
                try:
                    summary = get_project_summary(arg)
                    project_context = index_project(arg)
                    system_prompt = build_system_prompt(s, name, goal, project_context)
                    print_info(s["project_loaded"].format(summary))
                except Exception as e:
                    print_error(s["project_error"].format(e))
            continue
        if user_input == "/copy":
            if last_response:
                print_info(s["copied"] if _copy_to_clipboard(last_response) else s["copy_fail"])
            else:
                print_info(s["nothing_to_copy"])
            continue
        if user_input == "/reset":
            profile_path = os.path.expanduser("~/.juzzyai/profile.json")
            if os.path.exists(profile_path):
                os.remove(profile_path)
            print_info(s["profile_reset"])
            break

        messages.append({"role": "user", "content": user_input})
        save_message(session_id, "user", user_input)

        try:
            start_time = time.time()
            full_response, prompt_tokens, generated_tokens = stream_with_tokens(client, messages, system_prompt)
            elapsed = time.time() - start_time
            cleaned_response = process_file_ops(full_response, s)

            term_width = shutil.get_terminal_size().columns or 80
            line_count = sum(max(1, (len(line) + term_width - 1) // term_width) for line in full_response.splitlines()) + 1
            print(f"\033[{line_count}A\033[J", end="")
            console.print("[bold green]JuzzyAI:[/bold green]")
            print_markdown(cleaned_response)

            if prompt_tokens or generated_tokens:
                print(f"\033[90m{s['tokens'].format(client.model, prompt_tokens, generated_tokens, elapsed)}\033[0m")
            else:
                print(f"\033[90m{s['elapsed'].format(client.model, elapsed)}\033[0m")

            last_response = cleaned_response
            messages.append({"role": "assistant", "content": full_response})
            save_message(session_id, "assistant", full_response)

        except Exception as e:
            print_error(str(e))
            messages.pop()