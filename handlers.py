from aiogram import Router, Message, FSMContext
from aiogram.filters import Command, Text
from aiogram.fsm.state import State

from states import TaskStates
from database import add_task

router = Router()

@router.message(Command("add"))
async def cmd_add(message: Message, state: FSMContext) -> None:
    """
    Обработчик команды /add. Начинает процесс создания задачи,
    переходя в состояние waiting_for_title.
    """
    await message.answer("Введите название задачи:")
    await state.set_state(TaskStates.waiting_for_title)

@router.message(state=TaskStates.waiting_for_title)
async def handle_waiting_for_title(message: Message, state: FSMContext) -> None:
    """
    Обработчик для состояния waiting_for_title. Сохраняет введенное название задачи
    и переход к следующему состоянию - waiting_for_description.
    """
    title = message.text.strip()
    await state.update_data(title=title)
    await message.answer("Введите описание задачи:")
    await state.set_state(TaskStates.waiting_for_description)

@router.message(state=TaskStates.waiting_for_description)
async def handle_waiting_for_description(message: Message, state: FSMContext) -> None:
    """
    Обработчик для состояния waiting_for_description. Сохраняет введенное описание задачи
    и переход к следующему состоянию - waiting_for_time.
    """
    description = message.text.strip()
    await state.update_data(description=description)
    await message.answer("Введите время выполнения задачи (в формате HH:MM):")
    await state.set_state(TaskStates.waiting_for_time)

@router.message(state=TaskStates.waiting_for_time, Text(regexp=r"^\d{2}:\d{2}$"))
async def handle_waiting_for_time_valid(message: Message, state: FSMContext) -> None:
    """
    Обработчик для состояния waiting_for_time с валидацией формата времени.
    Сохраняет задачу в базе данных и очищает состояние FSM.
    """
    due_time = message.text.strip()
    data = await state.get_data()
    user_id = message.from_user.id
    title = data["title"]
    description = data["description"]

    task_id = await add_task(user_id, title, description, due_time)
    await message.answer(f"Задача успешно создана! ID задачи: {task_id}")
    await state.clear()

@router.message(state=TaskStates.waiting_for_time)
async def handle_waiting_for_time_invalid(message: Message) -> None:
    """
    Обработчик для состояния waiting_for_time без валидации формата времени.
    Просит пользователя ввести время выполнения задачи заново.
    """
    await message.answer("Неверный формат времени. Введите время в формате HH:MM (например, 14:30):")
