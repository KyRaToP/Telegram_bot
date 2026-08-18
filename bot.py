import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from dotenv import load_dotenv

from app.db import init_db
from app.handlers import router as tasks_router
from app.middlewares import DbMiddleware
from app.services import restore_reminders, start_scheduler
from app.services.access import log_allowlist_status
from app.services.bot_menu import setup_bot_menu
from app.services.network import resolve_telegram_proxy

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


def create_bot() -> Bot:
    """
    Create Bot with proxy-aware aiohttp session.

    Direct connections to api.telegram.org often fail on Windows when Telegram
    is blocked and traffic goes through a local proxy (Karing/Clash).
    urllib may still work via system proxy, but aiohttp needs an explicit proxy.
    """
    proxy = resolve_telegram_proxy()
    if proxy:
        session = AiohttpSession(proxy=proxy, limit=100, timeout=60)
        logger.info("✅ Bot session uses proxy")
        return Bot(token=BOT_TOKEN, session=session)

    session = AiohttpSession(limit=100, timeout=60)
    logger.info("✅ Bot session uses direct connection")
    return Bot(token=BOT_TOKEN, session=session)


async def main() -> None:
    logger.info("Запуск бота...")
    await init_db()
    log_allowlist_status()

    bot = create_bot()
    logger.info("✅ Бот инициализирован")

    await setup_bot_menu(bot)
    logger.info("✅ Синяя кнопка Menu настроена")

    # Pass Bot into scheduler so digest cron jobs can send messages.
    start_scheduler(bot)
    await restore_reminders(bot)
    logger.info("✅ Планировщик, digest jobs и reminders восстановлены.")

    dispatcher = Dispatcher()
    dispatcher.update.middleware(DbMiddleware())
    dispatcher.include_router(tasks_router)

    logger.info("🚀 Бот успешно запущен и готов к работе!")

    try:
        await dispatcher.start_polling(bot)  # type: ignore
    except Exception as error:
        logger.error(f"Ошибка при запуске polling: {error}")
        logger.error(
            "Если видите ClientConnectorError / semaphore timeout: "
            "проверьте, что локальный proxy (Karing) запущен, "
            "или задайте BOT_PROXY_URL=http://127.0.0.1:PORT"
        )
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
