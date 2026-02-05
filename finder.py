import asyncio
import base64
import re
import json
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs
import aiohttp

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

# Emojis to exclude
EXCLUDE_EMOJIS = ["📅", "📊"]

# --- Helper function to check if a string contains excluded emojis ---
def contains_excluded_emoji(text):
    """Check if text contains any of the excluded emojis"""
    for emoji in EXCLUDE_EMOJIS:
        if emoji in text:
            return True
    return False

# --- Extract flag from config name ---
def extract_flag_from_config(config_url):
    """Extract flag emoji from config name (fragment part)"""
    try:
        if "#" in config_url:
            fragment = config_url.split("#", 1)[1]
            # Find emojis in the fragment (simple emoji detection)
            # This regex matches most common emojis including flags
            emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
            emojis = emoji_pattern.findall(fragment)
            if emojis:
                # Return first emoji as flag
                return emojis[0]
    except:
        pass
    return "🏴"  # Default flag if none found

# --- Extract name without flag ---
def extract_name_without_flag(config_url):
    """Extract config name without the flag emoji"""
    try:
        if "#" in config_url:
            fragment = config_url.split("#", 1)[1]
            # Remove emojis from the fragment
            emoji_pattern = re.compile(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]')
            name = emoji_pattern.sub('', fragment).strip()
            return name if name else "Emergency Server"
    except:
        pass
    return "Emergency Server"

# --- Download subscription from URL ---
async def download_subscription(url):
    """Download and decode subscription from a URL"""
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=10)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    # Try to decode as base64
                    try:
                        decoded = base64.b64decode(content).decode('utf-8')
                        # Split by lines and filter empty lines
                        configs = [line.strip() for line in decoded.splitlines() if line.strip()]
                        return configs
                    except:
                        # If not base64, try as plain text
                        plain_text = content.decode('utf-8')
                        configs = [line.strip() for line in plain_text.splitlines() if line.strip()]
                        return configs
    except Exception as e:
        print(f"Error downloading subscription: {e}")
    return []

# --- Process mohammadaz2 subscription ---
async def process_mohammadaz2_subscription(client):
    """Check last message from @mohammadaz2 and process if it's a subscription link"""
    emergency_configs = []
    emergency_flags = []
    
    try:
        # Get the last message from @mohammadaz2
        async for message in client.search_messages("@mohammadaz2", limit=1):
            if not message.text:
                return emergency_configs, emergency_flags
                
            text = message.text.strip()
            
            # Check if it's a URL
            url_pattern = re.compile(r'https?://[^\s]+')
            match = url_pattern.search(text)
            
            if match:
                url = match.group(0)
                print(f"Found subscription URL from @mohammadaz2: {url}")
                
                # Download configs from subscription
                configs = await download_subscription(url)
                
                if configs:
                    print(f"Downloaded {len(configs)} configs from subscription")
                    
                    # Process configs
                    for i, config in enumerate(configs):
                        if "#" in config:
                            config_name = config.split("#", 1)[1]
                            
                            # Check if config contains excluded emoji (skip first config check only)
                            if i == 0 and contains_excluded_emoji(config_name):
                                # Skip this config if it's the first one with excluded emoji
                                continue
                            
                            # Extract flag from original config
                            flag = extract_flag_from_config(config)
                            emergency_flags.append(flag)
                            emergency_configs.append(config)
                        else:
                            # Add config without fragment
                            emergency_flags.append("🏴")
                            emergency_configs.append(config)
                    
                    print(f"Added {len(emergency_configs)} emergency configs (after filtering)")
                
    except Exception as e:
        print(f"Error processing @mohammadaz2 subscription: {e}")
    
    return emergency_configs, emergency_flags

# --- Format configs ---
def format_configs(configs, channels_scanned, emergency_configs, emergency_flags):
    if not configs and not emergency_configs:
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

    # ---- EMERGENCY SERVERS ----
    if emergency_configs:
 
        # Add emergency configs with flag and @mohammadaz2 in name
        for i, (config, flag) in enumerate(zip(emergency_configs, emergency_flags), start=1):
            url_part = config.split("#", 1)[0]
            # Format: EMERGENCY {flag} | @mohammadaz2
            fragment = f"EMERGENCY {flag} | @mohammadaz2"
            formatted.append(f"{url_part}#{fragment}")

    # ---- REGULAR CONFIGS (with numbers) ----
    if configs:
        # Add separator if we have both emergency and regular configs
        if emergency_configs:
            separator = "───────────────"
            formatted.append(f"{header_base}#{separator}")
            regular_header = "📡 REGULAR CONFIGS 📡 | @mohammadaz2"
            formatted.append(f"{header_base}#{regular_header}")
        
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

        # Process @mohammadaz2 subscription first
        emergency_configs, emergency_flags = await process_mohammadaz2_subscription(client)
        
        # Scan regular channels
        configs, channels_scanned = await scan_channels(client)

        if not configs and not emergency_configs:
            print("❌ No configs found")
            return

        formatted = format_configs(configs, channels_scanned, emergency_configs, emergency_flags)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(formatted))

        total_configs = len(formatted)
        emergency_count = len(emergency_configs) if emergency_configs else 0
        regular_count = len(configs) if configs else 0
        
        print(f"✅ Saved {total_configs} configs to {OUTPUT_FILE}")
        if emergency_count > 0:
            print(f"🚨 Added {emergency_count} emergency configs from @mohammadaz2")
        if regular_count > 0:
            print(f"📡 Added {regular_count} regular configs from channel scan")

if __name__ == "__main__":
    asyncio.run(telegram_scan())
