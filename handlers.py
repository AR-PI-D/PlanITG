from telegram import Update, CallbackQuery, Message  # Додаємо імпорти
from typing import Union  # Для аннотації типів
from telegram.ext import ContextTypes, MessageHandler, filters
from datetime import datetime, timedelta
from id_generator import generate_unique_id
from firestore import db
from keyboards import (
    main_menu, 
    days_keyboard, 
    edit_day_keyboard,
    all_subjects_keyboard,
    day_menu_keyboard,

    settings_keyboard,
    starting_week_keyboard,
    repeat_keyboard,

    teachers_keyboard,  # Додаємо новий імпорт
    teacher_edit_keyboard,  # І цей також

    subjects_keyboard,
    subject_edit_keyboard,
    teachers_list_keyboard
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
    elif data == "settings":
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

        
    elif data.startswith('teacher_'):
        teacher_id = int(data.split('_')[1])
        context.user_data['editing_teacher'] = {'id': teacher_id}

    elif data.startswith('delete_teacher_'):
        teacher_id = int(data.split('_')[2])
        user_ref = db.collection("TG_USERS").document(str(user_id))
        
        # Отримуємо поточний список викладачів
        teachers = user_ref.get().to_dict().get("schedule", {}).get("teachers", [])
        
        # Фільтруємо видаляємий елемент
        updated_teachers = [t for t in teachers if t['id'] != teacher_id]
        
        # Оновлюємо базу даних
        user_ref.update({"schedule.teachers": updated_teachers})
        await show_teachers_list(query, context, user_id) 

    elif data == 'manage_subjects':
        await show_subjects_list(query, context, user_id)

    elif data.startswith('subject_'):
        subject_id = int(data.split('_')[1])
        context.user_data['editing_subject'] = {'id': subject_id}
        await show_subject_edit_menu(query, context, user_id)

    elif data == 'add_subject':
        new_subject = {
            'id': generate_unique_id(),
            'name': 'Новий предмет',
            'teacher': 0,
            'zoom_link': ''
        }
        user_ref = db.collection("TG_USERS").document(str(user_id))
        user_ref.update({"schedule.subjects": firestore.ArrayUnion([new_subject])})
        await show_subjects_list(query, context, user_id)

    elif data.startswith('delete_subject_'):
        subject_id = int(data.split('_')[2])
        user_ref = db.collection("TG_USERS").document(str(user_id))
        subjects = user_ref.get().to_dict().get("schedule", {}).get("subjects", [])
        updated_subjects = [s for s in subjects if s['id'] != subject_id]
        user_ref.update({"schedule.subjects": updated_subjects})
        await show_subjects_list(query, context, user_id)

    elif data == 'edit_subject_name':
        await query.edit_message_text("✏️ Введіть нову назву предмету:")
        context.user_data['editing_subject']['field'] = 'name'

    elif data == 'edit_subject_link':
        await query.edit_message_text("🔗 Введіть нове посилання:")
        context.user_data['editing_subject']['field'] = 'zoom_link'

    elif data == 'edit_subject_teacher':
        user_data = db.collection("TG_USERS").document(str(user_id)).get().to_dict()
        teachers = user_data.get("schedule", {}).get("teachers", [])
        await query.edit_message_text("👨🏫 Оберіть викладача:", reply_markup=teachers_list_keyboard(teachers))

    elif data.startswith('assign_teacher_'):
        teacher_id = int(data.split('_')[2])
        subject_id = context.user_data['editing_subject']['id']
        user_ref = db.collection("TG_USERS").document(str(user_id))
        subjects = user_ref.get().to_dict().get("schedule", {}).get("subjects", [])
        for s in subjects:
            if s['id'] == subject_id:
                s['teacher'] = teacher_id
        user_ref.update({"schedule.subjects": subjects})
        await show_subject_edit_menu(query, context, user_id)

async def handle_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    
    # Обробка редагування предмету
    if 'editing_subject' in context.user_data:
        edit_data = context.user_data['editing_subject']
        field = edit_data.get('field')
        subject_id = edit_data['id']
        
        user_ref = db.collection("TG_USERS").document(str(user_id))
        subjects = user_ref.get().to_dict().get("schedule", {}).get("subjects", [])
        
        for subject in subjects:
            if subject['id'] == subject_id:
                subject[field] = text
                break
                
        user_ref.update({"schedule.subjects": subjects})
        await show_subject_edit_menu(update.message, context, user_id)
        return  # Вихід після обробки
    
    # Обробка дати (лише якщо не в режимі редагування)
    
    try:
        datetime.strptime(text, "%Y-%m-%d")
        await _update_starting_week(
            context=context,
            new_date=text,
            user_id=user_id,
            message=update.message
        )
    except ValueError:
        await update.message.reply_text("❌ Невірний формат дати!")

async def update_teacher_in_db(user_id: int, teacher_data: dict):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_ref.update({
        "schedule.teachers": firestore.ArrayUnion([teacher_data])
    })

async def update_teacher_field(user_id: int, teacher_id: int, field: str, value: str):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    teachers = user_ref.get().to_dict()["schedule"]["teachers"]
    
    updated_teachers = []
    for t in teachers:
        if t['id'] == teacher_id:
            t[field] = value.strip()
        updated_teachers.append(t)
    
    user_ref.update({"schedule.teachers": updated_teachers})

    
def get_next_teacher_id(user_id):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    teachers = user_ref.get().to_dict().get("schedule", {}).get("teachers", [])
    return generate_unique_id()


async def delete_teacher(context, user_id):
    teacher_id = context.user_data['editing_teacher']['id']
    user_ref = db.collection("TG_USERS").document(str(user_id))
    teachers = user_ref.get().to_dict()["schedule"]["teachers"]
    user_ref.update({"schedule.teachers": [t for t in teachers if t['id'] != teacher_id]})


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

# Відображення списку предметів
async def show_subjects_list(query, context, user_id):
    user_ref = db.collection("TG_USERS").document(str(user_id))
    subjects = user_ref.get().to_dict().get("schedule", {}).get("subjects", [])
    await query.edit_message_text("📚 Список занять:", reply_markup=subjects_keyboard(subjects))



# Відображення меню редагування предмету
async def show_subject_edit_menu(update_or_query, context, user_id):
    subject_id = context.user_data['editing_subject']['id']
    user_ref = db.collection("TG_USERS").document(str(user_id))
    user_data = user_ref.get().to_dict()
    subjects = user_data.get("schedule", {}).get("subjects", [])
    teachers = user_data.get("schedule", {}).get("teachers", [])
    
    subject = next((s for s in subjects if s['id'] == subject_id), None)
    
    if subject:
        teacher = next((t for t in teachers if t['id'] == subject['teacher']), None)
        teacher_name = teacher['name'] if teacher else "Не обрано"
        
        text = (
            f"📝 Редагування предмету:\n"
            f"▪️ Назва: {subject['name']}\n"
            f"▪️ Викладач: {teacher_name}\n"
            f"▪️ Посилання: {subject.get('zoom_link', 'немає')}"
        )
        
        # Визначаємо, як відправити повідомлення
        if isinstance(update_or_query, CallbackQuery):
            await update_or_query.edit_message_text(text, reply_markup=subject_edit_keyboard())
        else:
            await context.bot.send_message(
                chat_id=update_or_query.chat_id,
                text=text,
                reply_markup=subject_edit_keyboard()
            )

