from app.client.engsel2 import segments
from app.menus.util import clear_screen, pause
from app.menus.util_helper import print_panel, get_rupiah
from app.config.theme_config import get_theme
from app.service.auth import AuthInstance
from app.menus.package import show_package_details
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import MINIMAL_DOUBLE_HEAD
from rich.align import Align

console = Console()

def fetch_special_for_you(api_key: str, id_token: str, access_token: str, balance: int = 0) -> list:
    try:
        seg_data = segments(api_key, id_token, access_token, balance)
        if not seg_data:
            return []

        packages = seg_data.get("special_packages", [])
        special_packages = []

        for pkg in packages:
            try:
                name = pkg.get("name", "Unknown Package")
                kode_paket = pkg.get("kode_paket", "-")

                if not kode_paket or kode_paket == "-":
                    continue  # skip jika tidak ada kode paket

                original_price = int(pkg.get("original_price", 0))
                diskon_price = int(pkg.get("diskon_price", original_price))

                diskon_percent = 0
                if original_price > 0 and diskon_price < original_price:
                    diskon_percent = int(round((original_price - diskon_price) / original_price * 100))

                special_packages.append({
                    "name": name,
                    "kode_paket": kode_paket,
                    "original_price": f"Rp {original_price:,}".replace(",", "."),
                    "diskon_price": f"Rp {diskon_price:,}".replace(",", "."),
                    "diskon_percent": diskon_percent,
                })
            except Exception as e:
                print_panel("⚠️ Error", f"Gagal parse paket: {e}")
                continue

        special_packages.sort(key=lambda x: x["diskon_percent"], reverse=True)
        return special_packages

    except Exception as e:
        print_panel("⚠️ Error", f"Gagal mengambil data SFY: {e}")
        return []


def show_special_for_you_menu(tokens: dict, special_packages: list):
    theme = get_theme()

    while True:
        clear_screen()

        if not special_packages:
            print_panel("ℹ️ Info", "Tidak ada paket spesial tersedia saat ini.")
            pause()
            return

        # Panel informasi di atas tabel
        info_text = Align.center(
            f"[{theme['text_body']}]🔥 Daftar Paket Special For You 🔥[/{theme['text_body']}]"
        )
        console.print(Panel(
            info_text,
            #title=f"[{theme['text_title']}]🔥 Daftar Paket Special For You 🔥[/]",
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        # Tabel daftar paket
        table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("No", justify="right", style=theme["text_key"], width=4)
        table.add_column("Nama Paket", style=theme["text_body"])
        table.add_column("Diskon", justify="right", style=theme["text_money"])
        table.add_column("Harga Normal", justify="right", style=theme["text_err"])
        table.add_column("Harga Diskon", justify="right", style=theme["text_money"])

        for idx, pkg in enumerate(special_packages, 1):
            emoji_diskon = "💸" if pkg.get("diskon_percent", 0) >= 50 else ""
            emoji_kuota = "🔥" if pkg.get("kuota_gb", 0) >= 100 else ""

            # Konversi harga ke format rupiah
            try:
                original_int = int(str(pkg.get("original_price", "0")).replace("Rp", "").replace(".", "").replace(",", "").strip())
                diskon_int = int(str(pkg.get("diskon_price", "0")).replace("Rp", "").replace(".", "").replace(",", "").strip())
            except:
                original_int = 0
                diskon_int = 0

            original_price = get_rupiah(original_int)
            diskon_price = get_rupiah(diskon_int)

            table.add_row(
                str(idx),
                f"{emoji_kuota} {pkg.get('name', '-')}",
                f"{pkg.get('diskon_percent', 0)}% {emoji_diskon}",
                f"[{theme['text_err']}][strike]{original_price}[/strike][/{theme['text_err']}]",
                f"[{theme['text_money']}]{diskon_price}[/{theme['text_money']}]"
            )

        console.print(Panel(table, border_style=theme["border_primary"], padding=(0, 0), expand=True))

        # Panel navigasi
        nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav_table.add_column(justify="right", style=theme["text_key"], width=6)
        nav_table.add_column(style=theme["text_body"])
        nav_table.add_row("00", f"[{theme['text_sub']}]Kembali ke menu sebelumnya[/]")
        #nav_table.add_row("99", f"[{theme['text_sub']}]Kembali ke menu utama[/]")

        console.print(Panel(
            nav_table,
            border_style=theme["border_info"],
            padding=(0, 1),
            expand=True
        ))

        # Input pilihan
        choice = console.input(f"[{theme['text_sub']}]Pilih paket (nomor):[/{theme['text_sub']}] ").strip()

        if choice == "99":
            return "MAIN"
        if choice == "00":
            return "BACK"

        if not choice.isdigit():
            print_panel("⚠️ Error", "Input tidak valid. Masukkan angka yang sesuai.")
            pause()
            continue

        choice_idx = int(choice) - 1
        if 0 <= choice_idx < len(special_packages):
            selected_pkg = special_packages[choice_idx]
            #print_panel("📦 Paket Dipilih", selected_pkg["name"])
            #pause()
            api_key = AuthInstance.api_key
            result = show_package_details(api_key, tokens, selected_pkg["kode_paket"], is_enterprise=False)

            if result == "MAIN":
                return "MAIN"
            # jika "BACK", kita tetap di loop dan tampilkan daftar lagi
        else:
            print_panel("⚠️ Error", "Nomor paket tidak valid.")
            pause()
