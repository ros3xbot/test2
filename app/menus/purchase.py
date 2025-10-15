import time
import requests
from random import randint

from app.client.balance import settlement_balance
from app.client.encrypt import BASE_CRYPTO_URL
from app.client.engsel import get_family, get_package_details
from app.menus.util import pause
from app.service.auth import AuthInstance
from app.type_dict import PaymentItem
from app.config.theme_config import get_theme
from rich.text import Text
from rich.panel import Panel
from rich.table import Table
from rich.console import Console
from app.menus.util_helper import print_panel, get_rupiah

console = Console()
theme = get_theme()


def purchase_by_family(
        family_code: str,
        use_decoy: bool,
        pause_on_success: bool = True,
        token_confirmation_idx: int = 0,
):
    theme = get_theme()
    api_key = AuthInstance.api_key
    tokens: dict = AuthInstance.get_active_tokens() or {}

    decoy_package_detail = None
    if use_decoy:
        url = BASE_CRYPTO_URL + "/decoyxcp"
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print_panel("⚠️ Error", "Gagal mengambil data decoy package.")
            pause()
            return None

        decoy_data = response.json()
        decoy_package_detail = get_package_details(
            api_key,
            tokens,
            decoy_data["family_code"],
            decoy_data["variant_code"],
            decoy_data["order"],
            decoy_data["is_enterprise"],
            decoy_data["migration_type"],
        )

        balance_treshold = decoy_package_detail["package_option"]["price"]
        print_panel("⚠️ Warning", f"Pastikan sisa balance KURANG DARI Rp {get_rupiah(balance_treshold)}")
        balance_answer = input("Apakah anda yakin ingin melanjutkan pembelian? (y/n): ").strip().lower()
        if balance_answer != "y":
            print_panel("Info", "Pembelian dibatalkan oleh user.")
            pause()
            return None

    family_data = get_family(api_key, tokens, family_code)
    if not family_data:
        print_panel("⚠️ Error", f"Gagal mengambil data family untuk kode: {family_code}")
        pause()
        return None

    family_name = family_data["package_family"]["name"]
    variants = family_data["package_variants"]

    successful_purchases = []
    packages_count = sum(len(v["package_options"]) for v in variants)
    purchase_count = 0

    for variant in variants:
        variant_name = variant["name"]
        for option in variant["package_options"]:
            tokens = AuthInstance.get_active_tokens()
            option_name = option["name"]
            option_order = option["order"]
            option_price = option["price"]
            purchase_count += 1

            console.print(Panel(
                f"[bold]{purchase_count}/{packages_count}[/] - [green]{variant_name}[/] | [cyan]{option_order}. {option_name}[/] - Rp {get_rupiah(option_price)}",
                title="🛒 Proses Pembelian",
                border_style=theme["border_info"],
                padding=(0, 1),
                expand=True
            ))

            try:
                target_package_detail = get_package_details(
                    api_key,
                    tokens,
                    family_code,
                    variant["package_variant_code"],
                    option["order"],
                    None,
                    None,
                )
            except Exception as e:
                print_panel("⚠️ Error", f"Gagal mengambil detail paket: {e}")
                continue

            payment_items = [
                PaymentItem(
                    item_code=target_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=target_package_detail["package_option"]["price"],
                    item_name=str(randint(1000, 9999)) + target_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=target_package_detail["token_confirmation"],
                )
            ]

            if use_decoy and decoy_package_detail:
                payment_items.append(
                    PaymentItem(
                        item_code=decoy_package_detail["package_option"]["package_option_code"],
                        product_type="",
                        item_price=decoy_package_detail["package_option"]["price"],
                        item_name=str(randint(1000, 9999)) + decoy_package_detail["package_option"]["name"],
                        tax=0,
                        token_confirmation=decoy_package_detail["token_confirmation"],
                    )
                )

            overwrite_amount = target_package_detail["package_option"]["price"]
            if use_decoy and decoy_package_detail:
                overwrite_amount += decoy_package_detail["package_option"]["price"]

            try:
                res = settlement_balance(
                    api_key,
                    tokens,
                    payment_items,
                    "BUY_PACKAGE",
                    False,
                    overwrite_amount,
                )

                if res and res.get("status", "") != "SUCCESS":
                    error_msg = res.get("message", "Unknown error")
                    if "Bizz-err.Amount.Total" in error_msg:
                        error_msg_arr = error_msg.split("=")
                        valid_amount = int(error_msg_arr[1].strip())
                        console.print(f"[yellow]Jumlah disesuaikan ke Rp {get_rupiah(valid_amount)}[/]")
                        res = settlement_balance(
                            api_key,
                            tokens,
                            payment_items,
                            "BUY_PACKAGE",
                            False,
                            valid_amount,
                        )

                if res and res.get("status", "") == "SUCCESS":
                    successful_purchases.append(f"{variant_name}|{option_order}. {option_name} - {option_price}")
                    print_panel("✅ Sukses", f"Pembelian berhasil: {variant_name} - {option_name}")
                    if pause_on_success:
                        pause()
                else:
                    print_panel("❌ Gagal", f"Pembelian gagal: {variant_name} - {option_name}")
                    if pause_on_success:
                        pause()

            except Exception as e:
                print_panel("⚠️ Error", f"Gagal membuat order: {e}")
                continue

    summary_text = Text()
    summary_text.append(f"Total pembelian sukses untuk family [bold]{family_name}[/]: {len(successful_purchases)}\n", style=theme["text_body"])
    if successful_purchases:
        for purchase in successful_purchases:
            summary_text.append(f"• {purchase}\n", style=theme["text_body"])

    console.print(Panel(summary_text, title="📦 Ringkasan Pembelian", border_style=theme["border_success"], padding=(1, 2), expand=True))
    pause()


