import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from firestore import db
from handlers import start, handle_button  # Змінено імпорт

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))  # Без handlers.
    application.add_handler(CallbackQueryHandler(handle_button))  # Без handlers.
    
    application.run_polling()

if __name__ == "__main__":
    main()