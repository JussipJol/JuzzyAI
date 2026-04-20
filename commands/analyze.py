from core.client import AIClient
from utils.display import print_response, print_error, print_info
import os

STRINGS = {
    "en": {
        "file_not_found": "File not found: {}",
        "analyzing_file": "Analyzing file: {}",
        "paste_code": "Paste code and press Enter twice:",
        "code_empty": "Code is empty",
        "prompt": "Analyze this code. Find bugs, performance issues, best practice violations. Be specific:\n\n```\n{}\n```",
    },
    "ru": {
        "file_not_found": "Файл не найден: {}",
        "analyzing_file": "Анализирую файл: {}",
        "paste_code": "Вставь код и нажми Enter дважды:",
        "code_empty": "Код пустой",
        "prompt": "Проанализируй этот код. Найди баги, проблемы с производительностью, нарушения best practices. Будь конкретен:\n\n```\n{}\n```",
    },
}


def run_analyze(client: AIClient, file_path: str = None, lang: str = "en"):
    s = STRINGS.get(lang, STRINGS["en"])

    if file_path:
        if not os.path.exists(file_path):
            print_error(s["file_not_found"].format(file_path))
            return
        with open(file_path, "r", encoding="utf-8") as f:
            code = f.read()
        print_info(s["analyzing_file"].format(file_path))
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

    messages = [{"role": "user", "content": s["prompt"].format(code)}]

    try:
        response = client.send(messages)
        print_response(response)
    except Exception as e:
        print_error(str(e))