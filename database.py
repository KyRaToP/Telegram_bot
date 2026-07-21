import aiosqlite
import logging
from typing import List, Dict, Optional, Any

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = "bot_database.db"

async def init_db() -> None:
    """Инициализация базы данных и создание таблиц."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                registered_at TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                due_time TEXT,
                is_completed BOOLEAN DEFAULT 0
            )
        """)
        await db.commit()
        logger.info("База данных инициализирована.")

async def add_user(user_id: int, username: str, registered_at: str) -> None:
    """Добавление нового пользователя в БД."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (user_id, username, registered_at) VALUES (?, ?, ?)",
            (user_id, username, registered_at)
        )
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Получение информации о пользователе."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_task(user_id: int, title: str, description: str, due_time: str) -> int:
    """Добавление новой задачи. Возвращает ID созданной задачи."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks (user_id, title, description, due_time, is_completed) VALUES (?, ?, ?, ?, 0)",
            (user_id, title, description, due_time)
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore

async def get_user_tasks(user_id: int) -> List[Dict[str, Any]]:
    """Получение всех задач пользователя."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY due_time ASC", 
            (user_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_task(task_id: int, title: Optional[str] = None, description: Optional[str] = None, due_time: Optional[str] = None) -> None:
    """Обновление данных задачи (передавайте только те поля, которые нужно изменить)."""
    async with aiosqlite.connect(DB_PATH) as db:
        # ВОТ ЗДЕСЬ МЫ ЯВНО УКАЗЫВАЕМ ТИПЫ СПИСКОВ, ЧТОБЫ PYLANCE НЕ РУГАЛСЯ
        updates: List[str] = []
        values: List[Any] = []
        
        if title is not None:
            updates.append("title = ?")
            values.append(title)
        if description is not None:
            updates.append("description = ?")
            values.append(description)
        if due_time is not None:
            updates.append("due_time = ?")
            values.append(due_time)
        
        if updates:
            values.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?"
            await db.execute(query, tuple(values))
            await db.commit()

async def delete_task(task_id: int) -> None:
    """Удаление задачи по ID."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()

async def mark_task_completed(task_id: int) -> None:
    """Отметка задачи как выполненной."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET is_completed = 1 WHERE id = ?", (task_id,))
        await db.commit()