import asyncio
import logging
import secrets
from config import get_config
from typing import List, Tuple, Optional, Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from users import (
    is_admin,
    is_known,
    can_do,
    get_user_cfg,
    get_users_sorted,
    add_or_update_user,
    delete_user,
    grant_all_permissions,
    revoke_all_permissions,
    toggle_permission,
    ALL_PERMISSIONS,
    get_user_lang,
    set_user_lang
)

from nuki import nuki_lock_action, nuki_lock_state, summarize_state
from i18n import t, bt, DEFAULT_LANG

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers: menus and common responses
# ---------------------------------------------------------------------------

def _is_stranger(chat_id: int) -> bool:
    """True if user is NOT admin and NOT present in users.json."""
    return not is_admin(chat_id) and not is_known(chat_id)


def build_main_menu(chat_id: int) -> InlineKeyboardMarkup:
    """Build the main inline keyboard for a given user."""
    lang = get_user_lang(chat_id)
    buttons: List[List[InlineKeyboardButton]] = []

    # First row: lock / unlock
    row1: List[InlineKeyboardButton] = []
    if can_do(chat_id, "lock"):
        row1.append(
            InlineKeyboardButton(
                bt("close", lang), callback_data="cmd:lock"
            )
        )
    if can_do(chat_id, "unlock"):
        row1.append(
            InlineKeyboardButton(
                bt("unlock", lang), callback_data="cmd:unlock"
            )
        )
    if row1:
        buttons.append(row1)

    # Second row: open / lock'n'go
    row2: List[InlineKeyboardButton] = []
    if can_do(chat_id, "open"):
        row2.append(
            InlineKeyboardButton(
                bt("open_door", lang), callback_data="cmd:open"
            )
        )
    if can_do(chat_id, "lockngo"):
        row2.append(
            InlineKeyboardButton(
                bt("lockngo", lang), callback_data="cmd:lockngo"
            )
        )
    if row2:
        buttons.append(row2)

    # Third row: status / id
    row3: List[InlineKeyboardButton] = []
    if can_do(chat_id, "status"):
        row3.append(
            InlineKeyboardButton(
                bt("status", lang), callback_data="cmd:status"
            )
        )
    row3.append(
        InlineKeyboardButton(
            bt("id", lang), callback_data="cmd:id"
        )
    )
    buttons.append(row3)

    # Language selector
    buttons.append(
        [
            InlineKeyboardButton(
                bt("lang", lang),
                callback_data="lang:menu",
            )
        ]
    )

    # Admin menu
    if is_admin(chat_id):
        admin_row: List[InlineKeyboardButton] = [
            InlineKeyboardButton(
                bt("add_user", lang), callback_data="admin:adduser_help"
            ),
            InlineKeyboardButton(
                bt("list_users", lang), callback_data="admin:listusers"
            ),
        ]
        buttons.append(admin_row)

    return InlineKeyboardMarkup(buttons)


async def handle_unauthorized(update: Update) -> None:
    """Reply with an innocuous message to unauthorized users."""
    chat = update.effective_chat
    lang = get_user_lang(chat.id) if chat else DEFAULT_LANG
    if update.effective_message:
        await update.effective_message.reply_text(t("unauthorized", lang))


