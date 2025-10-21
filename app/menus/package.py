import json
import sys
import requests
from app.service.auth import AuthInstance
from app.client.engsel import get_family, get_package, get_addons, get_package_details, send_api_request
from app.client.engsel2 import unsubscribe
from app.service.bookmark import BookmarkInstance
from app.client.purchase import settlement_bounty, settlement_loyalty
from app.menus.util import clear_screen, pause, display_html
from app.menus.util_helper import print_panel, get_rupiah, live_loading
from app.menus.purchase import purchase_n_times
from app.client.qris import show_qris_payment
from app.client.ewallet import show_multipayment
from app.client.balance import settlement_balance
from app.type_dict import PaymentItem
from app.config.theme_config import get_theme

from rich.console import Console,Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.box import MINIMAL_DOUBLE_HEAD
from rich.align import Align
from rich.markup import escape

console = Console()


def show_package_details(api_key, tokens, package_option_code, is_enterprise, option_order=-1):
    clear_screen()
    package = get_package(api_key, tokens, package_option_code)
    if not package:
        print_panel("⚠️ Error", "Gagal memuat detail paket.")
        pause()
        return False

    price = package["package_option"]["price"]
    token_confirmation = package["token_confirmation"]
    ts_to_sign = package["timestamp"]
    payment_for = package["package_family"].get("payment_for", "") or "BUY_PACKAGE"
    variant_name = package.get("package_detail_variant", {}).get("name", "")
    option_name = package.get("package_option", {}).get("name", "")

    payment_items = [
        PaymentItem(
            item_code=package_option_code,
            product_type="",
            item_price=price,
            item_name=f"{variant_name} {option_name}".strip(),
            tax=0,
            token_confirmation=token_confirmation,
        )
    ]

    render_package_preview(package, option_order)
    result = handle_package_interaction(
        api_key, tokens, package, payment_items,
        is_enterprise, option_order,
        price, payment_for, token_confirmation, ts_to_sign
    )

    if result == "MAIN":
        return "MAIN"
    return result

def render_package_preview(package, option_order):
    theme = get_theme()
    option = package.get("package_option", {})
    family = package.get("package_family", {})
    variant = package.get("package_detail_variant", {})
    price = option.get("price", 0)
    formatted_price = get_rupiah(price)
    validity = option.get("validity", "-")
    point = option.get("point", "-")
    plan_type = family.get("plan_type", "-")
    payment_for = family.get("payment_for", "") or "BUY_PACKAGE"
    detail = display_html(option.get("tnc", ""))

    option_name = option.get("name", "")
    family_name = family.get("name", "")
    variant_name = variant.get("name", "")
    title = f"{family_name} - {variant_name} - {option_name}".strip()

    info_table = Table.grid(padding=(0, 1))
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_column(justify="left")
    info_table.add_row("Nama", f": [bold {theme['text_body']}]{title}[/]")
    info_table.add_row("Harga", f": Rp [{theme['text_money']}]{formatted_price}[/]")
    info_table.add_row("Masa Aktif", f": [{theme['text_date']}]{validity}[/]")
    info_table.add_row("Point", f": [{theme['text_body']}]{point}[/]")
    info_table.add_row("Plan Type", f": [{theme['text_body']}]{plan_type}[/]")
    info_table.add_row("Payment For", f": [{theme['text_body']}]{payment_for}[/]")

    console.print(Panel(info_table, title="📦 Detail Paket", border_style=theme["border_info"], expand=True))

    benefits = option.get("benefits", [])
    if benefits:
        benefit_table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        benefit_table.add_column("Nama", style=theme["text_body"])
        benefit_table.add_column("Jenis", style=theme["text_body"])
        benefit_table.add_column("Unli", style=theme["border_info"], justify="center")
        benefit_table.add_column("Total", style=theme["text_body"], justify="right")

        for b in benefits:
            dt = b["data_type"]
            total = b["total"]
            is_unli = b["is_unlimited"]

            if is_unli:
                total_str = {"VOICE": "menit", "TEXT": "SMS", "DATA": "kuota"}.get(dt, dt)
            else:
                if dt == "VOICE":
                    total_str = f"{total / 60:.0f} menit"
                elif dt == "TEXT":
                    total_str = f"{total} SMS"
                elif dt == "DATA":
                    if total >= 1_000_000_000:
                        total_str = f"{total / (1024 ** 3):.2f} GB"
                    elif total >= 1_000_000:
                        total_str = f"{total / (1024 ** 2):.2f} MB"
                    elif total >= 1_000:
                        total_str = f"{total / 1024:.2f} KB"
                    else:
                        total_str = f"{total} B"
                else:
                    total_str = f"{total} ({dt})"

            benefit_table.add_row(b["name"], dt, "YES" if is_unli else "-", total_str)

        console.print(Panel(benefit_table, title="🎁 Benefit Paket", border_style=theme["border_success"], padding=(0, 0), expand=True))

    console.print(Panel(detail, title="📜 Syarat & Ketentuan", border_style=theme["border_warning"], expand=True))

    option_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    option_table.add_column(justify="right", style=theme["text_key"], width=6)
    option_table.add_column(justify="left", style=theme["text_body"])
    option_table.add_row("1", "💰 Beli dengan Pulsa")
    option_table.add_row("2", "💳 E-Wallet")
    option_table.add_row("3", "📱 QRIS")
    option_table.add_row("4", "💰 Pulsa + Decoy XCP")
    option_table.add_row("5", "💰 Pulsa + Decoy XCP V2")
    option_table.add_row("6", "📱 QRIS + Decoy Edu")
    option_table.add_row("7", "🔁 Pulsa N kali")
    if payment_for == "REDEEM_VOUCHER":
        option_table.add_row("B", "🎁 Ambil sebagai bonus")
        option_table.add_row("L", "⭐ Beli dengan Poin")
    if option_order != -1:
        option_table.add_row("0", "🔖 Tambah ke Bookmark")
    option_table.add_row("00", f"[{theme['text_sub']}]Kembali ke daftar paket[/]")
    option_table.add_row("99", f"[{theme['text_err']}]Kembali ke menu utama[/]")

    console.print(Panel(option_table, title="🛒 Opsi Pembelian", border_style=theme["border_info"], expand=True))

