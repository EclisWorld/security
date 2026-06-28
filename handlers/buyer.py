from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import LicenseKey, Tenant, ProtectedChat

router = Router()

@router.message(Command("activate"))
async def activate_license(message: Message, is_owner: bool, is_tenant_owner: bool):
    """فعال‌سازی لایسنس توسط مشتری در پی‌وی ربات: /activate SEC-XXXX"""
    if message.chat.type != "private":
        await message.reply("❌ این دستور فقط در پی‌وی (Private Chat) ربات قابل استفاده است.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ لطفاً کد لایسنس را وارد کنید.\nمثال: `/activate SEC-123456`", parse_mode="Markdown")
        return

    license_code = args[1].strip().upper()
    user_id = message.from_user.id

    async with AsyncSessionLocal() as session:
        # ۱. بررسی موجود بودن و مصرف نشدن لایسنس
        lic_query = await session.execute(select(LicenseKey).where(LicenseKey.key == license_code))
        license_obj = lic_query.scalar_one_or_none()

        if not license_obj:
            await message.reply("❌ کد لایسنس وارد شده اشتباه است.")
            return

        if license_obj.is_used:
            await message.reply("❌ این کد لایسنس قبلاً استفاده شده است.")
            return

        # ۲. بررسی اینکه آیا این کاربر خودش از قبل لایسنس فعال دارد یا خیر
        tenant_query = await session.execute(select(Tenant).where(Tenant.owner_id == user_id))
        existing_tenant = tenant_query.scalar_one_or_none()

        duration = timedelta(days=license_obj.duration_days)

        if existing_tenant:
            # اگر از قبل اکانت داشت، مدت زمان جدید به اکانت فعلی‌اش اضافه (تمدید) می‌شود
            if existing_tenant.expires_at > datetime.utcnow():
                existing_tenant.expires_at += duration
            else:
                existing_tenant.expires_at = datetime.utcnow() + duration
            existing_tenant.is_active = True
            msg_text = f"✅ اشتراک شما با موفقیت تمدید شد!\n📅 تاریخ انقضای جدید: `{existing_tenant.expires_at.strftime('%Y-%m-%d')}`"
        else:
            # ایجاد یک مجموعه (Tenant) جدید برای خریدار جدید
            new_tenant = Tenant(
                owner_id=user_id,
                expires_at=datetime.utcnow() + duration,
                is_active=True
            )
            session.add(new_tenant)
            msg_text = f"🎉 تبریک! اشتراک شما با موفقیت فعال شد.\n📅 مدت اعتبار: {license_obj.duration_days} روز\n\nحالا می‌توانید ربات را به گروه‌ها یا کانال‌های خود اضافه کنید و با دستور `/addchat` آن‌ها را به پنل خود متصل کنید."

        # علامت‌گذاری لایسنس به عنوان استفاده شده
        license_obj.is_used = True
        license_obj.used_by = user_id
        
        await session.commit()

    await message.reply(msg_text, parse_mode="Markdown")


@router.message(Command("addchat"))
async def add_protected_chat(message: Message, is_tenant_owner: bool, tenant_id: int):
    """اتصال گروه یا کانال به مجموعه خریدار. باید در خود آن گروه/کانال زده شود"""
    if message.chat.type == "private":
        await message.reply("❌ این دستور باید در گروه یا کانالی که قصد محافظت از آن را دارید ارسال شود.")
        return

    if not is_tenant_owner:
        await message.reply("❌ شما اشتراک فعالی در ربات ندارید یا خریدار اصلی این مجموعه نیستید.")
        return

    chat_id = message.chat.id
    chat_type = message.chat.type

    async with AsyncSessionLocal() as session:
        # بررسی اینکه آیا این چت قبلاً توسط کسی ثبت شده یا خیر
        chat_query = await session.execute(select(ProtectedChat).where(ProtectedChat.chat_id == chat_id))
        existing_chat = chat_query.scalar_one_or_none()

        if existing_chat:
            await message.reply("❌ این چت قبلاً در سیستم ثبت شده است.")
            return

        # ثبت چت تحت مدیریت این خریدار
        new_chat = ProtectedChat(
            tenant_id=tenant_id,
            chat_id=chat_id,
            chat_type=chat_type
        )
        session.add(new_chat)
        await session.commit()

    await message.reply(f"✅ این {chat_type} با موفقیت به زون امنیتی مجموعه شما متصل شد و تحت نظارت ربات قرار گرفت.")
