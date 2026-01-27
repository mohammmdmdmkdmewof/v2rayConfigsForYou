import asyncio
import base64
import re
import json
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs

import jdatetime
import pytz
from pyrogram import Client as PyrogramClient, enums

OUTPUT_FILE = "configs.txt"
FORMAT_STRING = "Config | {number} / {total}"

DEFAULT_HEADER_CONFIG = "vless://93c34033-96f2-444a-8374-f5ff7fddd180@127.0.0.1:443?encryption=none&security=none&type=tcp#header"

# --- Protocol Patterns ---
PATTERNS = [
    re.compile(r"vmess://[a-zA-Z0-9+/=]+"),
    re.compile(r"vless://[^ \n\"]+"),
    re.compile(r"ss://[a-zA-Z0-9\-_=.@:+/#?&%]+(?=[ \n\"]|$)"),
    re.compile(r"trojan://[^ \n\"]+")
]


# --- Format configs ---
def format_configs(configs, channels_scanned):
    if not configs:
        return []

    # --- Tehran time ---
    tehran_tz = pytz.timezone("Asia/Tehran")
    now_utc = datetime.utcnow()
    now_tehran = now_utc.astimezone(tehran_tz)

    jalali_now = jdatetime.datetime.fromgregorian(datetime=now_tehran)

    persian_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

    # Persian weekday mapping
    weekday_map = {
        "Saturday": "شنبه",
        "Sunday": "یک‌شنبه",
        "Monday": "دوشنبه",
        "Tuesday": "سه‌شنبه",
        "Wednesday": "چهارشنبه",
        "Thursday": "پنج‌شنبه",
        "Friday": "جمعه"
    }
    weekday_en = now_tehran.strftime("%A")
    weekday_fa = weekday_map.get(weekday_en, weekday_en)

    # Hour:Minute in Tehran
    hour_min_fa = now_tehran.strftime("%H:%M").translate(persian_digits)

    # Channels scanned in Persian
    channels_fa = str(channels_scanned).translate(persian_digits)

    formatted = []

    
    header_base = DEFAULT_HEADER_CONFIG.split("#", 1)[0]

    # ---- HEADERS ----
    headers = [
        "Mohammad hossein Configs | @mohammadaz2",
        f"📅 آخرین آپدیت: {weekday_fa} ساعت {hour_min_fa}",
        f"📊 جمع آوری شده از {channels_fa} کانال",
        "🔄برای اپدیت کانفیگ ها سه نقطه را بفشارید و گزینه آخر را انتخاب کنید.",
    ]

    for h in headers:
        formatted.append(f"{header_base}#{h}")

    # ---- REAL CONFIGS ----
    total = len(configs)
    for i, config in enumerate(configs, start=1):
        url_part = config.split("#", 1)[0]
        fragment = FORMAT_STRING \
            .replace("{number}", str(i)) \
            .replace("{total}", str(total))
        formatted.append(f"{url_part}#{fragment}")

    return formatted


# --- Deduplication ---
def parse_config_for_deduplication(config_url):
    try:
        if config_url.startswith("vmess://"):
            encoded = config_url[8:]
            encoded += "=" * (-len(encoded) % 4)
            data = json.loads(base64.b64decode(encoded).decode())
            return ("vmess", data.get("add"), data.get("port"), data.get("id"))

        elif config_url.startswith(("vless://", "trojan://")):
            parsed = urlparse(config_url)
            q = parse_qs(parsed.query)
            return (
                parsed.scheme,
                parsed.username,
                parsed.hostname,
                parsed.port,
                q.get("security", [""])[0],
                q.get("sni", [""])[0],
            )

        elif config_url.startswith("ss://"):
            pure = config_url[5:].split("#", 1)[0]
            decoded = base64.b64decode(pure + "==").decode()
            auth, addr = decoded.split("@")
            method, password = auth.split(":")
            host, port = addr.split(":")
            return ("ss", method, password, host, int(port))

    except Exception:
        return None


# --- Scan channels ---
async def scan_channels(client):
    unique_ids = set()
    configs = []
    channels_scanned = 0

    cutoff = datetime.utcnow() - timedelta(hours=24)

    async for dialog in client.get_dialogs():
        if not (
            dialog.chat.type == enums.ChatType.CHANNEL
            and dialog.top_message
            and dialog.top_message.date >= cutoff
        ):
            continue

        channels_scanned += 1
        print(f"Scanning: {dialog.chat.title}")

        try:
            async for msg in client.get_chat_history(dialog.chat.id):
                if msg.date < cutoff:
                    break

                text = msg.text or msg.caption
                if not text:
                    continue

                for pattern in PATTERNS:
                    for match in pattern.finditer(text):
                        cfg = match.group(0).strip()
                        ident = parse_config_for_deduplication(cfg)
                        if ident and ident not in unique_ids:
                            unique_ids.add(ident)
                            configs.append(cfg)

        except Exception as e:
            print(f"Error in {dialog.chat.title}: {str(e)[:40]}...")

    return configs, channels_scanned


# --- Main ---
async def telegram_scan():
    async with PyrogramClient("my_accountb") as client:
        print("Starting Telegram scan...")

        configs, channels_scanned = await scan_channels(client)

        if not configs:
            print("❌ No configs found")
            return

        formatted = format_configs(configs, channels_scanned)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(formatted))

        print(f"✅ Saved {len(formatted)} configs to {OUTPUT_FILE}")


if __name__ == "__main__":
    asyncio.run(telegram_scan())