def purchase_n_times(
        n: int,
        family_code: str,
        variant_code: str,
        option_order: int,
        use_decoy: bool,
        delay_seconds: int = 0,
        pause_on_success: bool = False,
        token_confirmation_idx: int = 0,
):
    theme = get_theme()
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens() or {}

    decoy_package_detail = None
    if use_decoy:
        url = BASE_CRYPTO_URL + "/decoyxcp"
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            print_panel("⚠️ Error", "Gagal mengambil data decoy package.")
            pause()
            return None

        decoy_data = response.json()
        decoy_package_detail = get_package_details(
            api_key, tokens,
            decoy_data["family_code"],
            decoy_data["variant_code"],
            decoy_data["order"],
            decoy_data["is_enterprise"],
            decoy_data["migration_type"],
        )

        balance_treshold = decoy_package_detail["package_option"]["price"]
        print_panel("⚠️ Warning", f"Pastikan sisa balance KURANG DARI Rp {get_rupiah(balance_treshold)}")
        balance_answer = input("Apakah anda yakin ingin melanjutkan pembelian? (y/n): ").strip().lower()
        if balance_answer != "y":
            print_panel("Info", "Pembelian dibatalkan oleh user.")
            pause()
            return None

    family_data = get_family(api_key, tokens, family_code)
    if not family_data:
        print_panel("⚠️ Error", f"Gagal mengambil data family untuk kode: {family_code}")
        pause()
        return None

    family_name = family_data["package_family"]["name"]
    variants = family_data["package_variants"]
    target_variant = next((v for v in variants if v["package_variant_code"] == variant_code), None)
    if not target_variant:
        print_panel("⚠️ Error", f"Variant code {variant_code} tidak ditemukan dalam family {family_name}.")
        pause()
        return None

    target_option = next((o for o in target_variant["package_options"] if o["order"] == option_order), None)
    if not target_option:
        print_panel("⚠️ Error", f"Option order {option_order} tidak ditemukan dalam variant {target_variant['name']}.")
        pause()
        return None

    option_name = target_option["name"]
    option_price = target_option["price"]
    successful_purchases = []

    for i in range(n):
        console.print(Panel(
            f"[bold]{i+1}/{n}[/] - [green]{target_variant['name']}[/] | [cyan]{option_order}. {option_name}[/] - Rp {get_rupiah(option_price)}",
            title="🛒 Proses Pembelian",
            border_style=theme["border_info"],
            padding=(0, 1),
            expand=True
        ))

        tokens = AuthInstance.get_active_tokens() or {}
        payment_items = []

        try:
            if use_decoy:
                decoy_package_detail = get_package_details(
                    api_key, tokens,
                    decoy_data["family_code"],
                    decoy_data["variant_code"],
                    decoy_data["order"],
                    decoy_data["is_enterprise"],
                    decoy_data["migration_type"],
                )

            target_package_detail = get_package_details(
                api_key, tokens,
                family_code,
                target_variant["package_variant_code"],
                target_option["order"],
                None,
                None,
            )
        except Exception as e:
            print_panel("⚠️ Error", f"Gagal mengambil detail paket: {e}")
            continue

        payment_items.append(PaymentItem(
            item_code=target_package_detail["package_option"]["package_option_code"],
            product_type="",
            item_price=target_package_detail["package_option"]["price"],
            item_name=str(randint(1000, 9999)) + target_package_detail["package_option"]["name"],
            tax=0,
            token_confirmation=target_package_detail["token_confirmation"],
        ))

        if use_decoy and decoy_package_detail:
            payment_items.append(PaymentItem(
                item_code=decoy_package_detail["package_option"]["package_option_code"],
                product_type="",
                item_price=decoy_package_detail["package_option"]["price"],
                item_name=str(randint(1000, 9999)) + decoy_package_detail["package_option"]["name"],
                tax=0,
                token_confirmation=decoy_package_detail["token_confirmation"],
            ))

        overwrite_amount = target_package_detail["package_option"]["price"]
        if use_decoy and decoy_package_detail:
            overwrite_amount += decoy_package_detail["package_option"]["price"]

        try:
            res = settlement_balance(
                api_key, tokens,
                payment_items,
                "BUY_PACKAGE",
                False,
                overwrite_amount,
            )

            if res and res.get("status", "") != "SUCCESS":
                error_msg = res.get("message", "Unknown error")
                if "Bizz-err.Amount.Total" in error_msg:
                    valid_amount = int(error_msg.split("=")[1].strip())
                    console.print(f"[yellow]Jumlah disesuaikan ke Rp {get_rupiah(valid_amount)}[/]")
                    res = settlement_balance(
                        api_key, tokens,
                        payment_items,
                        "BUY_PACKAGE",
                        False,
                        valid_amount,
                    )

            if res and res.get("status", "") == "SUCCESS":
                successful_purchases.append(f"{target_variant['name']}|{option_order}. {option_name} - {option_price}")
                print_panel("✅ Sukses", f"Pembelian berhasil: {option_name}")
                if pause_on_success:
                    pause()
            else:
                print_panel("❌ Gagal", f"Pembelian gagal: {option_name}")
                if pause_on_success:
                    pause()

        except Exception as e:
            print_panel("⚠️ Error", f"Gagal membuat order: {e}")
            continue

        if delay_seconds > 0 and i < n - 1:
            console.print(f"[dim]Menunggu {delay_seconds} detik sebelum pembelian berikutnya...[/]")
            time.sleep(delay_seconds)

    summary_text = Text()
    summary_text.append(f"Total pembelian sukses: {len(successful_purchases)}/{n}\n", style=theme["text_body"])
    summary_text.append(f"Family: {family_name}\n", style=theme["text_body"])
    summary_text.append(f"Variant: {target_variant['name']}\n", style=theme["text_body"])
    summary_text.append(f"Option: {option_order}. {option_name} - Rp {get_rupiah(option_price)}\n\n", style=theme["text_body"])
    for idx, purchase in enumerate(successful_purchases):
        summary_text.append(f"{idx + 1}. {purchase}\n", style=theme["text_body"])

    console.print(Panel(summary_text, title="📦 Ringkasan Pembelian", border_style=theme["border_success"], padding=(1, 2), expand=True))
    pause()
    return True


