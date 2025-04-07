from telegram import Update
from telegram.ext import ContextTypes
from firestore import db
from keyboards import (
    main_menu, 
    days_keyboard, 
    edit_day_keyboard,
    all_subjects_keyboard,
    day_menu_keyboard
)
from default_schedule import default_schedule
import firebase_admin
from firebase_admin import firestore
import logging

logging.basicConfig(level=logging.INFO)
DAYS_ORDER = ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"]

async def format_schedule_text(user_data: dict, day: str, selected_week: str) -> str:
    try:
        day_index = DAYS_ORDER.index(day)
        schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
        
        if not schedule_ids:
            return "🎉 Вихідний день!"
        
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
        
        return "\n".join(schedule_entries)
    except Exception as e:
        logging.error(f"Помилка форматування розкладу: {e}")
        return "🚫 Помилка відображення розкладу"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        user_ref = db.collection("TG_USERS").document(str(user_id))
        
        if not user_ref.get().exists:
            user_ref.set({
                "schedule": default_schedule,
                "telegram_id": user_id,
                "created_at": firestore.SERVER_TIMESTAMP
            })
        
        await update.message.reply_text("🏠 Головне меню:", reply_markup=main_menu())
    except Exception as e:
        logging.error(f"Помилка команди /start: {e}")

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    context_data = context.user_data

    try:
        if data == "schedule":
            await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())

        elif data in DAYS_ORDER:
            await handle_day_selection(query, context, data, user_id)

        elif data == "edit_schedule":
            await show_edit_menu(query, context, user_id)

        elif data.startswith("select_week_"):
            await handle_week_selection(query, context, data, user_id)

        elif data.startswith("edit_lesson_"):
            await handle_lesson_edit(query, context, data, user_id)

        elif data == "add_lesson":
            await add_new_lesson(query, context, user_id)

        elif data.startswith("replace_lesson_"):
            await save_lesson_changes(query, context, data, user_id)

        elif data.startswith("delete_lesson_"):
            await delete_lesson(query, context, user_id)

        elif data == "back_to_day":
            await return_to_day_view(query, context, user_id)
        
        elif data == "back_to_days":
            await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())
        
        elif data == "main_menu":
            await query.edit_message_text("🏠 Головне меню:", reply_markup=main_menu())
        
        elif data == "settings":
            await query.edit_message_text("⚙️ Налаштування в розробці...", reply_markup=main_menu())
            
    except Exception as e:
        logging.error(f"Помилка обробки кнопки {data}: {e}")
        await query.edit_message_text("🚫 Сталася помилка")

