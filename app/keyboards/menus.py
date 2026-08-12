import calendar
from datetime import datetime, timedelta
from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
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

CATEGORY_ICONS = {
    "Дом": "🏠",
    "Работа": "💼",
    "Учеба": "🎓",
    "Учёба": "🎓",
    "Без категории": "·",
}

MENU_BUTTON_TEXT = "Меню"


def category_icon(category: str | None) -> str:
    name = category or "Без категории"
    return CATEGORY_ICONS.get(name, "🏷")


def _short_category_label(category: str, *, active: bool = False) -> str:
    labels = {
        "Без категории": "Без кат.",
        "Учеба": "Учёба",
        "Учёба": "Учёба",
    }
    base = labels.get(category, category)
    if len(base) > 12:
        base = base[:11] + "…"
    return f"{base} ✓" if active else base


def _btn(text: str, callback_data: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(text=text, callback_data=callback_data)


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    return [items[index : index + size] for index in range(0, len(items), size)]


def format_tasks_list_text(
    tasks: list[dict[str, Any]], filter_category: str = "ALL"
) -> str:
    filter_label = "Все" if filter_category == "ALL" else filter_category
    header = (
        f"<b>Задачи</b>  ·  {len(tasks)}\n"
        f"Фильтр · <b>{filter_label}</b>\n"
    )
    if not tasks:
        return header + "\nПока пусто. Смените фильтр или добавьте задачу."

    blocks: list[str] = [header]
    for index, task in enumerate(tasks, start=1):
        category = task.get("category") or "Без категории"
        description = (task.get("description") or "").strip()
        due_time = task.get("due_time") or "—"
        title = task.get("title") or "Без названия"
        icon = category_icon(category)

        block = (
            f"<b>{index} · {title}</b>\n"
            f"<code>#{task['id']}</code>  ·  {icon} {category}\n"
            f"{due_time}"
        )
        if description:
            short = description if len(description) <= 90 else description[:87] + "…"
            block += f"\n<i>{short}</i>"
        blocks.append(block)

    return "\n\n".join(blocks)


def get_tasks_list_kb(
    tasks: list[dict[str, Any]],
    categories: list[str],
    filter_category: str = "ALL",
) -> InlineKeyboardMarkup:
    """
    Explicit row layout:
    1) category filters
    2) per-task primary action
    3) per-task secondary actions
    4) navigation
    """
    builder = InlineKeyboardBuilder()

    filter_buttons = [
        _btn(
            _short_category_label(category, active=(filter_category == category)),
            f"filter:cat:{category}",
        )
        for category in categories
    ]
    filter_buttons.append(
        _btn(
            "Все ✓" if filter_category == "ALL" else "Все",
            "filter:cat:ALL",
        )
    )
    for row_buttons in _chunk(filter_buttons, 3):
        builder.row(*row_buttons)

    for index, task in enumerate(tasks, start=1):
        task_id = task["id"]
        if task.get("is_completed"):
            primary = _btn(f"↩  {index} · Вернуть", f"tasks:toggle:{task_id}")
        else:
            primary = _btn(f"✅  {index} · Выполнить", f"tasks:toggle:{task_id}")
        builder.row(primary)
        builder.row(
            _btn("Изменить", f"edit:open:{task_id}"),
            _btn("× Удалить", f"tasks:del:{task_id}"),
        )

    builder.row(_btn("‹  Меню", "menu:restart"))
    return builder.as_markup()


def format_history_text(tasks: list[dict[str, Any]]) -> str:
    header = f"<b>История</b>  ·  {len(tasks)}\n"
    if not tasks:
        return header + "\nВыполненных задач пока нет."

    blocks: list[str] = [header]
    for index, task in enumerate(tasks, start=1):
        category = task.get("category") or "Без категории"
        title = task.get("title") or "Без названия"
        due_time = task.get("due_time") or "—"
        icon = category_icon(category)
        blocks.append(
            f"<b>{index} · {title}</b>\n"
            f"<code>#{task['id']}</code>  ·  {icon} {category}\n"
            f"{due_time}"
        )
    return "\n\n".join(blocks)


def get_history_list_kb(tasks: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for index, task in enumerate(tasks, start=1):
        task_id = task["id"]
        builder.row(
            _btn(f"↩  {index} · Вернуть", f"history:reactivate:{task_id}"),
            _btn("× Удалить", f"history:del:{task_id}"),
        )
    builder.row(_btn("‹  Меню", "menu:restart"))
    return builder.as_markup()


def get_persistent_menu_kb() -> ReplyKeyboardMarkup:
    """Always-visible reply keyboard under the chat input."""
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=MENU_BUTTON_TEXT)]],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Или нажмите «Меню»",
    )


