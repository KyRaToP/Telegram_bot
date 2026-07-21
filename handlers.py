# === ИМПОРТЫ (Bot удален, так как понадобится только на Этапе 5) ===
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import TaskStates
from database import add_task, get_user_tasks, delete_task, mark_task_completed

router = Router()

# =========================================================================
# ЭТАП 3: FSM ДЛЯ ДОБАВЛЕНИЯ ЗАДАЧ
# =========================================================================

@router.message(Command("add"))
async def cmd_add_task(message: Message, state: FSMContext) -> None:
    await state.set_state(TaskStates.waiting_for_title)
    await message.answer("📝 Введите название задачи:")

@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")

@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_time)
    await message.answer(
        "⏰ Введите время выполнения задачи в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )

@router.message(TaskStates.waiting_for_time, F.text.regexp(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$"))
async def process_time_valid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    due_time = (message.text or "").strip()
    user_id = message.from_user.id if message.from_user else 0
    
    # add_task используется здесь, поэтому импорт больше не будет "неиспользуемым"
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

@router.message(TaskStates.waiting_for_time, F.text)
async def process_time_invalid(message: Message) -> None:
    await message.answer(
        "❌ Неверный формат времени!\n"
        "Пожалуйста, введите время в формате ДД.ММ.ГГГГ ЧЧ:ММ\n"
        "Пример: 25.12.2024 15:30"
    )

# =========================================================================
# ЭТАП 4: ПРОСМОТР И УПРАВЛЕНИЕ ЗАДАЧАМИ
# =========================================================================

@router.message(Command("tasks"))
async def cmd_show_tasks(message: Message) -> None:
    """Показывает список задач пользователя с Inline-кнопками."""
    user_id = message.from_user.id if message.from_user else 0
    tasks = await get_user_tasks(user_id)
    
    if not tasks:
        await message.answer("📋 У вас пока нет задач. Используйте /add, чтобы создать первую!")
        return
    
    tasks_text = "📋 Ваши задачи:\n\n"
    keyboard = InlineKeyboardBuilder()
    
    for task in tasks:
        tasks_text += (
            f"📌 ID: {task['id']}\n"
            f"📝 {(task['title'] or 'Без названия')}\n"
            f"⏰ {task['due_time']}\n\n"
        )
        
        title_short = (task['title'] or "Задача")[:15]
        
        keyboard.button(text=f"✅ {title_short}", callback_data=f"done:{task['id']}")
        keyboard.button(text=f"🗑 {title_short}", callback_data=f"del:{task['id']}")
        keyboard.adjust(2)
    
    await message.answer(tasks_text, reply_markup=keyboard.as_markup())


@router.callback_query(F.callback_data.regexp(r'^done:(\d+)$'))
async def callback_mark_done(callback: CallbackQuery) -> None:
    """Отмечает задачу как выполненную."""
    # 1. БЕЗОПАСНАЯ ПРОВЕРКА: защищаемся от callback.data == None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return
        
    task_id = int(callback.data.split(':')[1])
    
    await mark_task_completed(task_id)
    await callback.answer("✅ Задача выполнена!")
    
    # 2. БЕЗОПАСНОЕ УДАЛЕНИЕ: isinstance сужает тип до Message, у которого точно есть .delete()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.delete()
        await callback.message.answer(f"✅ Задача #{task_id} отмечена как выполненная!")


@router.callback_query(F.callback_data.regexp(r'^del:(\d+)$'))
async def callback_delete_task(callback: CallbackQuery) -> None:
    """Удаляет задачу."""
    # 1. БЕЗОПАСНАЯ ПРОВЕРКА: защищаемся от callback.data == None
    if not callback.data:
        await callback.answer("Ошибка: отсутствуют данные", show_alert=True)
        return
        
    task_id = int(callback.data.split(':')[1])
    
    await delete_task(task_id)
    await callback.answer("🗑 Задача удалена!")
    
    # 2. БЕЗОПАСНОЕ УДАЛЕНИЕ
    if callback.message and isinstance(callback.message, Message):
        await callback.message.delete()
        await callback.message.answer(f"🗑 Задача #{task_id} успешно удалена!")