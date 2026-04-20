import json
import os
import hashlib
import base64

JUZZYAI_DIR = os.path.expanduser("~/.juzzyai")
CONFIG_FILE = os.path.join(JUZZYAI_DIR, "config.json")

# ------------------------------------------------------------------ #
# #4 Шифрование API ключей через Fernet (симметричное AES-128-CBC).   #
# Ключ шифрования деривируется из machine ID — уникален для машины,  #
# не требует пароля от пользователя. Без cryptography — fallback на  #
# base64 (обфускация) с предупреждением.                             #
# ------------------------------------------------------------------ #

def _get_machine_id() -> str:
    candidates = [
        "/etc/machine-id",
        "/var/lib/dbus/machine-id",
    ]
    for path in candidates:
        try:
            with open(path) as f:
                mid = f.read().strip()
                if mid:
                    return mid
        except OSError:
            pass
    import socket
    return f"{socket.gethostname()}:{os.environ.get('USERNAME') or os.environ.get('USER', 'user')}"


def _derive_fernet_key() -> bytes:
    raw = _get_machine_id().encode()
    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


def _encrypt_key(api_key: str) -> str:
    if not api_key:
        return ""
    try:
        from cryptography.fernet import Fernet
        f = Fernet(_derive_fernet_key())
        return "enc:" + f.encrypt(api_key.encode()).decode()
    except ImportError:
        print("\033[33m⚠ Install 'cryptography' for proper key encryption: pip install cryptography\033[0m")
        return "b64:" + base64.urlsafe_b64encode(api_key.encode()).decode()


def _decrypt_key(stored: str) -> str:
    if not stored:
        return ""
    if stored.startswith("enc:"):
        try:
            from cryptography.fernet import Fernet
            f = Fernet(_derive_fernet_key())
            return f.decrypt(stored[4:].encode()).decode()
        except Exception:
            return ""
    if stored.startswith("b64:"):
        try:
            return base64.urlsafe_b64decode(stored[4:].encode()).decode()
        except Exception:
            return ""
    return stored  # старый формат — открытый текст

PROVIDERS = {
    "ollama":      {"default_model": None,                        "needs_key": False},
    "groq":        {"default_model": "llama-3.1-8b-instant",      "needs_key": True},
    "openrouter":  {"default_model": "mistralai/codestral-2501",  "needs_key": True},
    "gemini":      {"default_model": "gemini-2.0-flash-lite",     "needs_key": True},
    "huggingface": {"default_model": "bigcode/starcoder2-15b",    "needs_key": True},
}

HF_MODELS = [
    ("bigcode/starcoder2-15b",              "StarCoder2 15B — best for code generation"),
    ("bigcode/starcoder2-7b",               "StarCoder2 7B — lighter, faster"),
    ("Qwen/Qwen2.5-Coder-7B-Instruct",      "Qwen2.5 Coder 7B — strong multilingual coder"),
    ("Qwen/Qwen2.5-Coder-1.5B-Instruct",    "Qwen2.5 Coder 1.5B — very fast"),
    ("deepseek-ai/deepseek-coder-6.7b-instruct", "DeepSeek Coder 6.7B — 338 languages"),
    ("deepseek-ai/deepseek-coder-1.3b-instruct", "DeepSeek Coder 1.3B — ultra fast"),
    ("codellama/CodeLlama-7b-hf",           "Code Llama 7B — Meta's code model"),
    ("ise-uiuc/Magicoder-S-DS-6.7B",        "Magicoder-S — beats ChatGPT on HumanEval"),
    ("THUDM/codegeex4-all-9b",              "CodeGeeX4 9B — multilingual code generation"),
    ("facebook/incoder-6B",                 "InCoder 6B — code infilling specialist"),
]

GROQ_MODELS = [
    # Production — стабильные, рекомендуемые
    ("llama-3.1-8b-instant",        "Llama 3.1 8B — 560 t/s, fast ⭐"),
    ("llama-3.3-70b-versatile",     "Llama 3.3 70B — 280 t/s, powerful"),
    ("openai/gpt-oss-120b",         "GPT OSS 120B — 500 t/s, reasoning"),
    ("openai/gpt-oss-20b",          "GPT OSS 20B — 1000 t/s, fastest"),
    # Preview — могут быть отключены
    ("qwen/qwen3-32b",              "Qwen3 32B — 400 t/s, reasoning"),
    ("moonshotai/kimi-k2-instruct-0905", "Kimi K2 — 200 t/s, 262K context"),
    ("meta-llama/llama-4-scout-17b-16e-instruct", "Llama 4 Scout 17B — vision"),
]

