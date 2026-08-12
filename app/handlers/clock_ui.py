"""Shared helpers for the digital clock time picker."""

from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.keyboards import format_clock_text, generate_digital_clock


async def get_clock_values(state: FSMContext) -> tuple[int, int]:
    data = await state.get_data()
    return int(data.get("clock_hour", 0)), int(data.get("clock_minute", 0))


async def set_clock_values(state: FSMContext, hour: int, minute: int) -> None:
    await state.update_data(clock_hour=hour % 24, clock_minute=minute % 60)


async def render_clock(
    message: Message,
    hour: int,
    minute: int,
    *,
    cancel_callback: str = "menu:restart",
) -> None:
    text = format_clock_text(hour, minute)
    markup = generate_digital_clock(
        hour, minute, cancel_callback=cancel_callback
    ).as_markup()
    try:
        await message.edit_text(text, reply_markup=markup, parse_mode="HTML")
    except TelegramBadRequest as error:
        if "message is not modified" not in str(error):
            raise
