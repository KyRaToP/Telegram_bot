# =========================================================================
# middlewares.py — Middleware для автоматической регистрации пользователей
# =========================================================================

from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
from datetime import datetime

from database import get_user, add_user


class DbMiddleware(BaseMiddleware):
    """
    Middleware, который проверяет наличие пользователя в БД 
    при каждом обновлении и регистрирует его, если его там нет.
    """
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # В aiogram 3 пользователь извлекается ИМЕННО так из словаря data
        # Это официальный способ для версии 3.x
        user: User | None = data.get("event_from_user")
        
        if user:
            # Явное указание типов для Pylance
            user_id: int = user.id
            username: str = user.username or "Unknown"
            registered_at: str = datetime.now().isoformat()
            
            # Проверяем, есть ли пользователь в БД
            db_user = await get_user(user_id)
            if not db_user:
                await add_user(user_id, username, registered_at)
                
        # Продолжаем цепочку обработки
        return await handler(event, data)