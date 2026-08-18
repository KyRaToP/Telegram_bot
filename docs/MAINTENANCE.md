# Maintenance

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Routine

| Task | Cadence |
|------|---------|
| Confirm `bot.py` is running | Daily if digests are on |
| Backup `bot_database.db` | Before upgrades |
| After process restart | Future one-shot reminders restore automatically from SQLite |
| Rotate `BOT_TOKEN` | On leak |

## Proxy

If Telegram is blocked: local proxy up, or set `BOT_PROXY_URL`. Restart the bot after changing it.

## Warranty

**14 days after handover.**

---

<a id="русский"></a>

## Routine

| Task | Cadence |
|------|---------|
| Процесс `bot.py` запущен | Ежедневно, если дайджесты включены |
| Backup `bot_database.db` | Перед обновлениями |
| После рестарта процесса | Будущие разовые напоминания восстанавливаются из SQLite автоматически |
| Ротация `BOT_TOKEN` | При утечке |

## Proxy

Если Telegram заблокирован: поднять локальный proxy или задать `BOT_PROXY_URL`. После смены — рестарт бота.

## Warranty

**14 дней после передачи.**
