import json
import logging
import os
from typing import Dict, List, Optional, Tuple, Iterable, Set

from config import get_config

logger = logging.getLogger(__name__)

USERS_FILE = os.getenv("USERS_FILE", "users.json")

# Internal permission keys (English only):
#   - "lock"     → lock the door
#   - "unlock"   → unlock the door
#   - "open"     → unlatch / open door
#   - "lockngo"  → lock'n'go
#   - "status"   → read state
ALL_PERMISSIONS: List[str] = ["lock", "unlock", "open", "lockngo", "status"]

# In-memory store:
# {
#   chat_id (int): {
#       "name": "Some Name",
#       "allowed": ["lock", "status"],
#       "lang": "it" | "en"
#   },
#   ...
# }
_users: Dict[int, Dict] = {}


def _clean_permissions(perms: Iterable[str]) -> List[str]:
    """Keep only known permission identifiers and deduplicate them."""
    cleaned: Set[str] = set()
    for raw in perms:
        if not isinstance(raw, str):
            continue
        if raw in ALL_PERMISSIONS:
            cleaned.add(raw)
    return list(cleaned)


def load_users() -> None:
    """Load users from USERS_FILE into memory.

    Missing file → empty dict.
    """
    global _users
    if not os.path.exists(USERS_FILE):
        logger.warning("Users file %s not found, starting with empty user list.", USERS_FILE)
        _users = {}
        return

    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
    except Exception as exc:
        logger.error("Error reading users file %s: %s", USERS_FILE, exc)
        _users = {}
        return

    raw_users = data.get("users") or {}
    users: Dict[int, Dict] = {}
    for key, cfg in raw_users.items():
        try:
            chat_id = int(key)
        except (TypeError, ValueError):
            logger.warning("Ignoring invalid user key in users.json: %r", key)
            continue
        if not isinstance(cfg, dict):
            logger.warning("Ignoring invalid user config for %s: not an object", key)
            continue

        name = cfg.get("name") or ""
        allowed_raw = cfg.get("allowed") or []
        if not isinstance(allowed_raw, list):
            allowed_raw = []
        lang = cfg.get("lang") or "it"

        allowed = _clean_permissions(allowed_raw)

        users[chat_id] = {
            "name": name,
            "allowed": allowed,
            "lang": lang,
        }

    _users = users
    logger.info("Loaded %d users from %s", len(_users), USERS_FILE)


def save_users() -> None:
    """Persist current users to USERS_FILE.

    Data is always saved using the English internal permission identifiers.
    """
    data = {
        "users": {
            str(chat_id): cfg for chat_id, cfg in _users.items()
        }
    }
    tmp_file = USERS_FILE + ".tmp"
    try:
        with open(tmp_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp_file, USERS_FILE)
        logger.info("Users saved to %s", USERS_FILE)
    except Exception as exc:
        logger.error("Error saving users to %s: %s", USERS_FILE, exc)


def get_users() -> Dict[int, Dict]:
    """Return the internal users mapping (copy)."""
    return dict(_users)


def get_all_users() -> Dict[int, Dict]:
    """Backward-compatible alias used by older code.

    Returns the same as get_users().
    """
    return get_users()


def get_users_sorted() -> List[Tuple[int, Dict]]:
    """Return a list of (chat_id, cfg) sorted by name then ID."""
    return sorted(
        _users.items(),
        key=lambda item: ((item[1].get("name") or "").lower(), item[0]),
    )


def format_user_line(chat_id: int, cfg: Dict) -> str:
    """Helper to render a user line for admin lists."""
    name = cfg.get("name") or "(no name)"
    allowed = cfg.get("allowed") or []
    if allowed:
        perms_str = ", ".join(sorted(allowed))
    else:
        perms_str = "(no permissions)"
    return f"{name} [{chat_id}] - {perms_str}"


def is_known(chat_id: int) -> bool:
    """Return True if the chat_id is known."""
    return chat_id in _users


def is_admin(chat_id: int) -> bool:
    """Return True if the chat_id is in the owners list."""
    cfg = get_config()
    return chat_id in cfg.owners


def can_do(chat_id: int, command: str) -> bool:
    """Return True if the user is allowed to perform the given command.

    Command must be one of the ALL_PERMISSIONS list in English.
    Admin users can always do anything.
    """
    if is_admin(chat_id):
        return True
    cfg = _users.get(chat_id)
    if not cfg:
        return False
    allowed: Iterable[str] = cfg.get("allowed") or []
    return command in allowed


def get_user_cfg(chat_id: int) -> Optional[Dict]:
    """Return raw user config dict or None."""
    return _users.get(chat_id)


def add_or_update_user(chat_id: int, name: str, allowed: Optional[List[str]] = None) -> None:
    """Create or update a user with the given name and allowed permissions.

    The 'allowed' list must use the English permission identifiers.
    """
    if allowed is None:
        allowed = []
    allowed_clean = _clean_permissions(allowed)
    cfg = _users.get(chat_id) or {}
    cfg["name"] = name
    cfg["allowed"] = allowed_clean
    # Preserve existing lang if present, otherwise default to Italian
    cfg.setdefault("lang", "it")
    _users[chat_id] = cfg
    save_users()


def delete_user(chat_id: int) -> bool:
    """Delete a user.

    :return: True if deleted, False if not present.
    """
    if chat_id in _users:
        del _users[chat_id]
        save_users()
        return True
    return False


def toggle_permission(chat_id: int, perm: str) -> bool:
    """Toggle a single permission for a user (English identifier)."""
    if perm not in ALL_PERMISSIONS:
        return False
    cfg = _users.get(chat_id)
    if not cfg:
        return False
    allowed: List[str] = list(cfg.get("allowed") or [])
    if perm in allowed:
        allowed.remove(perm)
    else:
        allowed.append(perm)
    cfg["allowed"] = _clean_permissions(allowed)
    _users[chat_id] = cfg
    save_users()
    return True


def grant_all_permissions(chat_id: int) -> bool:
    """Grant all permissions to the given user."""
    cfg = _users.get(chat_id)
    if not cfg:
        return False
    current: Set[str] = set(cfg.get("allowed") or [])
    target: Set[str] = set(ALL_PERMISSIONS)
    if current == target:
        return False
    cfg["allowed"] = list(target)
    _users[chat_id] = cfg
    save_users()
    return True


def revoke_all_permissions(chat_id: int) -> bool:
    """Remove all permissions for the given user."""
    cfg = _users.get(chat_id)
    if not cfg:
        return False
    old_allowed = cfg.get("allowed") or []
    if not old_allowed:
        return False
    cfg["allowed"] = []
    _users[chat_id] = cfg
    save_users()
    return True


def get_user_lang(chat_id: int) -> str:
    """Return the preferred language for this user, defaulting to Italian."""
    cfg = _users.get(chat_id)
    if not cfg:
        return "it"
    return cfg.get("lang") or "it"


def set_user_lang(chat_id: int, lang: str) -> None:
    """Set the preferred language for this user."""
    cfg = _users.get(chat_id) or {}
    cfg.setdefault("name", "")
    cfg.setdefault("allowed", [])
    cfg["lang"] = lang
    _users[chat_id] = cfg
    save_users()
