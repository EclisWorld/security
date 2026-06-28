import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import Config
from database.connection import init_db
from middlewares.auth import AuthMiddleware
from handlers import owner, buyer, whitelist, anti_raid

# تنظیمات لاگر برای عیب‌یابی و مانیتورینگ ربات در ترمینال/VPS
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def main():
    # ۱. مقداردهی اولیه ربات و دیسپچر
    bot = Bot(token=Config.BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())

    # ۲. ست کردن و ایجاد جدول‌های دیتابیس در صورت عدم وجود
    logger.info("در حال اتصال و راه‌اندازی دیتابیس...")
    await init_db()
    logger.info("دیتابیس با موفقیت راه‌اندازی شد.")

    # ۳. ثبت کردن Middleware احراز هویت روی دیسپچر
    dp.update.outer_middleware(AuthMiddleware())

    # ۴. اتصال روترها (هندلرها) به دیسپچر اصلی
    # ترتیب قرارگیری مهم است تا دستورات تداخل نداشته باشند
    dp.include_router(owner.router)
    dp.include_router(buyer.router)
    dp.include_router(whitelist.router)
    dp.include_router(anti_raid.router)

    logger.info("روترها و ماژول‌های ربات با موفقیت بارگذاری شدند.")

    # ۵. حذف وب‌هوک‌های قدیمی و استارت زدن پولینگ (Polling) ربات
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("ربات امنیتی با موفقیت روشن شد و در حال گوش دادن به پیام‌هاست...")
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("ربات به صورت دستی خاموش شد.")
