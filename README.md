# JuzzyAI

AI-powered coding assistant in your terminal. Chat, analyze, generate and refactor code using free AI models — locally or in the cloud.

## Download

Download the latest version from the [Releases](https://github.com/Zhussup/juzzyai/releases) page.

## Features

- 💬 **Chat** — conversational coding assistant with session history
- 🔍 **Analyze** — find bugs, performance issues, bad practices
- ⚡ **Generate** — describe what you need, get production-ready code
- 🔧 **Refactor** — clean up and improve existing code
- 📡 **Streaming** — real-time responses with Markdown rendering
- 🌐 **Offline** — works fully offline with Ollama
- 📁 **File ops** — AI can create and edit files directly
- 🔑 **License** — protected with license key system

## Supported Providers

| Provider | Type | Cost |
|----------|------|------|
| Ollama | Local | Free |
| Groq | Cloud | Free |
| OpenRouter | Cloud | Free (28 models) |
| Gemini | Cloud | Free tier |
| HuggingFace | Cloud | Free tier |

## Usage
```bash
juzzyai                          # start chat
juzzyai analyze --file main.py   # analyze a file
juzzyai generate                 # generate code
juzzyai refactor --file main.py  # refactor a file
juzzyai history                  # view chat history
```

## Chat Commands

| Command | Description |
|---------|-------------|
| `/help` | Show all commands |
| `/new` | New session |
| `/sessions` | List sessions |
| `/copy` | Copy last response |
| `/clear` | Clear screen |
| `/reset` | Reset profile |
| `/exit` | Exit |

## License

Copyright (c) 2026 Zhussup. All rights reserved. See [LICENSE](LICENSE) for details.
