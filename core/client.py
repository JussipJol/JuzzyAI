import urllib.request
import urllib.error
import json
import socket
import time

TIMEOUT = 60
MAX_RETRIES = 3
RETRY_DELAY = 2

OPENROUTER_FALLBACKS = [
    "meta-llama/llama-3.3-70b-instruct:free",
    "mistralai/mistral-small-3.1-24b-instruct:free",
    "google/gemma-3-27b-it:free",
    "openrouter/free",
]


class RateLimitError(RuntimeError):
    """Raised when a provider returns 429 after all retries."""


def _request_with_retry(make_req_fn, provider, max_retries=MAX_RETRIES):
    for attempt in range(max_retries):
        try:
            return make_req_fn()
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8")
            if e.code == 401:
                raise RuntimeError(
                    f"{provider} API key is invalid or expired. "
                    f"Run the app again and enter a new key."
                )
            if e.code == 403:
                raise RuntimeError(
                    f"{provider} API key does not have permission. "
                    f"Check your plan or generate a new key."
                )
            if e.code == 429:
                wait = RETRY_DELAY * (2 ** attempt)   # 2, 4, 8, 16…
                print(f"\n\033[33m⚠ Rate limit ({provider}), retrying in {wait}s...\033[0m")
                time.sleep(wait)
                continue
            if e.code >= 500 and attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(f"{provider} API error {e.code}: {body}")
        except (socket.timeout, urllib.error.URLError) as e:
            if attempt < max_retries - 1:
                print(f"\n\033[33m⚠ Network error, retrying ({attempt+1}/{max_retries})...\033[0m")
                time.sleep(RETRY_DELAY)
                continue
            raise RuntimeError(f"{provider} network error: {e}")
    raise RateLimitError(f"{provider} rate-limited after {max_retries} retries")


