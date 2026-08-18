import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db import add_category, get_owned_task, get_user_categories, update_task
from app.handlers.clock_ui import get_clock_values, render_clock, set_clock_values
from app.keyboards import (
    MENU_BUTTON_TEXT,
    format_edit_task_text,
    generate_calendar,
    get_edit_task_kb,
)
from app.services import remove_reminder, schedule_reminder
from app.states import EditTaskStates

logger = logging.getLogger(__name__)
router = Router()


async def _show_edit_menu(message: Message, task_id: int, user_id: int) -> None:
    task = await get_owned_task(task_id, user_id)
    if not task:
        await message.answer("Задача не найдена.")
        return

    text = format_edit_task_text(task)
    try:
        await message.edit_text(
            text,
            reply_markup=get_edit_task_kb(task_id).as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest:
        await message.answer(
            text,
            reply_markup=get_edit_task_kb(task_id).as_markup(),
            parse_mode="HTML",
        )


@router.callback_query(F.data.regexp(r"^edit:open:(\d+)$"))
async def cb_edit_open(callback: CallbackQuery, state: FSMContext) -> None:
    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id if callback.from_user else 0
    task = await get_owned_task(task_id, user_id)
    if not task:
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return

    await callback.answer()

    await state.clear()
    await state.set_state(EditTaskStates.choosing_field)
    await state.update_data(edit_task_id=task_id)
    await _show_edit_menu(callback.message, task_id, user_id)


@router.callback_query(F.data.regexp(r"^edit:field:title:(\d+)$"))
async def cb_edit_title(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    task_id = int(callback.data.split(":")[3])
    user_id = callback.from_user.id if callback.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    await state.update_data(edit_task_id=task_id)
    await state.set_state(EditTaskStates.waiting_for_title)
    await callback.message.edit_text("✏️ Введите новое название задачи:")


@router.message(
    EditTaskStates.waiting_for_title, F.text, ~F.text.in_({MENU_BUTTON_TEXT})
)
async def process_edit_title(message: Message, state: FSMContext) -> None:
    title = (message.text or "").strip()
    if not title:
        await message.answer("Название не может быть пустым. Попробуйте снова:")
        return

    data = await state.get_data()
    task_id = int(data.get("edit_task_id", 0))
    user_id = message.from_user.id if message.from_user else 0
    task = await get_owned_task(task_id, user_id)
    if not task:
        await message.answer("❌ Задача не найдена.")
        await state.clear()
        return

    await update_task(task_id, user_id, title=title)
    if message.bot and task.get("due_time"):
        schedule_reminder(
            bot=message.bot,
            user_id=user_id,
            task_id=task_id,
            title=title,
            run_time_str=str(task["due_time"]),
        )

    await state.set_state(EditTaskStates.choosing_field)
    status = await message.answer("✅ Название обновлено.")
    await _show_edit_menu(status, task_id, user_id)


@router.callback_query(F.data.regexp(r"^edit:field:description:(\d+)$"))
async def cb_edit_description(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    task_id = int(callback.data.split(":")[3])
    user_id = callback.from_user.id if callback.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    await state.update_data(edit_task_id=task_id)
    await state.set_state(EditTaskStates.waiting_for_description)
    await callback.message.edit_text("📄 Введите новое описание задачи:")


@router.message(
    EditTaskStates.waiting_for_description, F.text, ~F.text.in_({MENU_BUTTON_TEXT})
)
async def process_edit_description(message: Message, state: FSMContext) -> None:
    description = (message.text or "").strip()
    data = await state.get_data()
    task_id = int(data.get("edit_task_id", 0))
    user_id = message.from_user.id if message.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await message.answer("❌ Задача не найдена.")
        await state.clear()
        return

    await update_task(task_id, user_id, description=description)
    await state.set_state(EditTaskStates.choosing_field)
    status = await message.answer("✅ Описание обновлено.")
    await _show_edit_menu(status, task_id, user_id)


@router.callback_query(F.data.regexp(r"^edit:field:time:(\d+)$"))
async def cb_edit_time(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    task_id = int(callback.data.split(":")[3])
    user_id = callback.from_user.id if callback.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    now = datetime.now(timezone(timedelta(hours=3)))
    await state.update_data(
        edit_task_id=task_id,
        cal_year=now.year,
        cal_month=now.month,
    )
    await state.set_state(EditTaskStates.waiting_for_calendar)
    await callback.message.edit_text(
        "📆 Выберите новую дату:",
        reply_markup=generate_calendar(
            now.year, now.month, cancel_callback="menu:tasks"
        ).as_markup(),
    )


@router.callback_query(
    F.data.regexp(r"^cal:(prev|next):(\d{4}):(\d{1,2})$"),
    EditTaskStates.waiting_for_calendar,
)
async def cb_edit_navigate_calendar(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    parts = callback.data.split(":")
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
        "📆 Выберите новую дату:",
        reply_markup=generate_calendar(
            year, month, cancel_callback="menu:tasks"
        ).as_markup(),
    )


@router.callback_query(
    F.data.regexp(r"^cal:day:(\d{4}):(\d{1,2}):(\d{1,2})$"),
    EditTaskStates.waiting_for_calendar,
)
async def cb_edit_select_day(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    day_str = callback.data.split(":")[-1]
    now = datetime.now(timezone(timedelta(hours=3)))
    await state.update_data(
        cal_day=int(day_str),
        clock_hour=now.hour,
        clock_minute=(now.minute // 5) * 5,
    )
    await state.set_state(EditTaskStates.waiting_for_clock)
    hour, minute = await get_clock_values(state)
    await render_clock(
        callback.message, hour, minute, cancel_callback="menu:tasks"
    )


@router.callback_query(
    F.data.regexp(r"^clock:set:hour:(\d{1,2})$"),
    EditTaskStates.waiting_for_clock,
)
async def cb_edit_clock_set_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    hour = int(callback.data.split(":")[-1])
    _, minute = await get_clock_values(state)
    await set_clock_values(state, hour, minute)
    await render_clock(
        callback.message, hour % 24, minute, cancel_callback="menu:tasks"
    )


@router.callback_query(
    F.data.regexp(r"^clock:set:minute:(\d{1,2})$"),
    EditTaskStates.waiting_for_clock,
)
async def cb_edit_clock_set_minute(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    minute = int(callback.data.split(":")[-1])
    hour, _ = await get_clock_values(state)
    await set_clock_values(state, hour, minute)
    await render_clock(
        callback.message, hour, minute % 60, cancel_callback="menu:tasks"
    )


@router.callback_query(
    F.data.regexp(r"^clock:adj:(up|down):minute$"),
    EditTaskStates.waiting_for_clock,
)
async def cb_edit_clock_adj_minute(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    direction = callback.data.split(":")[2]
    hour, minute = await get_clock_values(state)
    minute = (minute + 1) % 60 if direction == "up" else (minute - 1) % 60
    await set_clock_values(state, hour, minute)
    await render_clock(
        callback.message, hour, minute, cancel_callback="menu:tasks"
    )


@router.callback_query(F.data == "clock:confirm", EditTaskStates.waiting_for_clock)
async def cb_edit_clock_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    data = await state.get_data()
    task_id = int(data.get("edit_task_id", 0))
    user_id = callback.from_user.id if callback.from_user else 0
    task = await get_owned_task(task_id, user_id)
    if not task:
        await callback.message.answer("Задача не найдена.")
        await state.clear()
        return

    cal_day = data.get("cal_day")
    cal_month = data.get("cal_month")
    cal_year = data.get("cal_year")
    hour = int(data.get("clock_hour", 0))
    minute = int(data.get("clock_minute", 0))

    if cal_day is None or cal_month is None or cal_year is None:
        now = datetime.now(timezone(timedelta(hours=3)))
        due_time_str = f"{now.strftime('%d.%m.%Y')} {hour:02d}:{minute:02d}"
    else:
        due_time_str = (
            f"{cal_day:02d}.{cal_month:02d}.{cal_year} {hour:02d}:{minute:02d}"
        )

    await update_task(task_id, user_id, due_time=due_time_str)
    remove_reminder(task_id)
    if callback.message.bot:
        schedule_reminder(
            bot=callback.message.bot,
            user_id=user_id,
            task_id=task_id,
            title=str(task.get("title") or "Без названия"),
            run_time_str=due_time_str,
        )

    await state.set_state(EditTaskStates.choosing_field)
    await callback.message.edit_text(f"Время обновлено: {due_time_str}")
    await _show_edit_menu(callback.message, task_id, user_id)


@router.callback_query(F.data.regexp(r"^edit:field:category:(\d+)$"))
async def cb_edit_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    task_id = int(callback.data.split(":")[3])
    user_id = callback.from_user.id if callback.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    categories = await get_user_categories(user_id)
    await state.update_data(edit_task_id=task_id)
    await state.set_state(EditTaskStates.waiting_for_category)

    builder = InlineKeyboardBuilder()
    category_buttons = [
        InlineKeyboardButton(text=category, callback_data=f"edit:cat:{category}")
        for category in categories
    ]
    for index in range(0, len(category_buttons), 2):
        builder.row(*category_buttons[index : index + 2])
    builder.row(
        InlineKeyboardButton(text="＋  Создать", callback_data="edit:cat:new")
    )
    builder.row(
        InlineKeyboardButton(text="‹  Назад", callback_data=f"edit:open:{task_id}")
    )

    await callback.message.edit_text(
        "<b>Категория</b>\nВыберите новую",
        reply_markup=builder.as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(
    F.data.regexp(r"^edit:cat:(.+)$"), EditTaskStates.waiting_for_category
)
async def cb_edit_category_choose(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    raw = callback.data.split(":", 2)[2]
    data = await state.get_data()
    task_id = int(data.get("edit_task_id", 0))
    user_id = callback.from_user.id if callback.from_user else 0
    if not await get_owned_task(task_id, user_id):
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        await state.clear()
        return

    if raw == "new":
        await state.set_state(EditTaskStates.waiting_for_new_category_name)
        await callback.message.edit_text("✏️ Введите название новой категории:")
        return

    await update_task(task_id, user_id, category=raw)
    await state.set_state(EditTaskStates.choosing_field)
    await callback.message.edit_text(f"✅ Категория обновлена: {raw}")
    await _show_edit_menu(callback.message, task_id, user_id)


@router.message(
    EditTaskStates.waiting_for_new_category_name,
    F.text,
    ~F.text.in_({MENU_BUTTON_TEXT}),
)
async def process_edit_new_category(message: Message, state: FSMContext) -> None:
    category_name = (message.text or "").strip()
    if not category_name:
        await message.answer("Название не может быть пустым. Попробуйте снова:")
        return

    user_id = message.from_user.id if message.from_user else 0
    data = await state.get_data()
    task_id = int(data.get("edit_task_id", 0))
    if not await get_owned_task(task_id, user_id):
        await message.answer("❌ Задача не найдена.")
        await state.clear()
        return

    await add_category(user_id, category_name)
    await update_task(task_id, user_id, category=category_name)
    await state.set_state(EditTaskStates.choosing_field)
    status = await message.answer(f"✅ Категория «{category_name}» сохранена.")
    await _show_edit_menu(status, task_id, user_id)
