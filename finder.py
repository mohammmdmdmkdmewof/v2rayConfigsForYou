import asyncio
import base64
import re
import json
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs

import jdatetime
from pyrogram import Client as PyrogramClient, enums

OUTPUT_FILE = "configs.txt"
FORMAT_STRING = "Config | {number} / {total}"


# --- Protocol Patterns ---
PATTERNS = [
    re.compile(r"vmess://[a-zA-Z0-9+/=]+"),
    re.compile(r"vless://[^ \n\"]+"),
    re.compile(r"ss://[a-zA-Z0-9\-_=.@:+/#?&%]+(?=[ \n\"]|$)"),
    re.compile(r"trojan://[^ \n\"]+")
]


# --- Format configs ---
def format_configs(configs, channels_scanned):
    now = datetime.now()
    jalali_now = jdatetime.datetime.fromgregorian(datetime=now)

    # Persian date
    persian_date = jalali_now.strftime("%Y/%m/%d")
    persian_digits = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    persian_date = persian_date.translate(persian_digits)

    channels_scanned_fa = str(channels_scanned).translate(persian_digits)

    total = len(configs)
    formatted = []

    for i, config in enumerate(configs):
        if not config.strip():
            continue

        url_part = config.split('#', 1)[0]

        if i == 0:
            fragment = "Mohammad hossein Configs | @mohammadaz2"

        elif i == 1:
            fragment = f"📅 اخرین آپدیت: {persian_date}"

        elif i == 2:
            fragment = f"📊 تعداد کانال های اسکن شده: {channels_scanned_fa}"

        elif i == 3:
            fragment = "برای بروزرسانی : سه نقطه گزینه اخر"

        else:
            fragment = FORMAT_STRING \
                .replace("{number}", str(i + 1)) \
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
