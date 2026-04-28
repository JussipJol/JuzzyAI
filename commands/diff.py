"""
/diff [ref] — show git diff and get an AI review.

  /diff              → all changes vs HEAD (staged + unstaged)
  /diff --staged     → only staged changes
  /diff HEAD~1       → last commit
  /diff main         → against another branch
"""

import subprocess
import os
from rich.syntax import Syntax
from rich.panel import Panel

MAX_DIFF_CHARS = 12000

DIFF_REVIEW_PROMPT = {
    "en": (
        "You are a senior code reviewer. Review this git diff carefully.\n\n"
        "For each change note:\n"
        "- Bugs, logic errors, or regressions\n"
        "- Security issues\n"
        "- Style or naming problems\n"
        "- What looks correct\n\n"
        "Be concise. Reference file paths and line numbers.\n\n"
        "```diff\n{diff}\n```"
    ),
    "ru": (
        "Ты — опытный ревьюер кода. Внимательно проверь этот git diff.\n\n"
        "Для каждого изменения укажи:\n"
        "- Баги, логические ошибки, регрессии\n"
        "- Проблемы безопасности\n"
        "- Стиль и именование\n"
        "- Что сделано правильно\n\n"
        "Будь конкретным. Указывай путь к файлу и номера строк.\n\n"
        "```diff\n{diff}\n```"
    ),
}


def get_git_diff(args: str = "") -> tuple:
    """Returns (diff_text, error_msg). One of them will be empty."""
    args = args.strip()
    cmd = ["git", "diff"] + (args.split() if args else ["HEAD"])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", cwd=os.getcwd())
        if r.returncode != 0:
            if not args:
                # fallback for fresh repos with no commits yet
                r2 = subprocess.run(
                    ["git", "diff"], capture_output=True, text=True, encoding="utf-8", cwd=os.getcwd()
                )
                if r2.stdout.strip():
                    return r2.stdout, ""
            return "", r.stderr.strip() or "git diff failed"
        return r.stdout, ""
    except FileNotFoundError:
        return "", "git not found"
    except Exception as e:
        return "", str(e)


def diff_stats(diff_text: str) -> str:
    files, added, removed = set(), 0, 0
    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            files.add(line[6:])
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return f"{len(files)} file(s)  +{added} −{removed}"


def render_diff_syntax(diff_text: str) -> Syntax:
    return Syntax(
        diff_text[:MAX_DIFF_CHARS],
        "diff",
        theme="monokai",
        line_numbers=False,
        word_wrap=False,
    )


def build_review_prompt(diff_text: str, lang: str = "en") -> str:
    tmpl = DIFF_REVIEW_PROMPT.get(lang, DIFF_REVIEW_PROMPT["en"])
    truncated = diff_text[:MAX_DIFF_CHARS]
    if len(diff_text) > MAX_DIFF_CHARS:
        truncated += f"\n\n[diff truncated at {MAX_DIFF_CHARS} chars]"
    return tmpl.format(diff=truncated)


def make_diff_panel(diff_text: str, stats: str) -> Panel:
    return Panel(
        render_diff_syntax(diff_text),
        title=f"[bold]git diff[/bold]  [dim]{stats}[/dim]",
        border_style="blue",
    )