def get_main_menu_kb() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("＋  Новая задача", "menu:add"))
    builder.row(_btn("Задачи", "menu:tasks"), _btn("Категории", "menu:categories"))
    builder.row(_btn("История", "menu:history"), _btn("Дайджест", "menu:digest"))
    builder.row(_btn("Очистить задачи", "clear:tasks:ask"))
    builder.row(_btn("Очистить историю", "clear:history:ask"))
    builder.row(_btn("‹  Сбросить", "menu:restart"))
    return builder


def get_confirm_kb(yes_callback: str, no_callback: str = "menu:restart") -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(_btn("Да", yes_callback), _btn("Нет", no_callback))
    return builder


def generate_calendar(
    year: int, month: int, *, cancel_callback: str = "menu:restart"
) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("‹", f"cal:prev:{year}:{month}"),
        _btn(f"{MONTH_NAMES[month]} {year}", "ignore"),
        _btn("›", f"cal:next:{year}:{month}"),
    )

    weekdays = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    builder.row(*[_btn(weekday, "ignore") for weekday in weekdays])

    for week in calendar.monthcalendar(year, month):
        day_buttons: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                day_buttons.append(_btn(" ", "ignore"))
            else:
                day_buttons.append(
                    _btn(str(day), f"cal:day:{year}:{month}:{day}")
                )
        builder.row(*day_buttons)

    builder.row(_btn("Отмена", cancel_callback))
    return builder


def generate_hour_selector() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    hour_buttons = [
        _btn(f"{hour:02d}:00", f"hour:{hour:02d}:00") for hour in range(24)
    ]
    for row_buttons in _chunk(hour_buttons, 4):
        builder.row(*row_buttons)
    builder.row(_btn("Отмена", "menu:restart"))
    return builder


def format_clock_text(hour: int, minute: int) -> str:
    return (
        f"<b>Время</b>  ·  <code>{hour:02d}:{minute:02d}</code>\n\n"
        "Сначала часы, затем минуты.\n"
        "Для точной минуты используйте −1 / +1."
    )


def generate_digital_clock(
    hour: int, minute: int, *, cancel_callback: str = "menu:restart"
) -> InlineKeyboardBuilder:
    """
    Fast time picker:
    - 24 hour grid (one tap)
    - minute presets every 5 minutes (one tap)
    - fine ±1 minute for exact values
    """
    builder = InlineKeyboardBuilder()

    hour_buttons = [
        _btn(
            f"{value:02d} ✓" if value == hour else f"{value:02d}",
            f"clock:set:hour:{value}",
        )
        for value in range(24)
    ]
    for row_buttons in _chunk(hour_buttons, 4):
        builder.row(*row_buttons)

    minute_presets = list(range(0, 60, 5))
    minute_buttons = [
        _btn(
            f"{value:02d} ✓" if value == minute else f"{value:02d}",
            f"clock:set:minute:{value}",
        )
        for value in minute_presets
    ]
    for row_buttons in _chunk(minute_buttons, 4):
        builder.row(*row_buttons)

    builder.row(
        _btn("−1 мин", "clock:adj:down:minute"),
        _btn("+1 мин", "clock:adj:up:minute"),
    )
    builder.row(_btn("Готово", "clock:confirm"))
    builder.row(_btn("Отмена", cancel_callback))
    return builder


