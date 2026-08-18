# Database

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Engine

aiosqlite file `bot_database.db` (project root). Created in `init_db()`.

## Tables

| Table | Key | Notes |
|-------|-----|--------|
| `users` | `user_id` (Telegram id) | `username`, `registered_at`; `digest_daily`, `digest_slot` (`morning`/`evening`), `digest_weekly` |
| `tasks` | `id` INTEGER PK | `user_id`, `title`, `description`, `due_time` (`dd.mm.yyyy HH:MM` **MSK**), `is_completed`, `category` |
| `user_categories` | `(user_id, category_name)` | Defaults Работа, Дом, Учеба; plus «Без категории» in UI |

## Isolation

Handlers pass `message.from_user.id`. Lists and mutations use `WHERE user_id = ?`. Middleware also requires `ALLOWED_TELEGRAM_IDS` (empty = nobody). Strangers do not get a user row.

## Reminders vs rows

Task rows survive restart. APScheduler `date` jobs are in RAM, then **restored** from future `due_time` rows on start. Digest settings in `users` survive; cron is re-added on start.

## Backup

Copy `bot_database.db` with the bot stopped. Do not commit real user data.

---

<a id="русский"></a>

## Engine

Файл aiosqlite `bot_database.db` (корень проекта). Создаётся в `init_db()`.

## Tables

| Table | Key | Notes |
|-------|-----|--------|
| `users` | `user_id` (Telegram id) | `username`, `registered_at`; `digest_daily`, `digest_slot` (`morning`/`evening`), `digest_weekly` |
| `tasks` | `id` INTEGER PK | `user_id`, `title`, `description`, `due_time` (`dd.mm.yyyy HH:MM` **MSK**), `is_completed`, `category` |
| `user_categories` | `(user_id, category_name)` | По умолчанию Работа, Дом, Учеба; в UI плюс «Без категории» |

## Isolation

Handlers передают `message.from_user.id`. Списки и мутации — `WHERE user_id = ?`. Middleware также требует `ALLOWED_TELEGRAM_IDS` (пусто = никто). Чужие не получают строку user.

## Reminders vs rows

Строки задач переживают рестарт. Jobs APScheduler `date` живут в RAM и **восстанавливаются** из будущих `due_time` при старте. Настройки дайджеста в `users` сохраняются; cron добавляется при старте.

## Backup

Копировать `bot_database.db` при остановленном боте. Реальные данные пользователей не коммитить.
