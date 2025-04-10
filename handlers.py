from telegram import Update, CallbackQuery, Message  # Додаємо імпорти
from typing import Union  # Для аннотації типів
from telegram.ext import ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
from firestore import db
from keyboards import (
    main_menu, 
    days_keyboard, 
    edit_day_keyboard,
    all_subjects_keyboard,
    day_menu_keyboard,
    settings_keyboard,
    starting_week_keyboard,
    repeat_keyboard
)
from default_schedule import default_schedule
from firebase_admin import firestore

DAYS_ORDER = ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"]

def get_current_week(start_date: str, repeat: int) -> int:
    """Розраховує поточний тиждень з урахуванням циклічності"""
    today = datetime.now().date()
    start = datetime.strptime(start_date, "%Y-%m-%d").date()
    delta = (today - start).days
    
    if delta < 0:
        return 1
    
    total_weeks = (delta // 7) + 1
    return ((total_weeks - 1) % repeat) + 1

async def format_schedule_text(user_data: dict, day: str, selected_week: str) -> str:
    """Форматуємо текст розкладу з HTML розміткою"""
    day_index = DAYS_ORDER.index(day)
    schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
    
    if not schedule_ids:
        return f"Тиждень {selected_week[-1]}\n" + "🎉 Вихідний день!"
    
    subjects = user_data["schedule"]["subjects"]
    teachers = user_data["schedule"]["teachers"]
    schedule_entries = []
    
    for idx, subject_id in enumerate(schedule_ids, start=1):
        subject = next((s for s in subjects if s["id"] == subject_id), None)
        teacher = next((t for t in teachers if t["id"] == (subject["teacher"] if subject else None)), None)
        
        if not subject or not teacher:
            schedule_entries.append(f"{idx}. Помилка даних")
            continue
            
        teacher_name = teacher["name"]
        contact = teacher.get("phone", "").strip()
        
        if contact.startswith("@"):
            teacher_name = f'<a href="https://t.me/{contact[1:]}">{teacher_name}</a>'
        elif contact:
            teacher_name = f'{teacher_name} (<code>{contact}</code>)'
                
        entry = f'{idx}. <a href="{subject["zoom_link"]}">{subject["name"]}</a> - {teacher_name}'
        schedule_entries.append(entry)
        
    return f"Тиждень {selected_week[-1]}\n" + "\n".join(schedule_entries)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник команди /start з автоматичним виводом сьогоднішнього розкладу"""
    user_id = update.effective_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_doc = user_ref.get()
    
    # Обробка нового користувача
    if not user_doc.exists:
        user_ref.set({
            "schedule": default_schedule,
            "telegram_id": user_id,
            "created_at": firestore.SERVER_TIMESTAMP,
            "starting_week": None
        })
        await update.message.reply_text(
            "🔄 Будь ласка, встановіть дату початку семестру!",
            reply_markup=settings_keyboard()
        )
        return
    
    user_data = user_doc.to_dict()
    
    # Перевірка наявності starting_week
    if not user_data.get("starting_week"):
        await update.message.reply_text(
            "⚠️ Спочатку встановіть дату початку семестру!",
            reply_markup=settings_keyboard()
        )
        return
    
    # Відправка розкладу з навігацією
    await show_day_schedule(
        user_id=user_id,
        day=DAYS_ORDER[datetime.now().weekday()],
        update_obj=update.message,
        context=context
    )


async def show_day_schedule(user_id: int, day: str, update_obj, context: ContextTypes.DEFAULT_TYPE):
    """Уніфікована функція для показу розкладу дня"""
    try:
        user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
        
        if not user_data.get("starting_week"):
            await update_obj.reply_text("⚠️ Спочатку встановіть дату семестру!", reply_markup=settings_keyboard())
            return

        repeat = user_data.get("schedule", {}).get("repeat", 1)
        current_week = get_current_week(user_data["starting_week"], repeat)
        schedule_text = await format_schedule_text(user_data, day, f"week{current_week}")
        
        # Розрахунок дати
        today = datetime.now()
        day_index = DAYS_ORDER.index(day)
        target_date = today + timedelta(days=(day_index - today.weekday()))
        date_str = target_date.strftime("%d.%m.%Y")

        response = f"📅 <b>{day.capitalize()} ({date_str})</b>\n{schedule_text}"

        # Відправка повідомлення
        if isinstance(update_obj, CallbackQuery):
            await update_obj.edit_message_text(response, parse_mode="HTML", reply_markup=main_menu())
        else:
            await update_obj.reply_text(response, parse_mode="HTML", reply_markup=main_menu())
            
    except Exception as e:
        error_msg = f"❌ Помилка: {str(e)}"
        await update_obj.reply_text(error_msg)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробник всіх інлайн кнопок"""
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    # Додаємо обробники нових кнопок
    if data in ['prev_day', 'next_day', 'today']:
        current_day = context.user_data.get("current_day", DAYS_ORDER[datetime.now().weekday()])
        current_index = DAYS_ORDER.index(current_day)
        
        if data == 'prev_day':
            new_index = (current_index - 1) % 7
        elif data == 'next_day':
            new_index = (current_index + 1) % 7
        else:  # today
            new_index = datetime.now().weekday()
        
        new_day = DAYS_ORDER[new_index]
        context.user_data["current_day"] = new_day
        await show_day_schedule(user_id, new_day, query, context)
        return

    if data == "schedule":
        await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())
    elif data in DAYS_ORDER:
        await handle_day_selection(query, context, data, user_id)
    elif data == "edit_schedule":
        await show_edit_menu(query, context, user_id)
    elif data.startswith("select_week_"):
        context.user_data["selected_week"] = f"week{data.split('_')[-1]}"
        await show_edit_menu(query, context, user_id)
    elif data.startswith("edit_lesson_"):
        context.user_data["selected_lesson_position"] = int(data.split("_")[-1])
        user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
        await query.edit_message_text("🔁 Оберіть новий предмет:", reply_markup=all_subjects_keyboard(user_data["schedule"]["subjects"]))
    elif data == "add_lesson":
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(current_day)
        full_schedule = [day.copy() for day in user_data["schedule"]["schedule"]]
        if selected_week not in full_schedule[day_index]:
            full_schedule[day_index][selected_week] = []
        full_schedule[day_index][selected_week].append(0)
        user_ref.update({"schedule.schedule": full_schedule})
        user_data["schedule"]["schedule"] = full_schedule
        await show_edit_menu(query, context, user_id)
    elif data.startswith("replace_lesson_"):
        new_subject_id = int(data.split("_")[-1])
        position = context.user_data["selected_lesson_position"]
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(current_day)
        
        schedule = user_data["schedule"]["schedule"][day_index][selected_week]
        schedule[position] = new_subject_id
        user_ref.update({"schedule.schedule": user_data["schedule"]["schedule"]})
        await show_edit_menu(query, context, user_id)
    elif data.startswith("delete_lesson_"):
        lesson_index = int(data.split("_")[-1])
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(context.user_data["current_day"])
        del user_data["schedule"]["schedule"][day_index][context.user_data.get("selected_week", "week1")][lesson_index]
        user_ref.update({"schedule.schedule": user_data["schedule"]["schedule"]})
        await show_edit_menu(query, context, user_id)
    elif data == "back_to_days":
        await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())
    elif data == "main_menu":
        await query.edit_message_text("🏠 Головне меню:", reply_markup=main_menu())
    elif data == 'settings':
        await show_settings_menu(query, context, user_id)
    elif data == 'set_starting_week':
        await _update_starting_week(
            context=context,
            new_date=datetime.now().strftime("%Y-%m-%d"),
            user_id=user_id,
            query=query
        )
    elif data == 'input_date_manually':
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text="📅 Введіть дату початкового тижня у форматі РРРР-ММ-ДД (наприклад, 2025-01-20):"
        )
    elif data == 'set_today':
         await _update_starting_week(
             context=context,
             new_date=datetime.now().strftime("%Y-%m-%d"),
             user_id=user_id,
             query=query
         )
    elif data == 'set_repeat':
        user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
        current_repeat = user_data.get("schedule", {}).get("repeat", 1)
        await query.edit_message_text(
            "🔢 Оберіть кількість тижнів у циклі:",
            reply_markup=repeat_keyboard(current_repeat)
        )
    
    elif data.startswith('set_repeat_'):
        new_repeat = int(data.split('_')[-1])
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_ref.update({"schedule.repeat": new_repeat})
        
        await query.answer(f"✅ Встановлено {new_repeat} тижнів!")
        await show_settings_menu(query, context, user_id)
        

