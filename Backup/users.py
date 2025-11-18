import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Iterable, Set

from config import get_config

logger = logging.getLogger(__name__)

USERS_FILE = "users.json"

# Struttura utenti:
# {
#   chat_id (int): {
#       "name": "Mario",
#       "allowed": ["chiudi", "sblocca", "stato", "apri", "lockngo"]
#   },
#   ...
# }
_users: Dict[int, dict] = {}

VALID_COMMANDS: Set[str] = {"chiudi", "sblocca", "apri", "lockngo", "stato"}


def load_users() -> None:
    """
    Carica gli utenti da users.json.
    Pulisce eventuali chiavi legacy (es: latch_password).
    """
    global _users
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            raw_users = data.get("users", {})
            _users = {int(k): v for k, v in raw_users.items()}
            # pulizia vecchie chiavi
            for cfg in _users.values():
                cfg.pop("latch_password", None)
            logger.info("Utenti caricati: %s", _users)
        except Exception as e:
            logger.error("Errore leggendo %s: %s", USERS_FILE, e)
            _users = {}
    else:
        _users = {}
        logger.info("Nessun file utenti, si parte da zero.")


def save_users() -> None:
    """
    Salva la struttura utenti su users.json.
    """
    try:
        data = {"users": _users}
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info("Utenti salvati: %s", _users)
    except Exception as e:
        logger.error("Errore scrivendo %s: %s", USERS_FILE, e)


def is_admin(chat_id: int) -> bool:
    """
    True se il chat_id appartiene agli owner definiti in config.json.
    """
    return chat_id in get_config().owner_ids


def get_user_cfg(chat_id: int) -> Optional[dict]:
    return _users.get(chat_id)


def is_known(chat_id: int) -> bool:
    """
    Un utente è 'known' se è admin o se è presente in users.json.
    """
    return is_admin(chat_id) or chat_id in _users


def can_do(chat_id: int, cmd: str) -> bool:
    """
    True se l'utente (o admin) può eseguire il comando cmd.
    """
    if is_admin(chat_id):
        return True
    cfg = get_user_cfg(chat_id)
    if not cfg:
        return False
    allowed: List[str] = cfg.get("allowed") or []
    return cmd in allowed


def format_user_line(chat_id: int, cfg: dict) -> str:
    name = cfg.get("name") or ""
    allowed = cfg.get("allowed") or []
    return f"{chat_id} - {name}  |  permessi: {', '.join(allowed) if allowed else '(nessuno)'}"


def get_all_users() -> Dict[int, dict]:
    """
    Ritorna il dict grezzo degli utenti (solo lettura logica).
    """
    return _users


def get_users_sorted() -> Iterable[Tuple[int, dict]]:
    """
    Ritorna una lista di (chat_id, cfg) ordinata per chat_id.
    """
    return sorted(_users.items(), key=lambda kv: kv[0])


def add_or_update_user(chat_id: int, name: str, allowed: List[str]) -> None:
    """
    Crea o aggiorna un utente con il set di permessi specificato.
    """
    _users[chat_id] = {
        "name": name,
        "allowed": allowed,
    }
    save_users()


def update_user_allowed(chat_id: int, allowed: List[str]) -> None:
    """
    Aggiorna la lista di permessi per un utente esistente.
    Se l'utente non esiste, viene creato con nome vuoto.
    """
    cfg = _users.get(chat_id) or {}
    cfg.setdefault("name", "")
    cfg["allowed"] = allowed
    _users[chat_id] = cfg
    save_users()


def remove_user(chat_id: int) -> bool:
    """
    Rimuove un utente. Ritorna True se esisteva.
    """
    if chat_id in _users:
        del _users[chat_id]
        save_users()
        return True
    return False


def toggle_user_command(chat_id: int, cmd: str) -> None:
    """
    Attiva/disattiva un singolo comando per l'utente.
    """
    if cmd not in VALID_COMMANDS:
        return
    cfg = _users.get(chat_id)
    if not cfg:
        return
    allowed = set(cfg.get("allowed") or [])
    if cmd in allowed:
        allowed.remove(cmd)
    else:
        allowed.add(cmd)
    cfg["allowed"] = sorted(allowed)
    _users[chat_id] = cfg
    save_users()


def set_all_permissions(chat_id: int) -> bool:
    """
    Imposta tutti i permessi disponibili per l'utente.
    Ritorna True se qualcosa è cambiato, False se erano già tutti attivi.
    """
    cfg = _users.get(chat_id)
    if not cfg:
        return False

    new_allowed = sorted(VALID_COMMANDS)
    old_allowed = sorted(cfg.get("allowed") or [])

    if old_allowed == new_allowed:
        # Nessun cambiamento
        return False

    cfg["allowed"] = new_allowed
    _users[chat_id] = cfg
    save_users()
    return True

def clear_permissions(chat_id: int) -> bool:
    """
    Rimuove tutti i permessi per l'utente.
    Ritorna True se qualcosa è cambiato, False se erano già vuoti.
    """
    cfg = _users.get(chat_id)
    if not cfg:
        return False

    old_allowed = cfg.get("allowed") or []
    if not old_allowed:
        # Già nessun permesso
        return False

    cfg["allowed"] = []
    _users[chat_id] = cfg
    save_users()
    return True
