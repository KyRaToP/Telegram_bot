# Troubleshooting

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## Matrix

| Symptom | Checks |
|---------|--------|
| Missing `BOT_TOKEN` | Environment not set |
| `ClientConnectorError` / semaphore timeout | Start proxy (e.g. Karing); `BOT_PROXY_URL=http://127.0.0.1:PORT` |
| Reminder missing after reboot | Past `due_time` is skipped; future times should restore |
| Digest silent **09:00 / 21:00 MSK** | Flags in digest menu; process up; host vs `Europe/Moscow`; user on allowlist |
| `/restart` did not wipe tasks | FSM only |
| Empty list after `/clear_tasks` | Confirmed delete |
| User sees someone else’s tasks | Should not happen; mutations filter `user_id` |
| Everyone is rejected | Set `ALLOWED_TELEGRAM_IDS` |

Do not print token or proxy credential **values**.

---

<a id="русский"></a>

## Matrix

| Symptom | Checks |
|---------|--------|
| Нет `BOT_TOKEN` | Окружение не задано |
| `ClientConnectorError` / semaphore timeout | Поднять proxy (например Karing); `BOT_PROXY_URL=http://127.0.0.1:PORT` |
| Нет напоминания после reboot | Прошедший `due_time` пропускается; будущие должны восстановиться |
| Дайджест молчит **09:00 / 21:00 MSK** | Флаги в меню дайджеста; процесс жив; хост vs `Europe/Moscow`; пользователь в allowlist |
| `/restart` не стёр задачи | Только FSM |
| Пустой список после `/clear_tasks` | Подтверждённое удаление |
| Видны чужие задачи | Не должно быть; мутации фильтруют `user_id` |
| Всех отвергает | Задать `ALLOWED_TELEGRAM_IDS` |

Не печатать **значения** токена или учётных данных proxy.