async def handle_day_selection(query, context, day, user_id):
    """Обробка вибору дня"""
    context.user_data.update({"current_day": day, "selected_week": "week1"})
    user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
    schedule_text = await format_schedule_text(user_data, day, "week1")
    await query.edit_message_text(
        text=f"📚 {day.capitalize()} (week1):\n{schedule_text}",
        reply_markup=day_menu_keyboard(True),
        parse_mode="HTML"
    )

async def show_edit_menu(query, context, user_id):
    """Показуємо меню редагування"""
    user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
    day_index = DAYS_ORDER.index(context.user_data["current_day"])
    selected_week = context.user_data.get("selected_week", "week1")
    schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
    
    await query.edit_message_text(
        text="✏️ Редагування розкладу:",
        reply_markup=edit_day_keyboard(schedule_ids, user_data["schedule"]["subjects"], selected_week)
    )

async def show_settings_menu(query, context, user_id):
    """Оновлений обробник меню налаштувань"""
    user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
    current_repeat = user_data.get("schedule", {}).get("repeat", 1)
    
    await query.edit_message_text(
        text="⚙️ Налаштування:",
        reply_markup=settings_keyboard(current_repeat)
    )

async def _update_starting_week(context: ContextTypes.DEFAULT_TYPE, new_date: str, user_id: int, message=None, query=None):
    """Оновлення дати початку семестру"""
    try:
        datetime.strptime(new_date, "%Y-%m-%d")
        user_ref = db.collection("TG_USERS").document(str(user_id))
        
        user_ref.update({'starting_week': new_date})
        user_data = user_ref.get().to_dict()
        current_date = user_data.get('starting_week', new_date)
        
        response_text = f"📅 Поточна дата: {current_date}"
        
        if query:
            await query.edit_message_text(response_text, reply_markup=starting_week_keyboard())
        elif message:
            await message.reply_text(response_text, reply_markup=starting_week_keyboard())
            
    except ValueError:
        error_msg = "❌ Невірний формат даті!"
        await message.reply_text(error_msg) if message else await query.answer(error_msg)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обробка текстового вводу для дати"""
    await _update_starting_week(
        context=context,
        new_date=update.message.text,
        user_id=update.effective_user.id,
        message=update.message
    )