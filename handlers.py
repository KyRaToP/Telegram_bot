# =========================================================================
# handlers.py — Абсолютно чистая версия (0 ошибок Pylance)
# =========================================================================

import logging
import calendar
from datetime import datetime, timedelta

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
DAYS_OF_WEEK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]

def generate_calendar(year: int, month: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    kb.button(text=f"📅 {MONTH_NAMES[month]} {year}", callback_data="ignore")
    kb.button(text="◀️", callback_data=f"cal:prev:{year}:{month}")
    kb.button(text="▶️", callback_data=f"cal:next:{year}:{month}")
    kb.adjust(3)

    for day in DAYS_OF_WEEK:
        kb.button(text=day, callback_data="ignore")
    kb.adjust(7)

    month_cal = calendar.monthcalendar(year, month)
    for week in month_cal:
        for day in week:
            if day == 0:
                kb.button(text=" ", callback_data="ignore")
            else:
                kb.button(text=str(day), callback_data=f"cal:day:{year}:{month}:{day}")
        kb.adjust(7)

    kb.button(text="❌ Отмена", callback_data="menu:restart")
    kb.adjust(1)
    return kb

def generate_hour_selector() -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    hours = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", 
             "15:00", "16:00", "17:00", "18:00", "19:00", "20:00"]
    for h in hours:
        kb.button(text=h, callback_data=f"hour:{h}")
    kb.adjust(4)
    kb.button(text="❌ Отмена", callback_data="menu:restart")
    kb.adjust(1)
    return kb

async def _finalize_task(user_id: int, due_time_str: str, state: FSMContext, target_message: Message) -> None:
    """Единая функция для сохранения задачи и планирования напоминания."""
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
        await target_message.answer(f"✅ Задача добавлена!\n⏰ Время: {due_time_str}")
        await show_main_menu(target_message)
    except Exception as e:
        logger.error(f"Ошибка добавления задачи: {e}")
        await target_message.answer("❌ Ошибка при сохранении. Попробуйте /restart.")
        await state.clear()


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

    await message.answer("🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:", reply_markup=kb.as_markup(), parse_mode="HTML")


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

@router.callback_query(F.data.regexp(r"^time:quick:(today|tomorrow|week)$"))
async def cb_quick_time(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    
    choice = callback.data.split(":")[2]
    now = datetime.now()
    user_id = callback.from_user.id if callback.from_user else 0

    if choice == "today":
        target_time = now + timedelta(hours=1)
    elif choice == "tomorrow":
        target_time = (now + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
    else:
        target_time = (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)

    await _finalize_task(user_id, target_time.strftime("%d.%m.%Y %H:%M"), state, callback.message)


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
    
    # ИСПРАВЛЕНИЕ: прямое преобразование в int, без создания year_str и month_str
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
    if not callback.data or not isinstance(callback.message, Message): 
        return
    
    # ИСПРАВЛЕНИЕ: берем только день из конца строки, неиспользуемые переменные удалены
    day_str = callback.data.split(":")[-1]
    
    await state.update_data(cal_day=int(day_str))
    await state.set_state(TaskStates.waiting_for_hour)
    
    await callback.message.edit_text("🕒 Выберите час:", reply_markup=generate_hour_selector().as_markup())

@router.callback_query(F.data.regexp(r"^hour:(\d{2}:\d{2})$"))
async def cb_select_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    
    hour_str = callback.data.split(":")[1]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0
    
    due_time_str = f"{data.get('cal_day'):02d}.{data.get('cal_month'):02d}.{data.get('cal_year')} {hour_str}"
    await _finalize_task(user_id, due_time_str, state, callback.message)


# =========================================================================
# 4. МОИ ЗАДАЧИ И ИСТОРИЯ
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

@router.callback_query(F.data == "menu:tasks")
async def menu_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message)

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
    await cmd_show_tasks(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^tasks:del:(\d+)$"))
async def callback_delete_task_active(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    remove_reminder(task_id)
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    await cmd_show_tasks(user_id, callback.message)


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

@router.callback_query(F.data == "menu:history")
async def menu_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_history(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    await cmd_show_history(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    await cmd_show_history(user_id, callback.message)