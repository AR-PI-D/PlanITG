from telegram import Update, CallbackQuery  # Додаємо CallbackQuery
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters
from firestore import db
from keyboards import teacher_edit_keyboard, teachers_keyboard
from firebase_admin import firestore
import logging
from id_generator import generate_unique_id

# Додайте цей імпорт у верхній частині teacher_settings.py
from typing import Union

logger = logging.getLogger(__name__)

async def handle_manage_teachers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    teachers = user_data.get("schedule", {}).get("teachers", [])
    await query.edit_message_text(
        "👨🏫 Список викладачів:",
        reply_markup=teachers_keyboard(teachers)
    )

async def handle_add_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    new_teacher = {
        'id': generate_unique_id(),
        'name': '',
        'contact': ''
    }
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_ref.update({"schedule.teachers": firestore.ArrayUnion([new_teacher])})
    await show_teachers_list(query, context, user_id)

async def show_teachers_list(
    update_obj: Union[Update, CallbackQuery], 
    context: ContextTypes.DEFAULT_TYPE, 
    user_id: int
):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    teachers = user_ref.get().to_dict().get("schedule", {}).get("teachers", [])
    
    if isinstance(update_obj, CallbackQuery):
        await update_obj.edit_message_text(
            "👨🏫 Список викладачів:",
            reply_markup=teachers_keyboard(teachers)
        )
    else:
        await context.bot.send_message(
            chat_id=update_obj.chat_id,
            text="👨🏫 Список викладачів:",
            reply_markup=teachers_keyboard(teachers)
        )
    if 'editing_teacher' in context.user_data:
        del context.user_data['editing_teacher']

async def handle_edit_teacher_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['editing_field'] = 'name'
    await query.edit_message_text("✏️ Введіть нове ім'я викладача:")

async def handle_edit_teacher_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data['editing_field'] = 'contact'
    await query.edit_message_text("📞 Введіть новий контакт (тег або номер):")

async def handle_delete_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Виправляємо отримання ID викладача
    teacher_id = int(query.data.split('_')[2])  # delete_teacher_123
    
    user_id = query.from_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    
    # Оновлюємо список викладачів
    user_data = user_ref.get().to_dict()
    teachers = user_data.get("schedule", {}).get("teachers", [])
    updated_teachers = [t for t in teachers if t['id'] != teacher_id]
    
    # Зберігаємо зміни
    user_ref.update({"schedule.teachers": updated_teachers})
    
    # Повертаємось до списку викладачів
    await show_teachers_list(query, context, user_id)



# teacher_settings.py

async def show_teacher_edit_menu(update_or_query, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    try:
        # Перевірка наявності editing_teacher у контексті
        if 'editing_teacher' not in context.user_data:
            raise ValueError("Не обрано викладача для редагування.")
        
        teacher_id = context.user_data['editing_teacher']['id']
        
        # Отримання актуальних даних з бази
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        teachers = user_data.get("schedule", {}).get("teachers", [])
        
        # Пошук викладача
        teacher = next((t for t in teachers if t['id'] == teacher_id), None)
        if not teacher:
            raise ValueError("Викладача не знайдено.")
        
        # Формування тексту
        text = (
            f"👨🏫 Редагування викладача:\n"
            f"▪️ Ім'я: {teacher.get('name', 'Не вказано')}\n"
            f"▪️ Контакт: {teacher.get('contact', 'Не вказано')}"
        )

        # Відправка повідомлення або редагування існуючого
        if isinstance(update_or_query, CallbackQuery):
            # Якщо це CallbackQuery (інлайн-кнопка), редагуємо повідомлення
            await update_or_query.edit_message_text(
                text=text,
                reply_markup=teacher_edit_keyboard(teacher_id)
            )
        else:
            # Якщо це Message (звичайне повідомлення), відправляємо нове
            await context.bot.send_message(
                chat_id=update_or_query.chat_id,
                text=text,
                reply_markup=teacher_edit_keyboard(teacher_id)
            )

    except Exception as e:
        logger.error(f"Помилка: {str(e)}")
        # Обробка помилок з урахуванням типу об'єкта
        error_text = f"❌ Помилка: {str(e)}"
        if isinstance(update_or_query, CallbackQuery):
            await update_or_query.edit_message_text(error_text)
        else:
            await update_or_query.reply_text(error_text)

async def handle_teacher_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    # Отримуємо ID викладача з callback_data (формат: teacher_123)
    teacher_id = int(query.data.split('_')[1])  
    
    # Зберігаємо ID у контексті
    context.user_data['editing_teacher'] = {'id': teacher_id}
    
    # Показуємо меню редагування
    await show_teacher_edit_menu(query, context, query.from_user.id)

async def handle_teacher_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Перевірка стану редагування
    if 'editing_teacher' not in context.user_data or 'editing_field' not in context.user_data:
        await update.message.reply_text("❌ Помилка: не обрано поле або викладача!")
        return
    
    teacher_id = context.user_data['editing_teacher']['id']
    field = context.user_data['editing_field']
    
    try:
        user_ref = db.collection("TG_USERS").document(str(user_id))
        teachers = user_ref.get().to_dict().get("schedule", {}).get("teachers", [])
        
        # Оновлення даних
        updated_teachers = []
        for t in teachers:
            if t['id'] == teacher_id:
                t[field] = text
            updated_teachers.append(t)
        
        user_ref.update({"schedule.teachers": updated_teachers})
        
        # Повернення до меню викладача з оновленими даними
        await show_teacher_edit_menu(update.message, context, user_id)
        
    except Exception as e:
        logger.error(f"Помилка: {str(e)}")
        await update.message.reply_text("❌ Помилка при збереженні!")

async def handle_back_to_teacher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_teacher_edit_menu(query, context, query.from_user.id)

# Додайте до get_teacher_handlers:
CallbackQueryHandler(handle_back_to_teacher, pattern='^back_to_teacher$')

def get_teacher_handlers():
    return [
        CallbackQueryHandler(handle_manage_teachers, pattern='^manage_teachers$'),
        CallbackQueryHandler(handle_add_teacher, pattern='^add_teacher$'),
        CallbackQueryHandler(handle_edit_teacher_name, pattern='^edit_teacher_name$'),
        CallbackQueryHandler(handle_edit_teacher_contact, pattern='^edit_teacher_contact$'),
        CallbackQueryHandler(handle_delete_teacher, pattern='^delete_teacher_'),
        CallbackQueryHandler(handle_teacher_selection, pattern='^teacher_'),
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_teacher_text_input), # Додано
        CallbackQueryHandler(handle_back_to_teacher, pattern='^back_to_teacher$'),
    ]