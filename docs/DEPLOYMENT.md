# Deployment

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Target

Always-on host (PC or VPS) running:

```powershell
cd c:\projects\1_Telegram_bot_
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bot.py
```

No Docker, no webhook, no web port. Outbound HTTPS to `api.telegram.org` (or `BOT_PROXY_URL`).

## Environment

| Variable | Required |
|----------|----------|
| `BOT_TOKEN` | Yes |
| `ALLOWED_TELEGRAM_IDS` | Yes (empty = nobody) |
| `BOT_PROXY_URL` | No, e.g. `http://127.0.0.1:3067` |

## Process

Keep `bot.py` running for digest cron (**09:00 / 21:00 MSK**). Sleep/shutdown stops reminders and digests. After restart: digests return; **future** one-shot reminders are restored from SQLite.

## Related

[`ARCHITECTURE.md`](ARCHITECTURE.md) · [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)

---

<a id="русский"></a>

## Target

Хост, который не засыпает (ПК или VPS):

```powershell
cd c:\projects\1_Telegram_bot_
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bot.py
```

Нет Docker, webhook и web-порта. Исходящий HTTPS на `api.telegram.org` (или `BOT_PROXY_URL`).

## Environment

| Variable | Required |
|----------|----------|
| `BOT_TOKEN` | Да |
| `ALLOWED_TELEGRAM_IDS` | Да (пусто = никто) |
| `BOT_PROXY_URL` | Нет, например `http://127.0.0.1:3067` |

## Process

Держать `bot.py` запущенным для cron дайджеста (**09:00 / 21:00 MSK**). Сон/выключение останавливает напоминания и дайджесты. После рестарта: дайджесты возвращаются; **будущие** разовые напоминания восстанавливаются из SQLite.

## Related

[`ARCHITECTURE.md`](ARCHITECTURE.md) · [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md)
