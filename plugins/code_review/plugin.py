"""
Пример плагина: /review <код или путь к файлу>
Отправляет код на быстрое ревью модели.
"""
import os

def run(client, message: str, context: dict) -> str:
    lang = context.get("lang", "en")

    # Если передан путь к файлу — читаем его
    if message and os.path.exists(message.strip()):
        with open(message.strip(), "r", encoding="utf-8") as f:
            code = f.read()
        source = message.strip()
    elif message:
        code = message
        source = "input"
    else:
        return "Usage: /review <code or file path>" if lang == "en" else "Использование: /review <код или путь к файлу>"

    if lang == "ru":
        prompt = f"Сделай быстрое code review. Найди проблемы, предложи улучшения. Будь краток:\n\n```\n{code}\n```"
    else:
        prompt = f"Do a quick code review. Find issues, suggest improvements. Be concise:\n\n```\n{code}\n```"

    messages = [{"role": "user", "content": prompt}]
    return client.send(messages)
