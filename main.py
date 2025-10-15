from dotenv import load_dotenv
load_dotenv()

import sys
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.align import Align
from rich.box import MINIMAL_DOUBLE_HEAD

from app.menus.util import pause
from app.client.engsel import get_balance, get_profile, get_package
from app.client.engsel2 import get_tiering_info, segments
from app.menus.payment import show_transaction_history
from app.service.auth import AuthInstance
from app.menus.bookmark import show_bookmark_menu
from app.menus.account import show_account_menu
from app.menus.package import fetch_my_packages, get_packages_by_family
from app.menus.hot import show_hot_menu, show_hot_menu2
from app.service.sentry import enter_sentry_mode
from app.menus.purchase import purchase_by_family, purchase_loop
from app.menus.util_helper import clear_screen, get_rupiah
from app.menus.donate import show_donate_menu
from app.menus.bundle import show_bundle_menu
from app.menus.points import run_point_exchange
from app.menus.family_grup import show_family_menu
from app.menus.points import run_point_exchange
from app.menus.special import show_special_for_you_menu
from app.menus.theme import show_theme_menu
from app.config.theme_config import get_theme

console = Console()
theme = get_theme()

def build_profile():
    tokens = AuthInstance.get_active_tokens()
    if not tokens:
        print_panel("⚠️ Error", "Token pengguna aktif tidak ditemukan.")
        pause()
        return None

    api_key = AuthInstance.api_key

    print("Fetching balance...")
    balance = get_balance(api_key, tokens["id_token"])

    print("Fetching profile...")
    profile_data = get_profile(api_key, tokens["access_token"], tokens["id_token"])

    balance_remaining = balance.get("remaining", 0)

    print("Fetching tiering info...")
    sub_type = profile_data["profile"].get("subscription_type", "-")
    sub_id = profile_data["profile"].get("subscriber_id", "-")

    point_info = "Points: N/A | Tier: N/A"
    if sub_type == "PREPAID":
        tiering_data = get_tiering_info(api_key, tokens)
        tier = tiering_data.get("tier", 0)
        current_point = tiering_data.get("current_point", 0)
        point_info = f"Points: {current_point} | Tier: {tier}"

    segments_data = segments(balance_remaining, tokens["id_token"], tokens["access_token"]) or {}

    return {
        "number": AuthInstance.get_active_user()["number"],
        "subscriber_id": sub_id,
        "subscription_type": sub_type,
        "balance": balance.get("remaining", 0),
        "balance_expired_at": balance.get("expired_at", 0),
        "point_info": point_info,
        "segments": segments_data
    }



def show_main_menu(profile):
    clear_screen()
    theme = get_theme()
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d %H:%M:%S")
    pulsa_str = get_rupiah(profile["balance"])

    # Panel Informasi Akun
    info_table = Table.grid(padding=(0, 1))
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_row(" Nomor", f": 📞 [bold {theme['text_body']}]{profile['number']}[/]")
    info_table.add_row(" Type", f": 🧾 [{theme['text_body']}]{profile['subscription_type']} ({profile['subscriber_id']})[/]")
    info_table.add_row(" Pulsa", f": 💰 Rp [{theme['text_money']}]{pulsa_str}[/]")
    info_table.add_row(" Masa Aktif", f": ⏳ [{theme['text_date']}]{expired_at_dt}[/]")
    info_table.add_row(" Tiering", f": 🏅 [{theme['text_date']}]{profile['point_info']}[/]")

    console.print(Panel(info_table, title=f"[{theme['text_title']}]✨Informasi Akun✨[/]", title_align="center", border_style=theme["border_info"], padding=(1, 2), expand=True))

    # Panel Menu Utama
    menu_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    menu_table.add_column("Kode", justify="right", style=theme["text_key"], width=6)
    menu_table.add_column("Aksi", style=theme["text_body"])
    menu_table.add_row("1", "🔐 Login/Ganti akun")
    menu_table.add_row("2", "📑 Lihat Paket Saya")
    menu_table.add_row("3", "📜 Riwayat Transaksi")
    menu_table.add_row("4", "🎁 Tukar Point Reward")
    menu_table.add_row("5", "🔥 Beli Paket Hot Promo")
    menu_table.add_row("6", "🔥 Beli Paket Hot Promo-2")
    menu_table.add_row("7", "🔍 Beli Paket Berdasarkan Family Code")
    menu_table.add_row("8", "🧪 Beli semua Paket dalam Family Code")
    menu_table.add_row("9", "🔁 Order berulang dari Family Code")
    menu_table.add_row("10", "🛒 Beli/Buat Paket Bundle (multi)")
    menu_table.add_row("11", "💾 Simpan/Kelola Family Code")
    menu_table.add_row("00", "⭐ Bookmark Paket")
    menu_table.add_row("", "")
    menu_table.add_row("77", f"[{theme['border_warning']}]📢 Info Unlock Code [/]")  
    menu_table.add_row("88", f"[{theme['text_sub']}]🎨 Ganti Tema CLI [/]")  
    menu_table.add_row("99", f"[{theme['text_err']}]⛔ Tutup aplikasi [/]")

    console.print(Panel(menu_table, title=f"[{theme['text_title']}]✨ Menu Utama ✨[/]", title_align="center", border_style=theme["border_primary"], padding=(0, 1), expand=True))

    # Panel Paket Spesial
    special_packages = profile.get("segments", {}).get("special_packages", [])
    if special_packages:
        import random
        best = random.choice(special_packages)

        name = best.get("name", "-")
        diskon_percent = best.get("diskon_percent", 0)
        diskon_price = best.get("diskon_price", 0)
        original_price = best.get("original_price", 0)
        emoji_diskon = "💸" if diskon_percent >= 50 else ""
        emoji_kuota = "🔥" if best.get("kuota_gb", 0) >= 100 else ""

        special_text = (
            f"[bold {theme['text_title']}]🔥🔥🔥 Paket Special Untukmu! 🔥🔥🔥[/{theme['text_title']}]\n\n"
            f"[{theme['text_body']}]{emoji_kuota} {name}[/{theme['text_body']}]\n"
            f"Diskon {diskon_percent}% {emoji_diskon} "
            f"Rp[{theme['text_err']}][strike]{get_rupiah(original_price)}[/strike][/{theme['text_err']}] ➡️ "
            f"Rp[{theme['text_money']}]{get_rupiah(diskon_price)}[/{theme['text_money']}]"
        )

        panel_width = console.size.width
        console.print(Panel(
            Align.center(special_text),
            border_style=theme["border_warning"],
            padding=(0, 2),
            width=panel_width
        ))

        console.print(Align.center(
            f"[{theme['text_sub']}]Pilih [S] untuk lihat semua paket spesial[/{theme['text_sub']}]"
        ))


