# =========================================================================
# handlers.py — Исправлена ошибка "message is not modified"
# =========================================================================

import logging
import calendar
from datetime import datetime, timedelta, timezone

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest  # <--- ДОБАВЛЕНО

from states import TaskStates
from database import add_task, get_user_tasks, delete_task, get_completed_tasks, reactivate_task, toggle_task_status
from scheduler import schedule_reminder, remove_reminder

logger = logging.getLogger(__name__)
router = Router()

# =========================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================================================

MONTH_NAMES = ["", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", 
               "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

def get_main_menu_kb() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Добавить задачу", callback_data="menu:add")
    kb.button(text="📋 Мои задачи", callback_data="menu:tasks")
    kb.button(text="📜 История задач", callback_data="menu:history")
    kb.button(text="🔄 Перезапустить", callback_data="menu:restart")
    kb.adjust(1)
    return kb

def generate_calendar(year: int, month: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️", callback_data=f"cal:prev:{year}:{month}")
    kb.button(text=f"{MONTH_NAMES[month]} {year}", callback_data="ignore")
    kb.button(text="▶️", callback_data=f"cal:next:{year}:{month}")
    kb.adjust(3)

    month_cal = calendar.monthcalendar(year, month)
    for week in month_cal:
        for day in week:
            if day == 0:
                kb.button(text="·", callback_data="ignore")
            else:
                kb.button(text=str(day), callback_data=f"cal:day:{year}:{month}:{day}")
        kb.adjust(7)

    kb.button(text="❌ Отмена", callback_data="menu:restart")
    kb.adjust(1)
    return kb

def generate_hour_selector() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    for hh in range(24):
        time_str = f"{hh:02d}:00"
        kb.button(text=time_str, callback_data=f"hour:{time_str}")
    kb.adjust(4)
    kb.button(text="❌ Отмена", callback_data="menu:restart")
    kb.adjust(1)
    return kb


def generate_week_selector(start_date: datetime) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    weekday_abbr = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    for i in range(7):
        d = start_date + timedelta(days=i)
        label = f"{weekday_abbr[i]} {d.day}.{d.month}"
        kb.button(text=label, callback_data=f"week:day:{d.year}:{d.month}:{d.day}")
    kb.adjust(7)
    kb.button(text="❌ Отмена", callback_data="menu:restart")
    kb.adjust(1)
    return kb


async def _finalize_task(user_id: int, due_time_str: str, state: FSMContext, target_message: Message) -> None:
    try:
        data = await state.get_data()
        task_id = await add_task(
            user_id=user_id,
            title=data.get("title", "Без названия"),
            description=data.get("description", "Без описания"),
            due_time=due_time_str
        )
        
        if target_message.bot:
            schedule_reminder(
                bot=target_message.bot, user_id=user_id, task_id=task_id,
                title=data.get("title", "Без названия"), run_time_str=due_time_str
            )
        
        await state.clear()
        
        # ИСПРАВЛЕНИЕ: Ловим ошибку, если сообщение и так такое же
        try:
            await target_message.edit_text(
                text=f"✅ Задача добавлена!\n⏰ Время: {due_time_str}",
                reply_markup=get_main_menu_kb().as_markup()
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                await target_message.answer("✅ Задача уже добавлена!")
            else:
                raise
                
    except Exception as e:
        logger.error(f"Ошибка добавления задачи: {e}")
        await target_message.answer("❌ Ошибка при сохранении. Попробуйте /restart.")
        await state.clear()


# =========================================================================
# 1. ГЛАВНОЕ МЕНЮ
# =========================================================================

async def show_main_menu(message: Message) -> None:
    await message.answer(
        "🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:", 
        reply_markup=get_main_menu_kb().as_markup(), 
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
# 2. ДОБАВЛЕНИЕ ЗАДАЧИ (FSM)
# =========================================================================

@router.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.answer("📝 Введите название задачи:")

@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")

@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_calendar)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⚡ Сегодня", callback_data="time:quick:today")
    kb.button(text="📅 Завтра", callback_data="time:quick:tomorrow")
    kb.button(text="🗓 Через неделю", callback_data="time:quick:week")
    kb.button(text="📆 Выбрать дату и время", callback_data="time:quick:calendar")
    kb.adjust(2)
    
    await message.answer("⏰ Выберите время выполнения задачи:", reply_markup=kb.as_markup())


# =========================================================================
# 3. ОБРАБОТКА ВЫБОРА ВРЕМЕНИ (CALLBACKS)
# =========================================================================

@router.callback_query(F.data == "time:quick:today")
async def cb_quick_today(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    now = datetime.now(timezone(timedelta(hours=3)))
    selected_date = now.strftime("%d.%m.%Y")
    await state.update_data(selected_date=selected_date)
    await state.set_state(TaskStates.waiting_for_today_time)
    try:
        await callback.message.edit_text(
            "🕒 Выберите час:", reply_markup=generate_hour_selector().as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data == "time:quick:tomorrow")
async def cb_quick_tomorrow(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    now = datetime.now(timezone(timedelta(hours=3)))
    tomorrow = now + timedelta(days=1)
    selected_date = tomorrow.strftime("%d.%m.%Y")
    await state.update_data(selected_date=selected_date)
    await state.set_state(TaskStates.waiting_for_tomorrow_time)
    try:
        await callback.message.edit_text(
            "🕒 Выберите час:", reply_markup=generate_hour_selector().as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data == "time:quick:week")
async def cb_quick_week(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    now = datetime.now(timezone(timedelta(hours=3)))
    days_ahead = 7 - now.weekday()
    next_monday = now + timedelta(days=days_ahead)
    await state.set_state(TaskStates.waiting_for_week_day)
    try:
        await callback.message.edit_text(
            "📆 Выберите день:", reply_markup=generate_week_selector(next_monday).as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data == "time:quick:calendar")
async def cb_open_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    
    now = datetime.now()
    await state.update_data(cal_year=now.year, cal_month=now.month)
    await callback.message.edit_text("📆 Выберите дату:", reply_markup=generate_calendar(now.year, now.month).as_markup())

@router.callback_query(F.data.regexp(r"^cal:(prev|next):(\d{4}):(\d{1,2})$"))
async def cb_navigate_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    
    parts = callback.data.split(":")
    if len(parts) < 4: return
    
    direction = parts[1]
    year = int(parts[2])
    month = int(parts[3])
    
    if direction == "prev":
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    else:
        month += 1
        if month == 13:
            month = 1
            year += 1
            
    await state.update_data(cal_year=year, cal_month=month)
    await callback.message.edit_text("📆 Выберите дату:", reply_markup=generate_calendar(year, month).as_markup())

@router.callback_query(F.data.regexp(r"^cal:day:(\d{4}):(\d{1,2}):(\d{1,2})$"))
async def cb_select_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    
    day_str = callback.data.split(":")[-1]
    
    await state.update_data(cal_day=int(day_str))
    await state.set_state(TaskStates.waiting_for_hour)
    await callback.message.edit_text("🕒 Выберите час:", reply_markup=generate_hour_selector().as_markup())

@router.callback_query(F.data.regexp(r"^hour:(\d{2}:\d{2})$"))
async def cb_select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    
    hour_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0

    selected_date = data.get("selected_date")
    if selected_date:
        due_time_str = f"{selected_date} {hour_str}"
    else:
        due_time_str = f"{data.get('cal_day'):02d}.{data.get('cal_month'):02d}.{data.get('cal_year')} {hour_str}"
    await _finalize_task(user_id, due_time_str, state, callback.message)


@router.callback_query(F.data.regexp(r"^hour:(\d{2}:\d{2})$"), TaskStates.waiting_for_today_time)
async def cb_select_hour_today(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    hour_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0
    selected_date = data.get("selected_date")
    due_time_str = f"{selected_date} {hour_str}" if selected_date else f"{datetime.now(timezone(timedelta(hours=3))).strftime('%d.%m.%Y')} {hour_str}"
    await _finalize_task(user_id, due_time_str, state, callback.message)


@router.callback_query(F.data.regexp(r"^hour:(\d{2}:\d{2})$"), TaskStates.waiting_for_tomorrow_time)
async def cb_select_hour_tomorrow(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    hour_str = callback.data.split(":", 1)[1]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0
    selected_date = data.get("selected_date")
    due_time_str = f"{selected_date} {hour_str}" if selected_date else f"{(datetime.now(timezone(timedelta(hours=3))) + timedelta(days=1)).strftime('%d.%m.%Y')} {hour_str}"
    await _finalize_task(user_id, due_time_str, state, callback.message)


@router.callback_query(F.data.regexp(r"^week:day:(\d{4}):(\d{1,2}):(\d{1,2})$"))
async def cb_week_day_selected(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    parts = callback.data.split(":")
    year = int(parts[2])
    month = int(parts[3])
    day = int(parts[4])
    selected_date = f"{day:02d}.{month:02d}.{year}"
    await state.update_data(selected_date=selected_date)
    await state.set_state(TaskStates.waiting_for_hour)
    try:
        await callback.message.edit_text(
            "🕒 Выберите час:", reply_markup=generate_hour_selector().as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise


# =========================================================================
# 4. ПЕРЕЗАПУСК И МЕНЮ
# =========================================================================

@router.callback_query(F.data == "menu:restart")
async def menu_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    
    await state.clear()
    
    # ИСПРАВЛЕНИЕ: Ловим ошибку, если пользователь нажал "Перезапустить", находясь в главном меню
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data == "menu:tasks")
async def menu_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message)

@router.callback_query(F.data == "menu:history")
async def menu_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_history(user_id, callback.message)


# =========================================================================
# 5. МОИ ЗАДАЧИ И ИСТОРИЯ
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
    kb.button(text="🏠 Главное меню", callback_data="menu:restart")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.regexp(r"^tasks:toggle:(\d+)$"))
async def callback_toggle_task(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    is_completed = await toggle_task_status(task_id)
    if is_completed:
        remove_reminder(task_id)
        await callback.answer("✅ Выполнена!")
    else:
        await callback.answer("↩️ Возвращена!")
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data.regexp(r"^tasks:del:(\d+)$"))
async def callback_delete_task_active(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    remove_reminder(task_id)
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise


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
    kb.button(text="🏠 Главное меню", callback_data="menu:restart")
    kb.adjust(2)
    await message.answer(text, reply_markup=kb.as_markup(), parse_mode="HTML")

@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise

@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML"
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise
