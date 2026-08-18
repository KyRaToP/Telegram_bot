# API

**Language:** [English](#english) · [Русский](#русский)

<a id="english"></a>

## HTTP

**None.** This product exposes no REST/FastAPI/webhook URL. The only network API is **Telegram Bot API** used by aiogram polling (`getUpdates`) and `sendMessage`.

## Bot commands (application interface)

| Command | Purpose |
|---------|---------|
| `/start` | Register + main menu |
| `/menu` | Main menu |
| `/tasks` | Active tasks |
| `/clear_tasks` | Confirm-delete active tasks |
| `/clear_history` | Confirm-delete completed tasks |
| `/restart` | Clear FSM, not SQLite |

Inline menus cover create/edit/digest. Due times are `dd.mm.yyyy HH:MM` **MSK**.

Optional `BOT_PROXY_URL` is for the Bot API session only.

---

<a id="русский"></a>

## HTTP

**Нет.** Продукт не отдаёт REST/FastAPI/webhook URL. Единственный сетевой API — **Telegram Bot API**: polling aiogram (`getUpdates`) и `sendMessage`.

## Bot commands (application interface)

| Command | Purpose |
|---------|---------|
| `/start` | Регистрация + главное меню |
| `/menu` | Главное меню |
| `/tasks` | Активные задачи |
| `/clear_tasks` | Подтвердить удаление активных |
| `/clear_history` | Подтвердить удаление выполненных |
| `/restart` | Сброс FSM, не SQLite |

Inline-меню: создание/правка/дайджест. Сроки — `dd.mm.yyyy HH:MM` **MSK**.

Опциональный `BOT_PROXY_URL` только для сессии Bot API.