def handle_choice(choice, profile):
    theme = get_theme()
    choice = choice.strip().lower()
    tokens = AuthInstance.get_active_user()["tokens"]
    api_key = AuthInstance.api_key

    if choice == "1":
        selected_user_number = show_account_menu()
        if selected_user_number:
            AuthInstance.set_active_user(selected_user_number)
        else:
            console.print("Tidak ada user dipilih atau gagal load.", style=theme["text_err"])

    elif choice == "2":
        fetch_my_packages()

    elif choice == "3":
        show_transaction_history(api_key, tokens)

    elif choice == "4":
        tokens = AuthInstance.get_active_tokens()
        if not tokens:
            print_panel("⚠️ Error", "Token tidak ditemukan. Silakan login terlebih dahulu.")
            pause()
        else:
            run_point_exchange(tokens)

    elif choice == "5":
        show_hot_menu()

    elif choice == "6":
        show_hot_menu2()

    elif choice == "7":
        family_code = input("Masukkan Family Code (atau '99' untuk batal): ").strip()
        if family_code != "99":
            get_packages_by_family(family_code)

    elif choice == "8":
        family_code = input("Masukkan Family Code: ").strip()
        if family_code != "99":
            use_decoy = input("Gunakan decoy? (y/n): ").strip().lower() == 'y'
            pause_on_success = input("Pause tiap sukses? (y/n): ").strip().lower() == 'y'
            purchase_by_family(family_code, use_decoy, pause_on_success)

    elif choice == "9":
        family_code = input("Masukkan Family Code: ").strip()
        if family_code != "99":
            use_decoy = input("Gunakan decoy? (y/n): ").strip().lower() == 'y'
            try:
                order = int(input("Urutan dari list Family Code: ").strip())
                delay = input("Delay (detik): ").strip()
                how_many = int(input("Berapa kali ulang: ").strip())
                purchase_loop(how_many, family_code, order, use_decoy, 0 if delay == "" else int(delay))
            except ValueError:
                print_panel("⚠️ Error", "Input angka tidak valid.")
                pause()

    elif choice == "10":
        show_bundle_menu()

    elif choice == "11":
        show_family_menu()

    elif choice == "00":
        show_bookmark_menu()

    elif choice == "77":
        show_donate_menu()

    elif choice == "88":
        show_theme_menu()

    elif choice == "99":
        console.print("Menutup aplikasi...", style=theme["text_err"])
        sys.exit(0)

    elif choice == "t":
        res = get_package(api_key, tokens, "")
        console.print(res)
        input("Tekan Enter untuk lanjut...")

    elif choice == "s":
        special_packages = profile.get("segments", {}).get("special_packages", [])
        if special_packages:
            result = show_special_for_you_menu(tokens, special_packages)
            if result in ("MAIN", "BACK"):
                return
        else:
            print_panel("ℹ️ Info", "Tidak ada paket Special For You yang tersedia saat ini.")
            pause()

    else:
        console.print("Pilihan tidak valid.", style=theme["text_err"])
        pause()
def main():
    while True:
        active_user = AuthInstance.get_active_user()
        if active_user:
            profile = build_profile()
            if profile:
                show_main_menu(profile)
                choice = input("Pilih menu: ").strip().lower()
                handle_choice(choice, profile)
            else:
                console.print("Gagal membangun profil.", style=get_theme()["text_err"])
                pause()
        else:
            selected_user_number = show_account_menu()
            if selected_user_number:
                AuthInstance.set_active_user(selected_user_number)
            else:
                console.print("Tidak ada user dipilih atau gagal load.", style=get_theme()["text_err"])
                pause()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\nMenutup aplikasi...", style=get_theme()["text_err"])

