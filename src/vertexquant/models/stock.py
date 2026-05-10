"""正股数据模型

StockBasic: 正股基础信息（静态属性）
StockDaily: 正股日线行情（时间序列）
"""

from __future__ import annotations

import datetime

from sqlalchemy import Boolean, Date, Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from vertexquant.models.base import Base


class StockBasic(Base):
    """正股基础信息表

    主键: stock_code
    一只正股通过 BondBasic.stock_code 外键与一只可转债 1:1 关联。
    """

    __tablename__ = "stock_basic"

    stock_code: Mapped[str] = mapped_column(String(10), primary_key=True)
    stock_name: Mapped[str] = mapped_column(String(50), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(50), nullable=True)
    list_date: Mapped[datetime.date | None] = mapped_column(Date, nullable=True)
    exchange: Mapped[str] = mapped_column(String(10), nullable=False)
    is_st: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # 反向关联
    bonds: Mapped[list[BondBasic]] = relationship(back_populates="stock")  # type: ignore[name-defined] # noqa: F821
    daily_quotes: Mapped[list[StockDaily]] = relationship(back_populates="stock")

    def __repr__(self) -> str:
        return f"<StockBasic {self.stock_code} {self.stock_name}>"


class StockDaily(Base):
    """正股日线行情表

    复合主键: (stock_code, trade_date)
    close 存储前复权价格，保证时间序列连续可比。
    """

    __tablename__ = "stock_daily"

    stock_code: Mapped[str] = mapped_column(
        String(10),
        ForeignKey("stock_basic.stock_code"),
        primary_key=True,
    )
    trade_date: Mapped[datetime.date] = mapped_column(Date, primary_key=True)
    open: Mapped[float] = mapped_column(Float, nullable=False)
    high: Mapped[float] = mapped_column(Float, nullable=False)
    low: Mapped[float] = mapped_column(Float, nullable=False)
    close: Mapped[float] = mapped_column(Float, nullable=False)
    volume: Mapped[float] = mapped_column(Float, nullable=False)
    turnover: Mapped[float | None] = mapped_column(Float, nullable=True)
    adj_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    is_suspended: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    stock: Mapped[StockBasic] = relationship(back_populates="daily_quotes")

    def __repr__(self) -> str:
        return f"<StockDaily {self.stock_code} {self.trade_date}>"
