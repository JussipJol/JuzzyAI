"""
JuzzyAI Plugin Loader
─────────────────────
Плагины ищутся в двух местах (в порядке приоритета):
  1. ./plugins/           — рядом с exe/main.py (встроенные)
  2. ~/.juzzyai/plugins/  — папка пользователя (устанавливаемые)

Структура плагина:

  my_plugin/
    manifest.json   — метаданные
    plugin.py       — точка входа

manifest.json:
  {
    "name": "my_plugin",
    "version": "1.0.0",
    "description": "Что делает плагин",
    "command": "/myplugin",
    "entry": "plugin.py"
  }

plugin.py должен содержать функцию:
  def run(client, message, context) -> str
    client  — AIClient
    message — текст пользователя после команды
    context — dict: lang, profile, session_id, project_context
"""

import os
import json
import importlib.util
from typing import Callable

# Два места поиска плагинов
_EXE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PLUGINS_DIRS = [
    os.path.join(_EXE_DIR, "plugins"),          # рядом с exe/main.py
    os.path.expanduser("~/.juzzyai/plugins"),    # папка пользователя
]

REQUIRED_FIELDS = {"name", "version", "command", "entry"}


class Plugin:
    def __init__(self, manifest: dict, run_fn: Callable):
        self.name        = manifest["name"]
        self.version     = manifest["version"]
        self.description = manifest.get("description", "")
        self.command     = manifest["command"]
        self._run        = run_fn

    def run(self, client, message: str, context: dict) -> str:
        return self._run(client, message, context)

    def __repr__(self):
        return f"<Plugin {self.name} {self.version} -> {self.command}>"


def _load_plugin(plugin_dir: str):
    """Загружает один плагин из директории. Возвращает None при ошибке."""
    manifest_path = os.path.join(plugin_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return None

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"\033[33m Warning: Plugin manifest error in {plugin_dir}: {e}\033[0m")
        return None

    missing = REQUIRED_FIELDS - set(manifest.keys())
    if missing:
        print(f"\033[33m Warning: Plugin '{os.path.basename(plugin_dir)}' missing fields: {missing}\033[0m")
        return None

    if not manifest["command"].startswith("/"):
        print(f"\033[33m Warning: Plugin '{manifest['name']}' command must start with /\033[0m")
        return None

    entry_path = os.path.join(plugin_dir, manifest["entry"])
    if not os.path.exists(entry_path):
        print(f"\033[33m Warning: Plugin '{manifest['name']}' entry not found: {entry_path}\033[0m")
        return None

    try:
        spec = importlib.util.spec_from_file_location(manifest["name"], entry_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    except Exception as e:
        print(f"\033[33m Warning: Plugin '{manifest['name']}' load error: {e}\033[0m")
        return None

    if not hasattr(module, "run") or not callable(module.run):
        print(f"\033[33m Warning: Plugin '{manifest['name']}' missing run() function\033[0m")
        return None

    return Plugin(manifest, module.run)


def load_plugins() -> dict:
    """Загружает плагины из всех PLUGINS_DIRS. Возвращает dict {command: Plugin}.
    Встроенные плагины (./plugins/) имеют приоритет над пользовательскими."""
    plugins = {}

    for plugins_dir in PLUGINS_DIRS:
        if not os.path.exists(plugins_dir):
            continue

        for entry in sorted(os.listdir(plugins_dir)):
            plugin_dir = os.path.join(plugins_dir, entry)
            if not os.path.isdir(plugin_dir):
                continue

            plugin = _load_plugin(plugin_dir)
            if plugin is None:
                continue

            if plugin.command in plugins:
                # Встроенный уже зарегистрирован — пользовательский не перезаписывает
                continue

            plugins[plugin.command] = plugin

    return plugins


def get_plugin_help(plugins: dict) -> list:
    """Возвращает список (command, description) для /help."""
    return [(p.command, p.description or p.name) for p in plugins.values()]