def handle_decoy_payment(api_key, tokens, payment_items, price, payment_for, decoy_url, method="balance", token_idx=-1):
    theme = get_theme()

    try:
        response = requests.get(decoy_url, timeout=30)
        response.raise_for_status()
        decoy_data = response.json()
    except Exception:
        print_panel("❌ Error", "Gagal mengambil data decoy package.", theme.get("border_error", "red"))
        pause()
        return False

    decoy_detail = get_package_details(
        api_key,
        tokens,
        decoy_data["family_code"],
        decoy_data["variant_code"],
        decoy_data["order"],
        decoy_data["is_enterprise"],
        decoy_data["migration_type"],
    )

    payment_items.append(
        PaymentItem(
            item_code=decoy_detail["package_option"]["package_option_code"],
            product_type="",
            item_price=decoy_detail["package_option"]["price"],
            item_name=decoy_detail["package_option"]["name"],
            tax=0,
            token_confirmation=decoy_detail["token_confirmation"],
        )
    )

    total_amount = price + decoy_detail["package_option"]["price"]

    if method == "qris":
        console.print(Panel(
            f"Harga Paket Utama: Rp {price}\n"
            f"Harga Paket Decoy: Rp {decoy_detail['package_option']['price']}\n"
            f"Silahkan sesuaikan amount (trial & error)",
            title="📊 Info QRIS Decoy",
            border_style=theme.get("border_info", "cyan"),
            padding=(1, 2),
            expand=True
        ))

        show_qris_payment(
            api_key,
            tokens,
            payment_items,
            payment_for,
            True,
            token_confirmation_idx=token_idx
        )

        input("Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL. Tekan Enter untuk kembali.")
        return True

    else:
        res = settlement_balance(
            api_key,
            tokens,
            payment_items,
            payment_for,
            False,
            total_amount,
            token_confirmation_idx=token_idx
        )

        if res and res.get("status", "") != "SUCCESS":
            msg = res.get("message", "")
            if "Bizz-err.Amount.Total" in msg:
                try:
                    valid_amount = int(msg.split("=")[1].strip())
                    print_panel("⚠️ Penyesuaian", f"Total disesuaikan ke Rp {valid_amount}", theme.get("border_warning", "yellow"))
                    res = settlement_balance(
                        api_key,
                        tokens,
                        payment_items,
                        "BUY_PACKAGE",
                        False,
                        valid_amount,
                        token_confirmation_idx=-1
                    )
                except Exception:
                    print_panel("❌ Error", "Gagal parsing fallback amount.", theme.get("border_error", "red"))

        if res and res.get("status", "") == "SUCCESS":
            print_panel("✅ Sukses", "Pembelian berhasil dilakukan!", theme.get("border_success", "green"))
        else:
            print_panel("❌ Gagal", res.get("message", "Transaksi gagal."), theme.get("border_error", "red"))

        pause()
        return True

