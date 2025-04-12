from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup  # Додано імпорт
from telegram.ext import ContextTypes, CallbackQueryHandler
from firestore import db
from keyboards import settings_keyboard

def repeat_keyboard(current_repeat: int):
    buttons = [
        [InlineKeyboardButton(
            f"{i} {'✅' if i == current_repeat else ''}", 
            callback_data=f'set_repeat_{i}'
        )] for i in range(1, 5)
    ]
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data='settings')])
    return InlineKeyboardMarkup(buttons)

# Решта коду залишається без змін...

async def handle_set_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    
    current_repeat = user_data.get("schedule", {}).get("repeat", 1)
    await query.edit_message_text(
        "🔢 Оберіть кількість тижнів у циклі:",
        reply_markup=repeat_keyboard(current_repeat)
    )

async def handle_update_repeat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    new_repeat = int(query.data.split('_')[-1])
    
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_ref.update({"schedule.repeat": new_repeat})
    
    await query.edit_message_text(
        f"Налаштування ⚙️\n✅ Встановлено {new_repeat} тижнів!",
        reply_markup=settings_keyboard(new_repeat)
    )

def get_repeat_handlers():
    return [
        CallbackQueryHandler(handle_set_repeat, pattern='^set_repeat$'),
        CallbackQueryHandler(handle_update_repeat, pattern='^set_repeat_')
    ]