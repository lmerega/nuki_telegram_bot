import asyncio
import json
import logging
import secrets  # [TOKEN] per generare token univoci di conferma
from typing import List, Tuple, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest


from users import (
    is_admin,
    is_known,
    can_do,
    get_user_cfg,
    get_all_users,
    get_users_sorted,
    format_user_line,
    VALID_COMMANDS,
    add_or_update_user,
    update_user_allowed,
    remove_user,
    toggle_user_command,
    set_all_permissions,
    clear_permissions,
)
from nuki import nuki_lock_action, nuki_lock_state, summarize_state

logger = logging.getLogger(__name__)


# ========= MENU BUILDERS =========
def build_main_menu(chat_id: int) -> InlineKeyboardMarkup:
    buttons: List[List[InlineKeyboardButton]] = []

    # Comandi serratura
    row1: List[InlineKeyboardButton] = []
    if can_do(chat_id, "chiudi"):
        row1.append(InlineKeyboardButton("🔒 Chiudi", callback_data="cmd:chiudi"))
    if can_do(chat_id, "sblocca"):
        row1.append(InlineKeyboardButton("🔓 Sblocca", callback_data="cmd:sblocca"))
    if row1:
        buttons.append(row1)

    row2: List[InlineKeyboardButton] = []
    if can_do(chat_id, "apri"):
        row2.append(InlineKeyboardButton("🚪 Apri porta", callback_data="cmd:apri"))
    if can_do(chat_id, "lockngo"):
        row2.append(InlineKeyboardButton("🚶‍♂️ Lock'n'Go", callback_data="cmd:lockngo"))
    if row2:
        buttons.append(row2)

    row3: List[InlineKeyboardButton] = []
    if can_do(chat_id, "stato"):
        row3.append(InlineKeyboardButton("📊 Stato", callback_data="cmd:stato"))
    # Il tasto ID esiste sempre per gli utenti noti
    row3.append(InlineKeyboardButton("🆔 ID", callback_data="cmd:id"))
    buttons.append(row3)

    # Admin row
    if is_admin(chat_id):
        admin_row = [
            InlineKeyboardButton("➕ Add user", callback_data="admin:adduser_help"),
            InlineKeyboardButton("📋 Lista utenti", callback_data="admin:listusers"),
        ]
        buttons.append(admin_row)

    return InlineKeyboardMarkup(buttons)


def build_edit_user_view(uid: int) -> Tuple[str, InlineKeyboardMarkup]:
    cfg = get_user_cfg(uid)
    if not cfg:
        text = f"Utente {uid} non trovato."
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("⬅️ Indietro", callback_data="admin:listusers")]]
        )
        return text, kb

    name = cfg.get("name") or ""
    allowed: List[str] = cfg.get("allowed") or []

    def flag(cmd: str) -> str:
        return "✅" if cmd in allowed else "❌"

    text = "Modifica utente:\n" + format_user_line(uid, cfg)

    rows: List[List[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                f"{flag('chiudi')} chiudi",
                callback_data=f"admin:toggle:{uid}:chiudi",
            ),
            InlineKeyboardButton(
                f"{flag('sblocca')} sblocca",
                callback_data=f"admin:toggle:{uid}:sblocca",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{flag('apri')} apri",
                callback_data=f"admin:toggle:{uid}:apri",
            ),
            InlineKeyboardButton(
                f"{flag('lockngo')} lockngo",
                callback_data=f"admin:toggle:{uid}:lockngo",
            ),
        ],
        [
            InlineKeyboardButton(
                f"{flag('stato')} stato",
                callback_data=f"admin:toggle:{uid}:stato",
            ),
        ],
        [
            InlineKeyboardButton(
                "✅ Tutti",
                callback_data=f"admin:setall:{uid}",
            ),
            InlineKeyboardButton(
                "🚫 Nessuno",
                callback_data=f"admin:setnone:{uid}",
            ),
        ],
        [
            InlineKeyboardButton(
                "🗑 Elimina utente",
                callback_data=f"admin:del:{uid}",
            ),
            InlineKeyboardButton("⬅️ Indietro", callback_data="admin:listusers"),
        ],
    ]

    return text, InlineKeyboardMarkup(rows)