def _format_nuki_action_response(res: dict, op: Optional[str], lang: str) -> str:
    """Render a Nuki bridge response in a human-friendly way.

    op can be: "lock", "unlock", "open", "lockngo" or None for generic.
    """
    parts: List[str] = []

    # Header based on operation
    if op == "lock":
        parts.append(t("lock_ok", lang))
    elif op == "unlock":
        parts.append(t("unlock_ok", lang))
    elif op == "open":
        parts.append(t("open_ok", lang))
    elif op == "lockngo":
        parts.append(t("lockngo_ok", lang))

    if "error" in res:
        parts.append(f"❌ {res['error']}")
        return "\n".join(parts)

    success = res.get("success")
    parts.append(t("bridge_response_header", lang))
    if success is True:
        parts.append(t("bridge_success", lang))
    elif success is False:
        parts.append(t("bridge_failure", lang))
    else:
        parts.append(t("bridge_unknown", lang))

    battery_critical = res.get("batteryCritical")
    if battery_critical:
        parts.append(t("battery_critical", lang))
    elif battery_critical is not None:
        parts.append(t("battery_ok", lang))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel current admin operation (like add_user wizard)."""
    chat = update.effective_chat
    chat_id = chat.id

    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    lang = get_user_lang(chat.id)

    if is_admin(chat.id) and context.user_data.get("mode"):
        context.user_data["mode"] = None
        text = t("operation_cancelled", lang)
    else:
        text = t("nothing_to_cancel", lang)

    await update.effective_message.reply_text(
        text,
        reply_markup=build_main_menu(chat.id),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    # Unknown users → fixed message, no menu
    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    lang = get_user_lang(chat_id)

    if is_admin(chat_id):
        text = t("start_admin", lang)
    else:
        cfg = get_user_cfg(chat_id)
        allowed = cfg.get("allowed") if cfg else []
        perms = ", ".join(sorted(allowed)) if allowed else "(nessuno)" if lang == "it" else "(none)"
        text = t("start_user", lang, perms=perms)

    await update.effective_message.reply_text(
        text, reply_markup=build_main_menu(chat_id)
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Alias of /start
    return await cmd_start(update, context)


async def cmd_id(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = update.effective_chat
    user = update.effective_user

    # Language for bot responses to this user
    lang = get_user_lang(chat.id)

    cfg = get_user_cfg(chat.id)
    known = cfg is not None
    admin_flag = is_admin(chat.id)

    lines = []

    # --- Telegram info ---
    lines.append("Telegram:")
    lines.append(f"- chat_id: {chat.id}")
    lines.append(f"- user_id: {user.id}")

    if user.username:
        lines.append(f"- username: @{user.username}")
    else:
        lines.append(f"- username: (none)")

    lines.append(f"- first_name: {user.first_name or '(none)'}")
    lines.append(f"- last_name: {user.last_name or '(none)'}")

    # Telegram language_code (not bot language)
    if getattr(user, "language_code", None):
        lines.append(f"- telegram_lang: {user.language_code}")

    lines.append("")  # empty line

    # --- Bot-side info ---
    lines.append("Bot:")
    lines.append(f"- known_user: {'yes' if known else 'no'}")
    lines.append(f"- admin: {'yes' if admin_flag else 'no'}")

    if known:
        name = cfg.get("name") or "(no name)"
        user_lang = cfg.get("lang") or lang
        allowed = cfg.get("allowed") or []

        lines.append(f"- name: {name}")
        lines.append(f"- lang: {user_lang}")

        if allowed:
            perms_str = ", ".join(sorted(allowed))
        else:
            perms_str = "(none)"
        lines.append(f"- permissions: {perms_str}")

    text = "\n".join(lines)

    # For unknown non-admin users we do NOT show the menu
    reply_markup = build_main_menu(chat.id) if (known or admin_flag) else None

    await update.effective_message.reply_text(
        text,
        reply_markup=reply_markup,
    )


async def _exec_nuki_action(
    chat_id: int,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    action: int,
    op: str,
) -> None:
    """Internal helper to send a Nuki action and report back."""
    lang = get_user_lang(chat_id)
    if op == "lock":
        sending_key = "sending_lock"
    elif op == "unlock":
        sending_key = "sending_unlock"
    elif op == "open":
        sending_key = "sending_open"
    elif op == "lockngo":
        sending_key = "sending_lockngo"
    else:
        sending_key = "sending_lock"

    await update.effective_message.reply_text(t(sending_key, lang))
    res = await asyncio.to_thread(nuki_lock_action, action)
    msg = _format_nuki_action_response(res, op=op, lang=lang)
    await update.effective_message.reply_text(msg, reply_markup=build_main_menu(chat_id))


async def cmd_lock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    if not can_do(chat_id, "lock"):
        return await handle_unauthorized(update)
    # Nuki lock action is 2
    await _exec_nuki_action(chat_id, update, context, action=2, op="lock")


async def cmd_unlock(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    if not can_do(chat_id, "unlock"):
        return await handle_unauthorized(update)
    # Nuki unlock action is 1
    await _exec_nuki_action(chat_id, update, context, action=1, op="unlock")


async def _cmd_open_internal(
    chat_id: int, update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Internal helper for the 'open door' (unlatch) operation."""
    # Nuki "unlatch" action is usually 3
    await _exec_nuki_action(chat_id, update, context, action=3, op="open")


