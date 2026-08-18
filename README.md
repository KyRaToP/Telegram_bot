# Telegram Task Planner

Personal Telegram bot for tasks, categories, reminders, and digests. **No website.**

[English](#english) · [Русский](#русский)

---

<a id="english"></a>

## English

### For the customer

#### What is this

A Telegram-only task planner: create tasks, pick date/time with an inline calendar and clock, organize by category, mark done, and receive reminders plus optional daily/weekly digests.

All clocks in this product use **Moscow time (MSK, UTC+3)**. Default scheduler: `Europe/Moscow`.

#### How to use

1. Open the bot → `/start` (or Menu).
2. Create a task: title, description, date/time (**MSK**), category.
3. List, edit, complete, or delete via inline keyboards.
4. Digest: daily **09:00 MSK** or **21:00 MSK**; weekly Monday **09:00 MSK**. Off by default.
5. There is **no web app**.

**Important:** one-shot **reminders** are restored from SQLite on startup for future `due_time` values (**MSK**). Digest cron is registered again on startup. Tasks stay in SQLite.

#### Production URL

| Item | Value |
|------|--------|
| Website | **none** |
| Telegram bot | `[bot username]` |
| Host | `[PC / VPS — to be filled]` |

#### Core functions

- Create / edit / complete / delete tasks
- Inline calendar and clock (**MSK**)
- Categories and filters
- History of completed tasks
- Reminder at due time (**MSK**; restored from SQLite on startup)
- Daily digest **09:00 / 21:00 MSK**; weekly Monday **09:00 MSK**
- SQLite `bot_database.db`
- **Polling**, not webhook

#### Security

The bot is private. Set `ALLOWED_TELEGRAM_IDS` (comma-separated numeric Telegram IDs). An empty list means **nobody** can use the bot. Do not share the token. If it leaks: regenerate in BotFather and restart. Details: [`docs/SECURITY.md`](docs/SECURITY.md).

### For the developer

#### Architecture

```text
Telegram (polling)
 → aiogram 3.30 Dispatcher + FSM
 → aiosqlite (bot_database.db)
 → APScheduler timezone Europe/Moscow
    • date jobs = per-task reminders (restored from SQLite on start)
    • cron = digests (re-registered on start)
```

No REST server, no Mini App. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

#### Tech Stack

| Package | Version | Role |
|---------|---------|------|
| Python | 3.10+ | Runtime |
| aiogram | 3.30.0 | Bot API, FSM, polling |
| aiosqlite | 0.22.1 | Async SQLite |
| APScheduler | 3.11.3 | Reminders and digest cron |
| aiohttp-socks | 0.11.0 | SOCKS proxy |
| python-dotenv | 1.2.2 | Load local environment |

#### Project Structure

```text
bot.py
requirements.txt
bot_database.db          created at runtime
docs/
app/
  db/  handlers/  keyboards/
  middlewares/  services/  states/
README.md
```

#### Installation

```powershell
cd c:\projects\1_Telegram_bot_
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bot.py
```

Set `BOT_TOKEN` and `ALLOWED_TELEGRAM_IDS` first.

#### Environment

| Name | Required | Purpose |
|------|----------|---------|
| `BOT_TOKEN` | yes | Telegram Bot API token |
| `ALLOWED_TELEGRAM_IDS` | yes | Comma-separated numeric IDs; empty = nobody |
| `BOT_PROXY_URL` | no | HTTP/SOCKS proxy if Telegram is blocked |

Timezone is not configurable per user. Always **MSK**.

#### Database

SQLite `bot_database.db`. Tables: `users`, `tasks`, `user_categories`. `due_time` is `dd.mm.yyyy HH:MM` **MSK**. [`docs/DATABASE.md`](docs/DATABASE.md).

#### Testing

`python -m unittest tests.test_security`. Manual: create a task with a near **MSK** time → reminder → digest preview → restart process and confirm a **future** one-shot reminder is restored.

#### Deployment

Keep `bot.py` running (PC or VPS). Polling only — no public HTTPS site. After restart: digest cron and **future** per-task reminders are restored from SQLite. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

#### Security

Token-only secret for Telegram. No public HTTP API. Required allowlist `ALLOWED_TELEGRAM_IDS` (empty = nobody). SQL mutations also check `user_id`. [`docs/SECURITY.md`](docs/SECURITY.md).

### For support

#### Troubleshooting

| Symptom | Checks |
|---------|--------|
| Bot does not start | `BOT_TOKEN` is set |
| Everyone is rejected | `ALLOWED_TELEGRAM_IDS` has your numeric ID |
| Cannot reach Telegram | `BOT_PROXY_URL` or Windows system proxy |
| Reminder missing after reboot | Past `due_time` is skipped; future times should restore |
| Digest silent at **09:00 / 21:00 MSK** | Digest flags; process up; `Europe/Moscow`; user is on allowlist |
| `/restart` did not wipe tasks | FSM only, not SQLite |

Full matrix: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

#### Backup

Copy `bot_database.db` with the bot stopped. Do not commit real user data.

#### Recovery

Restore `bot_database.db`, start `python bot.py`. Future due times are re-scheduled on startup.

#### Maintenance

Process 24/7 for polling and digest cron. One process per SQLite file. After restart, future reminders are restored automatically. [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md).

#### Warranty

**14 days after handover** for delivered bot features (tasks, categories, digest cron, time UI, reminder restore on start). Not covered: Telegram outages, proxy issues, data loss without backup.

#### Security (incidents)

Leaked `BOT_TOKEN`: revoke in BotFather, new env value, restart `bot.py`. Unwanted users: remove their ID from `ALLOWED_TELEGRAM_IDS` and restart. [`docs/SECURITY.md`](docs/SECURITY.md).

---

<a id="русский"></a>

## Русский

### Для заказчика

#### Что это

Планировщик задач только в Telegram: создание задач, дата/время через inline-календарь и часы, категории, выполнение, напоминания и опциональные ежедневные/еженедельные дайджесты.

Все часы в продукте — **московское время (MSK, UTC+3)**. Планировщик по умолчанию: `Europe/Moscow`.

#### Как пользоваться

1. Открыть бота → `/start` (или Menu).
2. Создать задачу: название, описание, дата/время (**MSK**), категория.
3. Список, правка, выполнение, удаление — inline-клавиатуры.
4. Дайджест: ежедневно **09:00 MSK** или **21:00 MSK**; еженедельно понедельник **09:00 MSK**. По умолчанию выключен.
5. **Веб-приложения нет.**

**Важно:** разовые **напоминания** восстанавливаются из SQLite при старте для будущих `due_time` (**MSK**). Cron дайджеста при старте регистрируется снова. Задачи остаются в SQLite.

#### Production URL

| Что | Значение |
|-----|----------|
| Сайт | **нет** |
| Telegram-бот | `[имя бота]` |
| Хост | `[ПК / VPS — указать]` |

#### Основные функции

- Создание / правка / выполнение / удаление задач
- Inline-календарь и часы (**MSK**)
- Категории и фильтры
- История выполненных задач
- Напоминание в срок (**MSK**; восстанавливается из SQLite при старте)
- Ежедневный дайджест **09:00 / 21:00 MSK**; еженедельный понедельник **09:00 MSK**
- SQLite `bot_database.db`
- **Polling**, не webhook

#### Безопасность

Бот приватный. Задайте `ALLOWED_TELEGRAM_IDS` (числовые Telegram ID через запятую). Пустой список = **никто** не получит доступ. Токен не раздавать. Утечка: сменить в BotFather и перезапустить. Подробнее: [`docs/SECURITY.md`](docs/SECURITY.md).

### Для разработчика

#### Architecture

```text
Telegram (polling)
 → aiogram 3.30 Dispatcher + FSM
 → aiosqlite (bot_database.db)
 → APScheduler timezone Europe/Moscow
    • date jobs = напоминания по задачам (восстанавливаются из SQLite при старте)
    • cron = дайджесты (регистрируются при старте)
```

REST-сервера и Mini App нет. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

#### Tech Stack

| Пакет | Версия | Роль |
|-------|--------|------|
| Python | 3.10+ | Runtime |
| aiogram | 3.30.0 | Bot API, FSM, polling |
| aiosqlite | 0.22.1 | Async SQLite |
| APScheduler | 3.11.3 | Напоминания и cron дайджеста |
| aiohttp-socks | 0.11.0 | SOCKS proxy |
| python-dotenv | 1.2.2 | Локальное окружение |

#### Project Structure

```text
bot.py
requirements.txt
bot_database.db          создаётся при запуске
docs/
app/
  db/  handlers/  keyboards/
  middlewares/  services/  states/
README.md
```

#### Installation

```powershell
cd c:\projects\1_Telegram_bot_
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bot.py
```

Сначала задать `BOT_TOKEN` и `ALLOWED_TELEGRAM_IDS`.

#### Environment

| Имя | Обязательно | Назначение |
|-----|-------------|------------|
| `BOT_TOKEN` | да | Токен Telegram Bot API |
| `ALLOWED_TELEGRAM_IDS` | да | Числовые ID через запятую; пусто = никто |
| `BOT_PROXY_URL` | нет | HTTP/SOCKS proxy, если Telegram заблокирован |

Часовой пояс у пользователя не выбирается. Всегда **MSK**.

#### Database

SQLite `bot_database.db`. Таблицы: `users`, `tasks`, `user_categories`. `due_time` — `dd.mm.yyyy HH:MM` **MSK**. [`docs/DATABASE.md`](docs/DATABASE.md).

#### Testing

`python -m unittest tests.test_security`. Вручную: создать задачу со временем **MSK** → напоминание → preview дайджеста → перезапустить процесс и убедиться, что **будущее** разовое напоминание восстановилось.

#### Deployment

Держать `bot.py` запущенным (ПК или VPS). Только polling — публичный HTTPS не нужен. После рестарта: cron дайджеста и **будущие** напоминания по задачам восстанавливаются из SQLite. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

#### Security

Единственный секрет Telegram — токен. Публичного HTTP API нет. Обязательный allowlist `ALLOWED_TELEGRAM_IDS` (пусто = никто). SQL-мутации тоже проверяют `user_id`. [`docs/SECURITY.md`](docs/SECURITY.md).

### Для поддержки

#### Troubleshooting

| Симптом | Проверить |
|---------|-----------|
| Бот не стартует | Задан `BOT_TOKEN` |
| Всех отвергает | В `ALLOWED_TELEGRAM_IDS` есть ваш числовой ID |
| Нет связи с Telegram | `BOT_PROXY_URL` или системный proxy Windows |
| Нет напоминания после reboot | Прошедший `due_time` пропускается; будущие должны восстановиться |
| Дайджест молчит в **09:00 / 21:00 MSK** | Флаги дайджеста; процесс жив; `Europe/Moscow`; пользователь в allowlist |
| `/restart` не стёр задачи | Только FSM, не SQLite |

Полная матрица: [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md).

#### Backup

Копия `bot_database.db` при остановленном боте. Реальные данные пользователей не коммитить.

#### Recovery

Вернуть `bot_database.db`, запустить `python bot.py`. Будущие сроки перепланируются при старте.

#### Maintenance

Процесс 24/7 для polling и cron дайджеста. Один процесс на файл SQLite. После рестарта будущие напоминания восстанавливаются автоматически. [`docs/MAINTENANCE.md`](docs/MAINTENANCE.md).

#### Warranty

**14 дней после передачи** на сданный функционал бота (задачи, категории, cron дайджеста, UI времени, восстановление напоминаний при старте). Не покрывается: сбои Telegram, проблемы proxy, потеря данных без backup.

#### Безопасность (инциденты)

Утечка `BOT_TOKEN`: revoke в BotFather, новое значение в env, рестарт `bot.py`. Нежелательные пользователи: убрать ID из `ALLOWED_TELEGRAM_IDS` и перезапустить. [`docs/SECURITY.md`](docs/SECURITY.md).

---

© All rights reserved.
