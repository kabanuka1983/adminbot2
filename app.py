from aiogram.utils import executor

from loader import bot, scheduler
from utils.database import create_db


async def on_shutdown(dp):
    await bot.close()


async def on_startup(dp):
    await create_db()


if __name__ == '__main__':
    from handlers.group.group_handlers import dp
    from handlers.admin.admin_handlers import dp

    scheduler.start()
    executor.start_polling(dp, on_startup=on_startup, on_shutdown=on_shutdown, skip_updates=True)
