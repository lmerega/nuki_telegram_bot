import logging
import os
from dataclasses import dataclass
from typing import List, Optional

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from a local .env file if present
load_dotenv()


@dataclass
class BotConfig:
    telegram_bot_token: str
    bridge_host: str
    bridge_port: int
    nuki_token: str
    nuki_id: int
    device_type: int
    owners: List[int]


_config: Optional[BotConfig] = None


def _read_env_int(name: str, default: Optional[int] = None) -> int:
    value = os.getenv(name)
    if value is None or value == "":
        if default is None:
            raise RuntimeError(f"Missing required int env variable: {name}")
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Env variable {name} must be an integer, got {value!r}") from exc


def _read_env_str(name: str, required: bool = True, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if required and (value is None or value == ""):
        raise RuntimeError(f"Missing required env variable: {name}")
    assert value is not None
    return value


def load_config() -> BotConfig:
    """Load configuration from environment variables.

    This function MUST be called once at startup (see :mod:`main`).
    It will also try to be reasonably helpful with error messages if something is missing.
    """
    global _config

    if _config is not None:
        return _config

    telegram_bot_token = _read_env_str("TELEGRAM_BOT_TOKEN")
    bridge_host = _read_env_str("NUKI_BRIDGE_HOST", required=False, default="127.0.0.1")
    bridge_port = _read_env_int("NUKI_BRIDGE_PORT", default=8080)
    nuki_token = _read_env_str("NUKI_TOKEN")
    nuki_id = _read_env_int("NUKI_ID")
    device_type = _read_env_int("NUKI_DEVICE_TYPE", default=0)

    owners_env = os.getenv("OWNERS", "")
    owners: List[int] = []
    if owners_env.strip():
        for raw in owners_env.split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                owners.append(int(raw))
            except ValueError:
                logger.warning("Ignoring invalid OWNERS entry %r (not an int)", raw)

    if not owners:
        logger.warning(
            "No OWNERS defined. Nobody will have admin permissions. "
            "Set OWNERS in your environment to a comma-separated list of Telegram chat IDs."
        )

    _config = BotConfig(
        telegram_bot_token=telegram_bot_token,
        bridge_host=bridge_host,
        bridge_port=bridge_port,
        nuki_token=nuki_token,
        nuki_id=nuki_id,
        device_type=device_type,
        owners=owners,
    )

    logger.info(
        "Configuration loaded. bridge=%s:%s, owners=%s",
        bridge_host,
        bridge_port,
        owners or "[]",
    )

    return _config


def get_config() -> BotConfig:
    """Return the current configuration.

    :raises RuntimeError: if :func:`load_config` has not been called first.
    """
    if _config is None:
        raise RuntimeError("Config not loaded. Call load_config() before get_config().")
    return _config
