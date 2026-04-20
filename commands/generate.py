from core.client import AIClient
from utils.display import print_response, print_error, print_info

def run_generate(client: AIClient):
    print_info("Опиши что нужно написать:")
    
    try:
        description = input("\n\033[35mОписание:\033[0m ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if not description:
        print_error("Описание пустое")
        return

    print_info("На каком языке? (python, javascript, go и т.д.) — Enter для пропуска:")
    try:
        language = input("\033[35mЯзык:\033[0m ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    prompt = f"Напиши код по описанию: {description}"
    if language:
        prompt += f"\nЯзык: {language}"
    prompt += "\nДай только код с краткими комментариями."

    messages = [{"role": "user", "content": prompt}]

    try:
        response = client.send(messages)
        print_response(response)
    except Exception as e:
        print_error(str(e))