from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import WhitelistedUser, BotAdmin, ProtectedChat

router = Router()

@router.message(Command("addadmin"))
async def add_bot_admin(message: Message, is_tenant_owner: bool, tenant_id: int):
    """افزودن ادمین فرعی برای ربات (فقط توسط خریدار اصلی مجموعه)"""
    if not is_tenant_owner:
        await message.reply("❌ فقط خریدار اصلی مجموعه می‌تواند ادمین جدید اضافه کند.")
        return

    # بررسی ریپلای یا وارد کردن آیدی عددی
    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) == 2 and args[1].isdigit():
            target_id = int(args[1])

    if not target_id:
        await message.reply("❌ لطفاً روی کاربر مورد نظر ریپلای کنید یا آیدی عددی او را جلوی دستور بفرستید.\nمثال: `/addadmin 123456`")
        return

    async with AsyncSessionLocal() as session:
        # بررسی تکراری نبودن ادمین
        query = await session.execute(
            select(BotAdmin).where(BotAdmin.tenant_id == tenant_id, BotAdmin.admin_id == target_id)
        )
        if query.scalar_one_or_none():
            await message.reply("❌ این کاربر از قبل ادمین این مجموعه هست.")
            return

        new_admin = BotAdmin(tenant_id=tenant_id, admin_id=target_id)
        session.add(new_admin)
        await session.commit()

    await message.reply(f"✅ کاربر `{target_id}` با موفقیت به عنوان ادمین فرعی این مجموعه در ربات ثبت شد.", parse_mode="Markdown")


@router.message(Command("register"))
async def register_user(message: Message, is_tenant_owner: bool, is_bot_admin: bool, tenant_id: int):
    """ثبت‌نام کاربر در لیست سفید (توسط خریدار یا ادمین فرعی)"""
    if not (is_tenant_owner or is_bot_admin):
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) == 2 and args[1].isdigit():
            target_id = int(args[1])

    if not target_id:
        await message.reply("❌ روی کاربر ریپلای کنید یا آیدی عددی او را جلوی دستور وارد کنید.")
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(WhitelistedUser).where(WhitelistedUser.tenant_id == tenant_id, WhitelistedUser.user_id == target_id)
        )
        if query.scalar_one_or_none():
            await message.reply("ℹ️ این کاربر از قبل در لیست سفید ثبت‌نام شده است.")
            return

        new_user = WhitelistedUser(tenant_id=tenant_id, user_id=target_id)
        session.add(new_user)
        await session.commit()

    await message.reply(f"✅ کاربر `{target_id}` با موفقیت ثبت‌نام شد و اجازه ورود به گروه‌ها/کانال‌ها را دارد.", parse_mode="Markdown")


@router.message(Command("unregister"))
async def unregister_user(message: Message, is_tenant_owner: bool, is_bot_admin: bool, tenant_id: int, bot: Bot):
    """حذف از لیست سفید و بلاک همگانی (Global Ban) از تمام چت‌های متصل به مجموعه"""
    if not (is_tenant_owner or is_bot_admin):
        return

    target_id = None
    if message.reply_to_message:
        target_id = message.reply_to_message.from_user.id
    else:
        args = message.text.split()
        if len(args) == 2 and args[1].isdigit():
            target_id = int(args[1])

    if not target_id:
        await message.reply("❌ روی کاربر ریپلای کنید یا آیدی عددی او را جلوی دستور وارد کنید.")
        return

    async with AsyncSessionLocal() as session:
        # ۱. حذف از لیست سفید دیتابیس
        query = await session.execute(
            select(WhitelistedUser).where(WhitelistedUser.tenant_id == tenant_id, WhitelistedUser.user_id == target_id)
        )
        whitelisted_user = query.scalar_one_or_none()
        
        if whitelisted_user:
            await session.delete(whitelisted_user)
            await session.commit()

        # ۲. بلاک همگانی (Global Ban) از تمام چت‌های ثبت شده این مجموعه
        chats_query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.tenant_id == tenant_id)
        )
        protected_chats = chats_query.scalars().all()

    banned_chats_count = 0
    for chat in protected_chats:
        try:
            await bot.ban_chat_member(chat_id=chat.chat_id, user_id=target_id)
            banned_chats_count += 1
        except Exception:
            pass  # اگر ربات در یکی از گروه‌ها ادمین نباشد یا دسترسی بن نداشته باشد رد می‌کند

    await message.reply(
        f"❌ کاربر `{target_id}` از لیست سفید حذف شد.\n"
        f"🚫 فرآیند بلاک همگانی اجرا شد و کاربر از {banned_chats_count} گروه/کانال این مجموعه بن گردید.",
        parse_mode="Markdown"
    )
