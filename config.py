import os
from dotenv import load_dotenv

# لود کردن فایل .env
load_dotenv()

class Config:
    BOT_TOKEN: str = os.getenv("BOT_TOKEN")
    OWNER_ID: int = int(os.getenv("OWNER_ID", 0))
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    if not BOT_TOKEN:
        raise ValueError("خطا: BOT_TOKEN در فایل .env تعریف نشده است!")
    if not OWNER_ID:
        raise ValueError("خطا: OWNER_ID در فایل .env تعریف نشده است!")
