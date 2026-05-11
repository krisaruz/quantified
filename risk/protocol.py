"""风控引擎 Protocol 定义"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class RiskViolation:
    """风控违规"""

    rule_name: str
    severity: str  # "hard" | "soft"
    cb_code: str | None = None
    message: str = ""
    current_value: float = 0.0
    threshold: float = 0.0
    suggested_action: str = ""  # "reduce" | "remove" | "pause" | "warn"
    suggested_volume: int | None = None


@runtime_checkable
class IRiskRule(Protocol):
    """风控规则接口"""

    name: str
    severity: str  # "hard" | "soft"

    def check(
        self,
        portfolio: object,
        signals: list,
        market_data: pd.DataFrame,
        config: object,
    ) -> list[RiskViolation]:
        """检查风控规则，返回违规列表"""
        ...

    def adjust(
        self,
        signals: list,
        violation: RiskViolation,
    ) -> list:
        """根据违规调整信号"""
        ...


@runtime_checkable
class PositionSizer(Protocol):
    """仓位管理算法接口"""

    name: str

    def calculate_weights(
        self,
        signals: list,
        total_capital: float,
        market_data: pd.DataFrame,
    ) -> dict[str, float]:
        """计算各标的的目标权重"""
        ...
