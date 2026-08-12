import logging

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.db import get_user, set_digest_settings
from app.keyboards import get_digest_settings_kb, get_main_menu_kb
from app.services import build_daily_digest_text, build_weekly_digest_text

logger = logging.getLogger(__name__)
router = Router()


def _digest_help_text(user: dict) -> str:
    daily = "вкл" if user.get("digest_daily") else "выкл"
    weekly = "вкл" if user.get("digest_weekly") else "выкл"
    slot = (
        "утро 09:00"
        if (user.get("digest_slot") or "morning") == "morning"
        else "вечер 21:00"
    )
    return (
        "<b>Дайджест</b>\n\n"
        "Ежедневный — сводка задач на сегодня.\n"
        "Еженедельный — каждый понедельник в 09:00.\n\n"
        f"Ежедневный · <b>{daily}</b>\n"
        f"Слот · <b>{slot}</b>\n"
        f"Еженедельный · <b>{weekly}</b>"
    )


async def _render_digest_menu(message: Message, user_id: int) -> None:
    user = await get_user(user_id)
    if not user:
        await message.answer(
            "❌ Пользователь не найден. Нажмите /start.",
            reply_markup=get_main_menu_kb().as_markup(),
        )
        return

    text = _digest_help_text(user)
    try:
        await message.edit_text(
            text,
            reply_markup=get_digest_settings_kb(user).as_markup(),
            parse_mode="HTML",
        )
    except TelegramBadRequest as error:
        if "message is not modified" in str(error):
            await message.answer(
                text,
                reply_markup=get_digest_settings_kb(user).as_markup(),
                parse_mode="HTML",
            )
        else:
            raise


@router.callback_query(F.data == "menu:digest")
async def menu_digest(callback: CallbackQuery, state: FSMContext) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    await state.clear()
    user_id = callback.from_user.id if callback.from_user else 0
    await _render_digest_menu(callback.message, user_id)


@router.callback_query(F.data == "digest:toggle:daily")
async def digest_toggle_daily(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    user_id = callback.from_user.id if callback.from_user else 0
    user = await get_user(user_id)
    if not user:
        return
    new_value = 0 if user.get("digest_daily") else 1
    await set_digest_settings(user_id, digest_daily=new_value)
    await _render_digest_menu(callback.message, user_id)


@router.callback_query(F.data == "digest:toggle:weekly")
async def digest_toggle_weekly(callback: CallbackQuery) -> None:
    await callback.answer()
    if not isinstance(callback.message, Message):
        return
    user_id = callback.from_user.id if callback.from_user else 0
    user = await get_user(user_id)
    if not user:
        return
    new_value = 0 if user.get("digest_weekly") else 1
    await set_digest_settings(user_id, digest_weekly=new_value)
    await _render_digest_menu(callback.message, user_id)


@router.callback_query(F.data.regexp(r"^digest:slot:(morning|evening)$"))
async def digest_set_slot(callback: CallbackQuery) -> None:
    await callback.answer()
    if not callback.data or not isinstance(callback.message, Message):
        return
    slot = callback.data.split(":")[2]
    user_id = callback.from_user.id if callback.from_user else 0
    await set_digest_settings(user_id, digest_slot=slot)
    await _render_digest_menu(callback.message, user_id)


@router.callback_query(F.data == "digest:preview")
async def digest_preview(callback: CallbackQuery) -> None:
    await callback.answer("Формирую дайджест...")
    if not isinstance(callback.message, Message):
        return
    user_id = callback.from_user.id if callback.from_user else 0
    daily_text = await build_daily_digest_text(user_id)
    weekly_text = await build_weekly_digest_text(user_id)
    await callback.message.answer(daily_text)
    await callback.message.answer(weekly_text)
    await _render_digest_menu(callback.message, user_id)
