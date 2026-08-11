# Telegram Task Bot

Telegram-бот для создания задач, распределения их по категориям и отправки
напоминаний в заданное время.

## Возможности

- создание и удаление задач;
- выбор даты и времени через inline-календарь;
- категории и фильтрация задач;
- отметка задач как выполненных;
- история выполненных задач;
- напоминания через APScheduler;
- хранение данных в SQLite.

## Структура проекта

```text
app/
├── db/             # Работа с SQLite
├── handlers/       # Telegram handlers и callbacks
├── keyboards/      # Inline-клавиатуры
├── middlewares/    # Регистрация пользователей
├── services/       # Планировщик напоминаний
└── states/         # FSM-состояния
bot.py              # Точка входа
requirements.txt    # Прямые Python dependencies
```

## Установка и запуск

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe bot.py
```

Перед запуском должна быть задана переменная окружения `BOT_TOKEN`.
