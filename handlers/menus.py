from aiogram import Router, Bot, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from sqlalchemy.future import select
from database.connection import AsyncSessionLocal
from database.models import Tenant, ProtectedChat, BotAdmin, WhitelistedUser

router = Router()

def get_main_menu() -> InlineKeyboardMarkup:
    """ساخت دکمه‌های شیشه‌ای منوی اصلی پنل مدیریت"""
    buttons = [
        [
            InlineKeyboardButton(text="📊 وضعیت اشتراک", callback_query_data="panel_status"),
            InlineKeyboardButton(text="💬 چت‌های متصل", callback_query_data="panel_chats")
        ],
        [
            InlineKeyboardButton(text="👮‍♂️ مدیران فرعی", callback_query_data="panel_admins"),
            InlineKeyboardButton(text="👥 آمار لیست سفید", callback_query_data="panel_whitelist")
        ],
        [
            InlineKeyboardButton(text="🔄 به‌روزرسانی پنل", callback_query_data="panel_main")
        ]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


@router.message(Command("panel"))
async def open_panel(message: Message, is_tenant_owner: bool):
    """باز کردن پنل اصلی مدیریت با دکمه‌های شیشه‌ای"""
    if not is_tenant_owner:
        await message.reply("❌ شما اشتراک فعالی ندارید یا دسترسی شما مجاز نیست.")
        return
        
    await message.reply(
        "🛡 **به پنل مدیریت هوشمند مجموعه خود خوش آمدید**\n\n"
        "جهت مدیریت بخش‌های مختلف ربات امنیتی، از دکمه‌های شیشه‌ای زیر استفاده کنید:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "panel_main")
async def back_to_main(callback: CallbackQuery, is_tenant_owner: bool):
    """برگشت به منوی اصلی پنل"""
    if not is_tenant_owner:
        await callback.answer("❌ دسترسی غیرمجاز", show_alert=True)
        return
        
    await callback.message.edit_text(
        "🛡 **به پنل مدیریت هوشمند مجموعه خود خوش آمدید**\n\n"
        "جهت مدیریت بخش‌های مختلف ربات امنیتی، از دکمه‌های شیشه‌ای زیر استفاده کنید:",
        reply_markup=get_main_menu(),
        parse_mode="Markdown"
    )


@router.callback_query(F.data == "panel_status")
async def view_status(callback: CallbackQuery, is_tenant_owner: bool, tenant_id: int):
    """نمایش وضعیت لایسنس و تاریخ انقضا"""
    if not is_tenant_owner:
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
        tenant = query.scalar_one_or_none()

    if not tenant:
        await callback.answer("خطا در یافتن اطلاعات مجموعه")
        return

    expire_date = tenant.expires_at.strftime('%Y-%m-%d %H:%M')
    status_text = "🟢 فعال" if tenant.is_active else "🔴 غیرفعال"

    text = (
        f"📋 **گزارش وضعیت اشتراک شما**\n\n"
        f"Status وضعیت اکانت: {status_text}\n"
        f"📅 تاریخ انقضا (UTC): `{expire_date}`\n\n"
        f"💡 در صورت نیاز به تمدید، لایسنس جدید خود را با دستور `/activate CODE` وارد کنید."
    )

    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_query_data="panel_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_button, parse_mode="Markdown")


@router.callback_query(F.data == "panel_chats")
async def view_chats(callback: CallbackQuery, is_tenant_owner: bool, tenant_id: int):
    """نمایش لیست تمام گروه‌ها و کانال‌های متصل شده"""
    if not is_tenant_owner:
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(select(ProtectedChat).where(ProtectedChat.tenant_id == tenant_id))
        chats = query.scalars().all()

    text = "💬 **لیست چت‌های تحت نظارت ربات:**\n\n"
    if not chats:
        text += "❌ هیچ گروه یا کانالی متصل نشده است.\nربات را در گروه خود ادمین کنید و دستور `/addchat` را بزنید."
    else:
        for idx, chat in enumerate(chats, 1):
            type_emoji = "👥" if chat.chat_type in ["group", "supergroup"] else "📢"
            log_status = "✅ دارد" if chat.log_chat_id else "❌ ندارد (`/setlog`)"
            text += f"{idx}. {type_emoji} آیدی چت: `{chat.chat_id}`\n   🪵 کانال لاگ: {log_status}\n\n"

    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_query_data="panel_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_button, parse_mode="Markdown")


@router.callback_query(F.data == "panel_admins")
async def view_admins(callback: CallbackQuery, is_tenant_owner: bool, tenant_id: int):
    """نمایش لیست ادمین‌های فرعی مجموعه"""
    if not is_tenant_owner:
        return

    async with AsyncSessionLocal() as session:
        query = await session.execute(select(BotAdmin).where(BotAdmin.tenant_id == tenant_id))
        admins = query.scalars().all()

    text = "👮‍♂️ **لیست مدیران فرعی ربات (دسترسی سفید کردن):**\n\n"
    if not admins:
        text += "ℹ️ هیچ ادمین فرعی تعریف نشده است.\nبرای افزودن، روی کاربر مورد نظر دستور `/addadmin` را بزنید."
    else:
        for idx, adm in enumerate(admins, 1):
            text += f"{idx}. 👤 آیدی عددی ادمین: `{adm.admin_id}`\n"

    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_query_data="panel_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_button, parse_mode="Markdown")


@router.callback_query(F.data == "panel_whitelist")
async def view_whitelist_stats(callback: CallbackQuery, is_tenant_owner: bool, tenant_id: int):
    """نمایش آمار کاربران ثبت‌نام شده"""
    if not is_tenant_owner:
        return

    async with AsyncSessionLocal() as session:
        # شمارش کاربران در لیست سفید
        query = await session.execute(select(WhitelistedUser).where(WhitelistedUser.tenant_id == tenant_id))
        count = len(query.scalars().all())

    text = (
        f"👥 **آمار لیست سفید (Register List)**\n\n"
        f"تعداد کل کاربران مجاز ثبت شده: `{count}` کاربر\n\n"
        f"ℹ️ برای ثبت کاربر جدید از دستور `/register` و برای بن همگانی از `/unregister` روی ریپلاي شخص استفاده کنید."
    )

    back_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 بازگشت به منو", callback_query_data="panel_main")]
    ])
    
    await callback.message.edit_text(text, reply_markup=back_button, parse_mode="Markdown")
