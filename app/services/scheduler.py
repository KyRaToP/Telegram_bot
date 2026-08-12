import logging
from datetime import datetime, timedelta

from aiogram import Bot
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # type: ignore

from app.db import (
    get_tasks_for_date,
    get_tasks_for_week,
    get_users_for_daily_digest,
    get_users_for_weekly_digest,
)

logger = logging.getLogger(__name__)

scheduler: AsyncIOScheduler = AsyncIOScheduler(timezone="Europe/Moscow")
DIGEST_MORNING_JOB_ID = "digest_daily_morning"
DIGEST_EVENING_JOB_ID = "digest_daily_evening"
DIGEST_WEEKLY_JOB_ID = "digest_weekly_monday"


def _format_task_line(task: dict) -> str:
    category = task.get("category") or "Без категории"
    return (
        f"• {task.get('title', 'Без названия')} "
        f"({task.get('due_time', 'без времени')}, {category})"
    )


async def build_daily_digest_text(user_id: int, day: datetime | None = None) -> str:
    target_day = day or datetime.now()
    tasks = await get_tasks_for_date(user_id, target_day)
    date_label = target_day.strftime("%d.%m.%Y")
    if not tasks:
        return f"📰 Дайджест на {date_label}\n\nНа сегодня задач нет. Отличный день!"

    lines = [_format_task_line(task) for task in tasks]
    return (
        f"📰 Дайджест на {date_label}\n\n"
        f"У вас {len(tasks)} задач(и) на сегодня:\n"
        + "\n".join(lines)
    )


async def build_weekly_digest_text(user_id: int, week_start: datetime | None = None) -> str:
    start = week_start or datetime.now()
    start = start.replace(hour=0, minute=0, second=0, microsecond=0)
    # Monday of current week
    start = start - timedelta(days=start.weekday())
    tasks = await get_tasks_for_week(user_id, start)
    end = start + timedelta(days=6)
    period = f"{start.strftime('%d.%m.%Y')} — {end.strftime('%d.%m.%Y')}"
    if not tasks:
        return f"🗓 Еженедельный дайджест\n{period}\n\nНа этой неделе активных задач нет."

    lines = [_format_task_line(task) for task in tasks]
    return (
        f"🗓 Еженедельный дайджест\n{period}\n\n"
        f"У вас {len(tasks)} задач(и) на эту неделю:\n"
        + "\n".join(lines)
    )


async def send_reminder(bot: Bot, user_id: int, title: str) -> None:
    await bot.send_message(chat_id=user_id, text=f"⏰ Напоминание: {title}")
    logger.info(f"Отправлено напоминание пользователю {user_id}: {title}")


def schedule_reminder(
    bot: Bot, user_id: int, task_id: int, title: str, run_time_str: str
) -> None:
    try:
        run_time = datetime.strptime(run_time_str, "%d.%m.%Y %H:%M")
        scheduler.add_job(  # type: ignore
            id=str(task_id),
            func=send_reminder,
            trigger="date",
            run_date=run_time,
            args=[bot, user_id, title],
            replace_existing=True,
        )
        logger.info(f"Напоминание запланировано для задачи #{task_id} на {run_time}")
    except ValueError as error:
        logger.error(f"Ошибка парсинга времени: {error}")


def remove_reminder(task_id: int) -> None:
    try:
        scheduler.remove_job(job_id=str(task_id))  # type: ignore
        logger.info(f"Напоминание для задачи #{task_id} удалено")
    except Exception:
        pass


async def send_daily_digest_batch(bot: Bot, slot: str) -> None:
    users = await get_users_for_daily_digest(slot)
    today = datetime.now()
    for user in users:
        user_id = int(user["user_id"])
        try:
            text = await build_daily_digest_text(user_id, today)
            await bot.send_message(chat_id=user_id, text=text)
            logger.info(f"Daily digest ({slot}) sent to {user_id}")
        except Exception as error:
            logger.error(f"Daily digest failed for {user_id}: {error}")


async def send_weekly_digest_batch(bot: Bot) -> None:
    users = await get_users_for_weekly_digest()
    for user in users:
        user_id = int(user["user_id"])
        try:
            text = await build_weekly_digest_text(user_id)
            await bot.send_message(chat_id=user_id, text=text)
            logger.info(f"Weekly digest sent to {user_id}")
        except Exception as error:
            logger.error(f"Weekly digest failed for {user_id}: {error}")


def start_scheduler(bot: Bot | None = None) -> None:
    if not scheduler.running:
        scheduler.start()
        logger.info("✅ Планировщик задач запущен")

    if bot is None:
        return

    scheduler.add_job(  # type: ignore
        id=DIGEST_MORNING_JOB_ID,
        func=send_daily_digest_batch,
        trigger="cron",
        hour=9,
        minute=0,
        args=[bot, "morning"],
        replace_existing=True,
    )
    scheduler.add_job(  # type: ignore
        id=DIGEST_EVENING_JOB_ID,
        func=send_daily_digest_batch,
        trigger="cron",
        hour=21,
        minute=0,
        args=[bot, "evening"],
        replace_existing=True,
    )
    scheduler.add_job(  # type: ignore
        id=DIGEST_WEEKLY_JOB_ID,
        func=send_weekly_digest_batch,
        trigger="cron",
        day_of_week="mon",
        hour=9,
        minute=0,
        args=[bot],
        replace_existing=True,
    )
    logger.info("✅ Digest jobs registered (09:00 / 21:00 / Mon 09:00)")
