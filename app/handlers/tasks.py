import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db import (
    add_category,
    add_task,
    delete_task,
    get_completed_tasks,
    get_user_categories,
    get_user_tasks,
    reactivate_task,
    toggle_task_status,
)
from app.keyboards import generate_calendar, generate_digital_clock, get_main_menu_kb
from app.services import remove_reminder, schedule_reminder
from app.states import TaskStates

logger = logging.getLogger(__name__)
router = Router()


async def _finalize_task(
    user_id: int,
    due_time_str: str,
    state: FSMContext,
    target_message: Message,
    category: str = "Без категории",
) -> None:
    try:
        data = await state.get_data()
        task_id = await add_task(
            user_id=user_id,
            title=data.get("title", "Без названия"),
            description=data.get("description", "Без описания"),
            due_time=due_time_str,
            category=category,
        )

        if target_message.bot:
            schedule_reminder(
                bot=target_message.bot,
                user_id=user_id,
                task_id=task_id,
                title=data.get("title", "Без названия"),
                run_time_str=due_time_str,
            )

        await state.clear()

        try:
            await target_message.edit_text(
                text=f"✅ Задача добавлена!\n⏰ Время: {due_time_str}\n🏷 Категория: {category}",
                reply_markup=get_main_menu_kb().as_markup(),
            )
        except TelegramBadRequest as error:
            if "message is not modified" in str(error):
                await target_message.answer("✅ Задача уже добавлена!")
            else:
                raise

    except Exception as error:
        logger.error(f"Ошибка добавления задачи: {error}")
        await target_message.answer("❌ Ошибка при сохранении. Попробуйте /restart.")
        await state.clear()


