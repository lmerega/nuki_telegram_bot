# Nuki Telegram Bot

<p align="center">
  <img src="docs/demo.gif" alt="Nuki Telegram Bot demo" width="360">
</p>

<p align="center">
  <a href="https://github.com/lmerega/nuki_telegram_bot/stargazers">
    <img src="https://img.shields.io/github/stars/lmerega/nuki_telegram_bot?style=flat-square&color=yellow" alt="GitHub stars" />
  </a>
  <a href="https://github.com/lmerega/nuki_telegram_bot/issues">
    <img src="https://img.shields.io/github/issues/lmerega/nuki_telegram_bot?style=flat-square&color=yellow" alt="GitHub issues" />
  </a>
  <img src="https://img.shields.io/badge/RaspiNukiBridge-required-blue?style=flat-square" alt="Requires RaspiNukiBridge" />
  <img src="https://img.shields.io/badge/Telegram-Bot-blue?style=flat-square" alt="Telegram bot" />
  <img src="https://img.shields.io/badge/Raspberry%20Pi-compatible-red?style=flat-square" alt="Raspberry Pi compatible" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-green?style=flat-square" alt="Python 3.10+" />
  <img src="https://img.shields.io/badge/License-MIT-lightgrey?style=flat-square" alt="MIT License" />
  <br>
  <a href="https://github.com/dauden1184/RaspiNukiBridge">
    <img src="https://img.shields.io/badge/Powered%20by-RaspiNukiBridge-blue?style=flat-square" alt="Powered by RaspiNukiBridge"/>
  </a>
</p>

> ⚠️ **Compatibility Notice**  
> This bot works **ONLY** with **[RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)**.  
> It does **not** support the official Nuki Bridge HTTP API.

---

## Overview

**Nuki Telegram Bot** is a self-hosted Telegram bot that lets you control a [Nuki](https://nuki.io/) Smart Lock through **[RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)** (running for example on a Raspberry Pi).  
It is designed to be simple, secure, production-ready and privacy-friendly.

Main features include:

- Self-hosting support (Raspberry Pi / VPS / Home Server)
- Per-user permissions (lock, unlock, open, lock’n’go, status)
- Admin UI with inline keyboards
- Multi-language support (IT/EN)
- Secure door-unlatch confirmation
- `.env`-based configuration
- systemd-friendly execution

---

## Features

### User Features

- `/start` to display main keyboard + permissions summary  
- `/id` to show your chat ID  
- Inline UI for:
  - Lock / Unlock  
  - Open (unlatch) with confirmation  
  - Lock’n’Go  
  - Lock status  
  - Language switch (IT/EN)

Each user can independently choose their UI language.

---

### Admin Features

Admins are Telegram chat IDs listed in the `OWNERS` variable.

Admins can:

- Add new users interactively
- List existing users
- Grant/Revoke individual permissions
- Grant/Revoke all permissions
- Delete users
- Always override all permissions

Permission keys (English only):

- `lock`
- `unlock`
- `open`
- `lockngo`
- `status`

---

## Compatibility

> This bot is **compatible only with [RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)**.  
> It cannot communicate with the official Nuki Bridge API.

You must have **[RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)** running and accessible.  
The bot communicates exclusively with it.

---

## Architecture

- **`main.py`** – Entrypoint, loads config and users, initializes Telegram bot  
- **`config.py`** – Loads config into a dataclass  
- **`users.py`** – Handles `users.json` and permission logic  
- **`nuki.py`** – Wrapper around RaspiNukiBridge endpoints  
- **`bot_handlers.py`** – Commands, callbacks, inline keyboards  
- **`i18n.py`** – Simple runtime translation (English + Italian)

Runtime user data is stored in `users.json`.

---

## Requirements

- Python **3.10+**
- A Nuki Smart Lock managed through **[RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)**
- A Telegram bot token (`BotFather`)

Install requirements:

```bash
pip install -r requirements.txt
```

Virtual environment recommended:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Installation

```bash
git clone https://github.com/lmerega/nuki_telegram_bot
cd nuki_telegram_bot
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Configuration

The bot reads config from environment variables.  
Use a local `.env` file for development or a systemd `EnvironmentFile` in production.

### Example `.env`

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

NUKI_TOKEN=your_raspinukibridge_token_here
NUKI_BRIDGE_HOST=192.168.1.50
NUKI_BRIDGE_PORT=8080
NUKI_ID=123456789
NUKI_DEVICE_TYPE=0

OWNERS=123456789,987654321

USERS_FILE=/srv/nuki_telegram_bot/users.json
```

---

## Users File (`users.json`)

Example:

```json
{
  "users": {
    "123456789": {
      "name": "John Doe",
      "allowed": ["lock", "unlock", "open", "lockngo", "status"],
      "lang": "en"
    },
    "987654321": {
      "name": "Mario Rossi",
      "allowed": ["lock", "status"],
      "lang": "it"
    }
  }
}
```

---

## Running the Bot (Development)

```bash
source .venv/bin/activate
python main.py
```

Send `/start` to your bot on Telegram.

---

## Usage

### Regular Users
- `/start`, `/id`
- Inline controls for the lock
- Language selection

### Admins
- Add users  
- Manage permissions  
- Delete users  
- View user list  

Admins bypass all permission restrictions.

---

## Deployment with systemd

Example service file:

```ini
[Unit]
Description=Nuki Telegram Bot
After=network.target

[Service]
WorkingDirectory=/srv/nuki_telegram_bot
ExecStart=/srv/nuki_telegram_bot/.venv/bin/python /srv/nuki_telegram_bot/main.py
EnvironmentFile=/srv/nuki_telegram_bot/.env
Restart=always
RestartSec=5
#User=nuki

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nuki-bot.service
sudo systemctl start nuki-bot.service
```

---

## Security Notes

- Never commit `.env` or `users.json`
- Use a dedicated system user
- Restrict access to **[RaspiNukiBridge](https://github.com/dauden1184/RaspiNukiBridge)**
- Unlatch confirmation requires one-time token
- Keep system updated

---

## Development Notes

- Translations stored in `i18n.py`
- Code split into clear modules
- Keep permissions in English internally
- PRs welcome

---

## FAQ

**Does it support the official Nuki Bridge API?**  
No, only RaspiNukiBridge.

**Can I run it remotely (VPS)?**  
Yes, if it can reach RaspiNukiBridge (VPN recommended).

**Multiple locks?**  
Not yet; requires code extension.

**What if users.json is deleted?**  
Admins can recreate everything.

---

## License

MIT License.  
See `LICENSE`.