OPENROUTER_MODELS = [
    ("qwen/qwen3-coder:free",                               "Qwen3 Coder — best for code ⭐ 262K"),
    ("nvidia/nemotron-3-super-120b-a12b:free",              "Nemotron Super 120B — NVIDIA 262K"),
    ("qwen/qwen3-next-80b-a3b-instruct:free",               "Qwen3 Next 80B — Alibaba 262K"),
    ("openai/gpt-oss-120b:free",                            "GPT OSS 120B — OpenAI 131K"),
    ("openai/gpt-oss-20b:free",                             "GPT OSS 20B — OpenAI 131K"),
    ("meta-llama/llama-3.3-70b-instruct:free",              "Llama 3.3 70B — Meta 128K"),
    ("mistralai/mistral-small-3.1-24b-instruct:free",       "Mistral Small 3.1 24B — 128K"),
    ("nousresearch/hermes-3-llama-3.1-405b:free",           "Hermes 3 Llama 405B — 131K"),
    ("arcee-ai/trinity-large-preview:free",                 "Trinity Large — Arcee AI 131K"),
    ("nvidia/nemotron-3-nano-30b-a3b:free",                 "Nemotron Nano 30B — NVIDIA 256K"),
    ("nvidia/nemotron-nano-12b-v2-vl:free",                 "Nemotron Nano 12B VL — Vision 128K"),
    ("google/gemma-3-27b-it:free",                          "Gemma 3 27B — Google Vision 131K"),
    ("z-ai/glm-4.5-air:free",                               "GLM-4.5 Air — Zhipu AI 131K"),
    ("stepfun/step-3.5-flash:free",                         "Step 3.5 Flash — StepFun 256K"),
    ("arcee-ai/trinity-mini:free",                          "Trinity Mini — Arcee AI 131K"),
    ("meta-llama/llama-3.2-3b-instruct:free",               "Llama 3.2 3B — Meta fast 131K"),
    ("cognitivecomputations/dolphin-mistral-24b-venice-edition:free", "Dolphin Mistral 24B 33K"),
    ("google/gemma-3-12b-it:free",                          "Gemma 3 12B — Google Vision 33K"),
    ("openrouter/free",                                     "Auto — best available free model"),
]

def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)
    if config.get("api_key"):
        config["api_key"] = _decrypt_key(config["api_key"])  # #4 расшифровываем при чтении
    return config

def save_config(config: dict):
    os.makedirs(JUZZYAI_DIR, exist_ok=True)
    to_save = dict(config)
    if to_save.get("api_key"):
        to_save["api_key"] = _encrypt_key(to_save["api_key"])  # #4 шифруем при записи
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(to_save, f, ensure_ascii=False, indent=2)

def _choose_model(models, choose_model_prompt, default_model_msg):
    for i, (m, desc) in enumerate(models, 1):
        name = m.split("/")[-1]
        print(f"  {i}. {name:<40} {desc}")
    m_choice = input(choose_model_prompt).strip()
    try:
        return models[int(m_choice) - 1][0]
    except:
        model = models[0][0]
        print(f"\033[33m→ {default_model_msg.format(model)}\033[0m")
        return model

def select_config(lang: str, get_ollama_models_fn) -> dict:
    config = load_config()

    if lang == "ru":
        use_saved     = "Использовать сохранённый конфиг"
        change        = "Изменить"
        choose_provider = "Выбери провайдера:"
        choose_model  = "\nВыбери модель (номер) → "
        available_models = "Доступные модели:"
        ask_key       = "Введи API ключ → "
        saved_label   = "Сохранить как конфиг по умолчанию? (y/n) → "
        no_ollama     = "Ollama не запущен или моделей нет"
        default_model_msg = "Выбрана по умолчанию: {}"
        or_hint       = "  Получи бесплатный ключ: https://openrouter.ai/keys"
    else:
        use_saved     = "Use saved config"
        change        = "Change"
        choose_provider = "Choose provider:"
        choose_model  = "\nChoose model (number) → "
        available_models = "Available models:"
        ask_key       = "Enter API key → "
        saved_label   = "Save as default config? (y/n) → "
        no_ollama     = "Ollama is not running or no models found"
        default_model_msg = "Default model selected: {}"
        or_hint       = "  Get a free key: https://openrouter.ai/keys"

    if config.get("provider"):
        print(f"\n\033[36m[1] {use_saved}: {config['provider']} / {config.get('model', '?')}")
        print(f"[2] {change}\033[0m")
        choice = input("→ ").strip()
        if choice != "2":
            return config

    providers = list(PROVIDERS.keys())
    print(f"\n\033[36m{choose_provider}\033[0m")
    for i, p in enumerate(providers, 1):
        print(f"  {i}. {p}")
    p_choice = input("→ ").strip()
    try:
        provider = providers[int(p_choice) - 1]
    except:
        provider = "ollama"

    api_key = None

    if provider == "ollama":
        models = get_ollama_models_fn()
        if not models:
            print(f"\033[31m{no_ollama}\033[0m")
            exit(1)
        print(f"\n\033[36m{available_models}\033[0m")
        for i, m in enumerate(models, 1):
            print(f"  {i}. {m}")
        m_choice = input(choose_model).strip()
        try:
            model = models[int(m_choice) - 1]
        except:
            model = models[0]
            print(f"\033[33m→ {default_model_msg.format(model)}\033[0m")

    elif provider == "openrouter":
        print(f"\033[90m{or_hint}\033[0m")
        api_key = input(ask_key).strip()
        print(f"\n\033[36m{available_models}\033[0m")
        model = _choose_model(OPENROUTER_MODELS, choose_model, default_model_msg)

    elif provider == "groq":
        api_key = input(ask_key).strip()
        print(f"\n\033[36m{available_models}\033[0m")
        model = _choose_model(GROQ_MODELS, choose_model, default_model_msg)

    elif provider == "huggingface":
        api_key = input(ask_key).strip()
        print(f"\n\033[36m{available_models}\033[0m")
        model = _choose_model(HF_MODELS, choose_model, default_model_msg)

    else:
        model = PROVIDERS[provider]["default_model"]
        api_key = input(ask_key).strip()

    save = input(saved_label).strip().lower()
    new_config = {"provider": provider, "model": model, "api_key": api_key}
    if save == "y":
        save_config(new_config)

    return new_config