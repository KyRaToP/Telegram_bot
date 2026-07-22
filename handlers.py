# =========================================================================
# handlers.py — АБСОЛЮТНО ФИНАЛЬНАЯ ВЕРСИЯ (Все 5 ошибок исправлены)
# =========================================================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import TaskStates
from database import (
    add_task, get_user_tasks, delete_task,
    get_completed_tasks, reactivate_task, toggle_task_status
)
from scheduler import schedule_reminder, remove_reminder
from datetime import datetime, timedelta
import calendar

logger = logging.getLogger(__name__)
router = Router()

# =========================================================================
# 1. ГЛАВНОЕ МЕНЮ
# =========================================================================

async def show_main_menu(message: Message) -> None:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задачу", callback_data="menu:add")
    kb.button(text="📋 Мои задачи", callback_data="menu:tasks")
    kb.button(text="📜 История задач", callback_data="menu:history")
    kb.button(text="🔄 Перезапустить", callback_data="menu:restart")
    kb.adjust(1)

    await message.answer(
        "🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(message)

@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("🔄 Состояние сброшено!")
    await show_main_menu(message)

# =========================================================================
# 2. ОБРАБОТЧИКИ КНОПОК МЕНЮ
# =========================================================================

@router.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.answer("📝 Введите название задачи:")

@router.callback_query(F.data == "menu:tasks")
async def menu_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message)

@router.callback_query(F.data == "menu:history")
async def menu_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_history(user_id, callback.message)

@router.callback_query(F.data == "menu:restart")
async def menu_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    await state.clear()
    await callback.message.answer("🔄 Состояние сброшено!")
    await show_main_menu(callback.message)

# =========================================================================
# 3. FSM: ДОБАВЛЕНИЕ ЗАДАЧИ
# =========================================================================

@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")