def handle_package_interaction(api_key, tokens, package, payment_items, is_enterprise, option_order, price, payment_for, token_confirmation, ts_to_sign):
    theme = get_theme()
    variant_name = package.get("package_detail_variant", {}).get("name", "")
    option_name = package.get("package_option", {}).get("name", "")
    family_code = package.get("package_family", {}).get("package_family_code", "")
    variant_code = package.get("package_detail_variant", {}).get("package_variant_code", "")

    while True:
        choice = console.input(f"[{theme['text_sub']}]Pilihan:[/{theme['text_sub']}] ").strip().lower()

        if choice == "00":
            return False
        if choice == "99":
            print_panel("🔙 Navigasi", "Kembali ke menu utama...", theme["border_info"])
            return "MAIN"

        if choice == "0" and option_order != -1:
            success = BookmarkInstance.add_bookmark(
                family_code=family_code,
                family_name=package.get("package_family", {}).get("name", ""),
                is_enterprise=is_enterprise,
                variant_name=variant_name,
                option_name=option_name,
                order=option_order,
            )
            msg = "Paket berhasil ditambahkan ke bookmark." if success else "Paket sudah ada di bookmark."
            print_panel("🔖 Bookmark", msg, theme["border_success"])
            pause()
            continue

        if choice == "1":
            settlement_balance(api_key, tokens, payment_items, payment_for, True)
            print_panel("✅ Info", "Silahkan cek hasil pembelian di aplikasi MyXL.", theme["border_success"])
            pause()
            return True

        elif choice == "2":
            show_multipayment(api_key, tokens, payment_items, payment_for, True)
            print_panel("✅ Info", "Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL.", theme["border_success"])
            pause()
            return True

        elif choice == "3":
            show_qris_payment(api_key, tokens, payment_items, payment_for, True)
            print_panel("✅ Info", "Silahkan lakukan pembayaran & cek hasil pembelian di aplikasi MyXL.", theme["border_success"])
            pause()
            return True

        elif choice == "4":
            return handle_decoy_payment(
                api_key, tokens, payment_items, price,
                payment_for,
                decoy_url="https://me.mashu.lol/pg-decoy-xcp.json",
                method="balance",
                token_idx=-1
            )
        
        elif choice == "5":
            return handle_decoy_payment(
                api_key, tokens, payment_items, price,
                payment_for="🤫",
                decoy_url="https://me.mashu.lol/pg-decoy-xcp.json",
                method="balance",
                token_idx=1
            )
        
        elif choice == "6":
            return handle_decoy_payment(
                api_key, tokens, payment_items, price,
                payment_for="SHARE_PACKAGE",
                decoy_url="https://me.mashu.lol/pg-decoy-edu.json",
                method="qris",
                token_idx=1
            )

        elif choice == "7":
            use_decoy = console.input("Gunakan decoy package? (y/n): ").strip().lower() == "y"
            n_times = console.input("Jumlah pembelian (misal: 3): ").strip()
            delay = console.input("Delay antar pembelian (detik): ").strip()

            try:
                n = int(n_times)
                d = int(delay)
                if n < 1:
                    raise ValueError
            except:
                print_panel("❌ Error", "Input tidak valid.", theme["border_error"])
                #pause()
                continue

            purchase_n_times(
                n,
                family_code=family_code,
                variant_code=variant_code,
                option_order=option_order,
                use_decoy=use_decoy,
                delay_seconds=d,
                pause_on_success=False,
            )
            pause()
            return True

        elif choice == "b":
            settlement_bounty(
                api_key=api_key,
                tokens=tokens,
                token_confirmation=token_confirmation,
                ts_to_sign=ts_to_sign,
                payment_target=payment_items[0].item_code,
                price=price,
                item_name=variant_name
            )
            print_panel("✅ Info", "Silahkan cek hasil pengambilan bonus di aplikasi MyXL.", theme["border_success"])
            pause()
            return True

        elif choice == "l":
            settlement_loyalty(
                api_key=api_key,
                tokens=tokens,
                token_confirmation=token_confirmation,
                ts_to_sign=ts_to_sign,
                payment_target=payment_items[0].item_code,
                price=price,
            )
            print_panel("✅ Info", "Silahkan cek hasil pembelian poin di aplikasi MyXL.", theme["border_success"])
            pause()
            return True

        else:
            print_panel("❌ Error", "Pilihan tidak dikenali.", theme["border_error"])

