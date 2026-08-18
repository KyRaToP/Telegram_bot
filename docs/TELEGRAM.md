# Telegram

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Mode

Long **polling**. Native Menu button (`MenuButtonCommands`). No Mini App. No webhook.

## Commands (BotFather list)

| Command | Description in code |
|---------|---------------------|
| `/start` | Launch and main menu |
| `/menu` | Open menu |
| `/tasks` | My tasks |
| `/clear_tasks` | Clear active tasks |
| `/clear_history` | Clear history |
| `/restart` | Reset FSM |

## Scheduler (**MSK**, `Europe/Moscow`)

| Job | When |
|-----|------|
| Daily digest `morning` | **09:00 MSK** if `digest_daily=1` and `digest_slot=morning` |
| Daily digest `evening` | **21:00 MSK** if `digest_daily=1` and `digest_slot=evening` |
| Weekly digest | Monday **09:00 MSK** if `digest_weekly=1` |
| Task reminder | `date` trigger at task `due_time`; RAM jobs restored from SQLite on start |

## Access

`ALLOWED_TELEGRAM_IDS` required (empty = nobody). Isolation also = `user_id` on every mutation.

---

<a id="русский"></a>

## Mode

Long **polling**. Нативная кнопка Menu (`MenuButtonCommands`). Нет Mini App. Нет webhook.

## Commands (список BotFather)

| Command | Description in code |
|---------|---------------------|
| `/start` | Запуск и главное меню |
| `/menu` | Открыть меню |
| `/tasks` | Мои задачи |
| `/clear_tasks` | Очистить активные задачи |
| `/clear_history` | Очистить историю |
| `/restart` | Сброс FSM |

## Scheduler (**MSK**, `Europe/Moscow`)

| Job | When |
|-----|------|
| Daily digest `morning` | **09:00 MSK**, если `digest_daily=1` и `digest_slot=morning` |
| Daily digest `evening` | **21:00 MSK**, если `digest_daily=1` и `digest_slot=evening` |
| Weekly digest | Понедельник **09:00 MSK**, если `digest_weekly=1` |
| Напоминание по задаче | Триггер `date` в `due_time`; RAM jobs восстанавливаются из SQLite при старте |

## Access

`ALLOWED_TELEGRAM_IDS` обязателен (пусто = никто). Изоляция также = `user_id` в каждой мутации.
