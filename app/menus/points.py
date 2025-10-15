from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.box import MINIMAL_DOUBLE_HEAD
from app.menus.util import clear_screen, pause, display_html
from app.menus.util_helper import print_panel, live_loading, get_rupiah
from app.config.theme_config import get_theme, theme_sets
from app.service.auth import AuthInstance
from app.client.engsel import send_api_request, BASE_API_URL, API_KEY, UA, java_like_timestamp
from app.client.encrypt import encryptsign_xdata, decrypt_xdata
from datetime import datetime, timezone
import requests, json, uuid

console = Console()
theme = get_theme()


def run_point_exchange(tokens: dict):
    theme = get_theme()
    while True:
        result = run_point_exchange_once(tokens)
        if result == "BACK":
            continue
        elif result == "MAIN":
            break
        else:
            break

def run_point_exchange_once(tokens: dict):
    clear_screen()
    theme = get_theme()
    access_code = console.input(f"[{theme['text_sub']}]Masukkan kode akses:[/{theme['text_sub']}] ").strip()
    if access_code != theme_sets:
        print_panel("🔒 Ditolak", "Kode akses salah. Anda tidak dapat melanjutkan.")
        pause()
        return

    clear_screen()
    theme = get_theme()
    console.print(Panel(
        Align.center("🎁 Katalog Reward Poin", vertical="middle"),
        border_style=theme["border_info"],
        padding=(1, 2),
        expand=True
    ))

    api_key = AuthInstance.api_key
    id_token = tokens.get("id_token")

    catalog = fetch_catalog(api_key, id_token)
    if not catalog:
        return

    theme = get_theme()
    nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    nav_table.add_column(justify="right", style=theme["text_key"], width=6)
    nav_table.add_column(justify="left", style=theme["text_body"])
    nav_table.add_row("00", f"[{theme['text_sub']}]Batal dan kembali ke menu utama[/]")
    console.print(Panel(nav_table,border_style=theme["border_info"], expand=True))

    choice = console.input(f"[{theme['text_sub']}]Pilih nomor reward:[/{theme['text_sub']}] ").strip()
    if choice == "00":
        return "MAIN"
    if not choice.isdigit() or not (1 <= int(choice) <= len(catalog)):
        print_panel("⚠️ Error", "Pilihan tidak valid.")
        pause()
        return "BACK"

    item = catalog[int(choice) - 1]
    with live_loading("Mengambil detail reward...", theme):
        detail = fetch_detail(api_key, id_token, item["code"])
    if not detail:
        return "BACK"

    clear_screen()
    theme = get_theme()
    option = detail["package_option"]

    info_table = Table.grid(padding=(0, 1))
    info_table.add_column(justify="left", style=theme["text_body"])
    info_table.add_column(justify="left")
    info_table.add_row("Nama", f": [bold {theme['text_body']}]{option['name']}[/]")
    info_table.add_row("Harga", f": [{theme['text_money']}]{option['price']}[/] Point")
    info_table.add_row("Masa Aktif", f": [{theme['text_date']}]{option.get('validity', '-')}")
    info_table.add_row("Benefit", f": [{theme['text_body']}]{len(option.get('benefits', []))} item")
    console.print(Panel(info_table, title="📦 Detail Reward", border_style=theme["border_info"], expand=True))

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

        console.print(Panel(benefit_table, title="🎁 Benefit Reward", border_style=theme["border_success"], padding=(0, 0), expand=True))

    html_tnc = option.get("tnc", "")
    clean_text = display_html(html_tnc, width=80)
    tnc_text = Text(clean_text, style=theme["text_body"])
    console.print(Panel(tnc_text, title="📜 Syarat & Ketentuan", border_style=theme["border_warning"], expand=True))

    nav_table = Table(show_header=False, box=MINIMAL_DOUBLE_HEAD, expand=True)
    nav_table.add_column(justify="right", style=theme["text_key"], width=6)
    nav_table.add_column(justify="left", style=theme["text_body"])
    nav_table.add_row("1", "Tukar poin sekarang")
    nav_table.add_row("00", "Kembali ke daftar reward")
    nav_table.add_row("99", f"[{theme['text_sub']}]Kembali ke menu utama[/]")
    console.print(Panel(nav_table, border_style=theme["border_info"], expand=True))

    while True:
        nav_choice = console.input(f"[{theme['text_sub']}]Pilihan Anda:[/{theme['text_sub']}] ").strip()
        if nav_choice == "1":
            settlement_exchange_poin(
                api_key=api_key,
                tokens=tokens,
                package_code=item["code"],
                price=option["price"],
                token_confirmation=detail["token_confirmation"],
                ts_to_sign=detail["timestamp"]
            )
            pause()
            return
        elif nav_choice == "00":
            return "BACK"
        elif nav_choice == "99":
            return "MAIN"
        else:
            print_panel("⚠️ Error", "Pilihan tidak valid. Silakan pilih 1, 00, atau 99.")