# ========= UTIL TELEGRAM / NUKI =========
async def handle_unauthorized(update: Update):
    """
    Risposta standard per non autorizzati (testo e comandi, tranne /id).
    """
    if update.effective_message:
        await update.effective_message.reply_text("Silence is golden.")


def format_nuki_action_response(res: dict, op: Optional[str] = None) -> str:
    """
    Rende la risposta del bridge più leggibile per l'utente.
    op può essere: "chiudi", "sblocca", "apri", "lockngo" (o None per generico).
    """
    parts: List[str] = []

    # Intestazione in base all'operazione
    if op == "chiudi":
        parts.append("🔒 Comando di CHIUSURA serratura eseguito.")
    elif op == "sblocca":
        parts.append("🔓 Comando di SBLOCCO serratura eseguito.")
    elif op == "apri":
        parts.append("🚪 Comando di APERTURA PORTA (unlatch) eseguito.")
    elif op == "lockngo":
        parts.append("🚶‍♂️ Comando LOCK'N'GO inviato.")
    else:
        parts.append("ℹ️ Risposta del bridge Nuki:")

    success = res.get("success")
    if success is True:
        parts.append("✅ Il bridge segnala che il comando è andato a buon fine.")
    elif success is False:
        parts.append(
            "❌ Il bridge segnala che il comando NON è stato eseguito correttamente."
        )
    else:
        parts.append("⚠️ Impossibile determinare con certezza l'esito dal bridge.")

    # Info batteria, se presenti
    if "batteryCritical" in res:
        if res["batteryCritical"]:
            parts.append(
                "🔋 ATTENZIONE: la serratura riporta batteria CRITICA.\n"
                "   Ti conviene sostituire le batterie al più presto."
            )
        else:
            parts.append("🔋 Batteria OK (non critica).")

    # Qui potresti aggiungere altri dettagli se il bridge li fornisce (es. errorCode, status, ecc.)

    return "\n".join(parts)


# ========= COMMAND HANDLERS =========
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not is_known(chat_id):
        return await handle_unauthorized(update)

    if is_admin(chat_id):
        text = "Ciao admin 👋\nUsa i pulsanti qui sotto per controllare il Nuki e gli utenti."
    else:
        cfg = get_user_cfg(chat_id)
        allowed = cfg.get("allowed") if cfg else []
        text = (
            "Ciao 👋\n"
            "Puoi controllare la serratura dai pulsanti qui sotto.\n"
            f"Permessi: {', '.join(allowed) if allowed else '(nessuno)'}"
        )

    await update.effective_message.reply_text(
        text, reply_markup=build_main_menu(chat_id)
    )


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # /id funziona SEMPRE, anche per non autorizzati
    chat = update.effective_chat
    msg = (
        f"Il tuo chat_id è: {chat.id}\n"
        f"Nome: {chat.full_name} (@{chat.username})"
    )
    await update.effective_message.reply_text(msg)
    # se è noto, mostra anche il menu
    if is_known(chat.id):
        await update.effective_message.reply_text(
            "Menu azioni:", reply_markup=build_main_menu(chat.id)
        )