def generate_week_selector(start_date: datetime) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    weekday_abbr = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    day_buttons: list[InlineKeyboardButton] = []
    for index in range(7):
        selected_date = start_date + timedelta(days=index)
        label = f"{weekday_abbr[index]} {selected_date.day}.{selected_date.month}"
        day_buttons.append(
            _btn(
                label,
                (
                    f"week:day:{selected_date.year}:"
                    f"{selected_date.month}:{selected_date.day}"
                ),
            )
        )
    builder.row(*day_buttons)
    builder.row(_btn("Отмена", "menu:restart"))
    return builder


def get_edit_task_kb(task_id: int) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    builder.row(
        _btn("Название", f"edit:field:title:{task_id}"),
        _btn("Описание", f"edit:field:description:{task_id}"),
    )
    builder.row(_btn("Дата и время", f"edit:field:time:{task_id}"))
    builder.row(_btn("Категория", f"edit:field:category:{task_id}"))
    builder.row(_btn("‹  К списку", "menu:tasks"))
    builder.row(_btn("‹  Меню", "menu:restart"))
    return builder


def get_categories_menu_kb(categories: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    category_buttons = [
        _btn(
            f"{category_icon(category)} {_short_category_label(category)}",
            f"cat_tasks:{category}",
        )
        for category in categories
    ]
    for row_buttons in _chunk(category_buttons, 2):
        builder.row(*row_buttons)
    builder.row(_btn("＋  Создать", "cat:manage:new"))
    builder.row(_btn("Удалить категорию", "cat:manage:delete"))
    builder.row(_btn("‹  Меню", "menu:restart"))
    return builder


def get_delete_category_kb(categories: list[str]) -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for category in categories:
        if category == "Без категории":
            continue
        builder.row(
            _btn(
                f"Удалить · {_short_category_label(category)}",
                f"cat:manage:del:{category}",
            )
        )
    builder.row(_btn("‹  Назад", "menu:categories"))
    return builder


def get_digest_settings_kb(user: dict[str, Any]) -> InlineKeyboardBuilder:
    daily_on = bool(user.get("digest_daily"))
    weekly_on = bool(user.get("digest_weekly"))
    slot = user.get("digest_slot") or "morning"

    daily_text = "Ежедневный · вкл" if daily_on else "Ежедневный · выкл"
    weekly_text = "Еженедельный · вкл" if weekly_on else "Еженедельный · выкл"
    morning_text = "Утро 09:00 ✓" if slot == "morning" else "Утро 09:00"
    evening_text = "Вечер 21:00 ✓" if slot == "evening" else "Вечер 21:00"

    builder = InlineKeyboardBuilder()
    builder.row(_btn(daily_text, "digest:toggle:daily"))
    builder.row(_btn(weekly_text, "digest:toggle:weekly"))
    builder.row(
        _btn(morning_text, "digest:slot:morning"),
        _btn(evening_text, "digest:slot:evening"),
    )
    builder.row(_btn("Прислать сейчас", "digest:preview"))
    builder.row(_btn("‹  Меню", "menu:restart"))
    return builder


def format_edit_task_text(task: dict[str, Any]) -> str:
    category = task.get("category") or "Без категории"
    return (
        f"<b>Изменение задачи</b>\n"
        f"<code>#{task.get('id')}</code>\n\n"
        f"<b>{task.get('title') or 'Без названия'}</b>\n"
        f"{category_icon(category)} {category}\n"
        f"{task.get('due_time') or '—'}\n"
        f"<i>{(task.get('description') or 'Без описания')}</i>\n\n"
        "Выберите, что изменить"
    )


def format_main_menu_text() -> str:
    return (
        "<b>Task Planner</b>\n"
        "Планируйте задачи спокойно и по делу.\n\n"
        "Выберите раздел:"
    )


def format_categories_menu_text() -> str:
    return (
        "<b>Категории</b>\n\n"
        "Откройте список задач по категории\n"
        "или создайте новую.\n"
        "Старт: Дом · Работа · Учёба"
    )