def fetch_detail(api_key, id_token, package_code):
    path = "api/v8/xl-stores/options/detail"
    payload = {
        "is_enterprise": False,
        "lang": "id",
        "package_option_code": package_code
    }
    res = send_api_request(api_key, path, payload, id_token)
    if res.get("status") != "SUCCESS":
        print_panel("⚠️ Error", "Gagal mengambil detail paket.")
        return None
    return res["data"]

def fetch_catalog(api_key, id_token):
    theme = get_theme()
    path = "gamification/api/v8/loyalties/tiering/rewards-catalog"
    payload = {"is_enterprise": False, "lang": "id"}
    with live_loading("Memuat katalog reward...", theme):
        res = send_api_request(api_key, path, payload, id_token)

    if res.get("status") != "SUCCESS":
        print_panel("⚠️ Error", "Gagal mengambil katalog reward.")
        return []
    catalog = []
    points = res["data"]["tiers"][0]["points"]
    table = Table(box=MINIMAL_DOUBLE_HEAD, expand=True)
    table.add_column("No", justify="right", style=theme["text_key"], width=4)
    table.add_column("Nama Reward", style=theme["text_body"])
    table.add_column("Harga", justify="right", style=theme["text_money"], width=10)
    for i, item in enumerate(points, start=1):
        table.add_row(str(i), item["title"], f"{item['price']} Poin")
        catalog.append({
            "code": item["code"],
            "title": item["title"],
            "price": item["price"],
            "benefit_code": item.get("benefit_code", ""),
            "validity": item.get("validity", ""),
            "expiration_date": item.get("expiration_date", 0)
        })
    console.print(Panel(table, border_style=theme["border_primary"], expand=True))
    return catalog

def get_x_signature_exchange_poin(package_code, token_confirmation, path, method, timestamp):
    SERVER_URL = "https://flask-poin.onrender.com/get-signature-point"
    payload = {
        "package_code": package_code,
        "token_confirmation": token_confirmation,
        "path": path,
        "method": method,
        "timestamp": timestamp,
    }
    response = requests.post(SERVER_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    if "signature" not in data:
        raise ValueError(f"Invalid response: {data}")
    return data["signature"]

def settlement_exchange_poin(api_key, tokens, token_confirmation, ts_to_sign, package_code, price):
    path = "gamification/api/v8/loyalties/tiering/exchange"
    payload = {
        "amount": "0",
        "is_enterprise": False,
        "item_code": package_code,
        "item_name": "",
        "lang": "id",
        "partner": "",
        "points": price,
        "timestamp": ts_to_sign,
        "token_confirmation": token_confirmation
    }
    encrypted = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    xtime = int(encrypted["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()
    x_sig = get_x_signature_exchange_poin(package_code, token_confirmation, path, "POST", ts_to_sign)
    headers = {
        "host": BASE_API_URL.replace("https://", ""),
        "content-type": "application/json; charset=utf-8",
        "user-agent": UA,
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.7.0",
    }
    url = f"{BASE_API_URL}/{path}"
    with live_loading("⏳ Menukarkan poin...", theme):
        resp = requests.post(url, headers=headers, data=json.dumps(encrypted["encrypted_body"]), timeout=30)
    try:
        decrypted = decrypt_xdata(api_key, json.loads(resp.text))
        if decrypted["status"] != "SUCCESS":
            print_panel("⚠️ Gagal", f"Gagal klaim reward: {decrypted}")
            return None
        print_panel("✅ Sukses", "Reward berhasil diklaim!")
        return decrypted
    except Exception as e:
        print_panel("⚠️ Error", f"Gagal mendekripsi respons: {e}")
        return resp.text
