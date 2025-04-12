from datetime import datetime
from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackQueryHandler
from firestore import db
from keyboards import starting_week_keyboard, settings_keyboard  # Імпорт клавіатур

# Сервісні функції
def _update_starting_date(user_id: int, new_date: str):
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_ref.update({'starting_week': new_date})  # Синхронний запит
        return True, None
    except ValueError as e:
        return False, f"Невірний формат дати: {e}"
    except Exception as e:
        return False, f"Помилка бази даних: {str(e)}"

# Обробники подій
async def handle_starting_week_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_doc = user_ref.get()  # Синхронний запит
    
    current_date = user_doc.get("starting_week") if user_doc.exists else "не встановлено"
    
    await query.edit_message_text(
        f"📅 **Поточна дата:** {current_date}\nОберіть спосіб оновлення:",
        reply_markup=starting_week_keyboard(),
        parse_mode="Markdown"
    )

async def handle_date_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    success, error = _update_starting_date(user_id, text)  # Синхронний виклик
    
    if success:
        # Повернення до меню налаштувань
        await update.message.reply_text(
            f"Налаштування ⚙️\n✅ Дата оновлена: `{text}`",
            reply_markup=settings_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(f"❌ {error}")

async def handle_set_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    today = datetime.now().strftime("%Y-%m-%d")
    success, error = _update_starting_date(user_id, today)  # Синхронний виклик
    
    query = update.callback_query
    await query.answer()
    
    if success:
        # Повернення до меню налаштувань
        await query.edit_message_text(
            f"Налаштування ⚙️\n✅ Встановлено сьогоднішню дату: `{today}`",
            reply_markup=settings_keyboard(),
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(f"❌ {error}")

# Реєстрація обробників
def get_date_handlers():
    return [
        CallbackQueryHandler(handle_starting_week_menu, pattern='^set_starting_week$'),
        CallbackQueryHandler(handle_set_today, pattern='^set_today$'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_date_input)
    ]