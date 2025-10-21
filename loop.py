import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from app.config.theme_config import get_theme
from app.service.auth import AuthInstance
from app.menus.util import pause
from app.menus.util_helper import print_panel, clear_screen
from app.menus.famplan import get_family
from app.client.engsel import get_package_details
from app.menus.payment import settlement_balance
from app.menus.payment_helper import PaymentItem
from app.menus.purchase import purchase_loop

console = Console()
theme = get_theme()

def prompt_decoy_type():
    console.print(Panel(
        "[bold]Pilih tipe decoy yang ingin digunakan:[/]\n\n"
        "[cyan]1.[/] Decoy XCP (default)\n"
        "[cyan]2.[/] Decoy XCP V2 (token confirmation dari decoy)\n"
        "[cyan]3.[/] Decoy EDU (QRIS share package)\n",
        title="🎭 Pilihan Decoy",
        border_style=theme.get("border_info", "cyan"),
        padding=(1, 2),
        expand=True
    ))
    choice = console.input(f"[{theme['text_sub']}]Masukkan pilihan (1/2/3):[/{theme['text_sub']}] ").strip()
    if choice == "2":
        return "xcp2"
    elif choice == "3":
        return "edu"
    return "xcp"

def loop():
    clear_screen()
    console.print(Panel(
        Align.center("🔁 Looping Pembelian dengan Decoy", vertical="middle"),
        border_style=theme["border_info"],
        padding=(1, 2),
        expand=True
    ))

    family_code = console.input(f"[{theme['text_sub']}]Masukkan Family Code:[/{theme['text_sub']}] ").strip()
    if not family_code or family_code == "99":
        print_panel("Info", "Pembelian dibatalkan.")
        pause()
        return

    use_decoy = console.input(f"[{theme['text_sub']}]Gunakan paket decoy? (y/n):[/{theme['text_sub']}] ").strip().lower() == "y"
    decoy_type = prompt_decoy_type() if use_decoy else "xcp"

    try:
        order = int(console.input(f"[{theme['text_sub']}]Urutan dari list Family Code:[/{theme['text_sub']}] ").strip())
        delay = int(console.input(f"[{theme['text_sub']}]Delay antar pembelian (detik):[/{theme['text_sub']}] ").strip() or "0")
        how_many = int(console.input(f"[{theme['text_sub']}]Berapa kali ulang pembelian:[/{theme['text_sub']}] ").strip())

        confirm_text = Text.from_markup(
            f"Family Code: [bold]{family_code}[/]\n"
            f"Urutan: [bold]{order}[/]\n"
            f"Jumlah Ulang: [bold]{how_many}[/]\n"
            f"Delay: [bold]{delay} detik[/]\n"
            f"Gunakan Decoy: {'Ya' if use_decoy else 'Tidak'}\n"
            f"Tipe Decoy: [bold]{decoy_type.upper()}[/]"
        )
        console.print(Panel(confirm_text, title="📦 Konfirmasi", border_style=theme["border_warning"], padding=(1, 2), expand=True))
        if console.input(f"[{theme['text_sub']}]Lanjutkan pembelian? (y/n):[/{theme['text_sub']}] ").strip().lower() != "y":
            print_panel("Info", "Pembelian dibatalkan.")
            pause()
            return

        purchase_loop(
            loop=how_many,
            family_code=family_code,
            order=order,
            use_decoy=use_decoy,
            delay=delay,
            pause_on_success=True,
            decoy_type=decoy_type
        )

    except ValueError:
        print_panel("⚠️ Error", "Input angka tidak valid.")
        pause()

if __name__ == "__main__":
    try:
        loop()
    except KeyboardInterrupt:
        print_panel("👋 Keluar", "Aplikasi dihentikan oleh pengguna.")
        sys.exit(0)
