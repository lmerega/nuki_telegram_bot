import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import load_config
from users import load_users
from bot_handlers import (
    cmd_start,
    cmd_id,
    on_button,
    unknown_command,
    handle_text,
)


def main():
    # Configurazione logging
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logger = logging.getLogger(__name__)

    # Carica config e utenti
    cfg = load_config()
    load_users()

    # Crea applicazione Telegram
    app = ApplicationBuilder().token(cfg.telegram_bot_token).build()

    # Comandi principali
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))

    # Nessun comando admin, nessun /menu:
    # tutto è via tastiera inline

    # Callback tastiera
    app.add_handler(CallbackQueryHandler(on_button))

    # Comandi sconosciuti
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Qualunque testo → gestione custom (incluso flusso adduser per admin)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot avviato, in attesa di comandi...")
    app.run_polling()


if __name__ == "__main__":
    main()
