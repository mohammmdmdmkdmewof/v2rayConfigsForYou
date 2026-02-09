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
MY_CHAT_ID = 8550116045  # Your chat ID

DEFAULT_HEADER_CONFIG = "vless://93c34033-96f2-444a-8374-f5ff7fddd180@127.0.0.1:443?encryption=none&security=none&type=tcp#header"

# Protocol Patterns
PATTERNS = [
    re.compile(r"vmess://[a-zA-Z0-9+/=]+"),
    re.compile(r"vless://[^ \n\"]+"),
    re.compile(r"ss://[a-zA-Z0-9\-_=.@:+/#?&%]+(?=[ \n\"]|$)"),
    re.compile(r"trojan://[^ \n\"]+")
]

# Emojis to exclude
EXCLUDE_EMOJIS = ["📅", "📊", "📈", "📉", "📆", "🗓️", "📋", "📑"]

# Helper function to check if a string contains excluded emojis
def contains_excluded_emoji(text):
    """Check if text contains any of the excluded emojis"""
    try:
        decoded_text = unquote(text)
    except:
        decoded_text = text

    for emoji_char in EXCLUDE_EMOJIS:
        if emoji_char in decoded_text:
            return True
    return False

# Extract flag from config name
def extract_flag_from_config(config_url):
    """Extract flag emoji from config name (fragment part)"""
    try:
        if "#" in config_url:
            # Get the fragment part after #
            fragment_encoded = config_url.split("#", 1)[1]
            # URL decode the fragment
            fragment = unquote(fragment_encoded)
            return fragment
    except:
        pass
    return ""

# Check if config contains "لطفا قبل اتصال"
def contains_lotfan(config_url):
    """Check if config name contains Persian text 'لطفا قبل اتصال'"""
    try:
        if "#" in config_url:
            # Get the fragment part after #
            fragment_encoded = config_url.split("#", 1)[1]
            # URL decode the fragment
            fragment = unquote(fragment_encoded)
            return "لطفا قبل اتصال" in fragment
    except:
        pass
    return False

# Download subscription from URL
async def download_subscription(url):
    """Download and decode subscription from a URL"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=10) as response:
                if response.status == 200:
                    content = await response.text()
                    decoded = base64.b64decode(content).decode('utf-8')
                    return decoded.splitlines()
    except Exception as e:
        print(f"Error downloading subscription: {e}")
    return []

# Check for JSON notice from your chat
async def check_json_notice(client):
    """Check last message from your chat for JSON notice"""
    try:
        # Get the last message from your chat
        async for message in client.get_chat_history(MY_CHAT_ID, limit=1):
            if message.text:
                try:
                    # Try to parse as JSON
                    notice_data = json.loads(message.text)
                    # Check if it's a valid notice format
                    if isinstance(notice_data, (list, dict)):
                        return notice_data
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"Error checking JSON notice: {e}")
    return None

# Process mohammadaz2 subscription
async def process_mohammadaz2_subscription(client):
    """Check last message from @mohammadaz2 and process if it's a subscription link"""
    emergency_configs = []
    emergency_flags = []
    
    # Check JSON notice first
    notice_data = await check_json_notice(client)
    
    try:
        # Get last message from @mohammadaz2
        async for message in client.get_chat_history("mohammadaz2", limit=1):
            if message.text and "http" in message.text:
                # Extract URL from message
                urls = re.findall(r'https?://\S+', message.text)
                for url in urls:
                    configs = await download_subscription(url)
                    for config in configs:
                        if not contains_lotfan(config) and not contains_excluded_emoji(config):
                            flag = extract_flag_from_config(config)
                            emergency_configs.append(config)
                            emergency_flags.append(flag)
                
                # Send notice if exists
            
    except Exception as e:
        print(f"Error processing mohammadaz2: {e}")
    
    return emergency_configs, emergency_flags

# Format configs
def format_configs(configs, channels_scanned, emergency_configs, emergency_flags):
    if not configs and not emergency_configs:
        return []
    
    formatted = []
    
    # Add header
    header_config = DEFAULT_HEADER_CONFIG
    formatted.append(header_config)
    
    # Add emergency configs first
    if emergency_configs:
        for i, (config, flag) in enumerate(zip(emergency_configs, emergency_flags), 1):
            if flag:
                formatted.append(f"{config}")
            else:
                formatted.append(config)
    
    # Add regular configs
    for i, config in enumerate(configs, 1):
        formatted.append(config)
    
    return formatted

# Deduplication
def parse_config_for_deduplication(config_url):
    try:
        if config_url.startswith("vmess://"):
            encoded = config_url[8:]
            encoded += "=" * (-len(encoded) % 4)
            data = json.loads(base64.b64decode(encoded).decode())
            return ("vmess", data.get("add"), data.get("port"), data.get("id"))
        elif config_url.startswith("vless://"):
            parsed = urlparse(config_url)
            query = parse_qs(parsed.query)
            return ("vless", parsed.hostname, parsed.port, parsed.username)
        elif config_url.startswith("ss://"):
            return ("ss",)
        elif config_url.startswith("trojan://"):
            parsed = urlparse(config_url)
            return ("trojan", parsed.hostname, parsed.port, parsed.username)
    except:
        pass
    return None

# Scan channels
async def scan_channels(client):
    unique_ids = set()
    configs = []
    channels_scanned = 0
    
    # Your channel scanning logic here
    return configs, channels_scanned

# Main
async def telegram_scan():
    async with PyrogramClient("my_accountb") as client:
        print("Starting Telegram scan...")
        
        # Check for JSON notice
        notice_data = await check_json_notice(client)
        
        # Scan channels
        configs, channels_scanned = await scan_channels(client)
        
        # Process emergency subscription
        emergency_configs, emergency_flags = await process_mohammadaz2_subscription(client)
        
        # Format and output configs
        formatted_configs = format_configs(configs, channels_scanned, emergency_configs, emergency_flags)
        
        # Save to file
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            f.write('\n'.join(formatted_configs))
        
        print(f"Scan completed. Found {len(formatted_configs)} configs.")
        

if __name__ == "__main__":
    asyncio.run(telegram_scan())
