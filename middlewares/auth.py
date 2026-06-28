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
        
        # مقداردهی اولیه به صورت پیش‌فرض
        data["is_owner"] = (user_id == Config.OWNER_ID)
        data["is_tenant_owner"] = False
        data["is_bot_admin"] = False
        data["tenant_id"] = None

        # اگر اونر اصلی (تو) بودی، دسترسی‌های خریدار هم بهت داده بشه تا بتونی پنل رو باز و تست کنی
        if data["is_owner"]:
            data["is_tenant_owner"] = True
            # پیدا کردن اولین خریدار برای تست یا ست کردن صفر برای ادمین کل
            async with AsyncSessionLocal() as session:
                tenant_query = await session.execute(select(Tenant).limit(1))
                first_tenant = tenant_query.scalar_one_or_none()
                if first_tenant:
                    data["tenant_id"] = first_tenant.id
            return await handler(event, data)

        async with AsyncSessionLocal() as session:
            # بررسی وضعیت خریدار اصلی
            tenant_query = await session.execute(
                select(Tenant).where(Tenant.owner_id == user_id, Tenant.is_active == True)
            )
            tenant = tenant_query.scalar_one_or_none()

            if tenant:
                data["is_tenant_owner"] = True
                data["tenant_id"] = tenant.id
                return await handler(event, data)

            # بررسی وضعیت ادمین فرعی
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

        return await handler(event, data)from typing import Any, Awaitable, Callable, Dict
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

        if data["is_owner"]:
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
