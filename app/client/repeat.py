import time
import requests
from rich.table import Table
from rich.panel import Panel
from rich.console import Console

from app.service.auth import AuthInstance
from app.client.engsel import get_package_details
from app.client.balance import settlement_balance
from app.client.qris import show_qris_payment
from app.menus.util_helper import print_panel, get_rupiah
from app.config.theme_config import get_theme

console = Console()

# 🔧 Daftar preset decoy
DECOY_OPTIONS = {
    "1": {
        "name": "Decoy XCP",
        "url": "https://me.mashu.lol/pg-decoy-xcp.json"
    },
    "2": {
        "name": "Decoy XCP V2",
        "url": "https://me.mashu.lol/pg-decoy-xcp-v2.json"
    },
    "3": {
        "name": "Decoy Edu",
        "url": "https://me.mashu.lol/pg-decoy-edu.json"
    }
}

# 🔍 Ambil detail decoy dari URL JSON
def fetch_decoy_detail(api_key, tokens, url):
    try:
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
    except Exception as e:
        raise RuntimeError(f"Gagal mengambil decoy: {e}")

# 📦 Menu pemilihan decoy
def select_decoy_url():
    theme = get_theme()
    table = Table(show_header=False, expand=True)
    table.add_column("Kode", style=theme["text_key"], width=6)
    table.add_column("Nama Decoy", style=theme["text_body"])
    for key, val in DECOY_OPTIONS.items():
        table.add_row(key, val["name"])
    table.add_row("0", f"[{theme['text_sub']}]Batal / tanpa decoy[/]")

    print_panel("📦 Pilih Decoy", "Silakan pilih jenis decoy yang ingin digunakan:")
    console.print(Panel(table, border_style=theme["border_info"], expand=True))

    choice = input("Pilihan decoy: ").strip()
    if choice in DECOY_OPTIONS:
        return DECOY_OPTIONS[choice]["url"]
    return None

# 🔁 Pembelian N kali via balance
def purchase_n_times(n, family_code, variant_code, option_order, use_decoy=False, delay_seconds=0, pause_on_success=True):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

    decoy_url = None
    if use_decoy:
        decoy_url = select_decoy_url()
        if not decoy_url:
            print_panel("ℹ️ Info", "Pembelian dilanjutkan tanpa decoy.")
            use_decoy = False

    for i in range(n):
        try:
            print_panel("🔁 Pembelian", f"Iterasi ke-{i+1} sedang diproses...")
            detail = get_package_details(api_key, tokens, family_code, variant_code, option_order, is_enterprise=False, migration_type="")

            payment_items = []
            main_option = detail["package_option"]
            payment_items.append({
                "item_code": main_option["package_option_code"],
                "product_type": "",
                "item_price": main_option["price"],
                "item_name": main_option["name"],
                "tax": 0,
                "token_confirmation": detail["token_confirmation"]
            })

            total_amount = main_option["price"]

            if use_decoy:
                decoy_detail = fetch_decoy_detail(api_key, tokens, decoy_url)
                decoy_option = decoy_detail["package_option"]
                if decoy_option["package_option_code"] != main_option["package_option_code"]:
                    payment_items.append({
                        "item_code": decoy_option["package_option_code"],
                        "product_type": "",
                        "item_price": decoy_option["price"],
                        "item_name": decoy_option["name"],
                        "tax": 0,
                        "token_confirmation": decoy_detail["token_confirmation"]
                    })
                    total_amount += decoy_option["price"]
                else:
                    print_panel("⚠️ Error", "Item decoy sama dengan item utama, dilewati.")

            res = settlement_balance(api_key, tokens, payment_items, "BUY_PACKAGE", False, total_amount)

            if res and res.get("status") == "SUCCESS":
                print_panel("✅ Sukses", f"Pembelian ke-{i+1} berhasil.")
            else:
                msg = res.get("message", "Tidak diketahui")
                print_panel("⚠️ Gagal", f"Pembelian ke-{i+1} gagal: {msg}")

            if pause_on_success:
                input("Tekan Enter untuk lanjut...")
            if delay_seconds > 0 and i < n - 1:
                time.sleep(delay_seconds)

        except Exception as e:
            print_panel("⚠️ Error", f"Pembelian ke-{i+1} gagal: {e}")
            continue

# 🔁 Pembelian QRIS N kali
def purchase_qris_n_times(n, cart_items, use_decoy=False, delay_seconds=0):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

    decoy_url = None
    if use_decoy:
        decoy_url = select_decoy_url()
        if not decoy_url:
            print_panel("ℹ️ Info", "QRIS dilanjutkan tanpa decoy.")
            use_decoy = False

    for i in range(n):
        try:
            print_panel("🔁 QRIS", f"Iterasi ke-{i+1} sedang diproses...")
            items = cart_items.copy()
            if use_decoy:
                decoy_detail = fetch_decoy_detail(api_key, tokens, decoy_url)
                decoy_option = decoy_detail["package_option"]
                if decoy_option["package_option_code"] not in [item["item_code"] for item in items]:
                    items.append({
                        "item_code": decoy_option["package_option_code"],
                        "product_type": "",
                        "item_price": decoy_option["price"],
                        "item_name": decoy_option["name"],
                        "tax": 0,
                        "token_confirmation": decoy_detail["token_confirmation"]
                    })
                else:
                    print_panel("⚠️ Error", "Item decoy sudah ada di keranjang, dilewati.")

            show_qris_payment(api_key, tokens, items, "SHARE_PACKAGE", True, token_confirmation_idx=1 if use_decoy else 0)
            input("✅ QRIS ditampilkan. Tekan Enter untuk lanjut...")
            if delay_seconds > 0 and i < n - 1:
                time.sleep(delay_seconds)

        except Exception as e:
            print_panel("⚠️ Error", f"QRIS ke-{i+1} gagal: {e}")
            continue
