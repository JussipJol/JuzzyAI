import sys
import time
import threading
import os

# ─── ANSI ────────────────────────────────────────────────────────────────────
CYAN    = "\033[36m"
GREEN   = "\033[32m"
RED     = "\033[31m"
YELLOW  = "\033[33m"
MAGENTA = "\033[35m"
DIM     = "\033[90m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
CLEAR_LINE = "\033[2K\r"


# ─── Header ──────────────────────────────────────────────────────────────────

def print_header():
    print(CYAN)
    print("         ▓█▓▒  ▓█▓▒   ▓█▓▒░ ▓████████▓▒  ▓████████▓▒  ▓█▓▒░  ▓█▓▒   ▓██████▓▒░  ▓█▓▒░ ")
    print("         ▓█▓▒  ▓█▓▒   ▓█▓▒░        ▓█▓▒░        ▓█▓▒  ▓█▓▒░  ▓█▓▒  ▓█▓▒░  ▓█▓▒  ▓█▓▒░ ")
    print("         ▓█▓▒  ▓█▓▒   ▓█▓▒░      ▓██▓▒░       ▓██▓▒░  ▓█▓▒░  ▓█▓▒  ▓█▓▒░  ▓█▓▒  ▓█▓▒░  ")
    print("         ▓█▓▒  ▓█▓▒   ▓█▓▒░    ▓██▓▒░       ▓██▓▒░     ▓██████▓▒░  ▓████████▓▒  ▓█▓▒░ ")
    print("  ▓█▓▒   ▓█▓▒  ▓█▓▒   ▓█▓▒░  ▓██▓▒░       ▓██▓▒░         ▓█▓▒░     ▓█▓▒░  ▓█▓▒  ▓█▓▒░ ")
    print("  ▓█▓▒   ▓█▓▒  ▓█▓▒   ▓█▓▒░ ▓█▓▒░        ▓█▓▒░           ▓█▓▒░     ▓█▓▒░  ▓█▓▒  ▓█▓▒░ ")
    print("   ▓██████▓▒    ▓██████▓▒░░ ▓████████▓▒  ▓████████▓▒░    ▓█▓▒░     ▓█▓▒░  ▓█▓▒  ▓█▓▒░  ")
    print("                                   AI coding assistant")
    print(RESET)


# ─── Preloader ────────────────────────────────────────────────────────────────

class Preloader:
    """Анимированный прелоадер. Использование:
        with Preloader("Loading...") as p:
            p.step("Checking license")
            do_something()
            p.step("Loading profile")
            do_something_else()
    """

    SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
    BAR_WIDTH = 28
    BAR_FILL  = "█"
    BAR_EMPTY = "░"

    def __init__(self, total_steps: int = 4):
        self._total    = total_steps
        self._current  = 0
        self._label    = "Starting..."
        self._done     = False
        self._lock     = threading.Lock()
        self._thread   = threading.Thread(target=self._animate, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *args):
        self._done = True
        self._thread.join()
        # Стираем последнюю строку прелоадера
        sys.stdout.write(CLEAR_LINE)
        sys.stdout.flush()

    def step(self, label: str):
        with self._lock:
            self._current += 1
            self._label = label

    def _render(self, spinner_char: str) -> str:
        with self._lock:
            current = self._current
            label   = self._label

        filled = int(self.BAR_WIDTH * current / max(self._total, 1))
        bar = self.BAR_FILL * filled + self.BAR_EMPTY * (self.BAR_WIDTH - filled)
        pct = int(100 * current / max(self._total, 1))

        return (
            f"{CLEAR_LINE}"
            f"  {CYAN}{spinner_char}{RESET} "
            f"{DIM}[{RESET}{CYAN}{bar}{RESET}{DIM}]{RESET} "
            f"{DIM}{pct:3d}%{RESET}  "
            f"{BOLD}{label}{RESET}"
        )

    def _animate(self):
        i = 0
        while not self._done:
            frame = self.SPINNER[i % len(self.SPINNER)]
            sys.stdout.write(self._render(frame))
            sys.stdout.flush()
            time.sleep(0.08)
            i += 1
        # Финальная строка — всё готово
        bar = self.BAR_FILL * self.BAR_WIDTH
        sys.stdout.write(
            f"{CLEAR_LINE}"
            f"  {GREEN}✓{RESET} "
            f"{DIM}[{RESET}{GREEN}{bar}{RESET}{DIM}]{RESET} "
            f"{DIM}100%{RESET}  "
            f"{GREEN}Ready{RESET}\n"
        )
        sys.stdout.flush()


# ─── Остальные утилиты ────────────────────────────────────────────────────────

def print_response(text: str):
    print(f"\n{GREEN}JuzzyAI:{RESET}")
    print(text)
    print()

def print_error(text: str):
    print(f"\n{RED}❌ Error: {text}{RESET}\n")

def print_info(text: str):
    print(f"{YELLOW}→ {text}{RESET}")

def print_sessions(sessions: list):
    if not sessions:
        print_info("No history")
        return
    print(f"\n{CYAN}Sessions:{RESET}")
    for s in sessions:
        print(f"  • {s['session_id']}  {DIM}({s['last_message']}){RESET}")
    print()