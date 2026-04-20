import json
import os

JUZZYAI_DIR = os.path.expanduser("~/.juzzyai")
PROFILE_FILE = os.path.join(JUZZYAI_DIR, "profile.json")

STRINGS = {
    "en": {
        "welcome": "👋 Welcome to JuzzyAI! Let's get acquainted.",
        "ask_name": "What should I call you? → ",
        "default_name": "friend",
        "ask_goal": "\nHow will you use JuzzyAI?",
        "goals": ["Personal projects", "Work / freelance", "Learning", "Other"],
        "goal_map": {"1": "personal projects", "2": "work/freelance", "3": "learning", "4": "other"},
        "ask_usage": "\nYou are using JuzzyAI:",
        "usages": ["Solo (individually)", "In a team / organization"],
        "usage_map": {"1": "solo", "2": "organization"},
        "ask_source": "\nHow did you hear about JuzzyAI?",
        "sources": ["GitHub", "Friend / colleague", "Social media", "Other"],
        "source_map": {"1": "GitHub", "2": "friend/colleague", "3": "social media", "4": "other"},
        "choose_14": "Choose (1-4) → ",
        "choose_12": "Choose (1-2) → ",
        "done": "✅ All set, {}! Enjoy coding.",
        "default_other": "other",
    },
    "ru": {
        "welcome": "👋 Добро пожаловать в JuzzyAI! Давай познакомимся.",
        "ask_name": "Как к тебе обращаться? → ",
        "default_name": "друг",
        "ask_goal": "\nС какой целью будешь использовать JuzzyAI?",
        "goals": ["Личные проекты", "Работа / фриланс", "Обучение", "Другое"],
        "goal_map": {"1": "личные проекты", "2": "работа/фриланс", "3": "обучение", "4": "другое"},
        "ask_usage": "\nТы используешь JuzzyAI:",
        "usages": ["Один (индивидуально)", "В команде / организации"],
        "usage_map": {"1": "индивидуально", "2": "организация"},
        "ask_source": "\nОткуда узнал о JuzzyAI?",
        "sources": ["GitHub", "От друга / коллеги", "Соцсети", "Другое"],
        "source_map": {"1": "GitHub", "2": "от друга/коллеги", "3": "соцсети", "4": "другое"},
        "choose_14": "Выбери (1-4) → ",
        "choose_12": "Выбери (1-2) → ",
        "done": "✅ Готово, {}! Приятной работы.",
        "default_other": "другое",
    }
}

def get_ollama_models() -> list:
    import urllib.request #сомнительное решение импортировать в функции
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags") as r:
            data = json.loads(r.read())
            return [m["name"] for m in data.get("models", [])]
    except:
        return []

def is_registered() -> bool:
    return os.path.exists(PROFILE_FILE)

def load_profile() -> dict:
    with open(PROFILE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_profile(profile: dict):
    os.makedirs(JUZZYAI_DIR, exist_ok=True)
    with open(PROFILE_FILE, "w", encoding="utf-8") as f:
        json.dump(profile, f, ensure_ascii=False, indent=2)

def run_registration():
    print("\n\033[36mSelect language / Выберите язык:\033[0m")
    print("  1. English (default)")
    print("  2. Русский")
    lang_choice = input("→ ").strip()
    lang = "ru" if lang_choice == "2" else "en"
    s = STRINGS[lang]

    print(f"\n\033[36m{s['welcome']}\033[0m\n")

    name = input(s["ask_name"]).strip() or s["default_name"]

    print(s["ask_goal"])
    for i, g in enumerate(s["goals"], 1):
        print(f"  {i}. {g}")
    goal = s["goal_map"].get(input(s["choose_14"]).strip(), s["default_other"])

    print(s["ask_usage"])
    for i, u in enumerate(s["usages"], 1):
        print(f"  {i}. {u}")
    usage = s["usage_map"].get(input(s["choose_12"]).strip(), "solo")

    print(s["ask_source"])
    for i, src in enumerate(s["sources"], 1):
        print(f"  {i}. {src}")
    source = s["source_map"].get(input(s["choose_14"]).strip(), s["default_other"])

    profile = {"name": name, "goal": goal, "usage": usage, "source": source, "lang": lang}
    save_profile(profile)

    print(f"\n\033[32m{s['done'].format(name)}\033[0m\n")
    return profile