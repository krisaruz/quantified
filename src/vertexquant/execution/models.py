"""执行引擎数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class Fill:
    """成交记录"""

    fill_id: str
    order_id: str
    price: float
    volume: int
    amount: float
    fee: float
    timestamp: datetime


@dataclass
class Order:
    """订单"""

    order_id: str
    cb_code: str
    cb_name: str
    direction: str  # "buy" | "sell"
    target_volume: int
    filled_volume: int = 0
    limit_price: float | None = None
    status: str = "pending"  # "pending" | "partial" | "filled" | "cancelled" | "expired"
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    filled_at: datetime | None = None
    fills: list[Fill] = field(default_factory=list)
    reason: str = ""
    ttl_days: int = 3

    @property
    def remaining_volume(self) -> int:
        return self.target_volume - self.filled_volume

    @property
    def is_active(self) -> bool:
        return self.status in ("pending", "partial")

    @property
    def avg_fill_price(self) -> float:
        if not self.fills:
            return 0.0
        total_amount = sum(f.price * f.volume for f in self.fills)
        total_volume = sum(f.volume for f in self.fills)
        return total_amount / total_volume if total_volume > 0 else 0.0


@dataclass(frozen=True)
class MarketBar:
    """行情快照"""

    cb_code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float
    is_suspended: bool = False
