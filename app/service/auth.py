import json
import os
import time

from app.client.engsel import get_new_token
from app.menus.util_helper import live_loading
from app.config.theme_config import get_theme


class Auth:
    _instance_ = None
    _initialized_ = False

    api_key = ""
    refresh_tokens = []
    active_user = None
    last_refresh_time = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance_:
            cls._instance_ = super().__new__(cls)
        return cls._instance_

    def __init__(self):
        if not self._initialized_:
            if os.path.exists("refresh-tokens.json"):
                self.load_tokens()
            else:
                with open("refresh-tokens.json", "w", encoding="utf-8") as f:
                    json.dump([], f, indent=4)

            self.load_active_number()
            self.last_refresh_time = int(time.time())
            self._initialized_ = True


    def load_tokens(self):
        with open("refresh-tokens.json", "r", encoding="utf-8") as f:
            raw = json.load(f)
            self.refresh_tokens = []
            for rt in raw:
                if "number" in rt and "refresh_token" in rt:
                    self.refresh_tokens.append({
                        "number": int(rt["number"]),
                        "refresh_token": rt["refresh_token"],
                        "name": rt.get("name", "Tanpa Nama")
                    })

    def write_tokens_to_file(self):
        with open("refresh-tokens.json", "w", encoding="utf-8") as f:
            json.dump(self.refresh_tokens, f, indent=4)

    def add_refresh_token(self, number: int, refresh_token: str, name: str = "Tanpa Nama"):
        existing = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if existing:
            existing["refresh_token"] = refresh_token
            existing["name"] = name
        else:
            self.refresh_tokens.append({
                "number": int(number),
                "refresh_token": refresh_token,
                "name": name
            })

        self.write_tokens_to_file()
        self.set_active_user(number)

    def edit_account_name(self, number: int, new_name: str):
        for rt in self.refresh_tokens:
            if rt["number"] == number:
                rt["name"] = new_name
                break
        self.write_tokens_to_file()
        if self.active_user and self.active_user["number"] == number:
            self.active_user["name"] = new_name

    def remove_refresh_token(self, number: int):
        self.refresh_tokens = [rt for rt in self.refresh_tokens if rt["number"] != number]
        self.write_tokens_to_file()

        if self.active_user and self.active_user["number"] == number:
            if self.refresh_tokens:
                first_rt = self.refresh_tokens[0]
                theme = get_theme()
                with live_loading("Mengatur ulang pengguna aktif...", theme):
                    tokens = get_new_token(first_rt["refresh_token"])
                if tokens:
                    self.set_active_user(first_rt["number"])
            else:
                input("Tidak ada akun tersisa. Tekan Enter untuk lanjut...")
                self.active_user = None

    def set_active_user(self, number: int):
        rt_entry = next((rt for rt in self.refresh_tokens if rt["number"] == number), None)
        if not rt_entry:
            print(f"Tidak ditemukan token untuk nomor: {number}")
            input("Tekan Enter untuk lanjut...")
            return False

        theme = get_theme()
        with live_loading(f"Menyegarkan token untuk {number}...", theme):
            tokens = get_new_token(rt_entry["refresh_token"])

        if not tokens:
            print(f"Gagal mendapatkan token untuk nomor: {number}. Token mungkin kadaluarsa.")
            input("Tekan Enter untuk lanjut...")
            return False

        self.active_user = {
            "number": int(number),
            "tokens": tokens,
            "name": rt_entry.get("name", "Tanpa Nama")
        }

        self.write_active_number()
        return True

    def renew_active_user_token(self):
        if self.active_user:
            theme = get_theme()
            with live_loading("Memperbarui token pengguna aktif...", theme):
                tokens = get_new_token(self.active_user["tokens"]["refresh_token"])

            if tokens:
                self.active_user["tokens"] = tokens
                self.last_refresh_time = int(time.time())
                self.add_refresh_token(self.active_user["number"], tokens["refresh_token"], self.active_user["name"])
                print("✅ Token pengguna aktif berhasil diperbarui.")
                return True
            else:
                print("⚠️ Gagal memperbarui token pengguna aktif.")
                input("Tekan Enter untuk lanjut...")
        else:
            print("⚠️ Tidak ada pengguna aktif yang disetel.")
            input("Tekan Enter untuk lanjut...")
        return False

    def get_active_user(self):
        if not self.active_user and self.refresh_tokens:
            first_rt = self.refresh_tokens[0]
            theme = get_theme()
            with live_loading("Memuat pengguna aktif...", theme):
                tokens = get_new_token(first_rt["refresh_token"])
            if tokens:
                self.active_user = {
                    "number": int(first_rt["number"]),
                    "tokens": tokens,
                    "name": first_rt.get("name", "Tanpa Nama")
                }

        if self.last_refresh_time is None or (int(time.time()) - self.last_refresh_time) > 300:
            self.renew_active_user_token()
            self.last_refresh_time = time.time()

        return self.active_user

    def get_active_tokens(self) -> dict | None:
        active_user = self.get_active_user()
        return active_user["tokens"] if active_user else None

    def write_active_number(self):
        if self.active_user:
            with open("active.number", "w", encoding="utf-8") as f:
                f.write(str(self.active_user["number"]))
        elif os.path.exists("active.number"):
            os.remove("active.number")

    def load_active_number(self):
        if os.path.exists("active.number"):
            with open("active.number", "r", encoding="utf-8") as f:
                number_str = f.read().strip()
                if number_str.isdigit():
                    number = int(number_str)
                    self.set_active_user(number)

AuthInstance = Auth()
