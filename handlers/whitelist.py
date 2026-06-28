from aiogram import Router, Bot
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import WhitelistedUser, BotAdmin, ProtectedChat

router = Router()

async def send_log(bot: Bot, tenant_id: int, text: str):
    """تابع کمکی برای ارسال لاگ اختصاصی به چت لاگ همان مشتری"""
    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.tenant_id == tenant_id, ProtectedChat.log_chat_id != None)
        )
        chat = query.scalars().first()
        if chat and chat.log_chat_id:
            try:
                await bot.send_message(chat_id=chat.log_chat_id, text=text, parse_mode="Markdown")
            except Exception:
                pass

@router.message(Command("setlog"))
async def set_log_chat(message: Message, is_tenant_owner: bool, tenant_id: int):
    """تنظیم گروه یا کانال ارسال لاگ‌ها توسط خریدار"""
    if not is_tenant_owner:
        await message.reply("❌ فقط خریدار اصلی مجموعه می‌تواند چت لاگ را تنظیم کند.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply("❌ فرمت اشتباه است.\nمثال: `/setlog -100123456789` (آیدی عددی چت لاگ)")
        return

    try:
        log_id = int(args[1])
    except ValueError:
        await message.reply("❌ آیدی چت باید یک عدد معتبر باشد.")
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.tenant_id == tenant_id)
        )
        chats = query.scalars().all()
        if not chats:
            await message.reply("❌ ابتدا باید حداقل یک گروه را با `/addchat` متصل کنید.")
            return

        for chat in chats:
            chat.log_chat_id = log_id
        await session.commit()

    await message.reply(f"✅ چت لاگ این مجموعه با موفقیت روی آیدی `{log_id}` تنظیم شد. تمام گزارشات امنیتی به اینجا ارسال می‌شوند.")

@router.message(Command("register"))
async def register_user(message: Message, is_tenant_owner: bool, is_bot_admin: bool, tenant_id: int, bot: Bot):
    if not (is_tenant_owner or is_bot_admin):
        return

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        await message.reply("❌ لطفاً روی کاربر مورد نظر ریپلای کنید تا مشخصات کامل او ثبت شود.")
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(WhitelistedUser).where(WhitelistedUser.tenant_id == tenant_id, WhitelistedUser.user_id == target_user.id)
        )
        if query.scalar_one_or_none():
            await message.reply("ℹ️ این کاربر از قبل در لیست سفید ثبت‌نام شده است.")
            return

        new_user = WhitelistedUser(tenant_id=tenant_id, user_id=target_user.id)
        session.add(new_user)
        await session.commit()

    # ارسال لاگ
    username = f"@{target_user.username}" if target_user.username else "ندارد"
    log_text = (
        f"🟢 **ثبت‌نام کاربر جدید**\n\n"
        f"👤 نام: {target_user.full_name}\n"
        f"🆔 آیدی عددی: `{target_user.id}`\n"
        f"🏷 یوزرنیم: {username}\n"
        f"👮‍♂️ توسط ادمین: `{message.from_user.id}`"
    )
    await send_log(bot, tenant_id, log_text)
    await message.reply(f"✅ کاربر `{target_user.full_name}` با موفقیت ثبت‌نام شد.")

@router.message(Command("unregister"))
async def unregister_user(message: Message, is_tenant_owner: bool, is_bot_admin: bool, tenant_id: int, bot: Bot):
    if not (is_tenant_owner or is_bot_admin):
        return

    target_user = None
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
    else:
        await message.reply("❌ لطفاً روی کاربر مورد نظر ریپلای کنید.")
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(
            select(WhitelistedUser).where(WhitelistedUser.tenant_id == tenant_id, WhitelistedUser.user_id == target_user.id)
        )
        whitelisted_user = query.scalar_one_or_none()
        
        if whitelisted_user:
            await session.delete(whitelisted_user)
            await session.commit()

        chats_query = await session.execute(
            select(ProtectedChat).where(ProtectedChat.tenant_id == tenant_id)
        )
        protected_chats = chats_query.scalars().all()

    banned_chats_count = 0
    for chat in protected_chats:
        try:
            await bot.ban_chat_member(chat_id=chat.chat_id, user_id=target_user.id)
            banned_chats_count += 1
        except Exception:
            pass

    username = f"@{target_user.username}" if target_user.username else "ندارد"
    log_text = (
        f"🔴 **حذف و بلاک همگانی (Global Ban)**\n\n"
        f"👤 نام: {target_user.full_name}\n"
        f"🆔 آیدی عددی: `{target_user.id}`\n"
        f"🏷 یوزرنیم: {username}\n"
        f"🔨 وضعیت: از لیست حذف و از {banned_chats_count} چت بن شد.\n"
        f"👮‍♂️ توسط ادمین: `{message.from_user.id}`"
    )
    await send_log(bot, tenant_id, log_text)
    await message.reply(f"❌ کاربر `{target_user.full_name}` حذف و از تمام گروه‌ها بن شد.")
