# =========================================================================
# handlers.py — Обработчики команд Telegram-бота для планирования задач
# =========================================================================

# === ИМПОРТЫ ===
# Router, F — основа маршрутизации и фильтров aiogram 3
from aiogram import Router, F

# Message, CallbackQuery — типы событий от Telegram
from aiogram.types import Message, CallbackQuery

# Command — фильтр для текстовых команд (/add, /tasks и т.д.)
from aiogram.filters import Command

# FSMContext — контекст конечного автомата состояний (хранит промежуточные данные)
from aiogram.fsm.context import FSMContext

# InlineKeyboardBuilder — конструктор Inline-клавиатур (ПРАВИЛЬНЫЙ путь импорта!)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# Наши модули
from states import TaskStates
from database import add_task, get_user_tasks, delete_task, mark_task_completed
from scheduler import schedule_reminder, remove_reminder

# Создаём роутер на верхнем уровне файла
# (чтобы Pylance не ругался на reportUnusedFunction)
router = Router()


# =========================================================================
# ФУНКЦИЯ ДЛЯ ПОКАЗА ГЛАВНОГО МЕНЮ С КНОПКАМИ
# =========================================================================

def show_main_menu(message: Message) -> None:
    """
    Отправляет пользователю главное меню с Inline-кнопками для основных действий.
    """
    # Создаём билдер клавиатуры
    keyboard = InlineKeyboardBuilder()

    # Добавляем кнопки в столбик
    keyboard.button(text="➕ Добавить задачу", callback_data="menu:add")
    keyboard.button(text="📋 Мои задачи", callback_data="menu:tasks")
    keyboard.button(text="📜 История задач", callback_data="menu:history")
    keyboard.button(text="🔄 Перезапустить", callback_data="menu:restart")

    # Один столбец
    keyboard.adjust(1)

    # Отправляем сообщение с прикреплённой клавиатурой
    message.answer(
        "👋 Привет! Я бот для планирования задач.\n\nВыбери действие из меню ниже:",
        reply_markup=keyboard.as_markup()
    )


# =========================================================================
# КОМАНДА /restart — СБРОС СОСТОЯНИЯ И ВОЗВРАТ В ГЛАВНОЕ МЕНЮ
# =========================================================================

@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext) -> None:
    """
    Полностью сбрасывает состояние FSM пользователя.
    Полезно, если пользователь застрял в процессе ввода задачи
    или хочет начать взаимодействие с ботом заново.
    """
    # Получаем текущее состояние, чтобы понять, был ли пользователь в процессе ввода
    current_state = await state.get_state()

    # Очищаем FSM: удаляем все накопленные данные (title, description) и состояние
    await state.clear()

    # Отправляем главное меню с кнопками
    show_main_menu(message)


# =========================================================================
# КОМАНДА /start — НАЧАЛО РАБОТЫ С БОТОМ
# =========================================================================

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    """
    Приветствует пользователя и отправляет главное меню с кнопками.
    """
    # Отправляем главное меню с кнопками
    show_main_menu(message)


# =========================================================================
# ЭТАП 3: FSM ДЛЯ ПОШАГОВОГО ДОБАВЛЕНИЯ ЗАДАЧ
# =========================================================================

@router.message(Command("add"))
async def cmd_add_task(message: Message, state: FSMContext) -> None:
    """Начинает процесс создания новой задачи. Переводит FSM в ожидание названия."""
    await state.set_state(TaskStates.waiting_for_title)
    await message.answer("📝 Введите название задачи:")


@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    """Сохраняет введённое название в FSM и запрашивает описание."""
    # Безопасное извлечение текста: если message.text вдруг None, используем ""
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")


