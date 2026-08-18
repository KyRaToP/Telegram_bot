# Security

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Model

Telegram-only polling bot. No public HTTP surface. `BOT_TOKEN` only in the environment. Optional `BOT_PROXY_URL` is a local proxy URL.

## Controls

| Control | Behavior |
|---------|----------|
| Per-user SQL | `user_id` on tasks, categories, digest settings |
| Allowlist | `ALLOWED_TELEGRAM_IDS` required. Empty = nobody (fail-closed) |
| Owner checks | `toggle` / `delete` / `update` / `reactivate` / edit fields require matching `user_id` |
| FSM `/restart` | Clears conversation state, not other users’ rows |
| Clears | `/clear_tasks` / `/clear_history` require confirm; scoped to caller |
| Reminders | In-memory APScheduler jobs; **future** `due_time` rows are restored on startup (**MSK**) |

## Incidents

| Event | Action |
|-------|--------|
| Leaked `BOT_TOKEN` | Revoke in BotFather; new env value; restart `bot.py` |
| Unwanted users | Remove their numeric ID from `ALLOWED_TELEGRAM_IDS` and restart |
| DB file leaked | Task titles and usernames are personal data; restore backup; rotate token if the host was compromised |

## Warranty

**14 days after handover.**

Operational notes, not legal advice.

---

<a id="русский"></a>

## Model

Только Telegram, polling. Публичной HTTP-поверхности нет. `BOT_TOKEN` только в окружении. Опциональный `BOT_PROXY_URL` — URL локального proxy.

## Controls

| Control | Behavior |
|---------|----------|
| SQL по пользователю | `user_id` у задач, категорий, настроек дайджеста |
| Allowlist | `ALLOWED_TELEGRAM_IDS` обязателен. Пусто = никто (fail-closed) |
| Owner checks | `toggle` / `delete` / `update` / `reactivate` / поля edit требуют совпадающий `user_id` |
| FSM `/restart` | Сбрасывает состояние диалога, не строки других пользователей |
| Очистки | `/clear_tasks` / `/clear_history` с confirm; только вызывающий |
| Напоминания | In-memory jobs APScheduler; **будущие** `due_time` восстанавливаются при старте (**MSK**) |

## Incidents

| Event | Action |
|-------|--------|
| Утечка `BOT_TOKEN` | Revoke в BotFather; новое значение в env; рестарт `bot.py` |
| Нежелательные пользователи | Убрать числовой ID из `ALLOWED_TELEGRAM_IDS` и перезапустить |
| Утечка файла БД | Названия задач и username — персональные данные; restore; ротация токена, если хост скомпрометирован |

## Warranty

**14 дней после передачи.**

Операционные заметки, не юридическая консультация.
