"""可转债数据模型

BondStatus: 转债生命周期状态枚举（3 态）
BondBasic: 转债基础信息（静态属性 + 最新转股价）
BondDaily: 转债日线行情（时间序列）
ConversionPriceHistory: 转股价变动历史（事件序列）
"""

from __future__ import annotations

import datetime
import enum

from sqlalchemy import Boolean, Date, Enum, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vertexquant.models.base import Base


class BondStatus(str, enum.Enum):
    """转债生命周期状态

    ACTIVE -> REDEEM_WARNING -> DELISTED
                               ^
    ACTIVE ----(到期)-----------|
    """

    ACTIVE = "active"
    REDEEM_WARNING = "redeem_warning"
    DELISTED = "delisted"


class BondBasic(Base):
    """转债基础信息表

    主键: cb_code
    stock_code 外键指向 StockBasic，UNIQUE 约束保证 1:1。
    """

    __tablename__ = "bond_basic"

    cb_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    cb_name: Mapped[str] = mapped_column(String(50), nullable=False)
    stock_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basic.stock_code"),
        nullable=False,
    )
    list_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    delist_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    maturity_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    conv_price_latest: Mapped[float] = mapped_column(Float, nullable=False)
    issue_size: Mapped[float] = mapped_column(Float, nullable=False)
    redeem_trigger_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_rating: Mapped[str | None] = mapped_column(String(10), nullable=True)
    redeem_clause: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[BondStatus] = mapped_column(
        Enum(BondStatus),
        nullable=False,
        default=BondStatus.ACTIVE,
    )

    # 关联关系
    stock: Mapped[StockBasic] = relationship(back_populates="bonds")  # type: ignore[name-defined] # noqa: F821
    daily_quotes: Mapped[list[BondDaily]] = relationship(back_populates="bond")
    conv_price_history: Mapped[list[ConversionPriceHistory]] = relationship(
        back_populates="bond",
        order_by="ConversionPriceHistory.change_date",
    )

    def __repr__(self) -> str:
        return f"<BondBasic {self.cb_code} {self.cb_name}>"


class BondDaily(Base):
    """转债日线行情表

    复合主键: (cb_code, trade_date)
    """

    __tablename__ = "bond_daily"

    cb_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("bond_basic.cb_code"),
        primary_key=True,
    )
    trade_date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    bond: Mapped[BondBasic] = relationship(back_populates="daily_quotes")

    def __repr__(self) -> str:
        return f"<BondDaily {self.cb_code} {self.trade_date}>"


class ConversionPriceHistory(Base):
    """转股价变动历史表

    复合主键: (cb_code, change_date)
    记录每次转股价变动（下修/送股/配股/分红），回测时按日期查找生效的转股价。

    查询方式: SELECT ... WHERE cb_code=:code AND change_date <= :target_date
              ORDER BY change_date DESC LIMIT 1
    """

    __tablename__ = "conv_price_history"

    cb_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("bond_basic.cb_code"),
        primary_key=True,
    )
    change_date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    conversion_price: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)

    bond: Mapped[BondBasic] = relationship(back_populates="conv_price_history")

    def __repr__(self) -> str:
        return f"<ConvPrice {self.cb_code} {self.change_date} {self.conversion_price}>"
