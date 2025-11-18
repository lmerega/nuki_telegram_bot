from typing import Dict

DEFAULT_LANG = "it"
SUPPORTED_LANGS = {"it", "en"}


MESSAGES: Dict[str, Dict[str, str]] = {
    # General
    "start_admin": {
        "it": "Ciao admin 👋\nUsa i pulsanti qui sotto per controllare Nuki e gestire gli utenti.",
        "en": "Hi admin 👋\nUse the buttons below to control Nuki and manage users.",
    },
    "start_user": {
        "it": (
            "Ciao 👋\n"
            "Puoi controllare la serratura dai pulsanti qui sotto.\n"
            "Permessi: {perms}"
        ),
        "en": (
            "Hi 👋\n"
            "You can control the lock using the buttons below.\n"
            "Permissions: {perms}"
        ),
    },
    "menu_actions": {
        "it": "Menu azioni:",
        "en": "Actions menu:",
    },
    "unauthorized": {
        "it": "Silence is golden.",
        "en": "Silence is golden.",
    },
    "unknown_command": {
        "it": "Comando sconosciuto. Usa i pulsanti qui sotto.",
        "en": "Unknown command. Use the buttons below.",
    },
    "not_a_command": {
        "it": "\"{text}\" non è un comando. Usa i pulsanti qui sotto.",
        "en": "\"{text}\" is not a command. Use the buttons below.",
    },
    "unknown_text": {
        "it": "Testo non riconosciuto. Usa i pulsanti qui sotto.",
        "en": "Text not recognized. Use the buttons below.",
    },
    # Nuki actions
    "sending_lock": {
        "it": "Invio comando CHIUDI...",
        "en": "Sending LOCK command...",
    },
    "sending_unlock": {
        "it": "Invio comando SBLOCCA...",
        "en": "Sending UNLOCK command...",
    },
    "sending_open": {
        "it": "Invio comando APRI PORTA (unlatch)...",
        "en": "Sending OPEN DOOR (unlatch) command...",
    },
    "sending_lockngo": {
        "it": "Invio comando LOCK'N'GO...",
        "en": "Sending LOCK'N'GO...",
    },
    "reading_state": {
        "it": "Leggo stato serratura...",
        "en": "Reading lock state...",
    },
    "lock_ok": {
        "it": "🔒 Comando di CHIUSURA serratura eseguito.",
        "en": "🔒 LOCK command executed.",
    },
    "unlock_ok": {
        "it": "🔓 Comando di SBLOCCO serratura eseguito.",
        "en": "🔓 UNLOCK command executed.",
    },
    "open_ok": {
        "it": "🚪 Comando di APERTURA PORTA (unlatch) eseguito.",
        "en": "🚪 DOOR OPEN (unlatch) command executed.",
    },
    "lockngo_ok": {
        "it": "🚶‍♂️ Comando LOCK'N'GO inviato.",
        "en": "🚶‍♂️ LOCK'N'GO command sent.",
    },
    "bridge_response_header": {
        "it": "ℹ️ Risposta del bridge Nuki:",
        "en": "ℹ️ Nuki bridge response:",
    },
    "bridge_success": {
        "it": "✅ Il bridge segnala che il comando è andato a buon fine.",
        "en": "✅ The bridge reports that the command completed successfully.",
    },
    "bridge_failure": {
        "it": "❌ Il bridge segnala che il comando NON è stato eseguito correttamente.",
        "en": "❌ The bridge reports that the command did NOT complete successfully.",
    },
    "bridge_unknown": {
        "it": "⚠️ Impossibile determinare con certezza l'esito dal bridge.",
        "en": "⚠️ Unable to determine the result from the bridge.",
    },
    "battery_critical": {
        "it": (
            "🔋 ATTENZIONE: la serratura riporta batteria CRITICA.\n"
            "   Ti conviene sostituire le batterie al più presto."
        ),
        "en": (
            "🔋 WARNING: the lock reports CRITICAL BATTERY.\n"
            "   You should replace the batteries as soon as possible."
        ),
    },
    "battery_ok": {
        "it": "🔋 Batteria OK (non critica).",
        "en": "🔋 Battery OK (not critical).",
    },
    # State summary
    "state_no_data": {
        "it": "Nessun dato di stato disponibile.",
        "en": "No state data available.",
    },
    "state_header_state": {
        "it": "Stato serratura: {state_name} (state={state})",
        "en": "Lock state: {state_name} (state={state})",
    },
    "state_header_door": {
        "it": "Stato porta: {door_state_name} (doorState={door_state})",
        "en": "Door state: {door_state_name} (doorState={door_state})",
    },
    "state_header_battery": {
        "it": "Batteria: {batt_pct}%",
        "en": "Battery: {batt_pct}%",
    },
    "state_header_battery_critical": {
        "it": "Batteria critica: {critical}",
        "en": "Critical battery: {critical}",
    },
    "state_header_timestamp": {
        "it": "Ultimo aggiornamento (UTC): {ts}",
        "en": "Last update (UTC): {ts}",
    },
    # Users / admin
    "no_users": {
        "it": "Nessun utente configurato.",
        "en": "No users configured.",
    },
    "users_title": {
        "it": "Utenti:",
        "en": "Users:",
    },
    "choose_user_to_edit": {
        "it": "Scegli un utente da modificare:",
        "en": "Choose a user to edit:",
    },
    "user_not_found": {
        "it": "Utente {uid} non trovato.",
        "en": "User {uid} not found.",
    },
    "edit_user_header": {
        "it": "Modifica utente:\n",
        "en": "Edit user:\n",
    },
    "user_deleted": {
        "it": "Utente {uid} eliminato.",
        "en": "User {uid} deleted.",
    },
    "add_user_intro": {
        "it": (
            "Aggiunta nuovo utente:\n"
            "Invia ora un messaggio con il formato:\n"
            "<chat_id> [nome]\n"
            "Esempio: 123456789 Mario Rossi"
        ),
        "en": (
            "Add a new user:\n"
            "Send a message with the format:\n"
            "<chat_id> [name]\n"
            "Example: 123456789 John Doe"
        ),
    },
    "add_user_invalid_format": {
        "it": "Formato non valido. Esempio: 123456789 Mario Rossi",
        "en": "Invalid format. Example: 123456789 John Doe",
    },
    "add_user_ok": {
        "it": "Utente {uid} salvato con nome \"{name}\".",
        "en": "User {uid} saved with name \"{name}\".",
    },
    # Language
    "lang_choose": {
        "it": "Scegli la lingua:",
        "en": "Choose your language:",
    },
    "lang_updated": {
        "it": "Lingua aggiornata.",
        "en": "Language updated.",
    },
    # Open door confirmation
    "confirm_open_question": {
        "it": "Sei sicuro di voler APRIRE la porta?",
        "en": "Are you sure you want to OPEN the door?",
    },
    "confirm_open_expired": {
        "it": "Questa richiesta di conferma non è più valida.",
        "en": "This confirmation request is no longer valid.",
    },
    "confirm_open_cancelled": {
        "it": "Apertura porta annullata.",
        "en": "Door opening cancelled.",
    },
}