async def handle_day_selection(query, context, day, user_id):
    try:
        context.user_data.update({
            "current_day": day,
            "selected_week": context.user_data.get("selected_week", "week1")
        })
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        
        schedule_text = await format_schedule_text(user_data, day, context.user_data["selected_week"])
        has_schedule = bool(user_data["schedule"]["schedule"][DAYS_ORDER.index(day)])
        
        await query.edit_message_text(
            text=f"📚 {day.capitalize()} ({context.user_data['selected_week']}):\n{schedule_text}",
            reply_markup=day_menu_keyboard(has_schedule),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Помилка вибору дня: {e}")
        await query.answer("🚫 Помилка відображення дня")

async def show_edit_menu(query, context, user_id):
    try:
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(context.user_data["current_day"])
        selected_week = context.user_data.get("selected_week", "week1")
        
        schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
        
        if not schedule_ids:
            await query.edit_message_text("📭 Розклад порожній")
            return
        
        subjects = user_data["schedule"]["subjects"]
        if not any(subject["id"] == 0 for subject in subjects):
            subjects.append({
                "id": 0,
                "name": "Пустий слот",
                "teacher": 0,
                "zoom_link": "",
                "color": "gray"
            })
        
        await query.edit_message_text(
            text="✏️ Редагування розкладу:",
            reply_markup=edit_day_keyboard(schedule_ids, subjects, selected_week)
        )
    except Exception as e:
        logging.error(f"Помилка відображення меню редагування: {e}")
        await query.answer("🚫 Помилка меню")

async def handle_week_selection(query, context, data, user_id):
    try:
        week_num = data.split("_")[-1]
        context.user_data["selected_week"] = f"week{week_num}"
        await show_edit_menu(query, context, user_id)
    except Exception as e:
        logging.error(f"Помилка вибору тижня: {e}")
        await query.answer("🚫 Помилка тижня")

async def handle_lesson_edit(query, context, data, user_id):
    try:
        position = int(data.split("_")[-1])
        context.user_data["selected_lesson_position"] = position
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        
        await query.edit_message_text(
            text="🔁 Оберіть новий предмет:",
            reply_markup=all_subjects_keyboard(user_data["schedule"]["subjects"])
        )
    except Exception as e:
        logging.error(f"Помилка редагування уроку: {e}")
        await query.answer("🚫 Помилка вибору уроку")

async def add_new_lesson(query, context, user_id):
    try:
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(current_day)
        
        full_schedule = user_data["schedule"]["schedule"].copy()
        day_data = full_schedule[day_index].copy()
        
        if selected_week not in day_data:
            day_data[selected_week] = []
        
        day_data[selected_week].append(0)
        full_schedule[day_index] = day_data
        
        user_ref.update({"schedule.schedule": full_schedule})
        await show_edit_menu(query, context, user_id)
        await query.answer("🔄 Додано нову пару")
    except Exception as e:
        logging.error(f"Помилка додавання пари: {e}")
        await query.answer("🚫 Помилка додавання")

async def save_lesson_changes(query, context, data, user_id):
    try:
        new_subject_id = int(data.split("_")[-1])
        position = context.user_data["selected_lesson_position"]
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(current_day)
        
        full_schedule = user_data["schedule"]["schedule"].copy()
        day_data = full_schedule[day_index].copy()
        
        if selected_week not in day_data:
            day_data[selected_week] = []
        
        schedule = day_data[selected_week]
        
        if 0 <= position < len(schedule):
            schedule[position] = new_subject_id
            day_data[selected_week] = schedule
            full_schedule[day_index] = day_data
            
            user_ref.update({"schedule.schedule": full_schedule})
            await query.answer("✅ Зміни збережено!")
            await show_edit_menu(query, context, user_id)  # Залишаємось у меню редагування
        else:
            await query.answer("🚫 Невірна позиція уроку")
    except Exception as e:
        logging.error(f"Помилка збереження змін: {e}")
        await query.answer("🚫 Помилка збереження")

async def delete_lesson(query, context, user_id):
    try:
        lesson_index = int(query.data.split("_")[-1])
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        day_index = DAYS_ORDER.index(current_day)
        
        full_schedule = user_data["schedule"]["schedule"].copy()
        day_data = full_schedule[day_index].copy()
        
        if selected_week not in day_data or not day_data[selected_week]:
            await query.answer("🚫 Немає пар для видалення")
            return
            
        schedule = day_data[selected_week]
        
        if 0 <= lesson_index < len(schedule):
            del schedule[lesson_index]
            day_data[selected_week] = schedule
            full_schedule[day_index] = day_data
            
            user_ref.update({"schedule.schedule": full_schedule})
            await query.answer("🗑️ Пара видалена!")
            await show_edit_menu(query, context, user_id)
        else:
            await query.answer("🚫 Невірний номер пари")
    except Exception as e:
        logging.error(f"Помилка видалення: {e}")
        await query.answer("🚫 Помилка видалення")

async def return_to_day_view(query, context, user_id):
    try:
        current_day = context.user_data["current_day"]
        selected_week = context.user_data.get("selected_week", "week1")
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_data = user_ref.get().to_dict()
        
        schedule_text = await format_schedule_text(user_data, current_day, selected_week)
        has_schedule = bool(user_data["schedule"]["schedule"][DAYS_ORDER.index(current_day)])
        
        await query.edit_message_text(
            text=f"📚 {current_day.capitalize()} ({selected_week}):\n{schedule_text}",
            reply_markup=day_menu_keyboard(has_schedule),
            parse_mode="HTML"
        )
    except Exception as e:
        logging.error(f"Помилка повернення до дня: {e}")
        await query.answer("🚫 Помилка відображення")