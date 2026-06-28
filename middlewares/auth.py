from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, User
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
        
        # استخراج مستقیم یوزر از دیتای خود aiogram (بدون درگیری با نوع آپدیت)
        user: User = data.get("event_from_user")

        if not user:
            return await handler(event, data)

        user_id = user.id
        
        data["is_owner"] = (str(user_id) == str(Config.OWNER_ID))
        data["is_tenant_owner"] = False
        data["is_bot_admin"] = False
        data["tenant_id"] = None

        if data["is_owner"]:
            data["is_tenant_owner"] = True
            async with AsyncSessionLocal() as session:
                tenant_query = await session.execute(select(Tenant).limit(1))
                first_tenant = tenant_query.scalar_one_or_none()
                if first_tenant:
                    data["tenant_id"] = first_tenant.id
                else:
                    data["tenant_id"] = 1
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            tenant_query = await session.execute(
                select(Tenant).where(Tenant.owner_id == user_id, Tenant.is_active == True)
            )
            tenant = tenant_query.scalar_one_or_none()

            if tenant:
                data["is_tenant_owner"] = True
                data["tenant_id"] = tenant.id
                return await handler(event, data)

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
