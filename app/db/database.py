import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Keep the SQLite file in the project root after moving modules into app/.
DB_PATH = Path(__file__).resolve().parents[2] / "bot_database.db"

DEFAULT_CATEGORIES = ("Работа", "Дом", "Учеба")
DIGEST_MORNING_HOUR = 9
DIGEST_EVENING_HOUR = 21


async def init_db() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "CREATE TABLE IF NOT EXISTS users ("
            "user_id INTEGER PRIMARY KEY, "
            "username TEXT, "
            "registered_at TEXT, "
            "digest_daily INTEGER DEFAULT 0, "
            "digest_slot TEXT DEFAULT 'morning', "
            "digest_weekly INTEGER DEFAULT 0"
            ")"
        )
        await db.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "user_id INTEGER, "
            "title TEXT, "
            "description TEXT, "
            "due_time TEXT, "
            "is_completed INTEGER DEFAULT 0, "
            "category TEXT DEFAULT 'Без категории'"
            ")"
        )
        await db.execute(
            """CREATE TABLE IF NOT EXISTS user_categories (
            user_id INTEGER,
            category_name TEXT,
            PRIMARY KEY (user_id, category_name)
        )"""
        )

        for statement in (
            "ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'Без категории'",
            "ALTER TABLE users ADD COLUMN digest_daily INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN digest_slot TEXT DEFAULT 'morning'",
            "ALTER TABLE users ADD COLUMN digest_weekly INTEGER DEFAULT 0",
        ):
            try:
                await db.execute(statement)
            except Exception:
                pass

        await db.commit()


async def add_user(user_id: int, username: str, registered_at: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users "
            "(user_id, username, registered_at, digest_daily, digest_slot, digest_weekly) "
            "VALUES (?, ?, ?, 0, 'morning', 0)",
            (user_id, username, registered_at),
        )
        await db.commit()

    await ensure_default_categories(user_id)


async def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def add_task(
    user_id: int,
    title: str,
    description: str,
    due_time: str,
    category: str = "Без категории",
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO tasks "
            "(user_id, title, description, due_time, is_completed, category) "
            "VALUES (?, ?, ?, ?, 0, ?)",
            (user_id, title, description, due_time, category),
        )
        await db.commit()
        task_id = cursor.lastrowid
        if task_id is None:
            raise RuntimeError("Не удалось получить ID задачи")
        return task_id


async def get_task(task_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None


async def get_user_tasks(
    user_id: int, category: str | None = None
) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category:
            cursor = await db.execute(
                "SELECT * FROM tasks "
                "WHERE user_id = ? AND is_completed != 1 AND category = ? "
                "ORDER BY due_time ASC",
                (user_id, category),
            )
        else:
            cursor = await db.execute(
                "SELECT * FROM tasks "
                "WHERE user_id = ? AND is_completed != 1 "
                "ORDER BY due_time ASC",
                (user_id,),
            )
        return [dict(row) for row in await cursor.fetchall()]


async def get_completed_tasks(user_id: int) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks "
            "WHERE user_id = ? AND is_completed == 1 "
            "ORDER BY due_time DESC",
            (user_id,),
        )
        return [dict(row) for row in await cursor.fetchall()]


def _parse_due_time(due_time: str) -> Optional[datetime]:
    try:
        return datetime.strptime(due_time, "%d.%m.%Y %H:%M")
    except (TypeError, ValueError):
        return None


async def get_tasks_for_date(user_id: int, day: datetime) -> List[Dict[str, Any]]:
    day_prefix = day.strftime("%d.%m.%Y")
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM tasks "
            "WHERE user_id = ? AND is_completed != 1 AND due_time LIKE ? "
            "ORDER BY due_time ASC",
            (user_id, f"{day_prefix}%"),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_tasks_for_week(user_id: int, week_start: datetime) -> List[Dict[str, Any]]:
    week_end = week_start + timedelta(days=6)
    tasks = await get_user_tasks(user_id)
    result: List[Dict[str, Any]] = []
    for task in tasks:
        due = _parse_due_time(task.get("due_time", ""))
        if due is None:
            continue
        due_date = due.date()
        if week_start.date() <= due_date <= week_end.date():
            result.append(task)
    return result


async def update_task(
    task_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    due_time: str | None = None,
    category: str | None = None,
) -> None:
    fields: list[str] = []
    values: list[Any] = []

    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if description is not None:
        fields.append("description = ?")
        values.append(description)
    if due_time is not None:
        fields.append("due_time = ?")
        values.append(due_time)
    if category is not None:
        fields.append("category = ?")
        values.append(category)

    if not fields:
        return

    values.append(task_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?",
            values,
        )
        await db.commit()


