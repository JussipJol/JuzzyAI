from core.client import AIClient
from utils.display import print_response, print_error, print_info
import os

STRINGS = {
    "en": {
        "file_not_found": "File not found: {}",
        "refactoring_file": "Refactoring file: {}",
        "paste_code": "Paste code and press Enter twice:",
        "code_empty": "Code is empty",
        "ask_focus": "What to improve? (readability, performance, structure) — Enter for general refactor:",
        "focus_label": "\033[35mFocus:\033[0m ",
        "prompt": "Refactor this code",
        "prompt_focus": ", focus on: {}",
        "prompt_suffix": ". Show the improved code and briefly explain the changes:\n\n```\n{}\n```",
    },
    "ru": {
        "file_not_found": "Файл не найден: {}",
        "refactoring_file": "Рефакторинг файла: {}",
        "paste_code": "Вставь код и нажми Enter дважды:",
        "code_empty": "Код пустой",
        "ask_focus": "Что улучшить? (читаемость, производительность, структура) — Enter для общего рефакторинга:",
        "focus_label": "\033[35mФокус:\033[0m ",
        "prompt": "Сделай рефакторинг этого кода",
        "prompt_focus": ", фокус на: {}",
        "prompt_suffix": ". Покажи улучшенный код и кратко объясни изменения:\n\n```\n{}\n```",
    },
}


def run_refactor(client: AIClient, file_path: str = None, lang: str = "en"):
    s = STRINGS.get(lang, STRINGS["en"])

    if file_path:
        if not os.path.exists(file_path):
            print_error(s["file_not_found"].format(file_path))
            return
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        print_info(s["refactoring_file"].format(file_path))
    else:
        print_info(s["paste_code"])
        lines = []
        while True:
            try:
                line = input()
                if line == "" and lines and lines[-1] == "":
                    break
                lines.append(line)
            except (KeyboardInterrupt, EOFError):
                return
        code = "\n".join(lines)

    if not code.strip():
        print_error(s["code_empty"])
        return

    print_info(s["ask_focus"])
    try:
        focus = input(s["focus_label"]).strip()
    except (KeyboardInterrupt, EOFError):
        return

    prompt = s["prompt"]
    if focus:
        prompt += s["prompt_focus"].format(focus)
    prompt += s["prompt_suffix"].format(code)

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.send(messages)
        print_response(response)
    except Exception as e:
        print_error(str(e))