BUTTONS = {
    "close": {
        "it": "🔒 Chiudi",
        "en": "🔒 Lock",
    },
    "unlock": {
        "it": "🔓 Sblocca",
        "en": "🔓 Unlock",
    },
    "open_door": {
        "it": "🚪 Apri porta",
        "en": "🚪 Open door",
    },
    "lockngo": {
        "it": "🚶‍♂️ Lock'n'Go",
        "en": "🚶‍♂️ Lock'n'Go",
    },
    "status": {
        "it": "📊 Stato",
        "en": "📊 Status",
    },
    "id": {
        "it": "🆔 ID",
        "en": "🆔 ID",
    },
    "add_user": {
        "it": "➕ Add user",
        "en": "➕ Add user",
    },
    "list_users": {
        "it": "📋 Lista utenti",
        "en": "📋 User list",
    },
    "back": {
        "it": "⬅️ Indietro",
        "en": "⬅️ Back",
    },
    "lang": {
        "it": "🌐 Lingua",
        "en": "🌐 Language",
    },
    "yes_open": {
        "it": "✅ Sì, apri",
        "en": "✅ Yes, open",
    },
    "no_cancel": {
        "it": "❌ Annulla",
        "en": "❌ Cancel",
    },
    "perm_all": {
        "it": "✅ Tutti",
        "en": "✅ All",
    },
    "perm_none": {
        "it": "🚫 Nessuno",
        "en": "🚫 None",
    },
    "perm_delete": {
        "it": "🗑 Elimina utente",
        "en": "🗑 Delete user",
    },
    "perm_back": {
        "it": "⬅️ Indietro",
        "en": "⬅️ Back",
    },
}


def t(key: str, lang: str = DEFAULT_LANG, **kwargs) -> str:
    """Translate a message key to the given language, formatting with kwargs."""
    lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    template = MESSAGES.get(key, {}).get(lang, key)
    try:
        return template.format(**kwargs)
    except Exception:
        # In case of missing kwargs, return the template as-is
        return template


def bt(key: str, lang: str = DEFAULT_LANG) -> str:
    """Translate a button label key to the given language."""
    lang = lang if lang in SUPPORTED_LANGS else DEFAULT_LANG
    return BUTTONS.get(key, {}).get(lang, key)
