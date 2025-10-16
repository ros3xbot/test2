import app.menus.banner as banner
ascii_art = banner.load("https://me.mashu.lol/mebanner880.png", globals())
ascii_art = banner.load("https://d17e22l2uh4h4n.cloudfront.net/corpweb/pub-xlaxiata/2019-03/xl-logo.png", globals())
import requests
from html.parser import HTMLParser

import os
import textwrap
import re
from html.parser import HTMLParser
from datetime import datetime
from app.config.theme_config import get_theme
from app.service.auth import AuthInstance
from app.client.engsel import get_balance, get_profile
from rich.console import Console
from rich.panel import Panel
from rich.align import Align
from rich.table import Table
from rich import box
from app.menus.util_helper import print_panel, get_rupiah

console = Console()


def print_banner():
    theme = get_theme()
    banner_text = Align.center(
        "[bold]myXL CLI v8.8.0 gen.Z[/]",
        vertical="middle"
    )
    console.print(Panel(
        banner_text,
        border_style=theme["border_primary"],
        style=theme["text_title"],
        padding=(1, 2),
        expand=True,
        box=box.DOUBLE
        #box=box.SIMPLE_HEAVY
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
        text = "".join(self.result)
        text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
        return "\n".join(textwrap.wrap(text, width=self.width, replace_whitespace=False))

def display_html(html_text, width=80):
    parser = HTMLToText(width=width)
    parser.feed(html_text)
    return parser.get_text()

def show_simple_number_panel():
    theme = get_theme()
    active_user = AuthInstance.get_active_user()

    if not active_user:
        text = f"[bold {theme['text_err']}]Tidak ada akun aktif saat ini.[/]"
    else:
        number = active_user.get("number", "-")
        text = f"[bold {theme['text_body']}]Akun yang sedang aktif ✨ {number} ✨[/]"

    console.print(Panel(
        Align.center(text),
        border_style=theme["border_warning"],
        padding=(0, 0),
        expand=True
    ))
