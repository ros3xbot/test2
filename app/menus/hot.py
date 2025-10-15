import os
import json
import requests
import ast
import logging
from app.client.engsel import get_family, get_package_details
from app.menus.package import show_package_details
from app.service.auth import AuthInstance
from app.menus.util import clear_screen, pause
from app.menus.util_helper import get_rupiah, print_panel
from app.client.ewallet import show_multipayment
from app.client.qris import show_qris_payment
from app.client.balance import settlement_balance
from app.type_dict import PaymentItem
from app.client.encrypt import BASE_CRYPTO_URL
from app.config.theme_config import get_theme
from rich.console import Console, Group
from rich.text import Text
from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.box import MINIMAL_DOUBLE_HEAD

console = Console()

CACHE_FILE = "family_cache.json"

def load_family_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_family_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def show_hot_main_menu():
    theme = get_theme()
    while True:
        clear_screen()

        console.print(Panel(
            Align.center("✨ Paket Promo ✨", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        menu_table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        menu_table.add_column("Kode", justify="right", style=theme["text_key"], width=6)
        menu_table.add_column("Menu Paket", style=theme["text_body"])
        menu_table.add_row("1", "Paket Hot Promo")
        menu_table.add_row("2", "Paket Hot Promo-2")
        menu_table.add_row("00", f"[{theme['text_err']}]Kembali ke menu utama[/]")

        console.print(Panel(
            menu_table,
            border_style=theme["border_primary"],
            padding=(0, 1),
            expand=True
        ))

        choice = console.input(f"[{theme['text_sub']}]Pilih menu:[/{theme['text_sub']}] ").strip()
        if choice == "1":
            show_hot_menu()
        elif choice == "2":
            show_hot_menu2()
        elif choice == "00":
            live_loading(text="Kembali ke menu utama...", theme=theme)
            return
        else:
            print_panel("⚠️ Error", "Input tidak valid. Silahkan coba lagi.")
            pause()

def validate_family_data(data):
    return (
        data and
        isinstance(data, dict) and
        "package_variants" in data
    )

def refresh_family_data(family_code, is_enterprise, api_key, tokens, cache):
    data = get_family(api_key, tokens, family_code, is_enterprise)
    if validate_family_data(data):
        cache[(family_code, is_enterprise)] = data
    return data

def show_hot_menu():
    theme = get_theme()
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

    if not tokens:
        print_panel("⚠️ Error", "Token pengguna tidak ditemukan.")
        pause()
        return

    raw_cache = load_family_cache()
    try:
        family_cache = {eval(k): v for k, v in raw_cache.items()}
    except Exception:
        family_cache = {}

    while True:
        clear_screen()

        try:
            response = requests.get("https://me.mashu.lol/pg-hot.json", timeout=30)
            hot_packages = response.json()
        except Exception:
            print_panel("⚠️ Error", "Gagal mengambil data HOT Package.")
            pause()
            return

        if not hot_packages:
            print_panel("⚠️ Error", "Tidak ada data paket tersedia.")
            pause()
            return

        enriched_packages = []

        for p in hot_packages:
            fc_key = (p["family_code"], p["is_enterprise"])
            family_data = family_cache.get(fc_key)

            if not validate_family_data(family_data):
                family_data = refresh_family_data(p["family_code"], p["is_enterprise"], api_key, tokens, family_cache)

            if not validate_family_data(family_data):
                continue

            for variant in family_data.get("package_variants", []):
                if variant.get("name") == p.get("variant_name"):
                    for option in variant.get("package_options", []):
                        if option.get("order") == p.get("order"):
                            p["option_code"] = option.get("package_option_code")
                            p["price"] = option.get("price")
                            p["option_name"] = option.get("name", "-")
                            break
            enriched_packages.append(p)

        save_family_cache({str(k): v for k, v in family_cache.items()})

        if not enriched_packages:
            print_panel("⚠️ Error", "Gagal memproses data paket. Silakan coba lagi nanti.")
            pause()
            return

        console.print(Panel(
            Align.center("🔥 Paket Hot Promo 🔥", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("No", justify="right", style=theme["text_key"], width=6)
        table.add_column("Nama Paket", style=theme["text_body"])
        table.add_column("Harga", justify="right", style=theme["text_money"], width=10)

        for idx, p in enumerate(enriched_packages):
            label = f"{p.get('family_name', '-') } - {p.get('variant_name', '-') } - {p.get('option_name', '-') }"
            harga = get_rupiah(p.get("price", 0))
            table.add_row(str(idx + 1), label, harga)

        console.print(Panel(table, border_style=theme["border_primary"], padding=(0, 0), expand=True))

        nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav_table.add_column(justify="right", style=theme["text_key"], width=4)
        nav_table.add_column(style=theme["text_body"])
        nav_table.add_row("00", f"[{theme['text_sub']}]Kembali ke menu awal[/]")
        nav_table.add_row("99", f"[{theme['text_err']}]Reset[/] [{theme['text_body']}](apabila gagal memuat detail paket)[/]")

        console.print(Panel(nav_table, border_style=theme["border_info"], padding=(0, 1), expand=True))

        choice = console.input(f"[{theme['text_sub']}]Pilih paket:[/{theme['text_sub']}] ").strip()
        if choice == "00":
            #print_panel("ℹ️ Info", "Kembali ke menu awal...")
            #pause()
            return

        elif choice == "99":
            try:
                os.remove(CACHE_FILE)
                family_cache.clear()
                print_panel("✅ Cache Direset", "Cache paket berhasil dihapus.")
            except Exception:
                print_panel("⚠️ Error", "Gagal menghapus cache.")
            pause()
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(enriched_packages):
            selected_pkg = enriched_packages[int(choice) - 1]
            option_code = selected_pkg.get("option_code")
            if not option_code:
                print_panel("⚠️ Error", "Kode paket tidak ditemukan.")
                pause()
                continue

            try:
                result = show_package_details(api_key, tokens, option_code, selected_pkg.get("is_enterprise", False))
            except Exception:
                print_panel("⚠️ Error", "Gagal menampilkan detail paket.")
                pause()
                continue

            if result == "MAIN":
                return
            elif result in ("BACK", True):
                continue
        else:
            print_panel("⚠️ Error", "Input tidak valid. Silakan masukkan nomor yang tersedia.")
            pause()


def validate_package_detail(detail):
    return (
        detail and
        isinstance(detail, dict) and
        "package_option" in detail and
        "token_confirmation" in detail and
        isinstance(detail["package_option"], dict) and
        "package_option_code" in detail["package_option"] and
        "price" in detail["package_option"] and
        "name" in detail["package_option"]
    )


def show_hot_menu2():
    theme = get_theme()
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print_panel("⚠️ Error", "Token tidak tersedia. Silakan login ulang.")
        pause()
        return

    while True:
        clear_screen()
        console.print(Panel(
            Align.center("🔥 Paket Hot Promo-2 🔥", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        try:
            url = BASE_CRYPTO_URL + "/pghot2"
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            hot_packages = response.json()
        except Exception as e:
            print_panel("⚠️ Error", f"Gagal mengambil data HOT-2 Package.\n{e}")
            pause()
            return

        if not hot_packages:
            print_panel("⚠️ Error", "Tidak ada data paket tersedia.")
            pause()
            return

        table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("No", justify="right", style=theme["text_key"], width=6)
        table.add_column("Nama Paket", style=theme["text_body"])
        table.add_column("Harga", justify="right", style=theme["text_money"], width=12)

        for idx, p in enumerate(hot_packages):
            table.add_row(str(idx + 1), p["name"], get_rupiah(p["price"]))

        console.print(Panel(table, border_style=theme["border_primary"], padding=(0, 0), expand=True))
        console.print(Panel("[bold]00[/] Kembali ke menu utama", border_style=theme["border_info"], padding=(0, 1), expand=True))

        choice = console.input(f"[{theme['text_sub']}]Pilih paket:[/{theme['text_sub']}] ").strip()
        if choice == "00":
            return

        if not choice.isdigit() or not (1 <= int(choice) <= len(hot_packages)):
            print_panel("⚠️ Error", "Input tidak valid. Silahkan coba lagi.")
            pause()
            continue

        selected_package = hot_packages[int(choice) - 1]
        packages = selected_package.get("packages", [])
        if not packages:
            print_panel("⚠️ Error", "Paket tidak tersedia.")
            pause()
            continue

        payment_items = []
        for package in packages:
            detail = get_package_details(
                api_key,
                tokens,
                package["family_code"],
                package["variant_code"],
                package["order"],
                package["is_enterprise"],
            )
            if not detail:
                print_panel("⚠️ Error", f"Gagal mengambil detail paket untuk {package['family_code']}.")
                return

            payment_items.append(PaymentItem(
                item_code=detail["package_option"]["package_option_code"],
                product_type="",
                item_price=detail["package_option"]["price"],
                item_name=detail["package_option"]["name"],
                tax=0,
                token_confirmation=detail["token_confirmation"],
            ))

        clear_screen()
        console.print(Panel(
            f"[bold]{selected_package['name']}[/]\n\n"
            f"Harga: Rp [bold {theme['text_money']}]{get_rupiah(selected_package['price'])}[/]\n\n"
            f"[{theme['text_body']}]Detail:[/]\n" +
            "\n".join([f"- {line.strip()}" for line in selected_package.get("detail", "").split("\n") if line.strip()]),
            title=f"[{theme['text_title']}]📦 Detail Paket[/]",
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        payment_for = selected_package.get("payment_for", "BUY_PACKAGE")
        ask_overwrite = selected_package.get("ask_overwrite", False)
        overwrite_amount = selected_package.get("overwrite_amount", -1)
        token_confirmation_idx = selected_package.get("token_confirmation_idx", 0)
        amount_idx = selected_package.get("amount_idx", -1)

        while True:
            method_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
            method_table.add_column(justify="right", style=theme["text_key"], width=6)
            method_table.add_column(style=theme["text_body"])
            method_table.add_row("1", "💰 Balance")
            method_table.add_row("2", "📱 E-Wallet")
            method_table.add_row("3", "🏧 QRIS")
            method_table.add_row("00", f"[{theme['text_sub']}]Kembali ke daftar paket[/]")

            console.print(Panel(
                method_table,
                title=f"[{theme['text_title']}]💳 Pilih Metode Pembayaran[/]",
                border_style=theme["border_primary"],
                padding=(0, 1),
                expand=True
            ))

            method = console.input(f"[{theme['text_sub']}]Pilih metode:[/{theme['text_sub']}] ").strip()
            if method == "00":
                break
            elif method == "1":
                if overwrite_amount == -1:
                    harga_rp = get_rupiah(payment_items[-1].item_price)
                    konfirmasi_text = Text()
                    konfirmasi_text.append("⚠️ Pastikan sisa balance KURANG DARI\n", style=theme["text_err"])
                    konfirmasi_text.append(f"Harga paket: Rp {harga_rp}\n", style=theme["text_money"])
                    konfirmasi_text.append("Lanjutkan pembelian?", style=theme["text_body"])

                    console.print(Panel(
                        Align.center(konfirmasi_text),
                        title=f"[{theme['text_title']}]Konfirmasi Pembelian[/]",
                        border_style=theme["border_warning"],
                        padding=(1, 2),
                        expand=True
                    ))

                    confirm = console.input(f"[{theme['text_sub']}]Ketik 'y' untuk lanjut, atau lainnya untuk batal:[/{theme['text_sub']}] ").strip().lower()
                    if confirm != "y":
                        print_panel("ℹ️ Info", "Pembelian dibatalkan oleh pengguna.")
                        pause()
                        break

                settlement_balance(api_key, tokens, payment_items, payment_for, ask_overwrite, overwrite_amount, token_confirmation_idx, amount_idx)
                console.input(f"[{theme['text_sub']}]Tekan enter untuk kembali...[/{theme['text_sub']}] ")
                return
            elif method == "2":
                show_multipayment(api_key, tokens, payment_items, payment_for, ask_overwrite, overwrite_amount, token_confirmation_idx, amount_idx)
                console.input(f"[{theme['text_sub']}]Tekan enter untuk kembali...[/{theme['text_sub']}] ")
                return
            elif method == "3":
                show_qris_payment(api_key, tokens, payment_items, payment_for, ask_overwrite, overwrite_amount, token_confirmation_idx, amount_idx)
                console.input(f"[{theme['text_sub']}]Tekan enter untuk kembali...[/{theme['text_sub']}] ")
                return
            else:
                print_panel("⚠️ Error", "Metode tidak valid. Silahkan coba lagi.")
                pause()