def get_packages_by_family(
    family_code: str,
    is_enterprise: bool | None = None,
    migration_type: str | None = None,
    return_package_detail: bool = False
):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    theme = get_theme()

    if not tokens:
        print_panel("⚠️ Error", "Token pengguna aktif tidak ditemukan.")
        pause()
        return None if return_package_detail else "BACK"

    data = get_family(api_key, tokens, family_code, is_enterprise, migration_type)
    if not data:
        print_panel("⚠️ Error", "Gagal memuat data paket family.")
        pause()
        return None if return_package_detail else "BACK"

    packages = []
    for idx, variant in enumerate(data["package_variants"]):
        for option in variant["package_options"]:
            packages.append({
                "number": len(packages) + 1,
                "variant_name": variant["name"],
                "option_name": option["name"],
                "price": option["price"],
                "code": option["package_option_code"],
                "option_order": option["order"]
            })

    while True:
        clear_screen()

        info_text = Text()
        info_text.append("Nama: ", style=theme["text_body"])
        info_text.append(f"{data['package_family']['name']}\n", style=theme["text_value"])
        info_text.append("Kode: ", style=theme["text_body"])
        info_text.append(f"{family_code}\n", style=theme["border_warning"])
        info_text.append("Tipe: ", style=theme["text_body"])
        info_text.append(f"{data['package_family']['package_family_type']}\n", style=theme["text_value"])
        info_text.append("Jumlah Varian: ", style=theme["text_body"])
        info_text.append(f"{len(data['package_variants'])}\n", style=theme["text_value"])

        console.print(Panel(
            info_text,
            title=f"[{theme['text_title']}]📦 Info Paket Family[/]",
            border_style=theme["border_info"],
            padding=(0, 2),
            expand=True
        ))

        table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
        table.add_column("No", justify="right", style=theme["text_key"], width=4)
        table.add_column("Varian", style=theme["text_body"])
        table.add_column("Nama Paket", style=theme["text_body"])
        table.add_column("Harga", style=theme["text_money"], justify="right")

        for pkg in packages:
            table.add_row(
                str(pkg["number"]),
                pkg["variant_name"],
                pkg["option_name"],
                get_rupiah(pkg["price"])
            )

        console.print(Panel(
            table,
            border_style=theme["border_primary"],
            padding=(0, 1),
            expand=True
        ))

        nav = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav.add_column(justify="right", style=theme["text_key"], width=6)
        nav.add_column(style=theme["text_body"])
        nav.add_row("00", f"[{theme['text_sub']}]Kembali ke menu sebelumnya[/]")
        nav.add_row("000", f"[{theme['text_err']}]Kembali ke menu utama[/]")

        console.print(Panel(
            nav,
            border_style=theme["border_info"],
            padding=(0, 1),
            expand=True
        ))

        choice = console.input(f"[{theme['text_sub']}]Pilih paket (nomor):[/{theme['text_sub']}] ").strip()
        if choice == "00":
            return "BACK" if not return_package_detail else None
        elif choice == "000":
            return "MAIN"

        elif not choice.isdigit():
            print_panel("⚠️ Error", "Input tidak valid. Masukkan nomor paket.")
            pause()
            continue

        selected = next((p for p in packages if p["number"] == int(choice)), None)
        if not selected:
            print_panel("⚠️ Error", "Nomor paket tidak ditemukan.")
            pause()
            continue

        if return_package_detail:
            variant_code = next((v["package_variant_code"] for v in data["package_variants"] if v["name"] == selected["variant_name"]), None)
            detail = get_package_details(
                api_key, tokens,
                family_code,
                variant_code,
                selected["option_order"],
                is_enterprise
            )
            if detail:
                display_name = f"{data['package_family']['name']} - {selected['variant_name']} - {selected['option_name']}"
                return detail, display_name
            else:
                print_panel("⚠️ Error", "Gagal mengambil detail paket.")
                pause()
                continue
        else:
            result = show_package_details(
                api_key,
                tokens,
                selected["code"],
                is_enterprise,
                option_order=selected["option_order"]
            )
            if result == "MAIN":
                return "MAIN"
            elif result == "BACK":
                continue
            elif result is True:
                continue


