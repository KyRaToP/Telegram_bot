import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message

from database import init_db
from middlewares import DbMiddleware
from handlers import router as tasks_router  # Импортируем роутер из handlers.py
from scheduler import start_scheduler  # Импортируем функцию для запуска планировщика

logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# ЖЕСТКАЯ загрузка токена (Pylance доволен)
load_dotenv()
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
except KeyError:
    raise ValueError("КРИТИЧЕСКАЯ ОШИБКА: Переменная BOT_TOKEN не найдена в файле .env!")

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    await message.answer("Привет! Я твой планировщик задач. Используй /add, чтобы создать задачу.")

async def main() -> None:
    logger.info("Запуск бота...")
    
    # Инициализируем базу данных
    await init_db()
    
    # Запускаем планировщик напоминаний
    start_scheduler()
    logger.info("✅ Планировщик запущен.")
    
    # Простое создание бота (Karing в TUN-режиме обеспечит маршрутизацию)
    bot = Bot(token=BOT_TOKEN)
    logger.info("✅ Бот инициализирован (используется системный маршрут Karing)")

    dp = Dispatcher()
    dp.update.middleware(DbMiddleware())
    
    # Подключаем роутер из handlers.py
    dp.include_router(tasks_router)
    
    logger.info("🚀 Бот успешно запущен и готов к работе!")
    
    try:
        await dp.start_polling(bot)  # type: ignore
    except Exception as e:
        logger.error(f"Ошибка при запуске polling: {e}")

if __name__ == "__main__":
    asyncio.run(main())
