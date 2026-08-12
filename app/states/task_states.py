from aiogram.fsm.state import State, StatesGroup


class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_calendar = State()
    waiting_for_hour = State()
    waiting_for_category = State()
    waiting_for_new_category_name = State()
    waiting_for_clock = State()


class EditTaskStates(StatesGroup):
    choosing_field = State()
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_calendar = State()
    waiting_for_clock = State()
    waiting_for_category = State()
    waiting_for_new_category_name = State()


class CategoryStates(StatesGroup):
    waiting_for_new_name = State()
