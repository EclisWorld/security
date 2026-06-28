from config import Config
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# ساخت موتور دیتابیس به صورت اسینک
engine = create_async_engine(Config.DATABASE_URL, echo=False, future=True)

# ساخت هماهنگ‌کننده سشن‌ها
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def get_db_session():
    """یک سشن دیتابیس باز می‌کند و پس از اتمام کار، آن را می‌بندد"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """برای ساختن خودکار جدول‌ها در ابتدای کار ربات (در صورت عدم وجود)"""
    from database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
