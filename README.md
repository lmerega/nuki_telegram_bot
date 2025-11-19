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
</p>

> ⚠️ **Compatibility Notice**  
> This bot works **ONLY** with **[RaspiNukiBridge](https://github.com/lmerega/RaspiNukiBridge)**.  
> It does **not** support the official Nuki Bridge HTTP API directly.

---

## Overview

**Nuki Telegram Bot** is a self‑hosted Telegram bot that lets you control a [Nuki](https://nuki.io/) smart lock through a **RaspiNukiBridge** instance (for example running on a Raspberry Pi).

The bot is designed to be simple, privacy‑friendly and production ready:

- Self‑hosted (VPS, home server, Raspberry Pi, etc.)
- Fine‑grained per‑user permissions (lock, unlock, open door, lock'n'go, status)
- Admin user management with inline keyboards
- Multi‑language support (Italian / English) per user
- Safety confirmation before door unlatch (open)
- Configuration via environment variables / `.env` file
- Easy service management with `systemd`

---

## Features

### User features

- `/start` command with a main inline keyboard and permission summary
- `/id` command to display your `chat_id` and basic profile info
- Inline buttons to:
  - Lock / unlock the door
  - Open the door (unlatch) — with confirmation
  - Lock'n'Go
  - Read the current lock state
  - Change language (Italian / English)
- Per‑user interface language (English or Italian) without affecting others

### Admin features

Admins are Telegram chat IDs listed in the `OWNERS` environment variable. Admins:

- See additional buttons in the main menu
- Can **add new users** interactively (by chat ID and optional name)
- Can **list users** and, for each user:
  - Toggle individual permissions
  - Grant all permissions
  - Revoke all permissions
  - Delete the user
- Always have full permissions regardless of what is stored in `users.json`

### Permissions model

Each user can have a subset of these internal permission keys:

- `lock` – lock the door
- `unlock` – unlock the door
- `open` – unlatch / open door
- `lockngo` – lock'n'go
- `status` – read current state

These permission identifiers are always in **English** internally, independent of the UI language.

---

## Compatibility

> ✅ **Supported:** Nuki smart lock controlled via **RaspiNukiBridge**  
> ❌ **Not supported:** Direct usage of the official Nuki Bridge HTTP API

This bot assumes that your Nuki smart lock is exposed through a running **RaspiNukiBridge** instance (for example on a Raspberry Pi in your LAN).  
The bot communicates only with that bridge and does not talk to Nuki cloud services.

If you currently use only the official Nuki HTTP Bridge (without RaspiNukiBridge), you must first deploy RaspiNukiBridge and configure it for your lock before using this bot.

---

## Architecture

The project is structured into a few small, focused modules:

- **`main.py`**  
  Entrypoint. Loads configuration and users, sets up the Telegram `Application`, registers handlers and starts polling.

- **`config.py`**  
  Loads configuration from environment variables into a `BotConfig` dataclass.

- **`users.py`**  
  Manages known users and their permissions, backed by `users.json`.  
  All internal permission keys are English: `lock`, `unlock`, `open`, `lockngo`, `status`.

- **`nuki.py`**  
  Wraps the HTTP API exposed by RaspiNukiBridge (e.g. lock action / status endpoints) and exposes small helper functions to the rest of the bot.

- **`bot_handlers.py`**  
  Contains all Telegram bot handlers, inline keyboards, admin flows and text processing.

- **`i18n.py`**  
  Minimal helper for internationalization / translations (currently Italian and English).  
  All strings in the code are English; translations are applied at runtime based on each user's preferred language.

Runtime data that can change (users, permissions, preferred language, etc.) is stored in **`users.json`**, not in environment variables.

---

## Requirements

- **Python** 3.10+
- **RaspiNukiBridge** running and reachable from the bot
- A **Nuki** smart lock configured with RaspiNukiBridge
- A **Telegram bot token** (from [BotFather](https://core.telegram.org/bots#6-botfather))

Install Python dependencies:

```bash
pip install -r requirements.txt
```

> 💡 It is strongly recommended to use a virtual environment:
>
> ```bash
> python -m venv .venv
> source .venv/bin/activate
> pip install -r requirements.txt
> ```

---

## Installation

Clone the repository and install dependencies:

```bash
cd /srv
git clone https://github.com/lmerega/nuki_telegram_bot.git
cd nuki_telegram_bot

python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create your own configuration by copying the example files (if present) or creating a new `.env` and `users.json` as described below.

---

## Configuration

The bot reads configuration from **environment variables**.  
In development you can use a local `.env` file, and in production you can either keep using `.env` or point `systemd` to an `EnvironmentFile`.

### Example `.env`

```env
# Telegram
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# RaspiNukiBridge / Nuki lock
NUKI_TOKEN=your_raspinukibridge_token_here
NUKI_BRIDGE_HOST=192.168.1.50
NUKI_BRIDGE_PORT=8080
NUKI_ID=123456789
NUKI_DEVICE_TYPE=0

# Comma-separated list of Telegram chat IDs that are admins
OWNERS=123456789,987654321

# Path to the JSON file where user data is stored
USERS_FILE=/srv/nuki_telegram_bot/users.json
```

> 🔑 **Notes**
>
> - `TELEGRAM_BOT_TOKEN` comes from BotFather.
> - `NUKI_TOKEN`, `NUKI_BRIDGE_HOST`, `NUKI_BRIDGE_PORT`, `NUKI_ID`, `NUKI_DEVICE_TYPE` must match your **RaspiNukiBridge** configuration.
> - `OWNERS` is a comma‑separated list of chat IDs that will have admin privileges in the bot.
> - `USERS_FILE` should point to a writable JSON file; it will be created/updated automatically by the bot.

### Environment variables summary

| Variable            | Required | Description                                              |
| ------------------- | :------: | -------------------------------------------------------- |
| `TELEGRAM_BOT_TOKEN`|   yes    | Telegram bot token                                       |
| `NUKI_TOKEN`        |   yes    | API token for RaspiNukiBridge                            |
| `NUKI_BRIDGE_HOST`  |   yes    | IP/hostname where RaspiNukiBridge is running            |
| `NUKI_BRIDGE_PORT`  |   yes    | Port of RaspiNukiBridge HTTP API                        |
| `NUKI_ID`           |   yes    | Nuki lock ID                                            |
| `NUKI_DEVICE_TYPE`  |   yes    | Nuki device type (e.g. `0` for Smart Lock)              |
| `OWNERS`            |   yes    | Comma‑separated list of admin chat IDs                  |
| `USERS_FILE`        |   yes    | Path to `users.json` file                               |

---

## Users file (`users.json`)

Users are stored in `users.json` and automatically created/updated via the admin inline UI.

An example structure:

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

- `allowed` is a list of **English** permission identifiers:
  - `lock`     → lock the door  
  - `unlock`   → unlock the door  
  - `open`     → unlatch / open door  
  - `lockngo`  → lock'n'go  
  - `status`   → read current state  
- `lang` is the preferred language for that user (`"it"` or `"en"`).

> 📝 **Best practice**  
> Version control only a `users.example.json` file, **not** your real `users.json` (which contains real chat IDs and permissions).

---

## Running the bot (development)

1. **Create and activate a virtualenv** (optional but recommended):

   ```bash
   cd /srv/nuki_telegram_bot
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Create your `.env`** file based on the example above and fill in your tokens and host/port.

3. **Run the bot**:

   ```bash
   python main.py
   ```

The bot uses long polling (`run_polling`).  
Once it is running, open Telegram, start a chat with your bot and send:

```text
/start
```

---

## Usage

### Regular users

Available commands (depending on granted permissions):

- `/start` – Shows the main inline keyboard and a short summary of your permissions.
- `/id` – Shows your `chat_id` and basic profile info (useful for admins when adding new users).

From the main inline keyboard users can:

- Lock / unlock the door
- Open the door (unlatch) – with a confirmation step
- Use Lock'n'Go
- Read current lock state
- Change their language (Italian / English)

Each user can switch their own language; only the **UI text** changes, while internal logic and permission keys remain in English.

### Admins

Admins are the chat IDs listed in the `OWNERS` environment variable.

In addition to regular user features, admins see extra buttons to:

- **Add user** – Interactive flow to create a new user by chat ID and optional name.
- **User list** – List of known users with options to:
  - Toggle individual permissions
  - Grant all permissions
  - Revoke all permissions
  - Delete the user

Admins can always perform **every action** regardless of their `allowed` permissions list in `users.json`.

---

## Deployment with systemd (example)

On a typical Linux server you can keep the bot running with `systemd`.

Example unit file: `/etc/systemd/system/nuki-bot.service`

```ini
[Unit]
Description=Nuki Telegram Bot
After=network.target

[Service]
WorkingDirectory=/srv/nuki_telegram_bot
ExecStart=/srv/nuki_telegram_bot/.venv/bin/python /srv/nuki_telegram_bot/main.py

# Load environment variables for the bot
EnvironmentFile=/srv/nuki_telegram_bot/.env

Restart=always
RestartSec=5

# It is recommended to run as a dedicated user instead of root
#User=nuki
#Group=nuki

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable nuki-bot.service
sudo systemctl start nuki-bot.service
sudo systemctl status nuki-bot.service
```

---

## Security notes

- Do **not** commit your real `.env` or `users.json` to the repository.
- Keep your **Telegram bot token** and **RaspiNukiBridge token** secret.
- Run the bot under a **dedicated unprivileged user** in production.
- Restrict network access to the RaspiNukiBridge HTTP interface (firewall, VPN, or local LAN only).
- The "open door" (unlatch) action always includes an additional confirmation step with a one‑time token to prevent accidental taps or interaction with old messages.
- Regularly update your dependencies and system packages to receive security fixes.

---

## Development notes

- Code is organized into small modules (`config.py`, `users.py`, `nuki.py`, `bot_handlers.py`, `i18n.py`, etc.) to keep concerns separated.
- Configuration is centralized in `config.py` using a dataclass for clarity and type safety.
- User data is persisted to `users.json` through the admin interface; editing the file manually should be done with care and only when the bot is stopped.
- When adding new features:
  - Keep all user‑visible strings in English and add translations via `i18n.py`.
  - Reuse the existing permission model (`lock`, `unlock`, `open`, `lockngo`, `status`) where possible.
- Pull requests and issues are welcome on GitHub.

---

## FAQ

**Q: Does this bot work with the official Nuki Bridge HTTP API?**  
**A:** No. This bot is designed to work **only** with **RaspiNukiBridge**. You must have RaspiNukiBridge running and properly configured for your Nuki lock.

---

**Q: Can I run the bot on a VPS while RaspiNukiBridge is at home?**  
**A:** Yes, as long as the VPS can reach RaspiNukiBridge over the network (for example via VPN or a securely exposed HTTPS endpoint). Make sure you secure access to the bridge (firewall, authentication, VPN, etc.).

---

**Q: Can I control multiple locks?**  
**A:** The current configuration is designed around a **single lock** (`NUKI_ID`, `NUKI_DEVICE_TYPE`). Controlling multiple locks would require either multiple deployments (one per lock) or extending the code to support multiple devices and per‑user lock selection.

---

**Q: What happens if `users.json` is deleted or corrupted?**  
**A:** If `users.json` is missing, the bot will start with no regular users and only the admins listed in `OWNERS` will be able to manage access and recreate entries. If the file is corrupted, you may need to restore it from a backup or rebuild it via the admin UI.

---

**Q: How do I find my Telegram chat ID to add a new user?**  
**A:** Ask the user to start the bot and run the `/id` command. The bot will respond with their chat ID, which you can then use from the admin interface to grant permissions.

---

**Q: How do I change a user’s language?**  
**A:** Users can change their own language from the inline menu (language button). Admins can also adjust the `lang` value in `users.json` manually (preferably while the bot is stopped) or through the admin flows if supported in the UI.

---

**Q: Can the bot be used without Internet access?**  
**A:** Once the bot is set up, it needs Internet access only to talk to the Telegram Bot API. Communication with RaspiNukiBridge can stay fully within your local network.

---

## License

This project is licensed under the **MIT License**.  
See the [`LICENSE`](LICENSE) file for full license text.
