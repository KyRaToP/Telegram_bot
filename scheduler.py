from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

# Глобальный планировщик с временной зоной Москва
scheduler = AsyncIOScheduler(timezone="Europe/Moscow")

def schedule_reminder(bot, user_id: int, task_id: int, title: str, run_time_str: str) -> None:
    """
    Парсит время выполнения задачи и добавляет джобу в планировщик.
    
    :param bot: Объект бота для отправки уведомлений
    :param user_id: ID пользователя, которому будет отправлено уведомление
    :param task_id: ID задачи
    :param title: Название задачи
    :param run_time_str: Время выполнения задачи в формате ДД.ММ.ГГГГ ЧЧ:ММ
    """
    try:
        run_time = datetime.strptime(run_time_str, "%d.%m.%Y %H:%M")
        job_id = str(task_id)
        
        # Проверяем, существует ли уже джоба с таким ID
        if scheduler.get_job(job_id):
            scheduler.remove_job(job_id)
        
        # Добавляем новую задачу в планировщик
        scheduler.add_job(
            send_reminder,
            run_date=run_time,
            args=(bot, user_id, task_id, title),
            id=job_id
        )
    except ValueError:
        print(f"Неверный формат времени: {run_time_str}")

async def send_reminder(bot, user_id: int, task_id: int, title: str) -> None:
    """
    Отправляет уведомление пользователю о выполнении задачи.
    
    :param bot: Объект бота для отправки сообщения
    :param user_id: ID пользователя, которому будет отправлено уведомление
    :param task_id: ID задачи
    :param title: Название задачи
    """
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"Напоминание: выполните задачу \"{title}\"!"
        )
    except Exception as e:
        print(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")

def start_scheduler() -> None:
    """
    Запускает планировщик.
    """
    scheduler.start()

def remove_reminder(task_id: int) -> None:
    """
    Удаляет джобу из планировщика по ID задачи.
    
    :param task_id: ID задачи
    """
    job_id = str(task_id)
    try:
        scheduler.remove_job(job_id)
    except Exception as e:
        print(f"Ошибка при удалении джобы {job_id}: {e}")
