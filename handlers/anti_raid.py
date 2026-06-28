from aiogram import Router, Bot, F
from aiogram.types import ChatMemberUpdated
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import ProtectedChat, WhitelistedUser, Tenant

router = Router()

@router.chat_member()
async def monitor_chat_members(event: ChatMemberUpdated, bot: Bot):
    """بررسی اعضای جدید در زمان ورود به گروه یا کانال"""
    # فقط زمانی که یک کاربر جدید وارد می‌شود یا وضعیتش به عضویت تغییر می‌کند
    if event.new_chat_member.status not in ["member", "administrator", "creator"]:
        # اگر کاربر لفت داده، قبلاً بن شده یا فقط تغییر دسترسی داشته، کاری انجام نده
        if event.old_chat_member.status in ["left", "kicked"] or event.new_chat_member.status != "member":
            return

    chat_id = event.chat.id
    user_id = event.from_user.id

    async with AsyncSessionLocal() as session:
        # ۱. بررسی اینکه آیا این چت تحت نظارت ربات قرار دارد؟
        chat_query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.chat_id == chat_id)
        )
        protected_chat = chat_query.scalar_one_or_none()

        if not protected_chat:
            return  # این چت در سیستم ثبت نشده است

        # ۲. بررسی فعال بودن لایسنس مجموعه (Tenant)
        tenant_query = await session.execute(
            select(Tenant).where(Tenant.id == protected_chat.tenant_id)
        )
        tenant = tenant_query.scalar_one_or_none()

        if not tenant or not tenant.is_active:
            return  # اشتراک مجموعه منقضی یا لغو شده است

        # ۳. بررسی اینکه آیا کاربر تازه وارد در لیست سفید ثبت‌نام شده است؟
        whitelist_query = await session.execute(
            select(WhitelistedUser).where(
                WhitelistedUser.tenant_id == protected_chat.tenant_id,
                WhitelistedUser.user_id == user_id
            )
        )
        is_registered = whitelist_query.scalar_one_or_none()

        # اگر کاربر در لیست سفید نباشد، فوراً او را بن کن
        if not is_registered:
            try:
                # بن کردن کاربر از چت جاری
                await bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
                
                # حذف پیام ورود (در صورت امکان برای تمیز ماندن گروه)
                # نکته: تلگرام گاهی اوقات پیام‌های سیستمی ورود را اتوماتیک حذف می‌کند، اما برای اطمینان این متد در صورت نیاز کارآمد است.
                
                # ارسال لاگ به چت ثبت شده برای گزارش‌ها (در صورت تنظیم شدن)
                if protected_chat.log_chat_id:
                    await bot.send_message(
                        chat_id=protected_chat.log_chat_id,
                        text=f"🚫 **سیستم امنیتی فعال شد**\n\n"
                             f"👤 کاربر: `{user_id}`\n"
                             f"📍 مکان: {event.chat.title}\n"
                             f"📝 علت: ورود بدون ثبت‌نام قبلی (Unregistered user).\n"
                             f"🔨 وضعیت: فوراً بن شد.",
                        parse_mode="Markdown"
                    )
            except Exception as e:
                # لاگ کردن خطای احتمالی ادمین نبودن ربات در سرور کنسول
                print(f"خطا در بن کردن کاربر {user_id} در چت {chat_id}: {e}")
