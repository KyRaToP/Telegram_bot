from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Any, Awaitable
import os
from datetime import datetime
from database import get_user, add_user

class DbMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Проверяем наличие user.id через get_user
        user_id = event.from_user.id
        user = await get_user(user_id)
        
        if not user:
            # Если пользователя нет в базе данных, добавляем его с текущим временем
            registered_at = datetime.now().isoformat()
            await add_user(user_id, event.from_user.username, registered_at)
        
        # Обязательно вызываем следующий обработчик
        return await handler(event, data)
