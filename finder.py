import asyncio
import base64
import re
import json
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs
import aiohttp
import emoji

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
EXCLUDE_EMOJIS = ["📅", "📊", "📈", "📉", "📆", "🗓️", "📋", "📑"]

# --- Helper function to check if a string contains excluded emojis ---
def contains_excluded_emoji(text):
    """Check if text contains any of the excluded emojis"""
    # First unquote the text to decode URL-encoded characters
    try:
        decoded_text = unquote(text)
    except:
        decoded_text = text
    
    # Use emoji library for comprehensive detection
    emoji_list = emoji.distinct_emoji_list(decoded_text)
    for emoji_char in emoji_list:
        if emoji_char in EXCLUDE_EMOJIS:
            return True
    return False

# --- Extract flag from config name ---
def extract_flag_from_config(config_url):
    """Extract flag emoji from config name (fragment part)"""
    try:
        if "#" in config_url:
            # Get the fragment part after #
            fragment_encoded = config_url.split("#", 1)[1]
            # URL decode the fragment
            fragment = unquote(fragment_encoded)
            
            # Use emoji library for comprehensive emoji detection
            emojis = emoji.distinct_emoji_list(fragment)
            if emojis:
                # Return first emoji as flag
                return emojis[0]
    except:
        pass
    return "🏴"  # Default flag if none found

# --- Check if config contains "لطفا قبل اتصال" ---
def contains_lotfan(config_url):
    """Check if config name contains Persian text 'لطفا قبل اتصال'"""
    try:
        if "#" in config_url:
            # Get the fragment part after #
            fragment_encoded = config_url.split("#", 1)[1]
            # URL decode the fragment
            fragment = unquote(fragment_encoded)
            
            # Check if the decoded fragment contains the Persian text
            if "لطفا قبل اتصال" in fragment:
                return True
    except:
        pass
    return False

# --- Download subscription from URL ---
async def download_subscription(url):
    """Download and decode subscription from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers=headers
        ) as session:
            async with session.get(url, ssl=False) as response:
                if response.status == 200:
                    content = await response.read()
                    
                    # Try to decode as base64
                    try:
                        # Remove any whitespace or newlines
                        encoded_content = content.decode('utf-8').strip()
                        # Add padding if needed
                        padding_needed = len(encoded_content) % 4
                        if padding_needed:
                            encoded_content += '=' * (4 - padding_needed)
                        
                        decoded = base64.b64decode(encoded_content).decode('utf-8')
                        # Split by lines and filter empty lines
                        configs = [line.strip() for line in decoded.splitlines() if line.strip()]
                        return configs
                    except Exception as decode_error:
                        # If not base64, try as plain text
                        try:
                            plain_text = content.decode('utf-8', errors='ignore')
                            # Try to find configs in plain text
                            configs = []
                            for pattern in PATTERNS:
                                for match in pattern.finditer(plain_text):
                                    cfg = match.group(0).strip()
                                    if cfg and cfg not in configs:
                                        configs.append(cfg)
                            
                            if configs:
                                return configs
                            else:
                                # If no patterns found, treat each line as a config
                                configs = [line.strip() for line in plain_text.splitlines() if line.strip()]
                                return configs
                        except:
                            print(f"Failed to decode subscription content")
                            return []
                else:
                    print(f"Subscription request failed with status: {response.status}")
                    return []
    except aiohttp.ClientError as e:
        print(f"Network error downloading subscription: {type(e).__name__}")
        return []
    except Exception as e:
        print(f"Unexpected error downloading subscription: {type(e).__name__}")
        return []

# --- Parse custom headers from @mohammadaz2 messages ---
def parse_custom_headers(text):
    """Parse custom headers from JSON list format in @mohammadaz2 messages"""
    custom_headers = []
    
    # Try to find JSON array in the message text
    json_pattern = re.compile(r'\[.*?\]', re.DOTALL)
    matches = json_pattern.findall(text)
    
    for match in matches:
        try:
            # Parse the JSON array
            headers_list = json.loads(match)
            if isinstance(headers_list, list):
                # Validate that all items are strings
                for header in headers_list:
                    if isinstance(header, str) and header.strip():
                        custom_headers.append(header.strip())
        except json.JSONDecodeError:
            # Try alternative parsing for malformed JSON
            # Look for content inside curly braces or quotes
            alt_pattern = re.compile(r'"([^"]+)"')
            alt_matches = alt_pattern.findall(match)
            for header in alt_matches:
                if header.strip():
                    custom_headers.append(header.strip())
        except Exception as e:
            print(f"Error parsing custom headers: {e}")
            continue
    
    # Also look for plain text lines that might be headers (lines starting with quotes or dashes)
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        
        # Skip if line looks like a URL or config
        if line.startswith(('http://', 'https://', 'vmess://', 'vless://', 'ss://', 'trojan://')):
            continue
        
        # Skip if line is empty or just contains brackets
        if not line or line in ['[', ']', '{', '}']:
            continue
        
        # Check if line might be a header item
        # Remove surrounding quotes if present
        if line.startswith('"') and line.endswith('"'):
            line = line[1:-1]
        elif line.startswith("'") and line.endswith("'"):
            line = line[1:-1]
        
        # Check if it's a meaningful header (more than 3 chars, not just numbers/symbols)
        if len(line) > 3 and any(c.isalpha() for c in line):
            # Avoid adding duplicate headers
            if line not in custom_headers:
                custom_headers.append(line)
    
    return custom_headers

# --- Process mohammadaz2 subscription ---
async def process_mohammadaz2_subscription(client):
    """Check last message from @mohammadaz2 and process if it's a subscription link"""
    emergency_configs = []
    emergency_flags = []
    custom_headers = []
    
    try:
        # Get the last 10 messages from @mohammadaz2 to look for custom headers
        async for message in client.search_messages("@mohammadaz2", limit=10):
            if not message.text:
                continue
                
            text = message.text.strip()
            
            # First check for custom headers in the message
            headers_in_message = parse_custom_headers(text)
            if headers_in_message:
                custom_headers.extend(headers_in_message)
                print(f"Found custom headers from @mohammadaz2: {headers_in_message}")
            
            # Then check for subscription URLs (only if we haven't found emergency configs yet)
            if not emergency_configs:
                url_pattern = re.compile(r'https?://[^\s]+')
                match = url_pattern.search(text)
                
                if match:
                    url = match.group(0)
                    print(f"Found subscription from @mohammadaz2")
                    
                    # Download configs from subscription
                    configs = await download_subscription(url)
                    
                    if configs:
                        print(f"Downloaded {len(configs)} configs from subscription")
                        
                        # Process configs
                        for i, config in enumerate(configs):
                            if "#" in config:
                                config_name_encoded = config.split("#", 1)[1]
                                
                                # Check if config contains excluded emoji (skip first config check only)
                                if i == 0 and contains_excluded_emoji(config_name_encoded):
                                    # Skip this config if it's the first one with excluded emoji
                                    print(f"Skipping first config due to excluded emoji")
                                    continue
                                
                                # Check if config contains "لطفا قبل اتصال"
                                if contains_lotfan(config):
                                    # Skip this config if it contains the Persian text
                                    print(f"Skipping config with 'لطفا قبل اتصال'")
                                    continue
                                
                                # Extract flag from original config (using URL decoding)
                                flag = extract_flag_from_config(config)
                                emergency_flags.append(flag)
                                emergency_configs.append(config)
                            else:
                                # Add config without fragment
                                emergency_flags.append("🏴")
                                emergency_configs.append(config)
                        
                        print(f"Added {len(emergency_configs)} emergency configs (after filtering)")
                    else:
                        print("No valid configs found in subscription")
                
    except Exception as e:
        print(f"Error processing @mohammadaz2 messages: {e}")
    
    # Remove duplicate headers
    custom_headers = list(dict.fromkeys(custom_headers))
    
    return emergency_configs, emergency_flags, custom_headers

