from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("← Попередній", callback_data='prev_day'),
            InlineKeyboardButton("Наступний →", callback_data='next_day')
        ],
        [
            InlineKeyboardButton("Сьогодні 🏠", callback_data='today')
        ],
        [InlineKeyboardButton("Розклад 🗓", callback_data='schedule')],
        [InlineKeyboardButton("Налаштування ⚙️", callback_data='settings')]
    ])

# Клавіатура з днями тижня (без кнопки "Змінити тиждень")
def days_keyboard():
    days = [
        ("Понеділок ☕️", "понеділок"),
        ("Вівторок 📘", "вівторок"),
        ("Середа 🧠", "середа"),
        ("Четвер 💼", "четвер"),
        ("П'ятниця 🎊", "п'ятниця"),
        ("Субота 🛌", "субота"),
        ("Неділя 🌅", "неділя")
    ]
    keyboard = [
        [InlineKeyboardButton(text, callback_data=data)] for text, data in days
    ]
    return InlineKeyboardMarkup(keyboard)

# Клавіатура для вибору предмета для заміни
def subjects_keyboard(subjects):
    keyboard = [
        [InlineKeyboardButton(subject["name"], callback_data=f"change_{subject['id']}")]
        for subject in subjects
    ]
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="back_to_day")])
    return InlineKeyboardMarkup(keyboard)


def weeks_keyboard():
    weeks = [
        ("Тиждень 1", "week1"),
        ("Тиждень 2", "week2"),
        ("Тиждень 3", "week3"),
        ("Тиждень 4", "week4")
    ]
    keyboard = [
        [InlineKeyboardButton(text, callback_data=data)] for text, data in weeks
    ]
    keyboard.append([InlineKeyboardButton("↩️ Назад до днів", callback_data="back_to_days")])
    return InlineKeyboardMarkup(keyboard)

def day_menu_keyboard(has_schedule: bool):
    buttons = [
        [InlineKeyboardButton("✏️ Змінити розклад", callback_data="edit_schedule")]
    ]
    buttons.append([InlineKeyboardButton("↩️ Назад до днів", callback_data="back_to_days")])
    return InlineKeyboardMarkup(buttons)

def edit_day_keyboard(schedule_ids, subjects, selected_week):
    keyboard = []
    
    # Кнопки уроків
    for index, subject_id in enumerate(schedule_ids):
        subject = next((s for s in subjects if s["id"] == subject_id), None)
        btn_text = f"{index+1}. {subject['name']}" if subject else f"{index+1} Помилка"
        keyboard.append([
            InlineKeyboardButton(btn_text, callback_data=f"edit_lesson_{index}"),
            InlineKeyboardButton("🗑️", callback_data=f"delete_lesson_{index}")
            ])
    
    # Нова кнопка для додавання пари
    keyboard.append([InlineKeyboardButton("➕ Додати пару", callback_data="add_lesson")])  # <-- Додано
    
    # Кнопки тижнів
    week_btns = [
        InlineKeyboardButton(
            f"{i+1} {'✅' if f'week{i+1}' == selected_week else ''}",
            callback_data=f"select_week_{i+1}"
        ) for i in range(4)
    ]
    keyboard.append(week_btns)
    
    # Навігація
    keyboard.append([
        InlineKeyboardButton("◀️ Назад", callback_data="back_to_day"),
        InlineKeyboardButton("🏠 Додому", callback_data="main_menu")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def all_subjects_keyboard(subjects):
    keyboard = [
        [InlineKeyboardButton(subject["name"], callback_data=f"replace_lesson_{subject['id']}")]
        for subject in subjects
    ]
    keyboard.append([InlineKeyboardButton("↩️ Назад", callback_data="back_to_lessons")])
    return InlineKeyboardMarkup(keyboard)





# keyboards.py

# keyboards.py

def settings_keyboard(current_repeat: int = 1):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("Поточна дата 📅", callback_data='set_starting_week')],
        [InlineKeyboardButton(f"Кількість тижнів 🔄 ({current_repeat})", callback_data='set_repeat')],
        [InlineKeyboardButton("Викладачі 👨🏫", callback_data='manage_teachers')],
        [InlineKeyboardButton("Заняття 📚", callback_data='manage_subjects')],  # Нова кнопка
        [InlineKeyboardButton("↩️ Назад", callback_data='main_menu')]
    ])
# keyboards.py
# keyboards.py
def teachers_keyboard(teachers):
    buttons = []
    for teacher in teachers:
        is_new = not teacher.get('name')
        
        # Визначення тексту кнопки
        if is_new:
            btn_text = "🆕 Новий викладач"
        else:
            contact = teacher.get('contact', '')
            btn_text = f"{teacher['name']} ({contact})" if contact else teacher['name']
        
        # Єдиний callback формат
        callback_data = f"teacher_{teacher['id']}"
        
        row = [
            InlineKeyboardButton(btn_text, callback_data=callback_data),
            InlineKeyboardButton("❌", callback_data=f"delete_teacher_{teacher['id']}")
        ]
        buttons.append(row)
    
    buttons.append([InlineKeyboardButton("➕ Додати викладача", callback_data="add_teacher")])
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="settings")])
    
    return InlineKeyboardMarkup(buttons)

def teacher_edit_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Ім'я", callback_data="edit_teacher_name"),
            InlineKeyboardButton("📞 Контакт", callback_data="edit_teacher_contact")
        ],
        [InlineKeyboardButton("🗑️ Видалити", callback_data="delete_teacher")],
        [InlineKeyboardButton("← Назад до списку", callback_data="manage_teachers")]
    ])

def repeat_keyboard(current_repeat: int):
    buttons = [
        [InlineKeyboardButton(
            f"{i} {'✅' if i == current_repeat else ''}", 
            callback_data=f'set_repeat_{i}'
        )] for i in range(1, 5)
    ]
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data='settings')])
    return InlineKeyboardMarkup(buttons)

def starting_week_keyboard():  # Немає аргументів у визначенні
    buttons = [
        [InlineKeyboardButton("Ввести дату 📝", callback_data='input_date_manually')],
        [InlineKeyboardButton("Сьогодні ✅", callback_data='set_today')],
        [InlineKeyboardButton("↩️ Назад", callback_data='settings')]
    ]
    return InlineKeyboardMarkup(buttons)


# Клавіатура списку предметів
def subjects_keyboard(subjects):
    buttons = []
    for subject in subjects:
        btn_text = f"{subject['name']} ({subject.get('zoom_link', 'немає посилання')})"
        row = [
            InlineKeyboardButton(btn_text, callback_data=f"subject_{subject['id']}"),
            InlineKeyboardButton("❌", callback_data=f"delete_subject_{subject['id']}")
        ]
        buttons.append(row)
    buttons.append([InlineKeyboardButton("➕ Додати заняття", callback_data="add_subject")])
    buttons.append([InlineKeyboardButton("↩️ Назад", callback_data="settings")])
    return InlineKeyboardMarkup(buttons)

# Клавіатура редагування предмету
def subject_edit_keyboard():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✏️ Назва", callback_data="edit_subject_name"),
            InlineKeyboardButton("🔗 Посилання", callback_data="edit_subject_link")
        ],
        [InlineKeyboardButton("👨🏫 Викладач", callback_data="edit_subject_teacher")],
        [InlineKeyboardButton("🗑️ Видалити", callback_data="delete_subject")],
        [InlineKeyboardButton("← Назад", callback_data="manage_subjects")]
    ])

# Клавіатура вибору викладача для предмету
def teachers_list_keyboard(teachers):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t['name'], callback_data=f"assign_teacher_{t['id']}")] 
        for t in teachers
    ])