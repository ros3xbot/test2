import random
import sys
import time
from datetime import datetime
from app.menus.util import pause, clear_sc
from app.menus.util_helper import print_panel, get_rupiah, clear_screen
from app.client.engsel import get_balance, get_profile, get_quota
from app.client.engsel2 import get_tiering_info, segments
from app.menus.payment import show_transaction_history
from app.service.auth import AuthInstance
from app.menus.bookmark import show_bookmark_menu
from app.menus.account import show_account_menu
from app.menus.package import fetch_my_packages, get_packages_by_family
from app.menus.hot import show_hot_menu, show_hot_menu2
from app.menus.family_grup import show_family_menu
from app.menus.donate import show_donate_menu
from app.menus.theme import show_theme_menu
from app.config.theme_config import get_theme
from app.menus.points import run_point_exchange
from app.menus.special import show_special_for_you_menu
from app.menus.bundle import show_bundle_menu
from app.menus.purchase import purchase_by_family, purchase_loop
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.box import MINIMAL_DOUBLE_HEAD
from rich.align import Align
from rich.text import Text

console = Console()
theme = get_theme()
cached_user_context = None
last_fetch_time = 0

def fetch_user_context(force_refresh=False):
    global cached_user_context, last_fetch_time
    now = time.time()

    if not force_refresh and cached_user_context and now - last_fetch_time < 60:
        return cached_user_context

    active_user = AuthInstance.get_active_user()
    if not active_user:
        return None

    api_key = AuthInstance.api_key
    tokens = active_user["tokens"]
    id_token = tokens.get("id_token")
    access_token = tokens.get("access_token")

    balance_data = get_balance(api_key, id_token)
    balance_remaining = balance_data.get("remaining", 0)
    balance_expired_at = balance_data.get("expired_at", 0)

    quota = get_quota(api_key, id_token) or {}
    remaining = quota.get("remaining", 0)
    total = quota.get("total", 0)
    has_unlimited = quota.get("has_unlimited", False)

    if total > 0 or has_unlimited:
        remaining_gb = remaining / 1e9
        total_gb = total / 1e9
        display_quota = (
            f"{remaining_gb:.2f}/{total_gb:.2f} GB (Unlimited)"
            if has_unlimited else f"{remaining_gb:.2f}/{total_gb:.2f} GB"
        )
    else:
        display_quota = "-"

    profile_data = get_profile(api_key, access_token, id_token)
    sub_id = profile_data["profile"].get("subscriber_id", "-")
    sub_type = profile_data["profile"].get("subscription_type", "-")

    point_info = "Points: N/A | Tier: N/A"
    if sub_type == "PREPAID":
        tiering_data = get_tiering_info(api_key, tokens)
        tier = tiering_data.get("tier", 0)
        current_point = tiering_data.get("current_point", 0)
        point_info = f"Points: {current_point} | Tier: {tier}"

    segments_data = segments(api_key, id_token, access_token, balance_remaining) or {}

    cached_user_context = {
        "api_key": api_key,
        "tokens": tokens,
        "number": active_user["number"],
        "subscriber_id": sub_id,
        "subscription_type": sub_type,
        "balance": balance_remaining,
        "balance_expired_at": balance_expired_at,
        "point_info": point_info,
        "display_quota": display_quota,
        "segments": segments_data
    }
    last_fetch_time = now
    return cached_user_context


def show_main_menu(profile, display_quota, segments):
    clear_screen()
    theme = get_theme()
    expired_at_dt = datetime.fromtimestamp(profile["balance_expired_at"]).strftime("%Y-%m-%d %H:%M:%S")
    pulsa_str = get_rupiah(profile["balance"])

    # Informasi Akun
    info_table = Table.grid(padding=(0, 1))
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_row(" Nomor", f": 📞 [bold {theme['text_body']}]{profile['number']}[/]")
    info_table.add_row(" Type", f": 🧾 [{theme['text_body']}]{profile['subscription_type']} ({profile['subscriber_id']})[/]")
    info_table.add_row(" Pulsa", f": 💰 Rp [{theme['text_money']}]{pulsa_str}[/]")
    info_table.add_row(" Kuota", f": 📊 [{theme['text_date']}]{display_quota}[/]")
    info_table.add_row(" Tiering", f": 🏅 [{theme['text_date']}]{profile['point_info']}[/]")
    info_table.add_row(" Masa Aktif", f": ⏳ [{theme['text_date']}]{expired_at_dt}[/]")

    console.print(Panel(info_table, title=f"[{theme['text_title']}]✨Informasi Akun✨[/]", title_align="center", border_style=theme["border_info"], padding=(1, 2), expand=True))

    # Paket Spesial
    special_packages = segments.get("special_packages", [])
    if special_packages:
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
        console.print(
            Panel(
                Align.center(special_text),
                border_style=theme["border_warning"],
                padding=(0, 2),
                width=panel_width
            )
        )

        console.print(Align.center(
            f"[{theme['text_sub']}]Pilih [S] untuk lihat semua paket spesial[/{theme['text_sub']}]"
        ))


    # Menu Utama
    menu_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    menu_table.add_column("Kode", justify="right", style=theme["text_key"], width=6)
    menu_table.add_column("Aksi", style=theme["text_body"])
    #menu_table.add_row("S", "🎁 Lihat Paket Special For You")
    menu_table.add_row("1", "🔐 Login/Ganti akun")
    menu_table.add_row("2", "📑 Lihat Paket Saya")
    menu_table.add_row("3", "📜 Riwayat Transaksi")
    menu_table.add_row("4", "🎁 Tukar Point Reward")
    menu_table.add_row("5", "🔥 Beli Paket Hot Promo")
    menu_table.add_row("6", "🔥 Beli Paket Hot Promo-2")
    menu_table.add_row("7", "🔍 Beli Paket Berdasarkan Family Code")
    menu_table.add_row("8", "💾 Simpan/Kelola Family Code")
    menu_table.add_row("", "")
    menu_table.add_row("9", "🧪 Beli/Buat Paket Bundle (multi)")
    menu_table.add_row("10", "🛒 Beli Semua Paket dalam Family Code")
    menu_table.add_row("11", "🔁 Order berulang dari Family Code")
    menu_table.add_row("00", "⭐ Bookmark Paket")
    menu_table.add_row("", "")
    menu_table.add_row("77", f"[{theme['border_warning']}]📢 Info Unlock Code [/]")  
    menu_table.add_row("88", f"[{theme['text_sub']}]🎨 Ganti Tema CLI [/]")          
    menu_table.add_row("99", f"[{theme['text_err']}]⛔ Tutup aplikasi [/]")

    console.print(Panel(menu_table, title=f"[{theme['text_title']}]✨ Menu Utama ✨[/]", title_align="center", border_style=theme["border_primary"], padding=(0, 1), expand=True))

