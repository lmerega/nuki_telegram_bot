# Nuki Telegram Bot

A simple Telegram bot to control a [Nuki] (https://nuki.io/) smart lock via the Nuki Bridge HTTP API.

The bot is designed to be self‑hosted (for example on a small VPS) and supports:

- Per‑user permissions (lock, unlock, open door, lock'n'go, status)
- Admin user management with inline keyboards
- Multi‑language support (Italian / English) on a per‑user basis
- Safety confirmation before opening the door (unlatch)
- Configuration via environment variables / `.env` file
- Systemd service friendly layout

---

## Architecture

The project is organized into a few small modules:

- `main.py` – Entrypoint that loads configuration and users, sets up the Telegram `Application`, registers handlers and starts polling.
- `config.py` – Loads configuration from environment variables into a `BotConfig` dataclass.
- `users.py` – Manages known users and their permissions, backed by `users.json`. All internal permission keys are English: `lock`, `unlock`, `open`, `lockngo`, `status`.
- `nuki.py` – Wraps the Nuki Bridge HTTP API (`/lockAction`, `/lockState`) and exposes small helper functions.
- `bot_handlers.py` – All Telegram bot handlers, inline keyboards, admin flows and text processing.
- `i18n.py` – Tiny helper for internationalization / translations (currently Italian and English). All strings in the code are English; translations are applied at runtime based on user preference.

Data that changes at runtime (users, permissions, preferred language) is stored in `users.json`, not in environment variables.

---

## Requirements

- Python 3.10+
- A Nuki lock with a Nuki Bridge reachable by the bot
- A Telegram bot token (from BotFather)

Install Python dependencies:

```bash
pip install -r requirements.txt
```

(You are strongly encouraged to use a virtualenv, e.g. `python -m venv .venv && source .venv/bin/activate`.)

---

## Configuration

The bot reads configuration from environment variables. In development you can use a local `.env` file, and in production you can either keep using `.env` or point `systemd` to an `EnvironmentFile`.

Example `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

NUKI_TOKEN=your_nuki_bridge_token_here
NUKI_BRIDGE_HOST=192.168.1.50
NUKI_BRIDGE_PORT=8080
NUKI_ID=123456789
NUKI_DEVICE_TYPE=0

# Comma-separated list of Telegram chat IDs that are admins
OWNERS=123456789,987654321

# Path to the JSON file where user data is stored
USERS_FILE=/srv/nuki_telegram_bot/users.json
```

### Users file (`users.json`)

Users are stored in `users.json` and automatically created/updated via the admin inline UI.  
An example structure looks like:

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

In production you should version only `users.example.json` and **not** your real `users.json` (which contains real chat IDs).

---

## Running the bot (development)

1. Create and activate a virtualenv (optional but recommended):

   ```bash
   cd /path/to/nuki_telegram_bot
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Create a `.env` file based on `.env.example` and fill in your tokens and IP/port.
3. Run the bot:

   ```bash
   python main.py
   ```

The bot uses long polling (`run_polling`). Once it is running, open Telegram, start a chat with your bot and send `/start`.

---

## Usage

### Regular users

Commands available to regular users (depending on permissions granted by an admin):

- `/start` – Shows the main inline keyboard and a short summary of your permissions.
- `/id` – Shows your `chat_id` and basic profile info (useful for admins when adding new users).

The main inline keyboard gives you buttons to:

- Lock / unlock the door
- Open the door (unlatch) – with a confirmation step
- Lock'n'Go
- Read the current lock state
- Change your language (Italian / English)

Each user can switch their own language; only the **UI text** changes, the internal logic and permission names remain in English.

### Admins

Admins are the chat IDs listed in the `OWNERS` environment variable.

Admins see additional buttons in the main menu:

- **Add user** – interactive flow to create a new user by chat ID and optional name.
- **User list** – list of known users; you can select one and:
  - toggle individual permissions
  - grant all permissions
  - revoke all permissions
  - delete the user

Admins can always perform every action regardless of their `allowed` permissions list.

---

## Deployment with systemd (example)

A typical deployment on a Linux server uses `systemd` to keep the bot running.

Example unit file `/etc/systemd/system/nuki-bot.service`:

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
- Keep your Telegram bot token and Nuki token secret.
- Run the bot under a dedicated unprivileged user in production.
- Restrict access to the Nuki Bridge HTTP interface (firewall, VPN, local network, etc.).
- Opening the door (unlatch) always goes through an additional confirmation step with a one‑time token to avoid accidental clicks or interaction with old messages.

---

## License

This project is licensed under the MIT License – see the LICENSE file for details.