def fetch_my_packages():
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()
    theme = get_theme()

    if not tokens:
        print_panel("⚠️ Error", "Tidak ditemukan token pengguna aktif.")
        pause()
        return "BACK"

    id_token = tokens.get("id_token")
    path = "api/v8/packages/quota-details"
    payload = {
        "is_enterprise": False,
        "lang": "en",
        "family_member_id": ""
    }

    while True:
        clear_screen()

        with live_loading("Mengambil daftar paket aktif Anda...", theme):
            res = send_api_request(api_key, path, payload, id_token, "POST")

        if res.get("status") != "SUCCESS":
            print_panel("⚠️ Error", "Gagal mengambil paket.")
            pause()
            return "BACK"

        quotas = res["data"]["quotas"]
        if not quotas:
            print_panel("Info", "Tidak ada paket aktif ditemukan.")
            pause()
            return "BACK"

        console.print(Panel(
            Align.center("📦 Paket Aktif Saya", vertical="middle"),
            border_style=theme["border_info"],
            padding=(1, 2),
            expand=True
        ))

        my_packages = []
        for num, quota in enumerate(quotas, start=1):
            quota_code = quota["quota_code"]
            group_code = quota["group_code"]
            group_name = quota["group_name"]
            quota_name = quota["name"]
            family_code = "N/A"

            with live_loading(f"Paket #{num}", theme):
                package_details = get_package(api_key, tokens, quota_code)

            if package_details:
                family_code = package_details["package_family"]["package_family_code"]

            benefits = quota.get("benefits", [])
            benefit_table = None
            if benefits:
                benefit_table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
                benefit_table.add_column("Nama", style=theme["text_body"])
                benefit_table.add_column("Jenis", style=theme["text_body"])
                benefit_table.add_column("Kuota", style=theme["text_body"], justify="right")

                for b in benefits:
                    name = b.get("name", "")
                    dt = b.get("data_type", "N/A")
                    r = b.get("remaining", 0)
                    t = b.get("total", 0)

                    if dt == "DATA":
                        def fmt(val):
                            if val >= 1_000_000_000:
                                return f"{val / (1024 ** 3):.2f} GB"
                            elif val >= 1_000_000:
                                return f"{val / (1024 ** 2):.2f} MB"
                            elif val >= 1_000:
                                return f"{val / 1024:.2f} KB"
                            return f"{val} B"
                        r_str = fmt(r)
                        t_str = fmt(t)
                    elif dt == "VOICE":
                        r_str = f"{r / 60:.2f} menit"
                        t_str = f"{t / 60:.2f} menit"
                    elif dt == "TEXT":
                        r_str = f"{r} SMS"
                        t_str = f"{t} SMS"
                    else:
                        r_str = str(r)
                        t_str = str(t)

                    benefit_table.add_row(name, dt, f"{r_str} / {t_str}")

            package_text = Text()
            package_text.append(f"📦 Paket {num}\n", style="bold")
            package_text.append("Nama: ", style=theme["border_info"])
            package_text.append(f"{quota_name}\n", style=theme["text_sub"])
            package_text.append("Quota Code: ", style=theme["border_info"])
            package_text.append(f"{quota_code}\n", style=theme["text_body"])
            package_text.append("Family Code: ", style=theme["border_info"])
            package_text.append(f"{family_code}\n", style=theme["border_warning"])
            package_text.append("Group Code: ", style=theme["border_info"])
            package_text.append(f"{group_code}\n", style=theme["text_body"])

            panel_content = [package_text]
            if benefit_table:
                panel_content.append(benefit_table)

            console.print(Panel(
                Group(*panel_content),
                border_style=theme["border_primary"],
                padding=(0, 1),
                expand=True
            ))

            my_packages.append({
                "number": num,
                "quota_code": quota_code,
            })

        package_range = f"(1–{len(my_packages)})"
        nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
        nav_table.add_column(justify="right", style=theme["text_key"], width=6)
        nav_table.add_column(style=theme["text_body"])
        nav_table.add_row(package_range, f"[{theme['text_body']}]Pilih nomor paket untuk pembelian ulang")
        nav_table.add_row("00", f"[{theme['text_err']}]Kembali ke menu utama")

        console.print(Panel(
            nav_table,
            border_style=theme["border_info"],
            padding=(0, 1),
            expand=True
        ))

        while True:
            choice = console.input(f"[{theme['text_sub']}]Masukkan nomor paket {package_range} atau 00:[/{theme['text_sub']}] ").strip().lower()
            if choice == "00":
                with live_loading("Kembali ke menu utama...", theme):
                    pass
                return "BACK"

            if not choice.isdigit():
                print_panel("⚠️ Error", "Input tidak valid. Masukkan nomor paket atau 00.")
                continue

            selected_pkg = next((pkg for pkg in my_packages if str(pkg["number"]) == choice), None)
            if not selected_pkg:
                print_panel("⚠️ Error", f"Nomor paket tidak ditemukan. Masukkan angka {package_range} atau 00.")
                continue

            result = show_package_details(api_key, tokens, selected_pkg["quota_code"], False)

            if result == "MAIN":
                return "BACK"
            elif result == "BACK":
                with live_loading("Kembali ke daftar paket...", theme):
                    pass
                break
            elif result is True:
                return "BACK"
