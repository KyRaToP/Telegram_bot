# =========================================================================
# handlers.py — АБСОЛЮТНО ФИНАЛЬНАЯ ВЕРСИЯ (Все 5 ошибок исправлены)
# =========================================================================

import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder

from states import TaskStates
from database import (
    add_task, get_user_tasks, delete_task,
    get_completed_tasks, reactivate_task, toggle_task_status
)
from scheduler import schedule_reminder, remove_reminder

logger = logging.getLogger(__name__)
router = Router()


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

    await message.answer(
        "🤖 <b>Я бот для планирования задач.</b>\n\nВыберите действие:",
        reply_markup=kb.as_markup(),
        parse_mode="HTML"
    )


@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_main_menu(message)


@router.message(Command("restart"))
async def cmd_restart(message: Message, state: FSMContext) -> None:
    # ИСПРАВЛЕНИЕ 1: Удалена неиспользуемая переменная current_state
    await state.clear()
    await message.answer("🔄 Состояние сброшено!")
    await show_main_menu(message)


# =========================================================================
# 2. ОБРАБОТЧИКИ КНОПОК МЕНЮ
# =========================================================================

@router.callback_query(F.data == "menu:add")
async def menu_add(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    # ИСПРАВЛЕНИЕ 2: Строгая проверка типа перед использованием callback.message
    if not isinstance(callback.message, Message):
        return
    
    await state.set_state(TaskStates.waiting_for_title)
    await callback.message.answer("📝 Введите название задачи:")


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


@router.callback_query(F.data == "menu:restart")
async def menu_restart(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    
    # ИСПРАВЛЕНИЕ 3: Используем переданный аргумент state, а не создаем FSMContext()
    await state.clear()
    await callback.message.answer("🔄 Состояние сброшено!")
    await show_main_menu(callback.message)


# =========================================================================
# 3. FSM: ДОБАВЛЕНИЕ ЗАДАЧИ
# =========================================================================

@router.message(TaskStates.waiting_for_title, F.text)
async def process_title(message: Message, state: FSMContext) -> None:
    await state.update_data(title=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_description)
    await message.answer("📄 Введите описание задачи:")


@router.message(TaskStates.waiting_for_description, F.text)
async def process_description(message: Message, state: FSMContext) -> None:
    await state.update_data(description=(message.text or "").strip())
    await state.set_state(TaskStates.waiting_for_time)
    await message.answer("⏰ Введите время (ДД.ММ.ГГГГ ЧЧ:ММ):")


@router.message(TaskStates.waiting_for_time, F.text.regexp(r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}$"))
async def process_time_valid(message: Message, state: FSMContext) -> None:
    try:
        data = await state.get_data()
        due_time = (message.text or "").strip()
        user_id = message.from_user.id if message.from_user else 0
        
        task_id = await add_task(
            user_id=user_id,
            title=data.get("title", "Без названия"),
            description=data.get("description", "Без описания"),
            due_time=due_time
        )
        
        if message.bot:
            schedule_reminder(
                bot=message.bot, user_id=user_id, task_id=task_id,
                title=data.get("title", "Без названия"), run_time_str=due_time
            )
        
        await state.clear()
        await message.answer(f"✅ Задача добавлена!\n⏰ Время: {due_time}")
        await show_main_menu(message)
        
    except Exception as e:
        logger.error(f"Ошибка добавления задачи: {e}")
        await message.answer("❌ Ошибка при сохранении. Попробуйте /restart.")
        await state.clear()


@router.message(TaskStates.waiting_for_time, F.text)
async def process_time_invalid(message: Message) -> None:
    await message.answer("❌ Неверный формат! Пример: 25.12.2024 15:30")


# =========================================================================
# 4. МОИ ЗАДАЧИ
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


@router.callback_query(F.data.regexp(r"^tasks:toggle:(\d+)$"))
async def callback_toggle_task(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
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
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    remove_reminder(task_id)
    await delete_task(task_id)
    
    await callback.answer("🗑 Удалена!")
    await cmd_show_tasks(user_id, callback.message)


# =========================================================================
# 5. ИСТОРИЯ
# =========================================================================

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


@router.callback_query(F.data.regexp(r"^history:reactivate:(\d+)$"))
async def callback_reactivate(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await reactivate_task(task_id)
    await callback.answer("↩️ Возвращена!")
    await cmd_show_history(user_id, callback.message)


@router.callback_query(F.data.regexp(r"^history:del:(\d+)$"))
async def callback_delete_history(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    
    user_id = callback.from_user.id if callback.from_user else 0
    task_id = int(callback.data.split(":")[2])
    await delete_task(task_id)
    await callback.answer("🗑 Удалена!")
    await cmd_show_history(user_id, callback.message)