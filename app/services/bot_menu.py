from aiogram import Bot
from aiogram.types import BotCommand, MenuButtonCommands


async def setup_bot_menu(bot: Bot) -> None:
    """
    Enable the native Telegram blue «Menu» button near the input field.

    Note: Telegram always draws the same letter-circle icon for every command
    (from the bot profile). Per-command custom icons are not supported by Bot API.
    We diversify commands with emoji in descriptions instead.
    """
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="🏠 Запуск и главное меню"),
            BotCommand(command="menu", description="📋 Открыть меню"),
            BotCommand(command="tasks", description="✅ Мои задачи"),
            BotCommand(command="clear_tasks", description="🗑 Очистить задачи"),
            BotCommand(command="clear_history", description="🧹 Очистить историю"),
            BotCommand(command="restart", description="🔄 Сбросить состояние"),
        ]
    )
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())
