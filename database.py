import aiosqlite
import logging
from typing import List, Dict, Optional, Any

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
DB_PATH = "bot_database.db"

async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, registered_at TEXT)")
        await db.execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, title TEXT, description TEXT, due_time TEXT, is_completed INTEGER DEFAULT 0)")
        await db.commit()

async def add_user(user_id: int, username: str, registered_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, username, registered_at) VALUES (?, ?, ?)", (user_id, username, registered_at))
        await db.commit()

async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_task(user_id: int, title: str, description: str, due_time: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("INSERT INTO tasks (user_id, title, description, due_time, is_completed) VALUES (?, ?, ?, ?, 0)", (user_id, title, description, due_time))
        await db.commit()
        task_id = cursor.lastrowid
        if task_id is None:
            raise RuntimeError("Не удалось получить ID задачи")
        return task_id

async def get_user_tasks(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE user_id = ? AND is_completed != 1 ORDER BY due_time ASC", (user_id,))
        return [dict(row) for row in await cursor.fetchall()]

# === ЭТИ 3 ФУНКЦИИ ОБЯЗАТЕЛЬНЫ ДЛЯ ИМПОРТА ===
async def get_completed_tasks(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE user_id = ? AND is_completed == 1 ORDER BY due_time DESC", (user_id,))
        return [dict(row) for row in await cursor.fetchall()]

async def reactivate_task(task_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET is_completed = 0 WHERE id = ?", (task_id,))
        await db.commit()

async def toggle_task_status(task_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT is_completed FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        if row:
            new_status = 0 if row[0] else 1
            await db.execute("UPDATE tasks SET is_completed = ? WHERE id = ?", (new_status, task_id))
            await db.commit()
            return bool(new_status)
        return False

async def delete_task(task_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()