@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    
    kb = InlineKeyboardBuilder()
    kb.button(text="Сегодня", callback_data="time:quick:today")
    kb.button(text="📅 Завтра", callback_data="time:quick:tomorrow")
    kb.button(text="🗓 Через неделю", callback_data="time:quick:week")
    kb.button(text="📆 Выбрать дату и время", callback_data="time:quick:calendar")
    kb.adjust(2)
    
    await message.answer("⏰ Выберите время выполнения задачи:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("time:quick:"))
async def quick_time_selection(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    now = datetime.now()
    
    if callback.data == "time:quick:today":
        due_time = (now + timedelta(hours=1)).strftime("%d.%m.%Y %H:%M")
    elif callback.data == "time:quick:tomorrow":
        due_time = (now + timedelta(days=1, hours=9)).strftime("%d.%m.%Y 09:00")
    elif callback.data == "time:quick:week":
        due_time = (now + timedelta(days=7, hours=9)).strftime("%d.%m.%Y 09:00")
    
    data = await state.get_data()
    user_id = message.from_user.id if message.from_user else 0
    
    task_id = await add_task(
        user_id=user_id,
        title=data.get("title", "Без названия"),
        description=data.get("description", "Без описания"),
        due_time=due_time
    )
    
    if message.bot:
        schedule_reminder(
            bot=message.bot, user_id=user_id, task_id=task_id,
            title=data.get("title", "Без названия"), run_time_str=due_time
        )
    
    await state.clear()
    await callback.message.answer(f"✅ Задача добавлена!\n⏰ Время: {due_time}")
    await show_main_menu(callback.message)

@router.callback_query(F.data == "time:quick:calendar")
async def open_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    await state.set_state(TaskStates.waiting_for_calendar)
    kb = generate_calendar(now.year, now.month)
    await callback.message.answer("📅 Выберите дату:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("cal:navigate:"))
async def navigate_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    data = await state.get_data()
    year = data.get("year", datetime.now().year)
    month = data.get("month", datetime.now().month)
    
    if callback.data == "cal:navigate:prev":
        month -= 1
        if month < 1:
            month = 12
            year -= 1
    elif callback.data == "cal:navigate:next":
        month += 1
        if month > 12:
            month = 1
            year += 1
    
    await state.update_data(year=year, month=month)
    kb = generate_calendar(year, month)
    await callback.message.edit_reply_markup(reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("cal:day:"))
async def select_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    day = int(callback.data.split(":")[2])
    data = await state.get_data()
    year = data.get("year", datetime.now().year)
    month = data.get("month", datetime.now().month)
    
    selected_date = datetime(year, month, day)
    if selected_date < datetime.now():
        await callback.message.answer("❌ Вы не можете выбрать прошедшую дату.")
        return
    
    await state.update_data(selected_date=selected_date.strftime("%d.%m.%Y"))
    await state.set_state(TaskStates.waiting_for_hour)
    
    kb = generate_hour_selector()
    await callback.message.answer("⏰ Выберите время:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("hour:"))
async def select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    hour = int(callback.data.split(":")[1])
    data = await state.get_data()
    selected_date = data.get("selected_date", "")
    
    due_time = f"{selected_date} {hour:02d}:00"
    user_id = message.from_user.id if message.from_user else 0
    title = data.get("title", "Без названия")
    description = data.get("description", "Без описания")
    
    task_id = await add_task(
        user_id=user_id,
        title=title,
        description=description,
        due_time=due_time
    )
    
    if message.bot:
        schedule_reminder(
            bot=message.bot, user_id=user_id, task_id=task_id,
            title=title, run_time_str=due_time
        )
    
    await state.clear()
    await callback.message.answer(f"✅ Задача добавлена!\n⏰ Время: {due_time}")
    await show_main_menu(callback.message)

@router.callback_query(F.data == "cancel")
async def cancel_add_task(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    await state.clear()
    await show_main_menu(callback.message)
    await callback.message.answer("❌ Добавление задачи отменено.")

# =========================================================================
# 4. МОИ ЗАДАЧИ
# =========================================================================

async def cmd_show_tasks(user_id: int, message: Message) -> None:
    tasks = await get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("📋 Нет активных задач.")
        return
    
    text = "📋 <b>Ваши задачи:</b>\n\n"
    kb = InlineKeyboardBuilder()
    
    for task in tasks:
        text += f"📌 {task['id']}: {task['title']}\n⏰ {task['due_time']}\n\n"
        title_short = (task['title'] or "Задача")[:10]
        toggle_text = "↩️ В активные" if task['is_completed'] else "✅ Выполнить"
        kb.button(text=toggle_text, callback_data=f"tasks:toggle:{task['id']}")
        kb.button(text=f"🗑 {title_short}", callback_data=f"tasks:del:{task['id']}")
        
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.regexp(r"^tasks:toggle:(\d+)$"))
async def callback_toggle_task(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    is_completed = await toggle_task_status(task_id)
    
    if is_completed:
        remove_reminder(task_id)
        await callback.answer("✅ Выполнена!")
    else:
        await callback.answer("↩️ Возвращена!")
    
    await cmd_show_tasks(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^tasks:del:(\d+)$"))
async def callback_delete_task_active(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    remove_reminder(task_id)
    await delete_task(task_id)
    
    await callback.answer("🗑 Удалена!")
    await cmd_show_tasks(user_id, callback.message)

# =========================================================================
# 5. ИСТОРИЯ
# =========================================================================

async def cmd_show_history(user_id: int, message: Message) -> None:
    tasks = await get_completed_tasks(user_id)
    
    if not tasks:
        await message.answer("📜 История пуста.")
        return
    
    text = "📜 <b>История:</b>\n\n"
    kb = InlineKeyboardBuilder()
    
    for task in tasks:
        text += f"📌 {task['id']}: {task['title']}\n⏰ {task['due_time']}\n\n"
        title_short = (task['title'] or "Задача")[:10]
        kb.button(text="↩️ Вернуть", callback_data=f"history:reactivate:{task['id']}")
        kb.button(text=f"🗑 {title_short}", callback_data=f"history:del:{task['id']}")
        
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    await cmd_show_history(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    await cmd_show_history(user_id, callback.message)

# Вспомогательные функции

def generate_calendar(year: int, month: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    
    # Названия месяцев на русском
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
    
    # Названия дней недели на русском
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    
    kb.button(text=f"{months[month-1]} {year}", callback_data="cal:navigate:current")
    kb.button(text="<", callback_data="cal:navigate:prev")
    kb.button(text=">", callback_data="cal:navigate:next")
    kb.adjust(3)
    
    for day in days_of_week:
        kb.button(text=day, callback_data=f"cal:day:{day}")
    
    calendar_matrix = calendar.monthcalendar(year, month)
    for week in calendar_matrix:
        for day in week:
            if day == 0:
                kb.button(text=" ", callback_data="cal:day:0")
            else:
                kb.button(text=str(day), callback_data=f"cal:day:{day}")
    
    kb.button(text="❌ Отмена", callback_data="cancel")
    kb.adjust(7)
    
    return kb

def generate_hour_selector() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    
    hours = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00",
             "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
    
    for hour in hours:
        kb.button(text=hour, callback_data=f"hour:{hour.split(':')[0]}")
    
    kb.button(text="❌ Отмена", callback_data="cancel")
    kb.adjust(4)
    
    return kb