async def cmd_chiudi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not can_do(chat_id, "chiudi"):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text("Invio comando CHIUDI...")
    res = await asyncio.to_thread(nuki_lock_action, 2)

    if "error" in res:
        await update.effective_message.reply_text(f"Errore: {res['error']}")
    else:
        await update.effective_message.reply_text(
            format_nuki_action_response(res, op="chiudi")
        )

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def cmd_sblocca(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not can_do(chat_id, "sblocca"):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text("Invio comando SBLOCCA...")
    res = await asyncio.to_thread(nuki_lock_action, 1)

    if "error" in res:
        await update.effective_message.reply_text(f"Errore: {res['error']}")
    else:
        await update.effective_message.reply_text(
            format_nuki_action_response(res, op="sblocca")
        )

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def cmd_apri(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not can_do(chat_id, "apri"):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text("Invio comando APRI PORTA (unlatch)...")
    res = await asyncio.to_thread(nuki_lock_action, 3)

    if "error" in res:
        await update.effective_message.reply_text(f"Errore: {res['error']}")
    else:
        await update.effective_message.reply_text(
            format_nuki_action_response(res, op="apri")
        )

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def cmd_lockngo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not can_do(chat_id, "lockngo"):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text("Invio comando LOCK'N'GO...")
    res = await asyncio.to_thread(nuki_lock_action, 4)

    if "error" in res:
        await update.effective_message.reply_text(f"Errore: {res['error']}")
    else:
        await update.effective_message.reply_text(
            format_nuki_action_response(res, op="lockngo")
        )

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def cmd_stato(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not can_do(chat_id, "stato"):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text("Leggo stato serratura...")
    data = await asyncio.to_thread(nuki_lock_state)
    summary = summarize_state(data)
    await update.effective_message.reply_text(summary)

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


# ====== COMANDI ADMIN (solo per uso interno da callback, NON registrati) ======
async def cmd_adduser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    NON più registrato come comando Telegram.
    Lasciato solo se in futuro vuoi riusarlo da qualche callback.
    """
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text(
        "Questo comando non è più usato direttamente. "
        "Usa il pulsante '➕ Add user' dal menu."
    )


async def cmd_setperms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    NON registrato come comando /setperms.
    Rimane disponibile solo se serve da altre parti (al momento no).
    """
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text(
        "La gestione permessi ora avviene solo tramite tastiera inline."
    )


async def cmd_deluser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    NON registrato come comando /deluser.
    """
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text(
        "Per cancellare un utente usa la tastiera inline nella schermata di modifica utente."
    )


async def cmd_listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usato sia come comando (se registrato) sia da callback admin:listusers.
    Attualmente viene chiamato solo dai pulsanti.
    """
    chat_id = update.effective_chat.id
    if not is_admin(chat_id):
        return await handle_unauthorized(update)

    if not get_all_users():
        await update.effective_message.reply_text("Nessun utente configurato.")
        await update.effective_message.reply_text(
            "Menu azioni:", reply_markup=build_main_menu(chat_id)
        )
        return

    await update.effective_message.reply_text("Scegli un utente da modificare:")

    rows: List[List[InlineKeyboardButton]] = []
    for uid, cfg in get_users_sorted():
        label = f"{uid} - {cfg.get('name') or ''}"
        rows.append(
            [InlineKeyboardButton(f"✏️ {label}", callback_data=f"admin:edit:{uid}")]
        )
    rows.append([InlineKeyboardButton("⬅️ Indietro", callback_data="admin:back_main")])

    kb = InlineKeyboardMarkup(rows)
    await update.effective_message.reply_text("Utenti:", reply_markup=kb)


# ====== MENU / TESTO / ERRORI =========
async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_known(chat_id):
        return await handle_unauthorized(update)

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_known(chat_id):
        return await handle_unauthorized(update)

    cmd_text = (update.effective_message.text or "").strip()
    await update.effective_message.reply_text(
        f'"{cmd_text}" non è un comando valido. Usa i pulsanti qui sotto.'
    )
    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_data = context.user_data

    # Utenti non autorizzati → sempre Silence is golden
    if not is_known(chat_id):
        return await handle_unauthorized(update)

    text = (update.effective_message.text or "").strip()

    # ===== Flusso interattivo ADD USER (solo admin) =====
    if is_admin(chat_id) and user_data.get("adduser_waiting"):
        if not text:
            await update.effective_message.reply_text(
                "Formato non valido.\n"
                "Invia: <chat_id> [nome]\n"
                "Esempio: 123456789 Mario Rossi"
            )
            return

        parts = text.split()
        if not parts:
            await update.effective_message.reply_text(
                "Formato non valido.\n"
                "Invia: <chat_id> [nome]\n"
                "Esempio: 123456789 Mario Rossi"
            )
            return

        try:
            new_id = int(parts[0])
        except ValueError:
            await update.effective_message.reply_text(
                "chat_id non valido. Deve essere un numero.\n"
                "Invia: <chat_id> [nome]\n"
                "Esempio: 123456789 Mario Rossi"
            )
            return

        name = " ".join(parts[1:]).strip() if len(parts) > 1 else ""

        # Crea l'utente con nessun permesso iniziale:
        add_or_update_user(new_id, name, [])

        # Chiudiamo lo stato di attesa
        user_data.pop("adduser_waiting", None)

        await update.effective_message.reply_text(
            f"Utente {new_id} creato.\n"
            f"Nome: {name or '(nessuno)'}\n"
            "Ora scegli i permessi:"
        )

        text_view, kb = build_edit_user_view(new_id)
        await update.effective_message.reply_text(text_view, reply_markup=kb)
        return

    # ===== Testo normale per utenti noti =====
    if text:
        await update.effective_message.reply_text(
            f'"{text}" non è un comando. Usa i pulsanti qui sotto.'
        )
    else:
        await update.effective_message.reply_text(
            "Testo non riconosciuto. Usa i pulsanti qui sotto."
        )

    await update.effective_message.reply_text(
        "Menu azioni:", reply_markup=build_main_menu(chat_id)
    )


# ====== CALLBACK BUTTONS =========
async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    chat_id = query.message.chat.id
    user_data = context.user_data  # [TOKEN] user_data per gestire token per-utente

    # 🛑 Qualsiasi bottone diverso da "confirm_apri" annulla la conferma pendente
    if not data.startswith("confirm_apri:"):
        user_data.pop("pending_confirm_apri", None)

    # Conferma latch con token: confirm_apri:<token>:yes/no
    if data.startswith("confirm_apri:"):
        parts = data.split(":", 2)
        if len(parts) != 3:
            # Formato inatteso → consideriamo la richiesta non valida
            try:
                await query.message.edit_reply_markup(reply_markup=None)
            except BadRequest:
                pass
            await query.message.reply_text("Questa richiesta di conferma non è più valida.")
            return

        _, token, choice = parts
        pending_token = user_data.get("pending_confirm_apri")

        # Token mancante o non corrispondente → NON eseguire l'azione
        if not pending_token or token != pending_token:
            try:
                # Disattiva i pulsanti di questa (vecchia) richiesta
                await query.message.edit_reply_markup(reply_markup=None)
            except BadRequest:
                pass
            await query.message.reply_text("Questa richiesta di conferma non è più valida.")
            return

        # Token valido: azzera subito per evitare doppi click
        user_data.pop("pending_confirm_apri", None)

        # Rimuove la tastiera inline dal messaggio di conferma
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except BadRequest:
            # Messaggio già modificato o altro problema non critico
            pass

        if choice == "yes":
            # Ricontrolla permessi prima di eseguire l'azione
            if not can_do(chat_id, "apri"):
                fake_update = Update(update.update_id, message=query.message)
                return await handle_unauthorized(fake_update)

            await query.message.reply_text("Invio comando APRI PORTA (unlatch)...")
            res = await asyncio.to_thread(nuki_lock_action, 3)
            if "error" in res:
                await query.message.reply_text(f"Errore: {res['error']}")
            else:
                await query.message.reply_text(
                    format_nuki_action_response(res, op="apri")
                )
        else:
            # choice == "no" o altro → trattiamo come annullamento
            await query.message.reply_text("Operazione annullata.")

        await query.message.reply_text(
            "Menu azioni:", reply_markup=build_main_menu(chat_id)
        )
        return

    # Pulsanti admin
    if data.startswith("admin:"):
        if not is_admin(chat_id):
            fake_update = Update(update.update_id, message=query.message)
            return await handle_unauthorized(fake_update)

        parts = data.split(":")
        action = parts[1]

        if action == "back_main":
            await query.message.reply_text(
                "Menu azioni:", reply_markup=build_main_menu(chat_id)
            )
            return

        if action == "listusers":
            fake_update = Update(update.update_id, message=query.message)
            return await cmd_listusers(fake_update, context)

        if action == "adduser_help":
            # Attiviamo il flusso interattivo di aggiunta utente
            context.user_data["adduser_waiting"] = True
            await query.message.reply_text(
                "Aggiunta nuovo utente:\n"
                "Invia ora un messaggio con il formato:\n"
                "<chat_id> [nome]\n"
                "Esempio: 123456789 Mario Rossi"
            )
            await query.message.reply_text(
                "Dopo la creazione ti mostrerò la tastiera per assegnare i permessi."
            )
            return

        if action == "edit" and len(parts) >= 3:
            uid = int(parts[2])
            text, kb = build_edit_user_view(uid)
            await query.message.reply_text(text, reply_markup=kb)
            return

        if action == "toggle" and len(parts) >= 4:
            uid = int(parts[2])
            cmd = parts[3]
            toggle_user_command(uid, cmd)
            text, kb = build_edit_user_view(uid)
            try:
                await query.message.edit_text(text, reply_markup=kb)
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    pass
                else:
                    raise
            return

        if action == "setall" and len(parts) >= 3:
            uid = int(parts[2])
            changed = set_all_permissions(uid)

            if not changed:
                # Nessuna modifica effettiva: l'utente aveva già tutti i permessi
                await query.message.reply_text("Questo utente ha già tutti i permessi.")
                return

            text, kb = build_edit_user_view(uid)
            await query.message.edit_text(text, reply_markup=kb)
            return

        if action == "setnone" and len(parts) >= 3:
            uid = int(parts[2])
            changed = clear_permissions(uid)

            if not changed:
                # Nessuna modifica: aveva già zero permessi
                await query.message.reply_text("Questo utente non ha già nessun permesso.")
                return

            text, kb = build_edit_user_view(uid)
            await query.message.edit_text(text, reply_markup=kb)
            return

        if action == "del" and len(parts) >= 3:
            uid = int(parts[2])
            deleted = remove_user(uid)
            if deleted:
                await query.message.edit_text(f"Utente {uid} eliminato.")
            else:
                await query.message.edit_text(f"Utente {uid} non trovato.")
            await query.message.reply_text(
                "Menu azioni:", reply_markup=build_main_menu(chat_id)
            )
            return

        return

    # Pulsanti standard cmd:...
    if not data.startswith("cmd:"):
        return

    cmd = data.split(":", 1)[1]
    fake_update = Update(update.update_id, message=query.message)

    if cmd == "chiudi":
        if not can_do(chat_id, "chiudi"):
            return await handle_unauthorized(fake_update)
        return await cmd_chiudi(fake_update, context)

    if cmd == "sblocca":
        if not can_do(chat_id, "sblocca"):
            return await handle_unauthorized(fake_update)
        return await cmd_sblocca(fake_update, context)

    if cmd == "apri":
        if not can_do(chat_id, "apri"):
            return await handle_unauthorized(fake_update)

        # [TOKEN] Genera un nuovo token di conferma per questo utente
        token = secrets.token_hex(8)
        user_data["pending_confirm_apri"] = token

        warning = (
            "ATTENZIONE: Questo comando aprirà IRREVERSIBILMENTE la porta.\n"
            "Continuare?"
        )
        kb = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Sì, apri", callback_data=f"confirm_apri:{token}:yes"
                    ),
                    InlineKeyboardButton(
                        "❌ No", callback_data=f"confirm_apri:{token}:no"
                    ),
                ]
            ]
        )
        return await query.message.reply_text(warning, reply_markup=kb)

    if cmd == "lockngo":
        if not can_do(chat_id, "lockngo"):
            return await handle_unauthorized(fake_update)
        return await cmd_lockngo(fake_update, context)

    if cmd == "stato":
        if not can_do(chat_id, "stato"):
            return await handle_unauthorized(fake_update)
        return await cmd_stato(fake_update, context)

    if cmd == "id":
        return await cmd_id(fake_update, context)
