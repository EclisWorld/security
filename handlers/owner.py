import uuid
from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from database.connection import AsyncSessionLocal
from database.models import LicenseKey, Tenant
from config import Config

router = Router()

# اعمال فیلتر سراسری روی این روتر: فقط اونر اصلی آیدی‌اش مجاز است
router.message.filter(F.from_user.id == Config.OWNER_ID)

@router.message(Command("gen"))
async def generate_license(message: Message):
    """فرمان ساخت لایسنس جدید: /gen <days>"""
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ دستور اشتباه است.\nفرمت صحیح: `/gen 30` (برای اشتراک ۳۰ روزه)", parse_mode="Markdown")
        return
    
    days = int(args[1])
    unique_key = f"SEC-{uuid.uuid4().hex[:12].upper()}"
    
    async with AsyncSessionLocal() as session:
        new_license = LicenseKey(key=unique_key, duration_days=days)
        session.add(new_license)
        await session.commit()
        
    await message.reply(
        f"✅ **لایسنس جدید با موفقیت ساخته شد:**\n\n"
        f"🔑 ` {unique_key} `\n"
        f"📅 مدت اعتبار: {days} روز\n\n"
        f"خریدار می‌تواند با دستور `/activate {unique_key}` در پی‌وی ربات، اشتراک خود را فعال کند.",
        parse_mode="Markdown"
    )

@router.message(Command("terminate"))
async def terminate_tenant(message: Message):
    """قطع دستی اشتراک یک مجموعه: /terminate <buyer_telegram_id>"""
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ دستور اشتباه است.\nفرمت صحیح: `/terminate 8423995337`", parse_mode="Markdown")
        return
        
    target_owner_id = int(args[1])
    
    async with AsyncSessionLocal() as session:
        from sqlalchemy.future import select
        query = await session.execute(select(Tenant).where(Tenant.owner_id == target_owner_id))
        tenant = query.scalar_one_or_none()
        
        if not tenant:
            await message.reply("❌ مجموعه‌ای با این مشخصات یا آیدی مالک یافت نشد.")
            return
            
        tenant.is_active = False
        await session.commit()
        
    await message.reply(f"🔒 اشتراک مجموعه متعلق به کاربر `{target_owner_id}` فوراً لغو و دسترسی‌های ربات برای آن کلاً مسدود شد.", parse_mode="Markdown")import uuid
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import LicenseKey, Tenant

router = Router()

@router.message(Command("gen"))
async def generate_license(message: Message, is_owner: bool):
    """فرمان ساخت لایسنس جدید: /gen <days>"""
    if not is_owner:
        return  # فقط اونر اصلی اجازه دارد
    
    # استخراج تعداد روزها از دستور
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ دستور اشتباه است.\nفرمت صحیح: `/gen 30` (برای اشتراک ۳۰ روزه)", parse_mode="Markdown")
        return
    
    days = int(args[1])
    unique_key = f"SEC-{uuid.uuid4().hex[:12].upper()}"  # ساخت یک کلید رندوم و شیک
    
    async with AsyncSessionLocal() as session:
        new_license = LicenseKey(key=unique_key, duration_days=days)
        session.add(new_license)
        await session.commit()
        
    await message.reply(
        f"✅ **لایسنس جدید با موفقیت ساخته شد:**\n\n"
        f"🔑 ` {unique_key} `\n"
        f"📅 مدت اعتبار: {days} روز\n\n"
        f"خریدار می‌تواند با دستور `/activate {unique_key}` در پی‌وی ربات، اشتراک خود را فعال کند.",
        parse_mode="Markdown"
    )

@router.message(Command("terminate"))
async def terminate_tenant(message: Message, is_owner: bool):
    """قطع دستی اشتراک یک مجموعه از طریق آیدی تلگرام خریدار: /terminate <buyer_telegram_id>"""
    if not is_owner:
        return
        
    args = message.text.split()
    if len(args) < 2 or not args[1].isdigit():
        await message.reply("❌ دستور اشتباه است.\nفرمت صحیح: `/terminate 8423995337`", parse_mode="Markdown")
        return
        
    target_owner_id = int(args[1])
    
    async with AsyncSessionLocal() as session:
        query = await session.execute(select(Tenant).where(Tenant.owner_id == target_owner_id))
        tenant = query.scalar_one_or_none()
        
        if not tenant:
            await message.reply("❌ مجموعه‌ای با این مشخصات یا آیدی مالک یافت نشد.")
            return
            
        tenant.is_active = False  # غیرفعال کردن لایسنس مجموعه
        await session.commit()
        
    await message.reply(f"🔒 اشتراک مجموعه متعلق به کاربر `{target_owner_id}` فوراً لغو و دسترسی‌های ربات برای آن کلاً مسدود شد.", parse_mode="Markdown")
