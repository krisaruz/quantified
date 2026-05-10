"""策略框架 Protocol 定义

IStrategy: 策略接口，生成交易信号
IFactor: 因子接口，计算因子值
Signal: 交易信号数据类
StrategyContext: 策略执行上下文
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

import pandas as pd


@dataclass(frozen=True)
class Signal:
    """交易信号"""

    cb_code: str
    direction: str  # "buy" | "sell" | "hold"
    weight: float  # 0.0 ~ 1.0，目标仓位权重
    score: float  # 策略评分（越高越优先）
    reason: str
    metadata: dict = field(default_factory=dict)


@dataclass
class StrategyContext:
    """策略执行上下文"""

    date: str
    universe: pd.DataFrame
    portfolio: object  # Portfolio 实例
    market_history: pd.DataFrame | None = None
    config: object = None  # AppConfig


@runtime_checkable
class IStrategy(Protocol):
    """策略接口"""

    name: str
    version: str
    description: str

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        """生成交易信号"""
        ...

    def get_parameters(self) -> dict:
        """返回当前参数快照"""
        ...

    def set_parameters(self, params: dict) -> None:
        """更新参数"""
        ...


@runtime_checkable
class IFactor(Protocol):
    """因子接口"""

    name: str
    category: str  # "value" | "momentum" | "quality" | "technical"
    description: str

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算因子值，返回与 df 同 index 的 Series"""
        ...

    def compute_single(self, row: pd.Series) -> float:
        """计算单行因子值"""
        ...
