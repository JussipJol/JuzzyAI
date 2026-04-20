import os

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".cpp", ".h",
    ".cs", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".md", ".json",
    ".yaml", ".yml", ".toml", ".env", ".sh", ".bat", ".sql", ".html", ".css"
}

IGNORE_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "env",
    "dist", "build", ".next", ".nuxt", "target", "bin", "obj",
    ".idea", ".vscode", "coverage", ".pytest_cache"
}

MAX_FILE_SIZE  = 5 * 1024   # 5KB per file
MAX_TOTAL_SIZE = 8 * 1024   # 8KB total context
MAX_FILES      = 200        # #20 не загружать миллион файлов

# #5 паттерны prompt injection
_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "ignore above",
    "disregard your",
    "you are now",
    "act as",
    "jailbreak",
    "system prompt",
    "forget everything",
]

def _sanitize_content(content: str) -> str:
    """#5 удаляем строки с prompt injection из файлов проекта."""
    lines = content.splitlines()
    clean = []
    for line in lines:
        low = line.lower()
        if any(p in low for p in _INJECTION_PATTERNS):
            clean.append("# [line removed: potential prompt injection]")
        else:
            clean.append(line)
    return "\n".join(clean)


def index_project(path: str) -> str:
    """Read project files and return as context string."""
    # #17 нормализуем путь с поддержкой Unicode
    path = os.path.abspath(os.fsdecode(os.fsencode(path)))
    if not os.path.exists(path):
        raise ValueError(f"Path not found: {path}")

    files = []
    total_size = 0
    file_count = 0

    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for filename in sorted(filenames):
            if file_count >= MAX_FILES:  # #20 лимит файлов
                files.append("# [...]\n[truncated — file limit reached]")
                return "PROJECT FILES:\n\n" + "\n\n".join(files)

            ext = os.path.splitext(filename)[1].lower()
            if ext not in SUPPORTED_EXTENSIONS:
                continue

            filepath = os.path.join(root, filename)
            # #17 безопасное получение относительного пути
            try:
                relpath = os.path.relpath(filepath, path)
            except ValueError:
                continue

            try:
                size = os.path.getsize(filepath)
                if size > MAX_FILE_SIZE:
                    continue
                if total_size + size > MAX_TOTAL_SIZE:
                    files.append(f"# {relpath}\n[truncated — context limit reached]")
                    break

                with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read().strip()

                if content:
                    content = _sanitize_content(content)  # #5
                    files.append(f"# {relpath}\n```\n{content}\n```")
                    total_size += size
                    file_count += 1
            except Exception:
                continue

    if not files:
        return ""

    return "PROJECT FILES:\n\n" + "\n\n".join(files)


def get_project_summary(path: str) -> str:
    """Return short summary of what was indexed."""
    # #17 Unicode path fix
    path = os.path.abspath(os.fsdecode(os.fsencode(path)))
    count = 0
    total_size = 0
    for root, dirs, filenames in os.walk(path):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext in SUPPORTED_EXTENSIONS:
                filepath = os.path.join(root, filename)
                try:
                    size = os.path.getsize(filepath)
                    if size <= MAX_FILE_SIZE:
                        count += 1
                        total_size += size
                except Exception:
                    continue
    return f"{count} files, {total_size // 1024}KB"