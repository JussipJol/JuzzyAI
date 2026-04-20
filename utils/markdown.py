from rich.console import Console
from rich.markdown import Markdown
from rich.theme import Theme

theme = Theme({
    "markdown.h1": "bold white",
    "markdown.h2": "bold white",
    "markdown.h3": "bold white",
    "markdown.h4": "bold white",
    "markdown.link": "cyan underline",
})

console = Console(theme=theme)

def print_markdown(text: str):
    console.print(Markdown(text))