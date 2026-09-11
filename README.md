<div align="center">
  <h1>🚀 v2rayConfigsForYou</h1>
  <p><b>Automated Telegram V2Ray Config Scraper & Subscription Link</b></p>
  
  [![Update Configs](https://github.com/mohammadaz2/v2rayConfigsForYou/actions/workflows/update_configs.yaml/badge.svg)](https://github.com/mohammadaz2/v2rayConfigsForYou/actions)
  [![GitHub last commit](https://img.shields.io/github/last-commit/mohammadaz2/v2rayConfigsForYou)](https://github.com/mohammadaz2/v2rayConfigsForYou/commits/main)
</div>

---

## 💥 Overview

**v2rayConfigsForYou** is a personal project turned public to help users maintain access to unrestricted internet. This repository contains an automated Python script that continuously searches for various V2Ray configurations (Vmess, Vless, Trojan, Shadowsocks) across specific Telegram channels and chats. 

The configs are automatically extracted, deduplicated, and saved every **1 hour** using GitHub Actions, ensuring you always have a fresh pool of working proxies!

## 💡 Subscription Link (How to Use)

You can easily use this repository as a subscription link in your favorite proxy client (like v2rayN, v2rayNG, NekoBox, Hiddify, Shadowrocket, etc.).

Just copy the raw URL below and paste it into your app's subscription settings:

> **Subscription URL:**
> ```text
> https://raw.githubusercontent.com/mohammadaz2/v2rayConfigsForYou/main/configs.txt
> ```

*To get the latest working configs, just click **Update Subscription** (Update) inside your client app!*

## ⚼️ How it Works

1. **Telegram Scraper (`finder.py`)**: Uses the `pyrogram` library to log into a Telegram account and read the latest messages from specified chats.
2. **Regex Parsing**: Identifies and extracts valid `vmess://`, `vless://`, `ss://`, and `trojan://` links while stripping out unwanted emojis and metadata.
3. **GitHub Actions Workflow**: Runs automatically every hour via a cron job.
4. **Encrypted Sessions**: The repository uses an AES-256 encrypted session file (`my_accountb.session.aes256`) along with GitHub Secrets (`TELEGRAM_SESSION_KEY`) to safely authenticate the Telegram account without exposing sensitive data in the public repo.

## 쟠️ Setup Your Own (Forking)

If you'd like to use this code to scrape your own Telegram channels:

1. **Fork this repository.**
2. **Create your Telegram Session:**
   - Run a pyrogram script locally to generate a `.session` file for your Telegram account.
   - Encrypt the session file using OpenSSL:
     ```bash
     openssl enc -aes-256-cbc -salt -md md5 -in your_session.session -out my_accountb.session.aes256 -pass pass:YOUR_SECRET_PASSWORD
     ```
3. **Upload the Encrypted Session:**
   - Replace the existing `my_accountb.session.aes256` in your fork with your newly encrypted file.
4. **Configure GitHub Secrets:**
   - Go to your repository **Settings > Secrets and variables > Actions**.
   - Create a new repository secret named `TELEGRAM_SESSION_KEY` and set its value to the password you used during encryption.
5. **Customize Channels (Optional)**:
   - Edit `finder.py` to target the specific Telegram chats you want to scrape.
6. **Enable Workflows**:
   - Go to the **Actions** tab in your repo and enable the workflow.

## ⚠️ Disclaimer

This project was initially created for personal use and is shared publicly in the hopes that it will be useful. Please use the configurations responsibly and ensure you comply with all local regulations and platform terms of service.