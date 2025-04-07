import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from firestore import db
import handlers

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

def main():
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Реєстрація обробників
    application.add_handler(CommandHandler("start", handlers.start))
    application.add_handler(CallbackQueryHandler(handlers.handle_button))
    
    application.run_polling()

if __name__ == "__main__":
    main()