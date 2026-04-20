#!/usr/bin/env python3
import os
os.environ["JUZZY_CWD"] = os.getcwd()

import argparse
import sys
from core.client import AIClient
from core.history import list_sessions
from core.profile import is_registered, load_profile, run_registration, get_ollama_models
from core.config import select_config, PROVIDERS, GROQ_MODELS, OPENROUTER_MODELS, HF_MODELS
from core.project import index_project, get_project_summary
from utils.display import print_header, print_error, print_info, print_sessions, Preloader

from commands.chat import run_chat
from commands.analyze import run_analyze
from commands.generate import run_generate
from commands.refactor import run_refactor
from commands.onecommand import run_onecommand, DEFAULT_ITERATIONS

VERSION = "2.0.0"

STRINGS = {
    "en": {
        "needs_key":        "Provider {} requires an API key: --key YOUR_KEY",
        "hello":            "Hey, {}! Provider: {} | Model: {}",
        "project_loaded":   "📁 Project loaded: {}",
        "project_error":    "Project error: {}",
        "unknown_model":    "Unknown model '{}' for provider '{}'. Available: {}",
        "no_model":         "Provider 'ollama' requires --model. Available: {}",
        "ollama_unavailable": "Ollama is not running or has no models loaded.",
    },
    "ru": {
        "needs_key":        "Для {} нужен API ключ: --key YOUR_KEY",
        "hello":            "Привет, {}! Провайдер: {} | Модель: {}",
        "project_loaded":   "📁 Проект загружен: {}",
        "project_error":    "Ошибка проекта: {}",
        "unknown_model":    "Неизвестная модель '{}' для провайдера '{}'. Доступные: {}",
        "no_model":         "Для провайдера 'ollama' нужен --model. Доступные: {}",
        "ollama_unavailable": "Ollama не запущен или нет загруженных моделей.",
    }
}

KNOWN_MODELS = {
    "groq":        {m for m, _ in GROQ_MODELS},
    "openrouter":  {m for m, _ in OPENROUTER_MODELS},
    "huggingface": {m for m, _ in HF_MODELS},
}


def _validate_model(provider, model, s):
    if provider == "ollama":
        available = get_ollama_models()
        if not available:
            raise ValueError(s["ollama_unavailable"])
        if not model:
            raise ValueError(s["no_model"].format(", ".join(available)))
        if model not in available:
            raise ValueError(s["unknown_model"].format(model, provider, ", ".join(available)))
    elif provider in KNOWN_MODELS and model:
        if model not in KNOWN_MODELS[provider]:
            print_info(f"⚠ Model '{model}' not in known list for {provider}, proceeding anyway.")


def cmd_chat(args, client, profile, project_context, lang):
    run_chat(client, session_id=args.session, profile=profile, project_context=project_context)

def cmd_analyze(args, client, profile, project_context, lang):
    run_analyze(client, file_path=args.file, lang=lang)

def cmd_generate(args, client, profile, project_context, lang):
    run_generate(client, lang=lang)

def cmd_refactor(args, client, profile, project_context, lang):
    run_refactor(client, file_path=args.file, lang=lang)

def cmd_history(args, client, profile, project_context, lang):
    print_sessions(list_sessions())

def cmd_onecommand(args, client, profile, project_context, lang):
    s = STRINGS.get(lang, STRINGS["en"])
    try:
        prompt = input("\n\033[35mDescribe your task →\033[0m ").strip()
    except (KeyboardInterrupt, EOFError):
        return
    if not prompt:
        print_error("Task description is empty")
        return
    iterations = DEFAULT_ITERATIONS
    try:
        raw = input(f"\033[90mIterations per agent (default {DEFAULT_ITERATIONS}, max 5) →\033[0m ").strip()
        if raw:
            iterations = max(1, min(5, int(raw)))
    except (ValueError, KeyboardInterrupt, EOFError):
        pass
    run_onecommand(client, prompt, iterations=iterations, lang=lang, s=s)


COMMANDS = {
    "chat":       cmd_chat,
    "analyze":    cmd_analyze,
    "generate":   cmd_generate,
    "refactor":   cmd_refactor,
    "history":    cmd_history,
    "onecommand": cmd_onecommand,
}


def main():
    parser = argparse.ArgumentParser(prog="juzzyai", description="JuzzyAI - Terminal AI Assistant")
    parser.add_argument("--version", "-v", action="version", version=f"JuzzyAI v{VERSION}")
    parser.add_argument("command", nargs="?", choices=list(COMMANDS.keys()), default="chat")
    parser.add_argument("--provider", "-p", default=None, choices=PROVIDERS.keys())
    parser.add_argument("--model",    "-m", default=None)
    parser.add_argument("--key",      "-k", default=None)
    parser.add_argument("--file",     "-f", default=None)
    parser.add_argument("--session",  "-s", default=None)
    parser.add_argument("--project",  default=None)
    args = parser.parse_args()

    print_header()

    # ─── Profile ─────────────────────────────────────────────────────────────
    if not is_registered():
        profile = run_registration()
    else:
        with Preloader(total_steps=2) as p:
            p.step("Loading profile...")
            p.step("Initializing...")
            profile = load_profile()

    lang = profile.get("lang", "en")
    s    = STRINGS.get(lang, STRINGS["en"])

    # ─── Provider / Model ────────────────────────────────────────────────────
    try:
        if any([args.provider, args.model, args.key]):
            provider = args.provider or "ollama"
            model    = args.model or PROVIDERS.get(provider, {}).get("default_model")
            api_key  = args.key
            if PROVIDERS.get(provider, {}).get("needs_key") and not api_key:
                raise ValueError(s["needs_key"].format(provider))
        else:
            config   = select_config(lang, get_ollama_models)
            provider = config["provider"]
            model    = config["model"]
            api_key  = config.get("api_key")

        _validate_model(provider, model, s)

    except ValueError as e:
        print_error(str(e))
        sys.exit(1)

    # ─── Client ──────────────────────────────────────────────────────────────
    client = AIClient(provider=provider, model=model, api_key=api_key)

    if args.command != "history":
        print_info(s["hello"].format(profile["name"], provider, model))

    # ─── Project context ─────────────────────────────────────────────────────
    project_context = ""
    if args.project:
        try:
            summary = get_project_summary(args.project)
            project_context = index_project(args.project)
            print_info(s["project_loaded"].format(summary))
        except Exception as e:
            print_error(s["project_error"].format(e))

    # ─── Execute ─────────────────────────────────────────────────────────────
    COMMANDS[args.command](args, client, profile, project_context, lang)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[!] Interrupted. Bye!")
        sys.exit(0)