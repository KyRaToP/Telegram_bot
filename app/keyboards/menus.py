import calendar
from datetime import datetime, timedelta

from aiogram.utils.keyboard import InlineKeyboardBuilder

MONTH_NAMES = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def get_main_menu_kb() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить задачу", callback_data="menu:add")
    keyboard.button(text="📂 Категории", callback_data="menu:categories")
    keyboard.button(text="📋 Мои задачи", callback_data="menu:tasks")
    keyboard.button(text="📜 История задач", callback_data="menu:history")
    keyboard.button(text="🔄 Перезапустить", callback_data="menu:restart")
    keyboard.adjust(1)
    return keyboard


def generate_calendar(year: int, month: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="◀️", callback_data=f"cal:prev:{year}:{month}")
    keyboard.button(text=f"📅 {MONTH_NAMES[month]} {year}", callback_data="ignore")
    keyboard.button(text="▶️", callback_data=f"cal:next:{year}:{month}")
    keyboard.adjust(3)

    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for weekday in weekdays:
        keyboard.button(text=weekday, callback_data="ignore")
    keyboard.adjust(7)

    for week in calendar.monthcalendar(year, month):
        for day in week:
            if day == 0:
                keyboard.button(text="·", callback_data="ignore")
            else:
                keyboard.button(
                    text=str(day), callback_data=f"cal:day:{year}:{month}:{day}"
                )
        keyboard.adjust(7)

    keyboard.button(text="❌ Отмена", callback_data="menu:restart")
    keyboard.adjust(1)
    return keyboard


def generate_hour_selector() -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    for hour in range(24):
        time_str = f"{hour:02d}:00"
        keyboard.button(text=time_str, callback_data=f"hour:{time_str}")
    keyboard.adjust(4)
    keyboard.button(text="❌ Отмена", callback_data="menu:restart")
    keyboard.adjust(1)
    return keyboard


def generate_digital_clock(hour: int, minute: int) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="⬇️", callback_data="clock:adj:down:hour")
    keyboard.button(text=f"⏰ {hour:02d}", callback_data="ignore")
    keyboard.button(text="⬆️", callback_data="clock:adj:up:hour")
    keyboard.adjust(3)

    keyboard.button(text="⬇️", callback_data="clock:adj:down:minute")
    keyboard.button(text=f"⏱ {minute:02d}", callback_data="ignore")
    keyboard.button(text="⬆️", callback_data="clock:adj:up:minute")
    keyboard.adjust(3)

    keyboard.button(text="✅ Подтвердить", callback_data="clock:confirm")
    keyboard.adjust(1)
    return keyboard


def generate_week_selector(start_date: datetime) -> InlineKeyboardBuilder:
    keyboard = InlineKeyboardBuilder()
    weekday_abbr = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for index in range(7):
        selected_date = start_date + timedelta(days=index)
        label = f"{weekday_abbr[index]} {selected_date.day}.{selected_date.month}"
        keyboard.button(
            text=label,
            callback_data=(
                f"week:day:{selected_date.year}:{selected_date.month}:{selected_date.day}"
            ),
        )
    keyboard.adjust(7)
    keyboard.button(text="❌ Отмена", callback_data="menu:restart")
    keyboard.adjust(1)
    return keyboard
