from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone="Europe/Moscow")

async def send_reminder(bot: Bot, user_id: int, title: str) -> None:
    await bot.send_message(chat_id=user_id, text=f"⏰ Напоминание: {title}")
    logger.info(f"Отправлено напоминание пользователю {user_id}: {title}")

def schedule_reminder(bot: Bot, user_id: int, task_id: int, title: str, run_time_str: str) -> None:
    try:
        run_time = datetime.strptime(run_time_str, "%d.%m.%Y %H:%M")
        scheduler.add_job(  # type: ignore
            id=str(task_id),
            func=send_reminder,
            trigger='date',
            run_date=run_time,
            args=[bot, user_id, title]
        )
        logger.info(f"Напоминание запланировано для задачи #{task_id} на {run_time}")
    except ValueError as e:
        logger.error(f"Ошибка парсинга времени: {e}")

def start_scheduler() -> None:
    scheduler.start()
    logger.info("✅ Планировщик задач запущен")

def remove_reminder(task_id: int) -> None:
    try:
        scheduler.remove_job(job_id=str(task_id))  # type: ignore
        logger.info(f"Напоминание для задачи #{task_id} удалено")
    except Exception:
        pass