def main():
    global cached_user_context, last_fetch_time

    while True:
        user_context = fetch_user_context()

        if not user_context:
            selected_user_number = show_account_menu()
            if selected_user_number:
                AuthInstance.set_active_user(selected_user_number)
                cached_user_context = None
                last_fetch_time = 0
                clear_screen()
                continue
            else:
                print_panel("⚠️ Error", "Tidak ada akun yang dipilih.")
                pause()
                continue

        show_main_menu(user_context, user_context["display_quota"], user_context["segments"])
        theme = get_theme()
        choice = console.input(f"[{theme['text_sub']}]Pilih menu:[/{theme['text_sub']}] ").strip().lower()

        match choice:
            case "1":
                selected_user_number = show_account_menu()
                if selected_user_number:
                    AuthInstance.set_active_user(selected_user_number)
                    cached_user_context = None
                    last_fetch_time = 0
                    clear_screen()
                else:
                    print_panel("⚠️ Error", "Tidak ada akun yang dipilih.")
                    pause()

            case "2":
                fetch_my_packages()

            case "3":
                show_transaction_history(user_context["api_key"], user_context["tokens"])

            case "4":
                tokens = AuthInstance.get_active_tokens()
                if not tokens:
                    print_panel("⚠️ Error", "Token tidak ditemukan. Silakan login terlebih dahulu.")
                    pause()
                else:
                    run_point_exchange(tokens)

            case "5":
                show_hot_menu()

            case "6":
                show_hot_menu2()

            case "7":
                family_code = console.input(f"[{theme['text_sub']}]Masukkan Family Code:[/{theme['text_sub']}] ").strip()
                if family_code != "99":
                    get_packages_by_family(family_code)

            case "8":
                show_family_menu()

            case "9":
                show_bundle_menu()

            case "10":
                clear_sc()
                console.print(Panel(
                    Align.center("🛒 Beli Semua Paket Yang ada dalam Family Code", vertical="middle"),
                    border_style=theme["border_info"],
                    padding=(1, 2),
                    expand=True
                ))

                family_code = console.input(f"[{theme['text_sub']}]Masukkan Family Code:[/{theme['text_sub']}] ").strip()
                if not family_code or family_code == "99":
                    print_panel("ℹ️ Info", "Pembelian dibatalkan.")
                    pause()
                    continue

                use_decoy_input = console.input(f"[{theme['text_sub']}]Gunakan paket decoy? (y/n):[/{theme['text_sub']}] ").strip().lower()
                use_decoy = use_decoy_input == "y"

                pause_input = console.input(f"[{theme['text_sub']}]Pause setiap pembelian sukses? (y/n):[/{theme['text_sub']}] ").strip().lower()
                pause_on_success = pause_input == "y"

                from rich.text import Text

                confirm_text = Text.from_markup(
                    f"Family Code: [bold]{family_code}[/]\n"
                    f"Gunakan Decoy: {'Ya' if use_decoy else 'Tidak'}\n"
                    f"Pause per pembelian: {'Ya' if pause_on_success else 'Tidak'}\n\n"
                    f"[{theme['text_sub']}]Lanjutkan pembelian semua paket dalam family code ini?[/{theme['text_sub']}]"
                )


                console.print(Panel(confirm_text, title="📦 Konfirmasi", border_style=theme["border_warning"], padding=(1, 2), expand=True))
                lanjut = console.input(f"[{theme['text_sub']}]Lanjutkan? (y/n):[/{theme['text_sub']}] ").strip().lower()
                if lanjut != "y":
                    print_panel("ℹ️ Info", "Pembelian dibatalkan.")
                    pause()
                    continue

                purchase_by_family(family_code, use_decoy, pause_on_success)

            case "11":
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

            case "00":
                show_bookmark_menu()

            case "77":
                show_donate_menu()

            case "88":
                show_theme_menu()

            case "99":
                print_panel("👋 Sampai Jumpa", "Aplikasi ditutup")
                sys.exit(0)

            case "s":
                special_packages = user_context.get("segments", {}).get("special_packages", [])
                if special_packages:
                    result = show_special_for_you_menu(user_context["tokens"], special_packages)
                    if result in ("MAIN", "BACK"):
                        continue
                else:
                    print_panel("ℹ️ Info", "Tidak ada paket Special For You yang tersedia saat ini.")
                    pause()

            case _:
                print_panel("⚠️ Error", "Pilihan tidak valid.")
                pause()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_panel("👋 Keluar", "Aplikasi dihentikan oleh pengguna.")
