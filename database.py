import aiosqlite

DATABASE_NAME = 'tasks.db'

async def init_db():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                registered_at TEXT
            )
        ''')
        await db.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                title TEXT,
                description TEXT,
                due_time TEXT,
                is_completed BOOLEAN DEFAULT 0
            )
        ''')
        await db.commit()

async def add_user(user_id, username):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO users (user_id, username, registered_at) VALUES (?, ?, datetime("now"))', (user_id, username))
        await db.commit()

async def get_user(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_task(user_id, title, description, due_time):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('INSERT INTO tasks (user_id, title, description, due_time) VALUES (?, ?, ?, ?)', (user_id, title, description, due_time))
        await db.commit()

async def get_user_tasks(user_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        cursor = await db.execute('SELECT * FROM tasks WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def update_task(task_id, title=None, description=None, due_time=None):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        updates = []
        params = []
        if title is not None:
            updates.append('title = ?')
            params.append(title)
        if description is not None:
            updates.append('description = ?')
            params.append(description)
        if due_time is not None:
            updates.append('due_time = ?')
            params.append(due_time)
        
        if updates:
            set_clause = ', '.join(updates)
            await db.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', params + [task_id])
            await db.commit()

async def delete_task(task_id):
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        await db.commit()