def purchase_loop(
        loop: int,
        family_code: str,
        order: int,
        use_decoy: bool,
        delay: int = 0,
        pause_on_success: bool = False,
):
    theme = get_theme()
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens() or {}

    successful_purchases = []
    family_name = None
    target_variant = None

    for i in range(loop):
        console.print(Panel(
            f"[bold]{i+1}/{loop}[/] - [cyan]Mencoba pembelian paket...[/]",
            title="🛒 Loop Pembelian",
            border_style=theme["border_info"],
            padding=(0, 1),
            expand=True
        ))

        family_data = get_family(api_key, tokens, family_code)
        if not family_data:
            print_panel("⚠️ Error", f"Gagal mengambil data family untuk kode: {family_code}")
            pause()
            return False

        family_name = family_data["package_family"]["name"]
        target_variant = None
        target_option = None

        for variant in family_data["package_variants"]:
            for option in variant["package_options"]:
                if option["order"] == order:
                    target_variant = variant
                    target_option = option
                    break
            if target_option:
                break

        if not target_variant or not target_option:
            print_panel("⚠️ Error", f"Paket dengan order {order} tidak ditemukan dalam family {family_code}")
            pause()
            return False

        option_name = target_option["name"]
        option_price = target_option["price"]
        variant_code = target_variant["package_variant_code"]

        decoy_package_detail = None
        if use_decoy:
            url = "https://me.mashu.lol/pg-decoy-xcp.json"
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                print_panel("⚠️ Error", "Gagal mengambil data decoy package.")
                pause()
                return False

            decoy_data = response.json()
            decoy_package_detail = get_package_details(
                api_key, tokens,
                decoy_data["family_code"],
                decoy_data["variant_code"],
                decoy_data["order"],
                decoy_data["is_enterprise"],
                decoy_data["migration_type"],
            )

            balance_treshold = decoy_package_detail["package_option"]["price"]
            print_panel("⚠️ Warning", f"Pastikan sisa balance KURANG DARI Rp {get_rupiah(balance_treshold)}")

        try:
            target_package_detail = get_package_details(
                api_key, tokens,
                family_code,
                variant_code,
                order,
                None,
                None,
            )
        except Exception as e:
            print_panel("⚠️ Error", f"Gagal mengambil detail paket: {e}")
            return False

        payment_items = [
            PaymentItem(
                item_code=target_package_detail["package_option"]["package_option_code"],
                product_type="",
                item_price=target_package_detail["package_option"]["price"],
                item_name=str(order) + target_package_detail["package_option"]["name"],
                tax=0,
                token_confirmation=target_package_detail["token_confirmation"],
            )
        ]

        if use_decoy and decoy_package_detail:
            payment_items.append(
                PaymentItem(
                    item_code=decoy_package_detail["package_option"]["package_option_code"],
                    product_type="",
                    item_price=decoy_package_detail["package_option"]["price"],
                    item_name=str(decoy_data["order"]) + decoy_package_detail["package_option"]["name"],
                    tax=0,
                    token_confirmation=decoy_package_detail["token_confirmation"],
                )
            )

        overwrite_amount = target_package_detail["package_option"]["price"]
        if use_decoy and decoy_package_detail:
            overwrite_amount += decoy_package_detail["package_option"]["price"]

        try:
            res = settlement_balance(
                api_key, tokens,
                payment_items,
                "BUY_PACKAGE",
                False,
                overwrite_amount,
            )

            if res and res.get("status", "") != "SUCCESS":
                error_msg = res.get("message", "Unknown error")
                console.print(f"[red]Gagal: {error_msg}[/]")
                if "Bizz-err.Amount.Total" in error_msg:
                    valid_amount = int(error_msg.split("=")[1].strip())
                    console.print(f"[yellow]Jumlah disesuaikan ke Rp {get_rupiah(valid_amount)}[/]")
                    res = settlement_balance(
                        api_key, tokens,
                        payment_items,
                        "BUY_PACKAGE",
                        False,
                        valid_amount,
                    )

            if res and res.get("status", "") == "SUCCESS":
                successful_purchases.append(f"{target_variant['name']}|{option_name} - {option_price}")
                print_panel("✅ Sukses", f"Pembelian berhasil: {option_name}")
                if pause_on_success:
                    choice = input("Lanjut Dor? (Y/N): ").strip().lower()
                    if choice == 'n':
                        return False
            else:
                print_panel("❌ Gagal", f"Pembelian gagal: {option_name}")
                if pause_on_success:
                    choice = input("Lanjut Dor? (Y/N): ").strip().lower()
                    if choice == 'n':
                        return False

        except Exception as e:
            print_panel("⚠️ Error", f"Gagal membuat order: {e}")
            return False

        if delay > 0 and i < loop - 1:
            console.print(f"[dim]Menunggu {delay} detik sebelum pembelian berikutnya...[/]")
            time.sleep(delay)

    summary_text = Text()
    summary_text.append(f"Total pembelian sukses: {len(successful_purchases)}/{loop}\n", style=theme["text_body"])
    summary_text.append(f"Family: {family_name}\n", style=theme["text_body"])
    summary_text.append(f"Variant: {target_variant['name']}\n\n", style=theme["text_body"])
    for idx, purchase in enumerate(successful_purchases):
        summary_text.append(f"{idx + 1}. {purchase}\n", style=theme["text_body"])

    console.print(Panel(summary_text, title="📦 Ringkasan Pembelian", border_style=theme["border_success"], padding=(1, 2), expand=True))
    pause()
    return True

