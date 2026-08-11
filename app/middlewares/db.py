from datetime import datetime
from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User

from app.db import add_user, get_user


class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")

        if user:
            user_id: int = user.id
            username: str = user.username or "Unknown"
            registered_at: str = datetime.now().isoformat()

            db_user = await get_user(user_id)
            if not db_user:
                await add_user(user_id, username, registered_at)

        return await handler(event, data)