# --- Create custom header configs ---
def create_custom_header_configs(custom_headers):
    """Create config entries for custom headers"""
    custom_configs = []
    
    header_base = DEFAULT_HEADER_CONFIG.split("#", 1)[0]
    
    for header in custom_headers:
        # Add a config with the custom header text
        custom_configs.append(f"{header_base}#⚠️ {header}")
    
    return custom_configs

# --- Format configs ---
def format_configs(configs, channels_scanned, emergency_configs, emergency_flags, custom_headers):
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

    # Jalali date
    jalali_date_str = jalali_now.strftime("%Y/%m/%d")
    jalali_date_fa = jalali_date_str.translate(persian_digits)

    # Channels scanned in Persian
    channels_fa = str(channels_scanned).translate(persian_digits)

    formatted = []

    header_base = DEFAULT_HEADER_CONFIG.split("#", 1)[0]

    # ---- STANDARD HEADERS ----
    headers = [
        "Mohammad hossein Configs | @mohammadaz2",
        f"📅 آخرین آپدیت: {weekday_fa} ساعت {hour_min_fa}",
        f"📊 جمع آوری شده از {channels_fa} کانال",
        "🔄برای اپدیت کانفیگ ها سه نقطه را بفشارید و گزینه آخر را انتخاب کنید.",
    ]

    for h in headers:
        formatted.append(f"{header_base}#{h}")

    # ---- CUSTOM HEADER CONFIGS (from @mohammadaz2) ----
    if custom_headers:
        # Create config entries for custom headers
        custom_configs = create_custom_header_configs(custom_headers)
        formatted.extend(custom_configs)
        
        # Add separator
        formatted.append(f"{header_base}#──────────────")

    # ---- EMERGENCY CONFIGS (without header) ----
    if emergency_configs:
        # Add emergency configs directly after headers/custom headers
        for config, flag in zip(emergency_configs, emergency_flags):
            url_part = config.split("#", 1)[0]
            # Format: EMERGENCY {flag} | @mohammadaz2
            fragment = f"EMERGENCY {flag} | @mohammadaz2"
            formatted.append(f"{url_part}#{fragment}")
        
        # Add separator between emergency and regular configs
        if configs:
            formatted.append(f"{header_base}#──────────────")

    # ---- REGULAR CONFIGS (with numbers) ----
    if configs:
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

        # Process @mohammadaz2 messages (subscription + custom headers)
        emergency_configs, emergency_flags, custom_headers = await process_mohammadaz2_subscription(client)
        
        # Scan regular channels
        configs, channels_scanned = await scan_channels(client)

        if not configs and not emergency_configs and not custom_headers:
            print("❌ No configs or headers found")
            return

        formatted = format_configs(configs, channels_scanned, emergency_configs, emergency_flags, custom_headers)

        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(formatted))

        total_configs = len(formatted)
        emergency_count = len(emergency_configs) if emergency_configs else 0
        regular_count = len(configs) if configs else 0
        headers_count = len(custom_headers) if custom_headers else 0
        
        print(f"✅ Saved {total_configs} configs to {OUTPUT_FILE}")
        if headers_count > 0:
            print(f"📢 Added {headers_count} custom header configs from @mohammadaz2")
        if emergency_count > 0:
            print(f"🚨 Added {emergency_count} emergency configs from @mohammadaz2")
        if regular_count > 0:
            print(f"📡 Added {regular_count} regular configs from channel scan")

if __name__ == "__main__":
    asyncio.run(telegram_scan())
