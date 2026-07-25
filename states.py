# states.py
from aiogram.fsm.state import StatesGroup, State

class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_calendar = State()  # Для выбора даты в календаре
    waiting_for_hour = State()      # Для выбора часа