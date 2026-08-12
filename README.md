# Telegram Task Bot

Telegram-бот для создания задач, категорий, редактирования и дайджестов.

## Возможности

- создание, выполнение и удаление задач;
- редактирование названия, описания, времени и категории;
- выбор даты и времени через inline-календарь;
- категории (Работа, Дом, Учеба + свои) и фильтрация;
- история выполненных задач;
- напоминания через APScheduler;
- ежедневный и еженедельный дайджест;
- хранение данных в SQLite.

## Структура проекта

```text
app/
├── db/             # Работа с SQLite
├── handlers/       # Telegram handlers (tasks / edit / digest)
├── keyboards/      # Inline-клавиатуры
├── middlewares/    # Регистрация пользователей
├── services/       # Планировщик напоминаний и дайджестов
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

Если Telegram API недоступен напрямую, бот автоматически использует
включённый Windows system proxy (например Karing на `127.0.0.1:3067`).
Можно задать proxy явно:

```text
BOT_PROXY_URL=http://127.0.0.1:3067
```

## Дайджест

- Ежедневный: 09:00 или 21:00 (Europe/Moscow)
- Еженедельный: каждый понедельник в 09:00
- Настройки: кнопка «📰 Дайджест» в главном меню
