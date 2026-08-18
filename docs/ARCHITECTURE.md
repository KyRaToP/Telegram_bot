# Architecture

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Overview

Polling Telegram task bot. **No website. No HTTP API.** SQLite via aiosqlite. APScheduler timezone `Europe/Moscow`.

## Components

| Component | Role |
|-----------|------|
| `bot.py` | Entry: `BOT_TOKEN`, allowlist log, proxy session, polling, scheduler start, reminder restore |
| `DbMiddleware` | Reject non-allowlisted users; insert `users` on first allowed update |
| `handlers/tasks.py` | Create, list, complete, clear, categories, calendar/clock |
| `handlers/edit.py` | Edit title / description / time / category |
| `handlers/digest.py` | Daily/weekly toggles, slot, preview |
| `app/db/database.py` | aiosqlite `bot_database.db` |
| `services/scheduler.py` | Cron digests + in-memory reminder jobs |
| `services/network.py` | `BOT_PROXY_URL` then Windows system proxy |

## Data flow

```text
Telegram update (polling)
 → middleware allowlist, then registers user_id
 → handler + aiosqlite (WHERE id = ? AND user_id = ? for mutations)
 → schedule_reminder() in RAM; restore_reminders() on startup
```

Digest cron is re-registered on every `start_scheduler(bot)`: **09:00 MSK**, **21:00 MSK**, Monday **09:00 MSK**.

## Related

[`TELEGRAM.md`](TELEGRAM.md) · [`DATABASE.md`](DATABASE.md) · [`SECURITY.md`](SECURITY.md)

---

<a id="русский"></a>

## Обзор

Polling Telegram-бот задач. **Нет сайта. Нет HTTP API.** SQLite через aiosqlite. APScheduler timezone `Europe/Moscow`.

## Components

| Component | Role |
|-----------|------|
| `bot.py` | Точка входа: `BOT_TOKEN`, лог allowlist, proxy-сессия, polling, старт scheduler, restore напоминаний |
| `DbMiddleware` | Отказ чужим ID; insert в `users` при первом разрешённом update |
| `handlers/tasks.py` | Создание, список, выполнение, очистка, категории, календарь/часы |
| `handlers/edit.py` | Правка названия / описания / времени / категории |
| `handlers/digest.py` | Тумблеры daily/weekly, слот, preview |
| `app/db/database.py` | aiosqlite `bot_database.db` |
| `services/scheduler.py` | Cron дайджестов + in-memory jobs напоминаний |
| `services/network.py` | Сначала `BOT_PROXY_URL`, затем системный proxy Windows |

## Data flow

```text
Telegram update (polling)
 → middleware allowlist, затем регистрирует user_id
 → handler + aiosqlite (мутации: WHERE id = ? AND user_id = ?)
 → schedule_reminder() в RAM; restore_reminders() при старте
```

Cron дайджеста регистрируется при каждом `start_scheduler(bot)`: **09:00 MSK**, **21:00 MSK**, понедельник **09:00 MSK**.

## Related

[`TELEGRAM.md`](TELEGRAM.md) · [`DATABASE.md`](DATABASE.md) · [`SECURITY.md`](SECURITY.md)
