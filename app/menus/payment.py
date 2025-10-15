from datetime import datetime, timedelta
from app.client.engsel2 import get_transaction_history
from app.menus.util import clear_screen, pause
from app.menus.util_helper import print_panel
from app.config.theme_config import get_theme
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.box import MINIMAL_DOUBLE_HEAD

console = Console()

def show_transaction_history(api_key, tokens):
    theme = get_theme()
    in_transaction_menu = True

    while in_transaction_menu:
        clear_screen()
        #console.print(Panel("📄 Riwayat Transaksi", title="💰 Transaksi", border_style=theme["border_info"], expand=True))
        console.print(Panel(
            Align.center("📄 Riwayat Transaksi", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        try:
            data = get_transaction_history(api_key, tokens)
            history = data.get("list", [])
        except Exception as e:
            print_panel("⚠️ Error", f"Gagal mengambil riwayat transaksi: {e}")
            history = []

        if not history:
            print_panel("ℹ️ Info", "Tidak ada riwayat transaksi.")
        else:
            for idx, transaction in enumerate(history, start=1):
                ts = transaction.get("timestamp", 0)
                dt = datetime.fromtimestamp(ts) - timedelta(hours=7)
                formatted_time = dt.strftime("%d %B %Y | %H:%M WIB")

                t = Table(box=MINIMAL_DOUBLE_HEAD, expand=True, padding=(0, 0))
                t.add_column("Label", justify="left", style=theme["text_body"], width=18)
                t.add_column("Detail", justify="right", style=theme["text_body"])
                t.add_row("Judul", transaction.get("title", "-"))
                t.add_row("Harga", f"Rp {transaction.get('price', '-')}")
                t.add_row("Tanggal", formatted_time)
                t.add_row("Metode", transaction.get("payment_method_label", "-"))
                t.add_row("Status Transaksi", transaction.get("status", "-"))
                t.add_row("Status Pembayaran", transaction.get("payment_status", "-"))

                console.print(Panel(t, title=f"🧾 Transaksi #{idx}", border_style=theme["border_success"], expand=True))

        # Navigasi
        nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav_table.add_column(justify="right", style=theme["text_key"], width=6)
        nav_table.add_column(justify="left", style=theme["text_body"])
        nav_table.add_row("0", "Refresh")
        nav_table.add_row("00", f"[{theme['text_sub']}]Kembali ke Menu Utama[/]")

        console.print(Panel(nav_table, border_style=theme["border_info"], expand=True))

        choice = console.input(f"[{theme['text_sub']}]Pilih opsi:[/{theme['text_sub']}] ").strip()
        if choice == "0":
            continue
        elif choice == "00":
            return
        else:
            print_panel("⚠️ Error", "Opsi tidak valid. Silakan coba lagi.")
            pause()
