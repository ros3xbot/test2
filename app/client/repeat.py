import time
import requests
from app.service.auth import AuthInstance
from app.client.engsel import get_package_details
from app.client.balance import settlement_balance
from app.client.qris import show_qris_payment
from app.menus.util_helper import print_panel, get_rupiah

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

def purchase_n_times(n, family_code, variant_code, option_order, use_decoy=False, delay_seconds=0, pause_on_success=True):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

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
                decoy_detail = fetch_decoy_detail(api_key, tokens, "https://me.mashu.lol/pg-decoy-xcp.json")
                decoy_option = decoy_detail["package_option"]
                payment_items.append({
                    "item_code": decoy_option["package_option_code"],
                    "product_type": "",
                    "item_price": decoy_option["price"],
                    "item_name": decoy_option["name"],
                    "tax": 0,
                    "token_confirmation": decoy_detail["token_confirmation"]
                })
                total_amount += decoy_option["price"]

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

def purchase_qris_n_times(n, cart_items, use_decoy=False, delay_seconds=0):
    api_key = AuthInstance.api_key
    tokens = AuthInstance.get_active_tokens()

    for i in range(n):
        try:
            print_panel("🔁 QRIS", f"Iterasi ke-{i+1} sedang diproses...")
            items = cart_items.copy()
            if use_decoy:
                decoy_detail = fetch_decoy_detail(api_key, tokens, "https://me.mashu.lol/pg-decoy-edu.json")
                decoy_option = decoy_detail["package_option"]
                items.append({
                    "item_code": decoy_option["package_option_code"],
                    "product_type": "",
                    "item_price": decoy_option["price"],
                    "item_name": decoy_option["name"],
                    "tax": 0,
                    "token_confirmation": decoy_detail["token_confirmation"]
                })

            show_qris_payment(api_key, tokens, items, "SHARE_PACKAGE", True, token_confirmation_idx=1 if use_decoy else 0)
            input("✅ QRIS ditampilkan. Tekan Enter untuk lanjut...")
            if delay_seconds > 0 and i < n - 1:
                time.sleep(delay_seconds)

        except Exception as e:
            print_panel("⚠️ Error", f"QRIS ke-{i+1} gagal: {e}")
            continue
