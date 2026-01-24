import asyncio
import base64
import re
import random
import requests
import string
import json
from datetime import datetime, timedelta
from urllib.parse import unquote, urlparse, parse_qs
from pyrogram import Client as PyrogramClient, enums

OUTPUT_FILE = "configs.txt"
FORMAT_STRING = "Config | {number} / {total}"  # Format for the config name


# --- Protocol Patterns for Extraction ---
PATTERNS = [
    # VMess (base64 encoded)
    re.compile(r"vmess://[a-zA-Z0-9+/=]+"),

    re.compile(r"vless://[^ \n\"]+"),
    re.compile(r"ss://[a-zA-Z0-9\-_=.@:+/#?&%]+(?=[ \n\"]|$)"),
    re.compile(r"trojan://[^ \n\"]+")
]


def format_configs(configs):
    """Formats a list of configuration URLs by adding dynamic fragments (names)."""
    now = datetime.now()
    total = len(configs)
    formatted = []
    for i, config in enumerate(configs):
        if not config.strip():
            continue
        parts = config.split('#', 1)
        url_part = parts[0]
        old_fragment = unquote(parts[1]) if len(parts) > 1 else ""
        replacements = {
            '{number}': str(i+1),
            '{total}': str(total),
            '{old}': old_fragment,
            '{date}': now.strftime("%Y-%m-%d"),
            '{time}': now.strftime("%H:%M:%S")
        }
        new_fragment = FORMAT_STRING
        for placeholder, value in replacements.items():
            new_fragment = new_fragment.replace(placeholder, value)
        formatted.append(f"{url_part}#{new_fragment}")
    return formatted

def parse_config_for_deduplication(config_url):
    """Parses a V2Ray/Shadowsocks/Trojan config URL to extract unique identifying features."""
    try:
        if config_url.startswith("vmess://"):
            encoded_json = config_url[len("vmess://"):]
            missing_padding = len(encoded_json) % 4
            if missing_padding:
                encoded_json += '=' * (4 - missing_padding)
            decoded_json = base64.b64decode(encoded_json).decode('utf-8')
            data = json.loads(decoded_json)
            return ("vmess", data.get("add"), data.get("port"), data.get("id"))
        elif config_url.startswith("vless://") or config_url.startswith("trojan://"):
            parsed = urlparse(config_url)
            protocol = parsed.scheme
            user_info = parsed.username
            host = parsed.hostname
            port = parsed.port
            query_params = parse_qs(parsed.query)
            type_param = query_params.get('type', [''])[0]
            security_param = query_params.get('security', [''])[0]
            sni_param = query_params.get('sni', [''])[0]
            fp_param = query_params.get('fp', [''])[0]
            if protocol == "vless":
                return (protocol, user_info, host, port, type_param, security_param, sni_param, fp_param)
            elif protocol == "trojan":
                return (protocol, user_info, host, port, security_param, sni_param)
        elif config_url.startswith("ss://"):
            pure_ss_url = config_url[len("ss://"):].split('#', 1)[0]
            if '@' in pure_ss_url:
                auth_part, addr_port_part = pure_ss_url.split('@')
                method = None
                password = None
                try:
                    if ':' in auth_part:
                        method, password = auth_part.split(':', 1)
                    else:
                        decoded_auth = base64.b64decode(auth_part + '==').decode('utf-8')
                        if ':' in decoded_auth:
                            method, password = decoded_auth.split(':', 1)
                except Exception:
                    pass
                try:
                    host, port_str = addr_port_part.split(':')
                    port = int(port_str)
                    return ("ss", method, password, host, port)
                except Exception:
                    return None
            else:
                try:
                    decoded_entire_string = base64.b64decode(pure_ss_url + '==').decode('utf-8')
                    if '@' in decoded_entire_string:
                        auth_part, addr_port_part = decoded_entire_string.split('@')
                        method, password = auth_part.split(':', 1)
                        host, port_str = addr_port_part.split(':')
                        port = int(port_str)
                        return ("ss", method, password, host, port)
                    else:
                        return None
                except Exception:
                    return None
        return None
    except Exception:
        return None

# --- Main Logic ---
async def scan_channels(client):
    """Scans Telegram channels for V2Ray/SS/Trojan configurations."""
    unique_identifiers = set()
    found_configs = []
    cutoff = datetime.utcnow() - timedelta(hours=24)
    async for dialog in client.get_dialogs():
        if not (dialog.chat.type == enums.ChatType.CHANNEL and dialog.top_message and dialog.top_message.date >= cutoff):
            continue
        print(f"Scanning: {dialog.chat.title}")
        try:
            async for msg in client.get_chat_history(dialog.chat.id):
                if msg.date < cutoff:
                    break
                if text := msg.text or msg.caption:
                    for pattern in PATTERNS:
                        for match in pattern.finditer(text):
                            config = match.group(0).strip()
                            if any(x in config for x in ['@', '.', ':', '//']):
                                identifier = parse_config_for_deduplication(config)
                                if identifier and identifier not in unique_identifiers:
                                    unique_identifiers.add(identifier)
                                    found_configs.append(config)
        except Exception as e:
            print(f"Error in {dialog.chat.title}: {str(e)[:50]}...")
    return found_configs

async def telegram_scan():
    """Orchestrates the Telegram scanning process."""
    async with PyrogramClient("my_accountb") as client:
        print("Starting Telegram scan...")
        configs = await scan_channels(client)
        if not configs:
            print("\n❌ No configurations found in Telegram!")
            return None
        print(f"\nFound {len(configs)} unique configurations (by identifier) from Telegram messages.")
        formatted_configs = format_configs(list(configs))
        output_text = "\n".join(formatted_configs)
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            f.write(output_text)
        print(f"\n✅ Processed {len(formatted_configs)} configurations and saved to: {OUTPUT_FILE}")
        return OUTPUT_FILE

async def main():
    """Runs the Telegram scan and deduplication before saving results."""
    output_file_path = await telegram_scan()
    if output_file_path:
        print("\n✔ Telegram scanning complete.")

if __name__ == "__main__":
    asyncio.run(main())
