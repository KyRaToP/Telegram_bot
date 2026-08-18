import logging
from datetime import datetime, timedelta, timezone

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, Message, ReplyKeyboardRemove
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db import (
    add_category,
    add_task,
    clear_active_tasks,
    clear_completed_tasks,
    delete_category,
    delete_task,
    get_completed_tasks,
    get_owned_task,
    get_user_categories,
    get_user_tasks,
    reactivate_task,
    toggle_task_status,
)
from app.keyboards import (
    MENU_BUTTON_TEXT,
    format_categories_menu_text,
    format_history_text,
    format_main_menu_text,
    format_tasks_list_text,
    generate_calendar,
    get_categories_menu_kb,
    get_confirm_kb,
    get_delete_category_kb,
    get_history_list_kb,
    get_main_menu_kb,
    get_tasks_list_kb,
)
from app.handlers.clock_ui import get_clock_values, render_clock, set_clock_values
from app.services import remove_reminder, schedule_reminder
from app.states import CategoryStates, TaskStates

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
                text=(
                    f"Задача добавлена!\n"
                    f"Время: {due_time_str}\n"
                    f"Категория: {category}"
                ),
                reply_markup=get_main_menu_kb().as_markup(),
            )
        except TelegramBadRequest as error:
            if "message is not modified" in str(error):
                await target_message.answer("Задача уже добавлена!")
            else:
                raise

    except Exception as error:
        logger.error(f"Ошибка добавления задачи: {error}")
        await target_message.answer("Ошибка при сохранении. Попробуйте /restart.")
        await state.clear()


