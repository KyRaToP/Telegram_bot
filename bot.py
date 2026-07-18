import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from middlewares import DbMiddleware
from database import init_db

# Загружаем токен из переменной окружения
API_TOKEN = os.getenv('BOT_TOKEN')

# Создаем экземпляры Bot и Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Подключаем middleware
dp.message.middleware.register(DbMiddleware())

# Простой хендлер на команду /start
@dp.message(Command("start"))
async def command_start(message: Message) -> None:
    await message.answer("Привет! Я твой планировщик задач.")

# Функция main для запуска бота
async def main() -> None:
    # Инициализируем базу данных
    await init_db()
    
    # Запускаем поллинг бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
