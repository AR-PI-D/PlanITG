import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from firestore import db
from handlers import start, handle_button, handle_text_input
from settings.date_handlers import get_date_handlers
from settings.repeat_settings import get_repeat_handlers  # Додати цей імпорт
from settings.teacher_settings import get_teacher_handlers

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Спочатку додаємо обробники для викладачів
    for handler in get_teacher_handlers():
        application.add_handler(handler)

    # Потім обробники для дати та інших налаштувань
    for handler in get_date_handlers():
        application.add_handler(handler)

    for handler in get_repeat_handlers():
        application.add_handler(handler)

    # Інші загальні обробники
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_input))
    application.run_polling()

if __name__ == "__main__":
    main()