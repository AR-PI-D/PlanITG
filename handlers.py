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

DAYS_ORDER = ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"]

async def format_schedule_text(user_data: dict, day: str, selected_week: str) -> str:
    day_index = DAYS_ORDER.index(day)
    schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
    
    if not schedule_ids:
        return "🎉 Вихідний день!"
    
    subjects = user_data["schedule"]["subjects"]
    teachers = user_data["schedule"]["teachers"]
    schedule_entries = []
    
    for idx, subject_id in enumerate(schedule_ids, start=1):
        subject = next((s for s in subjects if s["id"] == subject_id), None)
        teacher = next((t for t in teachers if t["id"] == subject["teacher"]), None) if subject else None
        
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_ref = db.collection("TG_USERS").document(str(user_id))
    
    if not user_ref.get().exists:
        user_ref.set({
            "schedule": default_schedule,
            "telegram_id": user_id,
            "created_at": firestore.SERVER_TIMESTAMP
        })
    
    await update.message.reply_text("🏠 Головне меню:", reply_markup=main_menu())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    context_data = context.user_data

    # Головне меню
    if data == "schedule":
        await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())

    # Вибір дня
    elif data in DAYS_ORDER:
        await handle_day_selection(query, context, data, user_id)

    # Меню редагування
    elif data == "edit_schedule":
        await show_edit_menu(query, context, user_id)

    # Вибір тижня
    elif data.startswith("select_week_"):
        await handle_week_selection(query, context, data, user_id)

    # Редагування уроку
    elif data.startswith("edit_lesson_"):
        await handle_lesson_edit(query, context, data, user_id)

    # Збереження змін
    elif data.startswith("replace_lesson_"):
        await save_lesson_changes(query, context, data, user_id)

    # Навігація
    elif data == "back_to_day":
        await return_to_day_view(query, context, user_id)
    
    elif data == "back_to_days":
        await query.edit_message_text("📅 Оберіть день:", reply_markup=days_keyboard())
    
    elif data == "main_menu":
        await query.edit_message_text("🏠 Головне меню:", reply_markup=main_menu())
    
    elif data == "settings":
        await query.edit_message_text("⚙️ Налаштування в розробці...", reply_markup=main_menu())

async def handle_day_selection(query, context, day, user_id):
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

async def show_edit_menu(query, context, user_id):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    day_index = DAYS_ORDER.index(context.user_data["current_day"])
    selected_week = context.user_data.get("selected_week", "week1")
    
    schedule_ids = user_data["schedule"]["schedule"][day_index].get(selected_week, [])
    
    await query.edit_message_text(
        text="✏️ Редагування розкладу:",
        reply_markup=edit_day_keyboard(schedule_ids, user_data["schedule"]["subjects"], selected_week)
    )

async def handle_week_selection(query, context, data, user_id):
    week_num = data.split("_")[-1]
    context.user_data["selected_week"] = f"week{week_num}"
    await show_edit_menu(query, context, user_id)

async def handle_lesson_edit(query, context, data, user_id):
    position = int(data.split("_")[-1])
    context.user_data["selected_lesson_position"] = position
    
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    
    await query.edit_message_text(
        text="🔁 Оберіть новий предмет:",
        reply_markup=all_subjects_keyboard(user_data["schedule"]["subjects"])
    )

async def save_lesson_changes(query, context, data, user_id):
    new_subject_id = int(data.split("_")[-1])
    position = context.user_data["selected_lesson_position"]
    current_day = context.user_data["current_day"]
    selected_week = context.user_data.get("selected_week", "week1")
    
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    day_index = DAYS_ORDER.index(current_day)
    
    schedule = user_data["schedule"]["schedule"][day_index][selected_week]
    if 0 <= position < len(schedule):
        schedule[position] = new_subject_id
        user_ref.update({f"schedule.schedule.{day_index}.{selected_week}": schedule})
        await query.answer("✅ Зміни збережено!")
        await return_to_day_view(query, context, user_id)
    else:
        await query.answer("🚫 Помилка при зміні")

async def return_to_day_view(query, context, user_id):
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