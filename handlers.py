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
from database import add_task, get_user_tasks, delete_task, get_completed_tasks, reactivate_task, toggle_task_status, add_category, get_user_categories
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
    kb.button(text="📂 Категории", callback_data="menu:categories")
    kb.button(text="📋 Мои задачи", callback_data="menu:tasks")
    kb.button(text="📜 История задач", callback_data="menu:history")
    kb.button(text="🔄 Перезапустить", callback_data="menu:restart")
    kb.adjust(1)
    return kb

def generate_calendar(year: int, month: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    # строка навигации
    kb.button(text="◀️", callback_data=f"cal:prev:{year}:{month}")
    kb.button(text=f"📅 {MONTH_NAMES[month]} {year}", callback_data="ignore")
    kb.button(text="▶️", callback_data=f"cal:next:{year}:{month}")
    kb.adjust(3)

    # заголовки дней недели
    weekdays = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    for wd in weekdays:
        kb.button(text=wd, callback_data="ignore")
    kb.adjust(7)

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


def generate_digital_clock(hour: int, minute: int) -> InlineKeyboardBuilder:
    kb = InlineKeyboardBuilder()
    # Часы
    kb.button(text="⬇️", callback_data="clock:adj:down:hour")
    kb.button(text=f"⏰ {hour:02d}", callback_data="ignore")
    kb.button(text="⬆️", callback_data="clock:adj:up:hour")
    kb.adjust(3)
    # Минуты
    kb.button(text="⬇️", callback_data="clock:adj:down:minute")
    kb.button(text=f"⏱ {minute:02d}", callback_data="ignore")
    kb.button(text="⬆️", callback_data="clock:adj:up:minute")
    kb.adjust(3)
    # Подтверждение
    kb.button(text="✅ Подтвердить", callback_data="clock:confirm")
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


async def _finalize_task(user_id: int, due_time_str: str, state: FSMContext, target_message: Message, category: str = "Без категории") -> None:
    try:
        data = await state.get_data()
        task_id = await add_task(
            user_id=user_id,
            title=data.get("title", "Без названия"),
            description=data.get("description", "Без описания"),
            due_time=due_time_str,
            category=category
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
                text=f"✅ Задача добавлена!\n⏰ Время: {due_time_str}\n🏷 Категория: {category}",
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
    now = datetime.now(timezone(timedelta(hours=3)))
    await state.update_data(cal_year=now.year, cal_month=now.month)
    await state.set_state(TaskStates.waiting_for_calendar)
    await message.answer("📆 Выберите дату:", reply_markup=generate_calendar(now.year, now.month).as_markup())


# =========================================================================
# 3. ОБРАБОТКА ВЫБОРА ВРЕМЕНИ (CALLBACKS)
# =========================================================================




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
    
    await state.update_data(cal_day=int(day_str), clock_hour=0, clock_minute=0)
    await state.set_state(TaskStates.waiting_for_clock)
    await callback.message.edit_text(
        "⏰ Установите время:",
        reply_markup=generate_digital_clock(0, 0).as_markup()
    )


@router.callback_query(F.data.regexp(r"^clock:adj:(up|down):(hour|minute)$"), TaskStates.waiting_for_clock)
async def cb_clock_adj(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    parts = callback.data.split(":")
    direction = parts[2]   # up/down
    unit = parts[3]        # hour/minute
    data = await state.get_data()
    cur_hour = int(data.get("clock_hour", 0))
    cur_minute = int(data.get("clock_minute", 0))
    if unit == "hour":
        if direction == "up":
            cur_hour = (cur_hour + 1) % 24
        else:
            cur_hour = (cur_hour - 1) % 24
    else:
        if direction == "up":
            cur_minute = (cur_minute + 1) % 60
        else:
            cur_minute = (cur_minute - 1) % 60
    await state.update_data(clock_hour=cur_hour, clock_minute=cur_minute)
    try:
        await callback.message.edit_text(
            "⏰ Установите время:",
            reply_markup=generate_digital_clock(cur_hour, cur_minute).as_markup()
        )
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise


@router.callback_query(F.data == "clock:confirm", TaskStates.waiting_for_clock)
async def cb_clock_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    data = await state.get_data()
    cal_day = data.get("cal_day")
    cal_month = data.get("cal_month")
    cal_year = data.get("cal_year")
    hour = int(data.get("clock_hour", 0))
    minute = int(data.get("clock_minute", 0))
    if cal_day is None or cal_month is None or cal_year is None:
        now = datetime.now(timezone(timedelta(hours=3)))
        due_time_str = f"{now.strftime('%d.%m.%Y')} {hour:02d}:{minute:02d}"
    else:
        due_time_str = f"{cal_day:02d}.{cal_month:02d}.{cal_year} {hour:02d}:{minute:02d}"
    user_id = callback.from_user.id if callback.from_user else 0
    await show_category_chooser(user_id, due_time_str, state, callback.message)


@router.callback_query(F.data.regexp(r"^hour:(\d{2}:\d{2})$"), TaskStates.waiting_for_hour)
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
        cal_day = data.get("cal_day")
        cal_month = data.get("cal_month")
        cal_year = data.get("cal_year")
        if cal_day is None or cal_month is None or cal_year is None:
            now = datetime.now(timezone(timedelta(hours=3)))
            due_time_str = f"{now.strftime('%d.%m.%Y')} {hour_str}"
        else:
            due_time_str = f"{cal_day:02d}.{cal_month:02d}.{cal_year} {hour_str}"
    await show_category_chooser(user_id, due_time_str, state, callback.message)










async def show_category_chooser(user_id: int, due_time_str: str, state: FSMContext, target_message: Message) -> None:
    categories = await get_user_categories(user_id)
    await state.update_data(final_due_time=str(due_time_str))
    await state.set_state(TaskStates.waiting_for_category)
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.button(text=cat, callback_data=f"cat:choose:{cat}")
    kb.button(text="➕ Создать новую", callback_data="cat:new")
    kb.adjust(2)
    try:
        await target_message.edit_text("📂 Выберите категорию:", reply_markup=kb.as_markup())
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await target_message.answer("Меню категорий уже показано")
        else:
            raise


@router.callback_query(F.data.regexp(r"^cat:choose:(.+)$"))
async def cb_category_choose(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    category = callback.data.split(":", 2)[2]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0
    due_time_str = str(data.get("final_due_time") or "")
    if not due_time_str:
        await callback.message.answer("❌ Ошибка: время не определено. Попробуйте /restart")
        return
    await _finalize_task(user_id, due_time_str, state, callback.message, category=category)


@router.callback_query(F.data == "cat:new")
async def cb_create_new_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    await state.set_state(TaskStates.waiting_for_new_category_name)
    try:
        await callback.message.edit_text("✏️ Введите название новой категории:")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Уже в режиме ввода")
        else:
            raise


@router.message(TaskStates.waiting_for_new_category_name, F.text)
async def process_new_category_name(message: Message, state: FSMContext) -> None:
    category_name = (message.text or "").strip()
    if not category_name:
        await message.answer("Название не может быть пустым. Попробуйте снова:")
        return
    user_id = message.from_user.id if message.from_user else 0
    await add_category(user_id, category_name)
    # получаем время из состояния
    data = await state.get_data()
    due_time_str = str(data.get("final_due_time") or "Не указано")
    # Отправляем новое сообщение, потому что пользовательское нельзя редактировать
    sent_msg = await message.answer("🔄 Обновляем категории...")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await show_category_chooser(user_id, due_time_str, state, sent_msg)


@router.callback_query(F.data.regexp(r"^filter:cat:(.+)$"))
async def cb_filter_category(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    parts = callback.data.split(":", 2)
    cat = parts[2]
    user_id = callback.from_user.id if callback.from_user else 0
    if cat == "ALL":
        filter_cat = "ALL"
    else:
        filter_cat = cat
    await cmd_show_tasks(user_id, callback.message, filter_category=filter_cat)


# =========================================================================
# 4. ПЕРЕЗАПУСК И МЕНЮ
# =========================================================================

@router.callback_query(F.data == "menu:restart")
async def menu_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    
    await state.clear()
    
    await show_main_menu(callback.message)


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery) -> None:
    await callback.answer()


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


@router.callback_query(F.data == "menu:categories")
async def menu_categories(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message): return
    user_id = callback.from_user.id if callback.from_user else 0
    categories = await get_user_categories(user_id)
    kb = InlineKeyboardBuilder()
    for cat in categories:
        kb.button(text=cat, callback_data=f"cat_tasks:{cat}")
    kb.button(text="🏠 Главное меню", callback_data="menu:restart")
    kb.adjust(2)
    try:
        await callback.message.edit_text("📂 Категории:", reply_markup=kb.as_markup())
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer("Меню уже актуально")
        else:
            raise


@router.callback_query(F.data.regexp(r"^cat_tasks:(.+)$"))
async def cb_cat_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    cat = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message, filter_category=cat)


# =========================================================================
# 5. МОИ ЗАДАЧИ И ИСТОРИЯ
# =========================================================================

async def cmd_show_tasks(user_id: int, message: Message, filter_category: str = "ALL") -> None:
    if filter_category == "ALL":
        category_param = None
    else:
        category_param = filter_category
    tasks = await get_user_tasks(user_id, category=category_param)
    categories = await get_user_categories(user_id)
    if not tasks:
        text = "📋 Нет активных задач."
        if filter_category and filter_category != "ALL":
            text = f"📋 Нет активных задач в категории «{filter_category}»."
        await message.answer(
            text,
            reply_markup=get_main_menu_kb().as_markup()
        )
        return
    
    filter_line = f" (фильтр: <b>{filter_category}</b>)" if filter_category and filter_category != "ALL" else ""
    text = f"📋 <b>Ваши задачи:</b>{filter_line}\n\n"
    kb = InlineKeyboardBuilder()
    
    # строка фильтров по категориям
    for cat in categories:
        cat_short = (cat[:15]) if cat else "Без категории"
        kb.button(text=f"📁 {cat_short}", callback_data=f"filter:cat:{cat}")
    kb.button(text="📁 Все", callback_data="filter:cat:ALL")
    kb.adjust(3)
    
    for task in tasks:
        text += f"📌 {task['id']}: {task['title']}\n⏰ {task['due_time']}\n"
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
    task_id = int(callback.data.split(":")[2])
    is_completed = await toggle_task_status(task_id)
    if is_completed:
        remove_reminder(task_id)
        await callback.answer("✅ Выполнена!")
    else:
        await callback.answer("↩️ Возвращена!")
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^tasks:del:(\d+)$"))
async def callback_delete_task_active(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
    task_id = int(callback.data.split(":")[2])
    remove_reminder(task_id)
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message)


async def cmd_show_history(user_id: int, message: Message) -> None:
    tasks = await get_completed_tasks(user_id)
    if not tasks:
        await message.answer(
            "📜 История пуста.",
            reply_markup=get_main_menu_kb().as_markup()
        )
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
    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_history(user_id, callback.message)

@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message): return
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
