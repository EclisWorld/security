from datetime import datetime
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Tenant(Base):
    """هر مشتری یا مجموعه خریداری شده (مثل مجموعه اکلیس)"""

    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )  # آیدی تلگرام خریدار اصلی مجموعه
    expires_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False
    )  # تاریخ انقضای اشتراک
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    # روابط
    admins = relationship(
        "BotAdmin", back_populates="tenant", cascade="all, delete-orphan"
    )
    chats = relationship(
        "ProtectedChat", back_populates="tenant", cascade="all, delete-orphan"
    )
    whitelist = relationship(
        "WhitelistedUser", back_populates="tenant", cascade="all, delete-orphan"
    )


class BotAdmin(Base):
    """ادمین‌های فرعی که توسط خریدار برای مدیریت لیست سفید اضافه می‌شوند"""

    __tablename__ = "bot_admins"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    admin_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # آیدی تلگرام ادمین فرعی
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    tenant = relationship("Tenant", back_populates="admins")


class ProtectedChat(Base):
    """گروه‌ها یا کانال‌هایی که ربات باید از آن‌ها محافظت کند"""

    __tablename__ = "protected_chats"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    chat_id: Mapped[int] = mapped_column(
        BigInteger, unique=True, nullable=False
    )  # آیدی عددی گروه یا کانال
    chat_type: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # 'group' or 'channel'
    log_chat_id: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )  # آیدی کانال/گروه ارسال لاگ‌های این مجموعه

    tenant = relationship("Tenant", back_populates="chats")


class WhitelistedUser(Base):
    """لیست سفید کاربران مجاز (Register شده) هر مجموعه"""

    __tablename__ = "whitelisted_users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    tenant_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False
    )  # آیدی تلگرام کاربر مجاز
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )

    tenant = relationship("Tenant", back_populates="whitelist")


class LicenseKey(Base):
    """کدهای لایسنسی که توسط مالک اصلی (تو) ساخته می‌شود تا مشتریان فعال کنند"""

    __tablename__ = "license_keys"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False
    )  # کد لایسنس منحصربه‌فرد
    duration_days: Mapped[int] = mapped_column(
        nullable=False
    )  # مدت زمان به روز (مثلاً ۳۰)
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_by: Mapped[int] = mapped_column(
        BigInteger, nullable=True
    )  # آیدی تلگرام کسی که لایسنس رو استفاده کرد
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow
    )
