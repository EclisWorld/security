from aiogram import Router, Bot
from aiogram.types import ChatMemberUpdated
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import ProtectedChat, WhitelistedUser, Tenant

router = Router()

@router.chat_member()
async def monitor_chat_members(event: ChatMemberUpdated, bot: Bot):
    chat_id = event.chat.id
    user = event.from_user
    username = f"@{user.username}" if user.username else "ندارد"

    async with AsyncSessionLocal() as session:
        chat_query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.chat_id == chat_id)
        )
        protected_chat = chat_query.scalar_one_or_none()
        if not protected_chat or not protected_chat.log_chat_id:
            return 

        tenant_query = await session.execute(
            select(Tenant).where(Tenant.id == protected_chat.tenant_id)
        )
        tenant = tenant_query.scalar_one_or_none()
        if not tenant or not tenant.is_active:
            return

        whitelist_query = await session.execute(
            select(WhitelistedUser).where(
                WhitelistedUser.tenant_id == protected_chat.tenant_id,
                WhitelistedUser.user_id == user.id
            )
        )
        is_registered = whitelist_query.scalar_one_or_none()

        # ۱. سناریو: کاربر ثبت‌نام نشده است -> بن درجا + ثبت لاگ حمله
        if not is_registered:
            if event.new_chat_member.status in ["member", "restricted"]:
                try:
                    await bot.ban_chat_member(chat_id=chat_id, user_id=user.id)
                    await bot.send_message(
                        chat_id=protected_chat.log_chat_id,
                        text=f"🚨 **تلاش برای ورود غیرمجاز (حمله)**\n\n"
                             f"👤 نام: {user.full_name}\n"
                             f"🆔 آیدی عددی: `{user.id}`\n"
                             f"🏷 یوزرنیم: {username}\n"
                             f"📍 مکان: {event.chat.title}\n"
                             f"🔨 وضعیت: کاربر عضو لیست سفید نبود، فوراً بلاک شد.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass
            return

        # ۲. سناریو: کاربر مجاز وارد شده است (Join)
        if event.old_chat_member.status in ["left", "kicked"] and event.new_chat_member.status == "member":
            await bot.send_message(
                chat_id=protected_chat.log_chat_id,
                text=f"📥 **ورود کاربر مجاز**\n\n"
                     f"👤 نام: {user.full_name}\n"
                     f"🆔 آیدی عددی: `{user.id}`\n"
                     f"🏷 یوزرنیم: {username}\n"
                     f"📍 مکان: {event.chat.title}",
                parse_mode="Markdown"
            )

        # ۳. سناریو: کاربر مجاز خارج شده است (Left)
        elif event.new_chat_member.status in ["left", "kicked"] and event.old_chat_member.status in ["member", "administrator"]:
            await bot.send_message(
                chat_id=protected_chat.log_chat_id,
                text=f"📤 **خروج کاربر مجاز**\n\n"
                     f"👤 نام: {user.full_name}\n"
                     f"🆔 آیدی عددی: `{user.id}`\n"
                     f"🏷 یوزرنیم: {username}\n"
                     f"📍 مکان: {event.chat.title}",
                parse_mode="Markdown"
            )