class AIClient:
    def __init__(self, provider: str, model: str, api_key: str = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key

    def send(self, messages: list, system_prompt: str = "") -> str:
        if self.provider == "ollama":
            return self._call_ollama(messages, system_prompt)
        elif self.provider == "groq":
            return self._call_groq(messages, system_prompt)
        elif self.provider == "gemini":
            return self._call_gemini(messages, system_prompt)
        elif self.provider == "huggingface":
            return self._call_huggingface(messages, system_prompt)
        elif self.provider == "openrouter":
            return self._call_openrouter(messages, system_prompt)
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def stream_tokens(self, messages: list, system_prompt: str = "", on_token=None) -> tuple:
        """Единая точка стриминга. Возвращает (full_text, prompt_tokens, generated_tokens).
        on_token(str) — колбэк на каждый токен.
        Если on_token=None — токены печатаются через print (классический режим).
        В TUI передаём колбэк который пишет токены прямо в RichLog."""
        if self.provider == "ollama":
            return self._stream_tokens_ollama(messages, system_prompt, on_token)
        elif self.provider in ("groq", "openrouter"):
            return self._stream_tokens_openai_compat(messages, system_prompt, on_token)
        else:
            # gemini, huggingface — нет стриминга, эмулируем
            try:
                response = self.send(messages, system_prompt)
                if on_token:
                    on_token(response)
                else:
                    print(response, end="", flush=True)
                return response, 0, 0
            except KeyboardInterrupt:
                print()
                return "", 0, 0

    def _stream_tokens_ollama(self, messages, system_prompt="", on_token=None):
        msgs = self._build_msgs(messages, system_prompt)
        payload = json.dumps({"model": self.model, "messages": msgs, "stream": True}).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        tokens = []
        prompt_tokens, generated_tokens = 0, 0
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                for line in r:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        tokens.append(token)
                        if on_token:
                            on_token(token)
                        else:
                            print(token, end="", flush=True)
                    if chunk.get("done"):
                        prompt_tokens = chunk.get("prompt_eval_count", 0)
                        generated_tokens = chunk.get("eval_count", 0)
                        break
        except KeyboardInterrupt:
            print()
            return "".join(tokens), 0, 0
        except socket.timeout:
            raise RuntimeError("Ollama request timed out after 60s")
        return "".join(tokens), prompt_tokens, generated_tokens

    def _stream_tokens_openai_compat(self, messages, system_prompt="", on_token=None):
        msgs = self._build_msgs(messages, system_prompt)
        url = (
            "https://api.groq.com/openai/v1/chat/completions"
            if self.provider == "groq"
            else "https://openrouter.ai/api/v1/chat/completions"
        )

        models_to_try = [self.model]
        if self.provider == "openrouter":
            models_to_try += [m for m in OPENROUTER_FALLBACKS if m != self.model]

        tokens = []
        last_error = None

        for model in models_to_try:
            tokens = []
            try:
                payload = json.dumps({"model": model, "messages": msgs, "stream": True}).encode()
                req = urllib.request.Request(url, data=payload, headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent": "Mozilla/5.0",
                })
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    for line in r:
                        line = line.decode("utf-8").strip()
                        if not line or line == "data: [DONE]":
                            continue
                        if line.startswith("data: "):
                            chunk = json.loads(line[6:])
                            choices = chunk.get("choices", [])
                            token = choices[0].get("delta", {}).get("content", "") if choices else ""
                            if token:
                                tokens.append(token)
                                if on_token:
                                    on_token(token)
                                else:
                                    print(token, end="", flush=True)
                return "".join(tokens), 0, 0
            except KeyboardInterrupt:
                print()
                return "".join(tokens), 0, 0
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8")
                if e.code == 429 and self.provider == "openrouter" and model != models_to_try[-1]:
                    print(f"\n\033[33m⚠ {model} rate limited, trying fallback...\033[0m")
                    continue
                last_error = RuntimeError(f"{self.provider} API error {e.code}: {body}")

        raise last_error

    def stream(self, messages: list, system_prompt: str = "") -> None:
        """Обратная совместимость."""
        self.stream_tokens(messages, system_prompt)

    def _build_msgs(self, messages, system_prompt):
        msgs = []
        if system_prompt:
            msgs.append({"role": "system", "content": system_prompt})
        msgs.extend(messages)
        return msgs

    def _call_ollama(self, messages, system_prompt=""):
        msgs = self._build_msgs(messages, system_prompt)
        payload = json.dumps({"model": self.model, "messages": msgs, "stream": False}).encode()

        def do_request():
            req = urllib.request.Request(
                "http://localhost:11434/api/chat",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read())["message"]["content"]

        return _request_with_retry(do_request, "ollama")

    def _call_openai_compat(self, messages, system_prompt, url):
        msgs = self._build_msgs(messages, system_prompt)
        payload = json.dumps({"model": self.model, "messages": msgs}).encode()

        def do_request():
            req = urllib.request.Request(url, data=payload, headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "Mozilla/5.0",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read())["choices"][0]["message"]["content"]

        return _request_with_retry(do_request, self.provider)

    def _call_groq(self, messages, system_prompt=""):
        return self._call_openai_compat(
            messages, system_prompt,
            "https://api.groq.com/openai/v1/chat/completions",
        )

    def _call_openrouter(self, messages, system_prompt=""):
        url  = "https://openrouter.ai/api/v1/chat/completions"
        msgs = self._build_msgs(messages, system_prompt)
        models = [self.model] + [m for m in OPENROUTER_FALLBACKS if m != self.model]

        last_err: Exception = RuntimeError("openrouter: no models available")
        for model in models:
            payload = json.dumps({"model": model, "messages": msgs}).encode()

            def do_request(p=payload):
                req = urllib.request.Request(url, data=p, headers={
                    "Content-Type":  "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                    "User-Agent":    "Mozilla/5.0",
                })
                with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                    return json.loads(r.read())["choices"][0]["message"]["content"]

            try:
                return _request_with_retry(do_request, f"openrouter/{model}", max_retries=2)
            except RateLimitError as e:
                last_err = e
                print(f"\n\033[33m⚠ {model} rate-limited, trying next model...\033[0m")
                time.sleep(3)
                continue
            except RuntimeError:
                raise   # auth errors, API errors — don't mask

        raise RuntimeError(
            f"All OpenRouter models rate-limited. Try again in a minute.\n"
            f"Tip: switch to Groq or Ollama for heavy tasks like /onecommand."
        )

    def _call_gemini(self, messages, system_prompt=""):
        contents = []
        for m in messages:
            role = "model" if m["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        payload = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        data = json.dumps(payload).encode()
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        def do_request():
            req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]

        return _request_with_retry(do_request, "gemini")

    def _call_huggingface(self, messages, system_prompt=""):
        prompt = messages[-1]["content"]
        if system_prompt:
            prompt = f"{system_prompt}\n\n{prompt}"
        payload = json.dumps({"inputs": prompt, "parameters": {"max_new_tokens": 512}}).encode()
        url = f"https://router.huggingface.co//{self.model}" # ПРОБЛЕМА. прошлый путь давал 410, сейчас дает 404. нужно чекнуть новую документацию, видимо тело запроса поменялось
        

        def do_request():
            req = urllib.request.Request(url, data=payload, headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                result = json.loads(r.read())
                return result[0]["generated_text"]

        return _request_with_retry(do_request, "huggingface")