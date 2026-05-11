"""监控告警数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class Alert:
    """告警"""

    alert_id: str
    rule_name: str
    severity: str  # "info" | "warning" | "critical"
    title: str
    message: str
    current_value: float
    threshold: float
    timestamp: datetime
    cb_code: str | None = None
    acknowledged: bool = False


@dataclass
class MonitorContext:
    """监控上下文（聚合所有监控所需数据）"""

    date: str
    cash: float
    holdings: list[Any]
    recent_snapshots: list[Any]
    recent_trades: list[Any]
    data_meta: dict[str, str]
    market_data: Any = None  # pd.DataFrame or None
    config: Any = None  # AppConfig or None


@runtime_checkable
class AlertRule(Protocol):
    """告警规则协议"""

    name: str

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        ...


@runtime_checkable
class Notifier(Protocol):
    """通知器协议"""

    def notify(self, alert: Alert) -> bool:
        ...