async def reactivate_task(task_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE tasks SET is_completed = 0 WHERE id = ?", (task_id,))
        await db.commit()


async def toggle_task_status(task_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT is_completed FROM tasks WHERE id = ?", (task_id,)
        )
        row = await cursor.fetchone()
        if row:
            new_status = 0 if row[0] else 1
            await db.execute(
                "UPDATE tasks SET is_completed = ? WHERE id = ?",
                (new_status, task_id),
            )
            await db.commit()
            return bool(new_status)
        return False


async def delete_task(task_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        await db.commit()


async def _reset_tasks_sequence(db: aiosqlite.Connection) -> None:
    """
    Keep sqlite_sequence in sync after bulk deletes.

    If tasks table is empty -> seq = 0 (next id starts from 1).
    Otherwise seq = MAX(id) so new ids stay unique.
    """
    cursor = await db.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sqlite_sequence'"
    )
    if await cursor.fetchone() is None:
        return

    cursor = await db.execute("SELECT COUNT(*), IFNULL(MAX(id), 0) FROM tasks")
    row = await cursor.fetchone()
    if row is None:
        return

    count, max_id = int(row[0]), int(row[1])
    new_seq = 0 if count == 0 else max_id
    await db.execute(
        "UPDATE sqlite_sequence SET seq = ? WHERE name = 'tasks'",
        (new_seq,),
    )


async def clear_active_tasks(user_id: int) -> list[int]:
    """Delete incomplete tasks and return their IDs for reminder cleanup."""
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT id FROM tasks WHERE user_id = ? AND is_completed != 1",
            (user_id,),
        )
        task_ids = [int(row["id"]) for row in await cursor.fetchall()]
        await db.execute(
            "DELETE FROM tasks WHERE user_id = ? AND is_completed != 1",
            (user_id,),
        )
        await _reset_tasks_sequence(db)
        await db.commit()
        return task_ids


async def clear_completed_tasks(user_id: int) -> int:
    """Delete completed tasks (history) and return deleted count."""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "DELETE FROM tasks WHERE user_id = ? AND is_completed == 1",
            (user_id,),
        )
        deleted_count = int(cursor.rowcount or 0)
        await _reset_tasks_sequence(db)
        await db.commit()
        return deleted_count


async def ensure_default_categories(user_id: int) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        for category_name in DEFAULT_CATEGORIES:
            await db.execute(
                "INSERT OR IGNORE INTO user_categories (user_id, category_name) "
                "VALUES (?, ?)",
                (user_id, category_name),
            )
        await db.commit()


async def add_category(user_id: int, category_name: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO user_categories (user_id, category_name) "
            "VALUES (?, ?)",
            (user_id, category_name),
        )
        await db.commit()


async def delete_category(user_id: int, category_name: str) -> None:
    if category_name == "Без категории":
        return
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM user_categories WHERE user_id = ? AND category_name = ?",
            (user_id, category_name),
        )
        await db.execute(
            "UPDATE tasks SET category = 'Без категории' "
            "WHERE user_id = ? AND category = ?",
            (user_id, category_name),
        )
        await db.commit()


async def get_user_categories(user_id: int) -> list[str]:
    await ensure_default_categories(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT category_name FROM user_categories WHERE user_id = ? "
            "ORDER BY category_name ASC",
            (user_id,),
        )
        rows = await cursor.fetchall()
        categories = [row["category_name"] for row in rows]
        if "Без категории" not in categories:
            categories.insert(0, "Без категории")
        return categories


async def set_digest_settings(
    user_id: int,
    *,
    digest_daily: int | None = None,
    digest_slot: str | None = None,
    digest_weekly: int | None = None,
) -> None:
    fields: list[str] = []
    values: list[Any] = []

    if digest_daily is not None:
        fields.append("digest_daily = ?")
        values.append(digest_daily)
    if digest_slot is not None:
        fields.append("digest_slot = ?")
        values.append(digest_slot)
    if digest_weekly is not None:
        fields.append("digest_weekly = ?")
        values.append(digest_weekly)

    if not fields:
        return

    values.append(user_id)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            f"UPDATE users SET {', '.join(fields)} WHERE user_id = ?",
            values,
        )
        await db.commit()


async def get_users_for_daily_digest(slot: str) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE digest_daily = 1 AND digest_slot = ?",
            (slot,),
        )
        return [dict(row) for row in await cursor.fetchall()]


async def get_users_for_weekly_digest() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE digest_weekly = 1"
        )
        return [dict(row) for row in await cursor.fetchall()]