async def show_main_menu(message: Message) -> None:
    await message.answer(
        "🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
        reply_markup=get_main_menu_kb().as_markup(),
        parse_mode="HTML",
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


@router.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
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
    await message.answer(
        "📆 Выберите дату:",
        reply_markup=generate_calendar(now.year, now.month).as_markup(),
    )


@router.callback_query(F.data == "time:quick:calendar")
async def cb_open_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    now = datetime.now()
    await state.update_data(cal_year=now.year, cal_month=now.month)
    await callback.message.edit_text(
        "📆 Выберите дату:",
        reply_markup=generate_calendar(now.year, now.month).as_markup(),
    )


@router.callback_query(F.data.regexp(r"^cal:(prev|next):(\d{4}):(\d{1,2})$"))
async def cb_navigate_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    parts = callback.data.split(":")
    if len(parts) < 4:
        return

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
    await callback.message.edit_text(
        "📆 Выберите дату:",
        reply_markup=generate_calendar(year, month).as_markup(),
    )


@router.callback_query(F.data.regexp(r"^cal:day:(\d{4}):(\d{1,2}):(\d{1,2})$"))
async def cb_select_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    day_str = callback.data.split(":")[-1]

    await state.update_data(cal_day=int(day_str), clock_hour=0, clock_minute=0)
    await state.set_state(TaskStates.waiting_for_clock)
    await callback.message.edit_text(
        "⏰ Установите время:",
        reply_markup=generate_digital_clock(0, 0).as_markup(),
    )


@router.callback_query(
    F.data.regexp(r"^clock:adj:(up|down):(hour|minute)$"),
    TaskStates.waiting_for_clock,
)
async def cb_clock_adj(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    parts = callback.data.split(":")
    direction = parts[2]
    unit = parts[3]
    data = await state.get_data()
    current_hour = int(data.get("clock_hour", 0))
    current_minute = int(data.get("clock_minute", 0))

    if unit == "hour":
        if direction == "up":
            current_hour = (current_hour + 1) % 24
        else:
            current_hour = (current_hour - 1) % 24
    else:
        if direction == "up":
            current_minute = (current_minute + 1) % 60
        else:
            current_minute = (current_minute - 1) % 60

    await state.update_data(clock_hour=current_hour, clock_minute=current_minute)
    try:
        await callback.message.edit_text(
            "⏰ Установите время:",
            reply_markup=generate_digital_clock(
                current_hour, current_minute
            ).as_markup(),
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await callback.answer()
        else:
            raise


@router.callback_query(F.data == "clock:confirm", TaskStates.waiting_for_clock)
async def cb_clock_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

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
    if not callback.data or not isinstance(callback.message, Message):
        return

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


async def show_category_chooser(
    user_id: int, due_time_str: str, state: FSMContext, target_message: Message
) -> None:
    categories = await get_user_categories(user_id)
    await state.update_data(final_due_time=str(due_time_str))
    await state.set_state(TaskStates.waiting_for_category)
    keyboard = InlineKeyboardBuilder()
    for category in categories:
        keyboard.button(text=category, callback_data=f"cat:choose:{category}")
    keyboard.button(text="➕ Создать новую", callback_data="cat:new")
    keyboard.adjust(2)
    try:
        await target_message.edit_text(
            "📂 Выберите категорию:", reply_markup=keyboard.as_markup()
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await target_message.answer("Меню категорий уже показано")
        else:
            raise


@router.callback_query(F.data.regexp(r"^cat:choose:(.+)$"))
async def cb_category_choose(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    category = callback.data.split(":", 2)[2]
    data = await state.get_data()
    user_id = callback.from_user.id if callback.from_user else 0
    due_time_str = str(data.get("final_due_time") or "")
    if not due_time_str:
        await callback.message.answer(
            "❌ Ошибка: время не определено. Попробуйте /restart"
        )
        return
    await _finalize_task(user_id, due_time_str, state, callback.message, category)


@router.callback_query(F.data == "cat:new")
async def cb_create_new_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await state.set_state(TaskStates.waiting_for_new_category_name)
    try:
        await callback.message.edit_text("✏️ Введите название новой категории:")
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
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
    data = await state.get_data()
    due_time_str = str(data.get("final_due_time") or "Не указано")
    status_message = await message.answer("🔄 Обновляем категории...")
    try:
        await message.delete()
    except TelegramBadRequest:
        pass
    await show_category_chooser(user_id, due_time_str, state, status_message)


@router.callback_query(F.data.regexp(r"^filter:cat:(.+)$"))
async def cb_filter_category(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    category = callback.data.split(":", 2)[2]
    user_id = callback.from_user.id if callback.from_user else 0
    filter_category = "ALL" if category == "ALL" else category
    await cmd_show_tasks(user_id, callback.message, filter_category=filter_category)


@router.callback_query(F.data == "menu:restart")
async def menu_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await state.clear()
    await show_main_menu(callback.message)


@router.callback_query(F.data == "ignore")
async def ignore_callback(callback: CallbackQuery) -> None:
    await callback.answer()


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


@router.callback_query(F.data == "menu:categories")
async def menu_categories(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    user_id = callback.from_user.id if callback.from_user else 0
    categories = await get_user_categories(user_id)
    keyboard = InlineKeyboardBuilder()
    for category in categories:
        keyboard.button(text=category, callback_data=f"cat_tasks:{category}")
    keyboard.button(text="🏠 Главное меню", callback_data="menu:restart")
    keyboard.adjust(2)
    try:
        await callback.message.edit_text(
            "📂 Категории:", reply_markup=keyboard.as_markup()
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await callback.answer("Меню уже актуально")
        else:
            raise


@router.callback_query(F.data.regexp(r"^cat_tasks:(.+)$"))
async def cb_cat_tasks(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    category = callback.data.split(":", 1)[1]
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_tasks(user_id, callback.message, filter_category=category)


async def cmd_show_tasks(
    user_id: int, message: Message, filter_category: str = "ALL"
) -> None:
    category_param = None if filter_category == "ALL" else filter_category
    tasks = await get_user_tasks(user_id, category=category_param)
    categories = await get_user_categories(user_id)

    if not tasks:
        text = "📋 Нет активных задач."
        if filter_category and filter_category != "ALL":
            text = f"📋 Нет активных задач в категории «{filter_category}»."
        await message.answer(text, reply_markup=get_main_menu_kb().as_markup())
        return

    filter_line = (
        f" (фильтр: <b>{filter_category}</b>)"
        if filter_category and filter_category != "ALL"
        else ""
    )
    text = f"📋 <b>Ваши задачи:</b>{filter_line}\n\n"
    keyboard = InlineKeyboardBuilder()

    for category in categories:
        short_name = category[:15] if category else "Без категории"
        keyboard.button(text=f"📁 {short_name}", callback_data=f"filter:cat:{category}")
    keyboard.button(text="📁 Все", callback_data="filter:cat:ALL")
    keyboard.adjust(3)

    for task in tasks:
        text += f"📌 {task['id']}: {task['title']}\n⏰ {task['due_time']}\n"
        title_short = (task["title"] or "Задача")[:10]
        toggle_text = "↩️ В активные" if task["is_completed"] else "✅ Выполнить"
        keyboard.button(text=toggle_text, callback_data=f"tasks:toggle:{task['id']}")
        keyboard.button(text=f"🗑 {title_short}", callback_data=f"tasks:del:{task['id']}")

    keyboard.button(text="🏠 Главное меню", callback_data="menu:restart")
    keyboard.adjust(2)
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^tasks:toggle:(\d+)$"))
async def callback_toggle_task(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

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
    if not callback.data or not isinstance(callback.message, Message):
        return

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
            reply_markup=get_main_menu_kb().as_markup(),
        )
        return

    text = "📜 <b>История:</b>\n\n"
    keyboard = InlineKeyboardBuilder()
    for task in tasks:
        text += f"📌 {task['id']}: {task['title']}\n⏰ {task['due_time']}\n\n"
        title_short = (task["title"] or "Задача")[:10]
        keyboard.button(text="↩️ Вернуть", callback_data=f"history:reactivate:{task['id']}")
        keyboard.button(
            text=f"🗑 {title_short}", callback_data=f"history:del:{task['id']}"
        )
    keyboard.button(text="🏠 Главное меню", callback_data="menu:restart")
    keyboard.adjust(2)
    await message.answer(text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    user_id = callback.from_user.id if callback.from_user else 0
    await cmd_show_history(user_id, callback.message)


@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    task_id = int(callback.data.split(":")[2])
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    try:
        await callback.message.edit_text(
            text="🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await callback.answer("Меню уже актуально")
        else:
            raise