async def show_main_menu(message: Message) -> None:
    await message.answer(
        format_main_menu_text(),
        reply_markup=get_main_menu_kb().as_markup(),
        parse_mode="HTML",
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    # Remove old ReplyKeyboard if it was shown earlier; native Menu button stays.
    await message.answer(
        "Используйте синюю кнопку <b>Menu</b> слева от поля ввода.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await show_main_menu(message)


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(message)


@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Состояние сброшено.")
    await show_main_menu(message)


@router.message(Command("tasks"))
async def cmd_tasks(message: Message, state: FSMContext) -> None:
    await state.clear()
    user_id = message.from_user.id if message.from_user else 0
    await cmd_show_tasks(user_id, message)


@router.message(Command("clear_tasks"))
async def cmd_clear_tasks(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Очистить задачи</b>\n\n"
        "Удалить все активные задачи?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_kb("clear:tasks:yes", "clear:tasks:no").as_markup(),
        parse_mode="HTML",
    )


@router.message(Command("clear_history"))
async def cmd_clear_history(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Очистить историю</b>\n\n"
        "Удалить все выполненные задачи из истории?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_kb(
            "clear:history:yes", "clear:history:no"
        ).as_markup(),
        parse_mode="HTML",
    )


@router.message(F.text == MENU_BUTTON_TEXT)
async def reply_menu_button(message: Message, state: FSMContext) -> None:
    """Compatibility for users who still have the old reply keyboard."""
    await state.clear()
    await show_main_menu(message)


@router.callback_query(F.data == "clear:tasks:ask")
async def clear_tasks_ask(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer(
        "<b>Очистить задачи</b>\n\n"
        "Удалить все активные задачи?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_kb("clear:tasks:yes", "clear:tasks:no").as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "clear:history:ask")
async def clear_history_ask(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer(
        "<b>Очистить историю</b>\n\n"
        "Удалить все выполненные задачи из истории?\n"
        "Это действие нельзя отменить.",
        reply_markup=get_confirm_kb(
            "clear:history:yes", "clear:history:no"
        ).as_markup(),
        parse_mode="HTML",
    )


@router.callback_query(F.data == "clear:tasks:yes")
async def clear_tasks_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    deleted_ids = await clear_active_tasks(user_id)
    for task_id in deleted_ids:
        remove_reminder(task_id)
    await callback.message.answer(
        f"Активные задачи удалены: <b>{len(deleted_ids)}</b>",
        parse_mode="HTML",
    )
    await show_main_menu(callback.message)


@router.callback_query(F.data == "clear:tasks:no")
async def clear_tasks_no(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Отменено")
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer("Очистка задач отменена.")
    await show_main_menu(callback.message)


@router.callback_query(F.data == "clear:history:yes")
async def clear_history_yes(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    deleted_count = await clear_completed_tasks(user_id)
    await callback.message.answer(
        f"История очищена. Удалено записей: <b>{deleted_count}</b>",
        parse_mode="HTML",
    )
    await show_main_menu(callback.message)


@router.callback_query(F.data == "clear:history:no")
async def clear_history_no(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer("Отменено")
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    await callback.message.answer("Очистка истории отменена.")
    await show_main_menu(callback.message)


@router.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.answer("📝 Введите название задачи:")


@router.message(TaskStates.waiting_for_title, F.text, ~F.text.in_({MENU_BUTTON_TEXT}))
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("Введите описание задачи:")


@router.message(
    TaskStates.waiting_for_description, F.text, ~F.text.in_({MENU_BUTTON_TEXT})
)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    now = datetime.now(timezone(timedelta(hours=3)))
    await state.update_data(cal_year=now.year, cal_month=now.month)
    await state.set_state(TaskStates.waiting_for_calendar)
    await message.answer(
        "📆 Выберите дату:",
        reply_markup=generate_calendar(now.year, now.month).as_markup(),
    )


@router.callback_query(
    F.data.regexp(r"^cal:(prev|next):(\d{4}):(\d{1,2})$"),
    TaskStates.waiting_for_calendar,
)
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


@router.callback_query(
    F.data.regexp(r"^cal:day:(\d{4}):(\d{1,2}):(\d{1,2})$"),
    TaskStates.waiting_for_calendar,
)
async def cb_select_day(callback: CallbackQuery, state: FSMContext) -> None:
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
    await state.set_state(TaskStates.waiting_for_clock)
    hour, minute = await get_clock_values(state)
    await render_clock(callback.message, hour, minute)


@router.callback_query(
    F.data.regexp(r"^clock:set:hour:(\d{1,2})$"),
    TaskStates.waiting_for_clock,
)
async def cb_clock_set_hour(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    hour = int(callback.data.split(":")[-1])
    _, minute = await get_clock_values(state)
    await set_clock_values(state, hour, minute)
    await render_clock(callback.message, hour % 24, minute)


@router.callback_query(
    F.data.regexp(r"^clock:set:minute:(\d{1,2})$"),
    TaskStates.waiting_for_clock,
)
async def cb_clock_set_minute(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    minute = int(callback.data.split(":")[-1])
    hour, _ = await get_clock_values(state)
    await set_clock_values(state, hour, minute)
    await render_clock(callback.message, hour, minute % 60)


@router.callback_query(
    F.data.regexp(r"^clock:adj:(up|down):minute$"),
    TaskStates.waiting_for_clock,
)
async def cb_clock_adj_minute(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return

    direction = callback.data.split(":")[2]
    hour, minute = await get_clock_values(state)
    minute = (minute + 1) % 60 if direction == "up" else (minute - 1) % 60
    await set_clock_values(state, hour, minute)
    await render_clock(callback.message, hour, minute)


@router.callback_query(F.data == "clock:confirm", TaskStates.waiting_for_clock)
async def cb_clock_confirm(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
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
        due_time_str = (
            f"{cal_day:02d}.{cal_month:02d}.{cal_year} {hour:02d}:{minute:02d}"
        )

    user_id = callback.from_user.id if callback.from_user else 0
    await show_category_chooser(user_id, due_time_str, state, callback.message)


async def show_category_chooser(
    user_id: int, due_time_str: str, state: FSMContext, target_message: Message
) -> None:
    categories = await get_user_categories(user_id)
    await state.update_data(final_due_time=str(due_time_str))
    await state.set_state(TaskStates.waiting_for_category)

    builder = InlineKeyboardBuilder()
    category_buttons = [
        InlineKeyboardButton(text=category, callback_data=f"cat:choose:{category}")
        for category in categories
    ]
    for index in range(0, len(category_buttons), 2):
        builder.row(*category_buttons[index : index + 2])
    builder.row(
        InlineKeyboardButton(text="＋  Создать", callback_data="cat:new")
    )
    try:
        await target_message.edit_text(
            "<b>Категория</b>\nВыберите или создайте новую",
            reply_markup=builder.as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await target_message.answer("Меню категорий уже показано")
        else:
            raise


@router.callback_query(F.data.regexp(r"^cat:choose:(.+)$"), TaskStates.waiting_for_category)
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


@router.callback_query(F.data == "cat:new", TaskStates.waiting_for_category)
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


@router.message(TaskStates.waiting_for_new_category_name, F.text, ~F.text.in_({MENU_BUTTON_TEXT}))
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
async def menu_tasks(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
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
async def menu_categories(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return

    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    categories = await get_user_categories(user_id)
    try:
        await callback.message.edit_text(
            format_categories_menu_text(),
            reply_markup=get_categories_menu_kb(categories).as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await callback.answer("Меню уже актуально")
        else:
            raise


@router.callback_query(F.data == "cat:manage:new")
async def cb_manage_create_category(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.set_state(CategoryStates.waiting_for_new_name)
    await callback.message.edit_text(
        "✏️ Введите название новой категории "
        "(например: Работа, Дом, Учеба):"
    )


@router.message(CategoryStates.waiting_for_new_name, F.text, ~F.text.in_({MENU_BUTTON_TEXT}))
async def process_manage_new_category(message: Message, state: FSMContext) -> None:
    category_name = (message.text or "").strip()
    if not category_name:
        await message.answer("Название не может быть пустым. Попробуйте снова:")
        return

    user_id = message.from_user.id if message.from_user else 0
    await add_category(user_id, category_name)
    await state.clear()
    categories = await get_user_categories(user_id)
    await message.answer(
        f"✅ Категория «{category_name}» создана.",
        reply_markup=get_categories_menu_kb(categories).as_markup(),
    )


@router.callback_query(F.data == "cat:manage:delete")
async def cb_manage_delete_menu(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    user_id = callback.from_user.id if callback.from_user else 0
    categories = await get_user_categories(user_id)
    await callback.message.edit_text(
        "🗑 Выберите категорию для удаления.\n"
        "Задачи из неё перейдут в «Без категории».",
        reply_markup=get_delete_category_kb(categories).as_markup(),
    )


@router.callback_query(F.data.regexp(r"^cat:manage:del:(.+)$"))
async def cb_manage_delete_category(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    category = callback.data.split(":", 3)[3]
    user_id = callback.from_user.id if callback.from_user else 0
    await delete_category(user_id, category)
    categories = await get_user_categories(user_id)
    await callback.message.edit_text(
        f"✅ Категория «{category}» удалена.",
        reply_markup=get_categories_menu_kb(categories).as_markup(),
    )


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

    text = format_tasks_list_text(tasks, filter_category=filter_category)
    keyboard = get_tasks_list_kb(
        tasks, categories, filter_category=filter_category
    )
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.regexp(r"^tasks:toggle:(\d+)$"))
async def callback_toggle_task(callback: CallbackQuery) -> None:
    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id if callback.from_user else 0
    is_completed = await toggle_task_status(task_id, user_id)
    if is_completed is None:
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    if is_completed:
        remove_reminder(task_id)
        await callback.answer("✅ Выполнена!")
    else:
        task = await get_owned_task(task_id, user_id)
        if task and task.get("due_time") and callback.message.bot:
            schedule_reminder(
                bot=callback.message.bot,
                user_id=user_id,
                task_id=task_id,
                title=str(task.get("title") or "Без названия"),
                run_time_str=str(task["due_time"]),
            )
        await callback.answer("↩️ Возвращена!")
    await cmd_show_tasks(user_id, callback.message)


@router.callback_query(F.data.regexp(r"^tasks:del:(\d+)$"))
async def callback_delete_task_active(callback: CallbackQuery) -> None:
    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id if callback.from_user else 0
    deleted = await delete_task(task_id, user_id)
    if not deleted:
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    remove_reminder(task_id)
    await callback.answer("🗑 Удалена!")
    await cmd_show_tasks(user_id, callback.message)


async def cmd_show_history(user_id: int, message: Message) -> None:
    tasks = await get_completed_tasks(user_id)
    text = format_history_text(tasks)
    if not tasks:
        await message.answer(
            text,
            reply_markup=get_main_menu_kb().as_markup(),
            parse_mode="HTML",
        )
        return

    await message.answer(
        text,
        reply_markup=get_history_list_kb(tasks),
        parse_mode="HTML",
    )


@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id if callback.from_user else 0
    restored = await reactivate_task(task_id, user_id)
    if not restored:
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    task = await get_owned_task(task_id, user_id)
    if task and task.get("due_time") and callback.message.bot:
        schedule_reminder(
            bot=callback.message.bot,
            user_id=user_id,
            task_id=task_id,
            title=str(task.get("title") or "Без названия"),
            run_time_str=str(task["due_time"]),
        )
    await callback.answer("↩️ Возвращена!")
    await cmd_show_history(user_id, callback.message)


@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    if not callback.data or not isinstance(callback.message, Message):
        await callback.answer()
        return

    task_id = int(callback.data.split(":")[2])
    user_id = callback.from_user.id if callback.from_user else 0
    deleted = await delete_task(task_id, user_id)
    if not deleted:
        await callback.answer("Нет доступа к этой задаче", show_alert=True)
        return
    remove_reminder(task_id)
    await callback.answer("Удалена")
    await cmd_show_history(user_id, callback.message)
