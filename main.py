import logging

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from config import load_config, get_config
from users import load_users
from bot_handlers import (
    cmd_cancel,
    cmd_start,
    cmd_menu, 
    cmd_id,
    on_button,
    unknown_command,
    handle_text,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main() -> None:
    # Load configuration and users
    load_config()
    cfg = get_config()
    load_users()

    app = ApplicationBuilder().token(cfg.telegram_bot_token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("id", cmd_id))
    app.add_handler(CommandHandler("menu", cmd_menu))
    app.add_handler(CommandHandler("cancel", cmd_cancel))  
    
    
    # Inline buttons
    app.add_handler(CallbackQueryHandler(on_button))

    # Unknown commands
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    # Any text → custom handling (including admin add-user flow)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot started, waiting for updates...")
    app.run_polling()


if __name__ == "__main__":
    main()