async def cmd_lockngo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    if not can_do(chat_id, "lockngo"):
        return await handle_unauthorized(update)
    # Nuki lock'n'go action is usually 4
    await _exec_nuki_action(chat_id, update, context, action=4, op="lockngo")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id

    if _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    if not can_do(chat_id, "status"):
        return await handle_unauthorized(update)

    lang = get_user_lang(chat_id)
    await update.effective_message.reply_text(t("reading_state", lang))
    res = await asyncio.to_thread(nuki_lock_state)
    if "error" in res:
        await update.effective_message.reply_text(
            f"❌ {res['error']}", reply_markup=build_main_menu(chat_id)
        )
        return

    summary = summarize_state(res, lang=lang)
    await update.effective_message.reply_text(
        summary, reply_markup=build_main_menu(chat_id)
    )


# ---------------------------------------------------------------------------
# Admin helpers
# ---------------------------------------------------------------------------


def _build_user_edit_keyboard(chat_id: int, target_id: int) -> InlineKeyboardMarkup:
    """Build the inline keyboard for editing a user's permissions."""
    lang = get_user_lang(chat_id)
    target_cfg = get_user_cfg(target_id) or {}
    allowed = set(target_cfg.get("allowed") or [])

    rows: List[List[InlineKeyboardButton]] = []

    def perm_button(perm: str, key: str) -> InlineKeyboardButton:
        enabled = perm in allowed
        label = bt(key, lang)
        prefix = "✅ " if enabled else "❌ "
        return InlineKeyboardButton(
            prefix + label,
            callback_data=f"admin:toggle:{target_id}:{perm}",
        )

    # First row: lock / unlock
    rows.append(
        [
            perm_button("lock", "close"),
            perm_button("unlock", "unlock"),
        ]
    )
    # Second row: open / lockngo
    rows.append(
        [
            perm_button("open", "open_door"),
            perm_button("lockngo", "lockngo"),
        ]
    )
    # Third row: status
    rows.append(
        [
            perm_button("status", "status"),
        ]
    )

    # Fourth row: all / none
    rows.append(
        [
            InlineKeyboardButton(
                bt("perm_all", lang),
                callback_data=f"admin:all:{target_id}",
            ),
            InlineKeyboardButton(
                bt("perm_none", lang),
                callback_data=f"admin:none:{target_id}",
            ),
        ]
    )

    # Fifth row: delete / back
    rows.append(
        [
            InlineKeyboardButton(
                bt("perm_delete", lang),
                callback_data=f"admin:delete:{target_id}",
            ),
            InlineKeyboardButton(
                bt("perm_back", lang),
                callback_data="admin:back",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


async def _show_user_list(update: Update, chat_id: int) -> None:
    """Show a list of users and a keyboard to select one to edit.

    Owners (admin) defined in OWNERS are not shown in the list.
    """
    lang = get_user_lang(chat_id)
    users_list = get_users_sorted()

    # Owners from config
    cfg = get_config()
    owners = set(cfg.owners)

    # Filter out owners from user list
    visible_users = [(uid, ucfg) for uid, ucfg in users_list if uid not in owners]

    if not visible_users:
        await update.effective_message.reply_text(t("no_users", lang))
        return

    lines = [t("users_title", lang)]
    kb_rows: List[List[InlineKeyboardButton]] = []

    for uid, ucfg in visible_users:
        name = ucfg.get("name") or "(no name)"
        lines.append(f"- {name} [{uid}]")
        kb_rows.append(
            [
                InlineKeyboardButton(
                    f"{name} ({uid})", callback_data=f"admin:edit:{uid}"
                )
            ]
        )

    # Final row: Back button to admin menu
    kb_rows.append(
        [
            InlineKeyboardButton(
                bt("perm_back", lang),
                callback_data="admin:back",
            )
        ]
    )

    kb = InlineKeyboardMarkup(kb_rows)
    await update.effective_message.reply_text(
        "\n".join(lines), reply_markup=kb
    )


# ---------------------------------------------------------------------------
# Callback query handler
# ---------------------------------------------------------------------------


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle all callback query interactions from inline keyboards."""
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    chat_id = query.message.chat.id
    lang = get_user_lang(chat_id)
    user_data: Dict = context.user_data

    # Unknown users: no actions on buttons
    if _is_stranger(chat_id):
        await query.message.reply_text("Silence is golden")
        return

    # OPEN DOOR confirmation tokens are stored per-user
    open_tokens: Dict[str, bool] = user_data.setdefault("open_tokens", {})

    # Language menu
    if data.startswith("lang:"):
        _, action, *rest = data.split(":", 2)
        if action == "menu":
            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🇮🇹 Italiano", callback_data="lang:set:it"),
                        InlineKeyboardButton("🇬🇧 English", callback_data="lang:set:en"),
                    ]
                ]
            )
            await query.message.reply_text(t("lang_choose", lang), reply_markup=kb)
            return

        if action == "set" and rest:
            new_lang = rest[0]
            set_user_lang(chat_id, new_lang)
            lang = new_lang
            await query.message.reply_text(t("lang_updated", lang))
            await query.message.reply_text(
                t("menu_actions", lang), reply_markup=build_main_menu(chat_id)
            )
            return

    # Admin actions
    if data.startswith("admin:"):
        _, cmd, *rest = data.split(":", 2)
        if not is_admin(chat_id):
            return await handle_unauthorized(update)

        if cmd == "adduser_help":
            # Enter "add user" mode: next text message will be parsed
            context.user_data["mode"] = "add_user"
            await query.message.reply_text(t("add_user_intro", lang))
            return

        if cmd == "listusers":
            await _show_user_list(update, chat_id)
            return

        if cmd == "edit" and rest:
            target_raw = rest[0]
            try:
                target_id = int(target_raw)
            except ValueError:
                await query.message.reply_text(t("user_not_found", lang, uid=target_raw))
                return
            target_cfg = get_user_cfg(target_id)
            if not target_cfg:
                await query.message.reply_text(
                    t("user_not_found", lang, uid=target_id)
                )
                return
            header = t("edit_user_header", lang) + f"{target_cfg.get('name')} [{target_id}]"
            kb = _build_user_edit_keyboard(chat_id, target_id)
            await query.message.reply_text(header, reply_markup=kb)
            return

        if cmd in {"all", "none", "delete"} and rest:
            target_raw = rest[0]
            try:
                target_id = int(target_raw)
            except ValueError:
                await query.message.reply_text(t("user_not_found", lang, uid=target_raw))
                return

            if cmd == "all":
                grant_all_permissions(target_id)
            elif cmd == "none":
                revoke_all_permissions(target_id)
            elif cmd == "delete":
                delete_user(target_id)
                # Show confirmation + Back button
                kb = InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                bt("perm_back", lang),
                                callback_data="admin:back",
                            )
                        ]
                    ]
                )
                await query.message.reply_text(
                    t("user_deleted", lang, uid=target_id),
                    reply_markup=kb,
                )
                return

            target_cfg = get_user_cfg(target_id) or {}
            header = t("edit_user_header", lang) + f"{target_cfg.get('name')} [{target_id}]"
            kb = _build_user_edit_keyboard(chat_id, target_id)
            try:
                await query.message.edit_text(header, reply_markup=kb)
            except BadRequest:
                await query.message.reply_text(header, reply_markup=kb)
            return

        if cmd == "back":
            # Exit from any admin mode (e.g. add_user)
            context.user_data.pop("mode", None)
            await query.message.reply_text(
                t("menu_actions", lang), reply_markup=build_main_menu(chat_id)
            )
            return

    # Confirmation for opening the door
    if data.startswith("confirm_open:"):
        token = data.split(":", 1)[1]
        if token not in open_tokens:
            await query.message.reply_text(t("confirm_open_expired", lang))
            return

        # Token is single-use
        open_tokens.pop(token, None)

        fake_update = Update(
            update.update_id,
            message=query.message,
        )
        await _cmd_open_internal(chat_id, fake_update, context)
        return

    if data.startswith("cancel_open:"):
        token = data.split(":", 1)[1]
        open_tokens.pop(token, None)
        await query.message.reply_text(
            t("confirm_open_cancelled", lang),
            reply_markup=build_main_menu(chat_id),
        )
        return

    # Command buttons
    if data.startswith("cmd:"):
        _, cmd = data.split(":", 1)

        # Reuse the same functions used for /commands
        fake_update = Update(
            update.update_id,
            message=query.message,
        )

        if cmd == "lock":
            if not can_do(chat_id, "lock"):
                return await handle_unauthorized(fake_update)
            return await cmd_lock(fake_update, context)

        if cmd == "unlock":
            if not can_do(chat_id, "unlock"):
                return await handle_unauthorized(fake_update)
            return await cmd_unlock(fake_update, context)

        if cmd == "open":
            if not can_do(chat_id, "open"):
                return await handle_unauthorized(fake_update)
            # Ask for confirmation with a one-time token
            token = secrets.token_urlsafe(16)
            open_tokens[token] = True
            kb = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            bt("yes_open", lang),
                            callback_data=f"confirm_open:{token}",
                        ),
                        InlineKeyboardButton(
                            bt("no_cancel", lang),
                            callback_data=f"cancel_open:{token}",
                        ),
                    ]
                ]
            )
            await query.message.reply_text(
                t("confirm_open_question", lang),
                reply_markup=kb,
            )
            return

        if cmd == "lockngo":
            if not can_do(chat_id, "lockngo"):
                return await handle_unauthorized(fake_update)
            return await cmd_lockngo(fake_update, context)

        if cmd == "status":
            if not can_do(chat_id, "status"):
                return await handle_unauthorized(fake_update)
            return await cmd_status(fake_update, context)

        if cmd == "id":
            return await cmd_id(fake_update, context)


# ---------------------------------------------------------------------------
# Generic text / unknown command handlers
# ---------------------------------------------------------------------------


async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle unknown /commands."""
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    # Unknown users → fixed response
    if chat_id is not None and _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    lang = get_user_lang(chat.id) if chat else DEFAULT_LANG
    await update.effective_message.reply_text(
        t("unknown_command", lang), reply_markup=build_main_menu(chat.id)
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle plain text messages (non-commands)."""
    chat = update.effective_chat
    chat_id = chat.id if chat else None

    if chat_id is not None and _is_stranger(chat_id):
        await update.effective_message.reply_text("Silence is golden")
        return

    lang = get_user_lang(chat.id) if chat else DEFAULT_LANG
    text = (update.effective_message.text or "").strip()

    # Admin "add user" wizard
    if is_admin(chat.id) and context.user_data.get("mode") == "add_user":
        parts = text.split()
        if not parts:
            await update.effective_message.reply_text(
                t("add_user_invalid_format", lang)
            )
            return

        chat_id_str, *name_parts = parts
        try:
            new_chat_id = int(chat_id_str)
        except ValueError:
            await update.effective_message.reply_text(
                t("add_user_invalid_format", lang)
            )
            return

        name = " ".join(name_parts).strip() or f"user_{new_chat_id}"
        add_or_update_user(new_chat_id, name, allowed=[])
        context.user_data["mode"] = None
        await update.effective_message.reply_text(
            t("add_user_ok", lang, uid=new_chat_id, name=name),
            reply_markup=build_main_menu(chat.id),
        )
        return

    # Non-command text → gentle hint to use buttons
    if text.startswith("/"):
        msg = t("not_a_command", lang, text=text)
    else:
        msg = t("unknown_text", lang)

    await update.effective_message.reply_text(
        msg,
        reply_markup=build_main_menu(chat.id),
    )
