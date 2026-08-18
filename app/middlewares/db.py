from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, Update, User

from app.db import add_user, get_user
from app.services.access import is_allowed


class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user:
            if not is_allowed(user.id):
                await _reject_stranger(event)
                return None
            user_id: int = user.id
            username: str = user.username or "Unknown"
            registered_at: str = datetime.now().isoformat()

            db_user = await get_user(user_id)
            if not db_user:
                await add_user(user_id, username, registered_at)

        return await handler(event, data)


async def _reject_stranger(event: TelegramObject) -> None:
    text = "Этот бот приватный."
    if isinstance(event, Update):
        if event.message:
            await event.message.answer(text)
        elif event.callback_query:
            await event.callback_query.answer(text, show_alert=True)
        return
    if isinstance(event, Message):
        await event.answer(text)
        return
    if isinstance(event, CallbackQuery):
        await event.answer(text, show_alert=True)
