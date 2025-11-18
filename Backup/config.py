import json
import logging
import os
from dataclasses import dataclass
from typing import Set, Optional

logger = logging.getLogger(__name__)

CONFIG_FILE = "config.json"


@dataclass
class BotConfig:
    telegram_bot_token: str
    bridge_host: str
    bridge_port: int
    nuki_token: str
    nuki_id: int
    device_type: int
    owner_ids: Set[int]


_config: Optional[BotConfig] = None


def load_config(path: str = CONFIG_FILE) -> BotConfig:
    """
    Legge config.json e inizializza la configurazione globale.
    Lancia RuntimeError se mancano dati obbligatori.
    """
    global _config

    if not os.path.exists(path):
        raise RuntimeError(f"{path} non trovato")

    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    telegram_bot_token = cfg.get("telegram_bot_token", "").strip()
    if not telegram_bot_token:
        raise RuntimeError("telegram_bot_token mancante in config.json")

    owners = cfg.get("owners") or []
    owner_ids: Set[int] = set(int(x) for x in owners)

    bridge_host = cfg.get("bridge_host", "127.0.0.1")
    bridge_port = int(cfg.get("bridge_port", 8080))

    nuki_token = cfg.get("nuki_token", "").strip()
    if not nuki_token:
        raise RuntimeError("nuki_token mancante in config.json")

    nuki_id = int(cfg.get("nuki_id", 0))
    if not nuki_id:
        raise RuntimeError("nuki_id mancante o 0 in config.json")

    device_type = int(cfg.get("device_type", 0))

    _config = BotConfig(
        telegram_bot_token=telegram_bot_token,
        bridge_host=bridge_host,
        bridge_port=bridge_port,
        nuki_token=nuki_token,
        nuki_id=nuki_id,
        device_type=device_type,
        owner_ids=owner_ids,
    )

    logger.info(
        "Config caricata: owners=%s, bridge=%s:%s, nuki_id=%s, device_type=%s",
        owner_ids,
        bridge_host,
        bridge_port,
        nuki_id,
        device_type,
    )

    return _config


def get_config() -> BotConfig:
    """
    Restituisce la configurazione corrente.
    Assicurarsi che load_config() sia stato chiamato prima.
    """
    if _config is None:
        raise RuntimeError("Config non caricata. Chiama load_config() prima di get_config().")
    return _config
