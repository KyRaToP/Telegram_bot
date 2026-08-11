import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from app.db import init_db
from app.handlers import router as tasks_router
from app.middlewares import DbMiddleware
from app.services import start_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()
try:
    BOT_TOKEN = os.environ["BOT_TOKEN"]
except KeyError as error:
    raise ValueError(
        "КРИТИЧЕСКАЯ ОШИБКА: Переменная BOT_TOKEN не найдена в файле .env!"
    ) from error


async def main() -> None:
    logger.info("Запуск бота...")
    await init_db()

    start_scheduler()
    logger.info("✅ Планировщик запущен.")

    bot = Bot(token=BOT_TOKEN)
    logger.info("✅ Бот инициализирован")

    dispatcher = Dispatcher()
    dispatcher.update.middleware(DbMiddleware())
    dispatcher.include_router(tasks_router)

    logger.info("🚀 Бот успешно запущен и готов к работе!")

    try:
        await dispatcher.start_polling(bot)  # type: ignore
    except Exception as error:
        logger.error(f"Ошибка при запуске polling: {error}")


if __name__ == "__main__":
    asyncio.run(main())
