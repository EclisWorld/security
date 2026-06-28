from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from sqlalchemy.future import select
from config import Config
from database.connection import AsyncSessionLocal
from database.models import Tenant, BotAdmin

class AuthMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # پیدا کردن اطلاعات کاربر از روی پیام یا کال‌بک کئوری
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if not user:
            return await handler(event, data)

        user_id = user.id
        
        # مقادیر پیش‌فرض نقش‌ها
        data["is_owner"] = (user_id == Config.OWNER_ID)
        data["is_tenant_owner"] = False
        data["is_bot_admin"] = False
        data["tenant_id"] = None

        # اگر اونر اصلی (تو) بود، نیازی به چک کردن بقیه نقش‌ها نیست
        if data["is_owner"]:
            return await handler(event, data)

        # بررسی وضعیت در دیتابیس
        async with AsyncSessionLocal() as session:
            # ۱. بررسی اینکه آیا کاربر خریدار (Tenant Owner) است؟
            tenant_query = await session.execute(
                select(Tenant).where(Tenant.owner_id == user_id, Tenant.is_active == True)
            )
            tenant = tenant_query.scalar_one_or_none()

            if tenant:
                data["is_tenant_owner"] = True
                data["tenant_id"] = tenant.id
                return await handler(event, data)

            # ۲. بررسی اینکه آیا کاربر ادمین فرعی یک مجموعه است؟
            admin_query = await session.execute(
                select(BotAdmin).where(BotAdmin.admin_id == user_id)
            )
            bot_admin = admin_query.scalar_one_or_none()

            if bot_admin:
                # چک کردن اینکه آیا مجموعه این ادمین همچنان فعال است؟
                active_tenant_query = await session.execute(
                    select(Tenant).where(Tenant.id == bot_admin.tenant_id, Tenant.is_active == True)
                )
                active_tenant = active_tenant_query.scalar_one_or_none()
                
                if active_tenant:
                    data["is_bot_admin"] = True
                    data["tenant_id"] = bot_admin.tenant_id

        return await handler(event, data)
