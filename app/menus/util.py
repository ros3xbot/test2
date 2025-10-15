import os
import re
import textwrap
from html.parser import HTMLParser


#def clear_screen():
#    os.system('cls' if os.name == 'nt' else 'clear')
#    width = 55
#    print("=" * width)
#    print(f" Join group telegram: https://t.me/AnooooMaliEngsellllll".center(width))
#    print("=" * width)
#    print("")


def print_banner():
    theme = get_theme()
    banner_text = Align.center(
        "[bold]myXL CLI v8.8.0 gen.1[/]",
        vertical="middle"
    )
    console.print(Panel(
        banner_text,
        border_style=theme["border_primary"],
        style=theme["text_title"],
        padding=(1, 2),
        expand=True
    ))
    show_simple_number_panel()

def clear_sc():
    print("Clearing screen...")
    os.system('cls' if os.name == 'nt' else 'clear')
    if ascii_art:
        ascii_art.to_terminal(columns=55)
    print_banner()

def clear_screen():
    print("Clearing screen...")
    os.system('cls' if os.name == 'nt' else 'clear')
    if ascii_art:
        ascii_art.to_terminal(columns=55)
    print_banner()

def pause():
    theme = get_theme()
    console.print(f"\n[bold {theme['border_info']}]Tekan Enter untuk melanjutkan...[/]")
    input()


class HTMLToText(HTMLParser):
    def __init__(self, width=80):
        super().__init__()
        self.width = width
        self.result = []
        self.in_li = False

    def handle_starttag(self, tag, attrs):
        if tag == "li":
            self.in_li = True
        elif tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag):
        if tag == "li":
            self.in_li = False
            self.result.append("\n")

    def handle_data(self, data):
        text = data.strip()
        if text:
            if self.in_li:
                self.result.append(f"- {text}")
            else:
                self.result.append(text)

    def get_text(self):
        # Join and clean multiple newlines
        text = "".join(self.result)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        # Wrap lines nicely
        return "\n".join(textwrap.wrap(text, width=self.width, replace_whitespace=False))


def display_html(html_text, width=80):
    parser = HTMLToText(width=width)
    parser.feed(html_text)
    return parser.get_text()
