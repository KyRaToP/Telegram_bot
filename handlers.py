# === ИМПОРТЫ (Bot удален, так как не используется) ===
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardBuilder
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

from states import TaskStates
from database import add_task, get_user_tasks, mark_task_completed, delete_task

# Создаем роутер на верхнем уровне
router = Router()

# 1. Обработчик команды /add
@router.message(Command("add"))
async def cmd_add_task(message: Message, state: FSMContext) -> None:
    await state.set_state(TaskStates.waiting_for_title)
    await message.answer("📝 Введите название задачи:")

# 2. Обработчик ожидания названия
@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    # БЕЗОПАСНОЕ ИЗВЛЕЧЕНИЕ: (message.text or "") гарантирует, что это строка
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")

# 3. Обработчик ожидания описания
@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_time)
    await message.answer(
        "⏰ Введите время выполнения задачи в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )

# 4. Обработчик ожидания времени (ВАЛИДНЫЙ ФОРМАТ)
@router.message(TaskStates.waiting_for_time, F.text.regexp(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$"))
async def process_time_valid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    
    # Безопасное извлечение текста
    due_time = (message.text or "").strip()
    
    # Безопасное извлечение ID пользователя (защита от None)
    user_id = message.from_user.id if message.from_user else 0
    
    # Вызываем функцию добавления задачи (без присваивания неиспользуемой переменной)
    await add_task(
        user_id=user_id,
        title=data.get("title", "Без названия"),
        description=data.get("description", "Без описания"),
        due_time=due_time
    )
    
    await state.clear()
    await message.answer(
        f"✅ Задача успешно добавлена!\n"
        f"📝 Название: {data.get('title')}\n"
        f"⏰ Время: {due_time}"
    )

# 5. Обработчик ожидания времени (НЕВАЛИДНЫЙ ФОРМАТ)
@router.message(TaskStates.waiting_for_time, F.text)
async def process_time_invalid(message: Message) -> None:
    await message.answer(
        "❌ Неверный формат времени!\n"
        "Пожалуйста, введите время в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )

# 6. Обработчик команды /tasks
@router.message(Command("tasks"))
async def cmd_tasks(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else 0
    tasks = await get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("Задач нет.")
        return
    
    text = "Ваши задачи:\n"
    keyboard = InlineKeyboardBuilder()
    
    for task in tasks:
        text += f"ID: {task['id']}\n"
        text += f"Название: {task['title']}\n"
        text += f"Описание: {task['description']}\n"
        text += f"Время выполнения: {task['due_time']}\n\n"
        
        keyboard.button(text="✅", callback_data=f"done:{task['id']}")
        keyboard.button(text="🗑", callback_data=f"del:{task['id']}")
        keyboard.row()
    
    await message.answer(text, reply_markup=keyboard.as_markup())

# 7. Callback-хендлер для "done:"
@router.callback_query(F.data.regexp(r'^done:(\d+)$'))
async def handle_done(callback: CallbackQuery) -> None:
    match = F.data.regexp(r'^done:(\d+)$').match(callback.data)
    if not match:
        await callback.answer("Ошибка в обработке задачи.")
        return
    
    task_id = int(match.group(1))
    await mark_task_completed(task_id)
    await callback.answer("Задача отмечена как выполненная.")
    
    # Удаляем сообщение, если оно существует
    if callback.message:
        await callback.message.delete()

# 8. Callback-хендлер для "del:"
@router.callback_query(F.data.regexp(r'^del:(\d+)$'))
async def handle_delete(callback: CallbackQuery) -> None:
    match = F.data.regexp(r'^del:(\d+)$').match(callback.data)
    if not match:
        await callback.answer("Ошибка в обработке задачи.")
        return
    
    task_id = int(match.group(1))
    await delete_task(task_id)
    await callback.answer("Задача удалена.")
    
    # Удаляем сообщение, если оно существует
    if callback.message:
        await callback.message.delete()
