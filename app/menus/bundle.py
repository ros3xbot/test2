import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import MINIMAL_DOUBLE_HEAD

from app.service.auth import AuthInstance
from app.client.engsel import get_package, get_package_details
from app.client.qris import show_qris_payment
from app.client.ewallet import show_multipayment
from app.client.balance import settlement_balance
from app.menus.util import clear_screen, pause
from app.menus.util_helper import print_panel, get_rupiah
from app.config.theme_config import get_theme
from app.type_dict import PaymentItem

console = Console()

def render_payment_menu(theme):
    table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column(justify="right", style=theme["text_key"], width=6)
    table.add_column(style=theme["text_body"])
    table.add_row("1", "💰 Balance")
    table.add_row("2", "💳 E-Wallet")
    table.add_row("3", "📱 QRIS")
    table.add_row("4", "💰 Pulsa + Decoy XCP")
    table.add_row("5", "💰 Pulsa + Decoy XCP V2")
    table.add_row("6", "🔁 Pulsa N kali")
    table.add_row("7", "📱 QRIS + Decoy Edu")
    table.add_row("00", f"[{theme['text_sub']}]Kembali ke menu sebelumnya[/]")
    return table

def fetch_decoy_detail(api_key, tokens, url):
    response = requests.get(url, timeout=30)
    data = response.json()
    return get_package_details(
        api_key, tokens,
        data["family_code"],
        data["variant_code"],
        data["order"],
        data["is_enterprise"],
        data["migration_type"]
    )

def append_decoy_to_items(payment_items, decoy_detail):
    item = PaymentItem(
        item_code=decoy_detail["package_option"]["package_option_code"],
        product_type="",
        item_price=decoy_detail["package_option"]["price"],
        item_name=decoy_detail["package_option"]["name"],
        tax=0,
        token_confirmation=decoy_detail["token_confirmation"],
    )
    payment_items.append(item)
    return item.item_price

def handle_fallback_amount(res, api_key, tokens, items, amount, token_idx):
    if res and res.get("status", "") != "SUCCESS":
        msg = res.get("message", "")
        if "Bizz-err.Amount.Total" in msg and "=" in msg:
            try:
                valid_amount = int(msg.split("=")[1].strip())
                print_panel("Info", f"Jumlah disesuaikan ke Rp {get_rupiah(valid_amount)}")
                return settlement_balance(api_key, tokens, items, "BUY_PACKAGE", False, valid_amount, token_idx)
            except:
                print_panel("⚠️ Error", "Gagal parsing fallback amount.")
    return res

def show_bundle_menu(package_option_code):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    theme = get_theme()

    package = get_package(api_key, tokens, package_option_code)
    if not package:
        print_panel("⚠️ Error", "Gagal memuat detail paket.")
        pause()
        return "BACK"

    option = package["package_option"]
    family = package["package_family"]
    variant = package["package_detail_variant"]
    price = option["price"]
    option_order = option.get("order", 0)
    token_confirmation = package["token_confirmation"]
    family_code = family.get("package_family_code", "")
    variant_code = variant.get("package_variant_code", "")
    title = f"{variant.get('name', '')} - {option.get('name', '')}".strip()

    payment_items = [PaymentItem(
        item_code=package_option_code,
        product_type="",
        item_price=price,
        item_name=title,
        tax=0,
        token_confirmation=token_confirmation,
    )]

    while True:
        clear_screen()
        console.print(Panel(
            Align.center("💳 Pilih Metode Pembayaran", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))
        console.print(Panel(render_payment_menu(theme), border_style=theme["border_primary"], padding=(0, 1), expand=True))
        choice = console.input(f"[{theme['text_sub']}]Pilih metode:[/{theme['text_sub']}] ").strip()

        if choice == "00":
            break
        elif choice == "1":
            settlement_balance(api_key, tokens, payment_items, "BUY_PACKAGE", True)
            pause(); break
        elif choice == "2":
            show_multipayment(api_key, tokens, payment_items, "BUY_PACKAGE", True)
            pause(); break
        elif choice == "3":
            show_qris_payment(api_key, tokens, payment_items, "BUY_PACKAGE", True)
            pause(); break
        elif choice in ["4", "5"]:
            try:
                decoy_detail = fetch_decoy_detail(api_key, tokens, "https://me.mashu.lol/pg-decoy-xcp.json")
                decoy_price = append_decoy_to_items(payment_items, decoy_detail)
                amount = price + decoy_price
                res = settlement_balance(api_key, tokens, payment_items, "BUY_PACKAGE", False, amount, token_confirmation_idx=-1)
                res = handle_fallback_amount(res, api_key, tokens, payment_items, amount, token_confirmation_idx=-1)
                print_panel("✅ Info", "Pembelian berhasil." if res.get("status") == "SUCCESS" else "Gagal.")
                pause(); break
            except Exception as e:
                print_panel("⚠️ Error", f"Gagal decoy: {e}")
                pause()
        elif choice == "6":
            use_decoy = console.input(f"[{theme['text_sub']}]Gunakan decoy? (y/n):[/{theme['text_sub']}] ").strip().lower() == "y"
            n_times = console.input(f"[{theme['text_sub']}]Berapa kali pembelian:[/{theme['text_sub']}] ").strip()
            delay = console.input(f"[{theme['text_sub']}]Delay antar pembelian (detik):[/{theme['text_sub']}] ").strip()
            try:
                from app.client.repeat import purchase_n_times  # ⬅️ Import di dalam try agar tidak error saat modul belum tersedia
                purchase_n_times(
                    int(n_times), family_code, variant_code,
                    option_order, use_decoy, int(delay), pause_on_success=False
                )
                break
            except Exception as e:
                print_panel("⚠️ Error", f"Gagal pembelian N kali: {e}")
                pause()

        elif choice == "7":
            try:
                decoy_detail = fetch_decoy_detail(api_key, tokens, "https://me.mashu.lol/pg-decoy-edu.json")
                decoy_price = append_decoy_to_items(payment_items, decoy_detail)
                info_text = Text()
                info_text.append(f"Harga Paket Utama: Rp {get_rupiah(price)}\n", style=theme["text_money"])
                info_text.append(f"Harga Decoy Edu: Rp {get_rupiah(decoy_price)}\n", style=theme["text_money"])
                info_text.append("Silahkan sesuaikan amount jika diperlukan (trial & error)", style=theme["text_body"])
                console.print(Panel(info_text, title="📦 Info Pembayaran QRIS + Decoy", border_style=theme["border_warning"], expand=True))
                show_qris_payment(api_key, tokens, payment_items, "SHARE_PACKAGE", True, token_confirmation_idx=1)
                pause(); break
            except Exception as e:
                print_panel("⚠️ Error", f"Gagal decoy Edu: {e}")
                pause()
        else:
            print_panel("⚠️ Error", "Metode tidak valid.")
            pause()