@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    """Сохраняет введённое описание в FSM и запрашивает время выполнения."""
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_time)
    await message.answer(
        "⏰ Введите время выполнения задачи в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )


@router.message(
    TaskStates.waiting_for_time,
    F.text.regexp(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$")
)
async def process_time_valid(message: Message, state: FSMContext) -> None:
    """
    Обрабатывает корректно введённое время (формат ДД.ММ.ГГГГ ЧЧ:ММ).
    Сохраняет задачу в БД, ставит напоминание в планировщик, очищает FSM.
    """
    # Извлекаем накопленные данные из FSM
    data = await state.get_data()

    # Безопасное извлечение текста времени
    due_time: str = (message.text or "").strip()

    # Безопасное извлечение ID пользователя (защита от None)
    user_id: int = message.from_user.id if message.from_user else 0

    # 1. Сохраняем задачу в базу данных и получаем её ID
    task_id: int = await add_task(
        user_id=user_id,
        title=data.get("title", "Без названия"),
        description=data.get("description", "Без описания"),
        due_time=due_time
    )

    # 2. Ставим напоминание в планировщик
    #    Проверка `if message.bot` защищает от ошибки reportArgumentType,
    #    так как message.bot имеет тип Bot | None
    if message.bot:
        schedule_reminder(
            bot=message.bot,
            user_id=user_id,
            task_id=task_id,
            title=data.get("title", "Без названия"),
            run_time_str=due_time
        )

    # 3. Очищаем состояние FSM — процесс создания завершён
    await state.clear()

    # 4. Подтверждаем пользователю
    await message.answer(
        f"✅ Задача успешно добавлена!\n"
        f"📝 Название: {data.get('title', 'Без названия')}\n"
        f"⏰ Время: {due_time}\n"
        f"🔔 Напоминание установлено!"
    )


@router.message(TaskStates.waiting_for_time, F.text)
async def process_time_invalid(message: Message) -> None:
    """
    Срабатывает, если введённый текст НЕ соответствует формату ДД.ММ.ГГГГ ЧЧ:ММ.
    Не меняет состояние FSM — пользователь остаётся в waiting_for_time.
    """
    await message.answer(
        "❌ Неверный формат времени!\n"
        "Пожалуйста, введите время в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )


# =========================================================================
# ЭТАП 4: ПРОСМОТР ЗАДАЧ С INLINE-КНОПКАМИ
# =========================================================================

@router.message(Command("tasks"))
async def cmd_show_tasks(message: Message) -> None:
    """Показывает список задач пользователя с кнопками управления."""
    # Безопасное получение ID
    user_id: int = message.from_user.id if message.from_user else 0

    # Получаем задачи из БД
    tasks = await get_user_tasks(user_id)

    # Если задач нет — сообщаем и выходим
    if not tasks:
        await message.answer(
            "📋 У вас пока нет задач.\n"
            "Используйте /add, чтобы создать первую!"
        )
        return

    # Формируем текст списка
    tasks_text: str = "📋 <b>Ваши задачи:</b>\n\n"

    # Создаём билдер клавиатуры
    keyboard = InlineKeyboardBuilder()

    for task in tasks:
        # Добавляем информацию о задаче в текст
        tasks_text += (
            f"📌 <b>ID:</b> {task['id']}\n"
            f"📝 {(task['title'] or 'Без названия')}\n"
            f"📄 {(task['description'] or '—')}\n"
            f"⏰ {task['due_time']}\n"
            f"{'✅ Выполнена' if task['is_completed'] else '⏳ Активна'}\n\n"
        )

        # Обрезаем название до 15 символов для аккуратных кнопок
        title_short: str = (task['title'] or "Задача")[:15]

        # Кнопка "Выполнено" с callback_data в формате "done:{id}"
        keyboard.button(
            text=f"✅ {title_short}",
            callback_data=f"done:{task['id']}"
        )
        # Кнопка "Удалить" с callback_data в формате "del:{id}"
        keyboard.button(
            text=f"🗑 {title_short}",
            callback_data=f"del:{task['id']}"
        )

    # Размещаем по 2 кнопки в ряд
    keyboard.adjust(2)

    # Отправляем сообщение с прикреплённой клавиатурой
    await message.answer(tasks_text, reply_markup=keyboard.as_markup(), parse_mode="HTML")


# =========================================================================
# ЭТАП 4: CALLBACK-ОБРАБОТЧИКИ ДЛЯ КНОПОК
# =========================================================================

@router.callback_query(F.callback_data.regexp(r"^done:(\d+)$"))
async def callback_mark_done(callback: CallbackQuery) -> None:
    """Отмечает задачу как выполненную по нажатию кнопки ✅."""
    # 1. Защита: callback.data теоретически может быть None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # 2. Безопасно извлекаем ID задачи из строки "done:123"
    task_id: int = int(callback.data.split(":")[1])

    # 3. Обновляем статус в БД
    await mark_task_completed(task_id)

    # 4. Убираем "часики" у кнопки в Telegram
    await callback.answer("✅ Задача выполнена!")

    # 5. Безопасное удаление сообщения:
    #    isinstance гарантирует Pylance, что у объекта есть метод .delete()
    #    (исключает InaccessibleMessage)
    if callback.message and isinstance(callback.message, Message):
        await callback.message.delete()
        await callback.message.answer(f"✅ Задача #{task_id} отмечена как выполненная!")


@router.callback_query(F.callback_data.regexp(r"^del:(\d+)$"))
async def callback_delete_task(callback: CallbackQuery) -> None:
    """Удаляет задачу и отменяет её напоминание по нажатию кнопки 🗑."""
    # 1. Защита: callback.data теоретически может быть None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # 2. Безопасно извлекаем ID задачи из строки "del:123"
    task_id: int = int(callback.data.split(":")[1])

    # 3. СНАЧАЛА удаляем напоминание из планировщика (Этап 5)
    #    Это нужно сделать ДО удаления из БД, чтобы планировщик не пытался
    #    отправить сообщение по уже несуществующей задаче
    remove_reminder(task_id)

    # 4. ЗАТЕМ удаляем задачу из базы данных
    await delete_task(task_id)

    # 5. Убираем "часики" у кнопки
    await callback.answer("🗑 Задача удалена!")

    # 6. Безопасное удаление сообщения
    if callback.message and isinstance(callback.message, Message):
        await callback.message.delete()
        await callback.message.answer(f"🗑 Задача #{task_id} успешно удалена!")


# =========================================================================
# CALLBACK-ОБРАБОТЧИКИ ДЛЯ КНОПОК ГЛАВНОГО МЕНЮ
# =========================================================================

@router.callback_query(F.callback_data == "menu:add")
async def callback_menu_add(callback: CallbackQuery) -> None:
    """Перенаправляет на FSM для добавления новой задачи."""
    # Защита от None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # Убираем "часики" у кнопки в Telegram
    await callback.answer()

    # Перенаправляем на FSM для добавления задачи
    await cmd_add_task(callback.message, FSMContext())


@router.callback_query(F.callback_data == "menu:tasks")
async def callback_menu_tasks(callback: CallbackQuery) -> None:
    """Показывает список задач пользователя."""
    # Защита от None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # Убираем "часики" у кнопки в Telegram
    await callback.answer()

    # Показываем список задач
    await cmd_show_tasks(callback.message)


@router.callback_query(F.callback_data == "menu:history")
async def callback_menu_history(callback: CallbackQuery) -> None:
    """Заглушка для истории задач."""
    # Защита от None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # Убираем "часики" у кнопки в Telegram
    await callback.answer()

    # Заглушка: отправляем сообщение о том, что эта функция пока не реализована
    await callback.message.answer("🚧 История задач временно недоступна.")


@router.callback_query(F.callback_data == "menu:restart")
async def callback_menu_restart(callback: CallbackQuery) -> None:
    """Сбрасывает состояние FSM и возвращает в главное меню."""
    # Защита от None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return

    # Убираем "часики" у кнопки в Telegram
    await callback.answer()

    # Сбрасываем состояние FSM и отправляем главное меню
    await cmd_restart(callback.message, FSMContext())
