# app/models.py
import enum
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import relationship, mapped_column, Mapped
from sqlalchemy import Integer, String, Float, DateTime, Boolean, Date, Enum, ForeignKey
from .database import db


class RecognitionStatus(enum.Enum):
    PENDING = "待处理"
    PROCESSING = "正在识别"
    FAILED = "识别失败"
    SUCCESS = "识别成功"


class Receipt(db.Model):
    __tablename__ = "receipts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(
        String(255), nullable=False, default="未命名小票"
    )  # 将长度扩展到255以支持AI生成的文件名
    image_filename: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    text_description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    exchange_rate: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    store_name: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # 店铺名称
    store_category: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 店铺分类
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    transaction_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
    status: Mapped[RecognitionStatus] = mapped_column(
        Enum(RecognitionStatus), default=RecognitionStatus.PENDING, nullable=False
    )

    items: Mapped[List["Item"]] = relationship(
        "Item", back_populates="receipt", cascade="all, delete-orphan"
    )

    def __init__(
        self,
        name="未命名小票",
        image_filename=None,
        text_description=None,
        notes=None,
        transaction_time=None,
        store_name=None,
        store_category=None,
    ):
        self.name = name
        self.image_filename = image_filename
        self.text_description = text_description
        self.notes = notes
        self.transaction_time = transaction_time  # 不设置默认值，由调用者决定
        self.store_name = store_name
        self.store_category = store_category


class Item(db.Model):
    __tablename__ = "items"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    receipt_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("receipts.id"), nullable=False
    )
    name_ja: Mapped[Optional[str]] = mapped_column(String(100))
    name_zh: Mapped[Optional[str]] = mapped_column(String(100))
    price_jpy: Mapped[Optional[float]] = mapped_column(Float)
    price_cny: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    special_info: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 特价信息，如"-20%"、"是"、"否"，与AI服务字段一致
    is_special_offer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )  # 是否特价商品
    category_1: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 新增：一级分类
    category_2: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 新增：二级分类
    category_3: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 新增：三级分类
    notes: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    receipt: Mapped["Receipt"] = relationship("Receipt", back_populates="items")
    durable_info: Mapped[Optional["DurableGood"]] = relationship(
        "DurableGood",
        uselist=False,
        back_populates="item",
        cascade="all, delete-orphan",
    )


class DurableGood(db.Model):
    __tablename__ = "durable_goods"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("items.id"), nullable=False, unique=True
    )
    start_date: Mapped[Optional[datetime]] = mapped_column(Date)
    end_date: Mapped[Optional[datetime]] = mapped_column(Date)
    item: Mapped["Item"] = relationship("Item", back_populates="durable_info")
