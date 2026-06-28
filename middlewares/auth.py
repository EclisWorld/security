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
        
        user = None
        if isinstance(event, (Message, CallbackQuery)):
            user = event.from_user

        if not user:
            return await handler(event, data)

        user_id = user.id
        
        data["is_owner"] = (user_id == Config.OWNER_ID)
        data["is_tenant_owner"] = False
        data["is_bot_admin"] = False
        data["tenant_id"] = None

        # اگر اونر اصلی (تو) بودی، بدون نیاز به لایسنس دسترسی داری
        if data["is_owner"]:
            data["is_tenant_owner"] = True
            async with AsyncSessionLocal() as session:
                tenant_query = await session.execute(select(Tenant).limit(1))
                first_tenant = tenant_query.scalar_one_or_none()
                if first_tenant:
                    data["tenant_id"] = first_tenant.id
                else:
                    # اگر هنوز هیچ تیوتی در دیتابیس نبود، یک آیدی فرضی ۱ بده تا دکمه‌ها کرش نکنند
                    data["tenant_id"] = 1
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            # بررسی وضعیت مشتریان واقعی
            tenant_query = await session.execute(
                select(Tenant).where(Tenant.owner_id == user_id, Tenant.is_active == True)
            )
            tenant = tenant_query.scalar_one_or_none()

            if tenant:
                data["is_tenant_owner"] = True
                data["tenant_id"] = tenant.id
                return await handler(event, data)

            # بررسی وضعیت ادمین‌های فرعی
            admin_query = await session.execute(
                select(BotAdmin).where(BotAdmin.admin_id == user_id)
            )
            bot_admin = admin_query.scalar_one_or_none()

            if bot_admin:
                active_tenant_query = await session.execute(
                    select(Tenant).where(Tenant.id == bot_admin.tenant_id, Tenant.is_active == True)
                )
                active_tenant = active_tenant_query.scalar_one_or_none()
                
                if active_tenant:
                    data["is_bot_admin"] = True
                    data["tenant_id"] = bot_admin.tenant_id

        return await handler(event, data)
