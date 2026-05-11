"""滑点模型

提供多种滑点估算策略。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class SlippageModel(Protocol):
    """滑点模型协议"""

    def estimate(
        self,
        direction: str,
        price: float,
        volume: int,
        daily_volume: float,
        volatility: float,
    ) -> float:
        """估算成交价格（含滑点）

        Args:
            direction: "buy" | "sell"
            price: 基准价格（通常为开盘价）
            volume: 成交量
            daily_volume: 日总成交量
            volatility: 波动率 (high - low) / close

        Returns:
            估算的成交价格
        """
        ...


@dataclass
class FixedSlippageModel:
    """固定比例滑点"""

    rate: float = 0.001  # 0.1%

    def estimate(
        self,
        direction: str,
        price: float,
        volume: int,
        daily_volume: float,
        volatility: float,
    ) -> float:
        if direction == "buy":
            return price * (1 + self.rate)
        return price * (1 - self.rate)


@dataclass
class VolumeBasedSlippageModel:
    """基于成交量的滑点

    成交量占日成交量比例越大，滑点越大。
    """

    base_rate: float = 0.0005
    impact_factor: float = 0.1

    def estimate(
        self,
        direction: str,
        price: float,
        volume: int,
        daily_volume: float,
        volatility: float,
    ) -> float:
        participation = volume / max(daily_volume, 1)
        impact = self.base_rate + self.impact_factor * participation
        if direction == "buy":
            return price * (1 + impact)
        return price * (1 - impact)


@dataclass
class VolatilitySlippageModel:
    """基于波动率的滑点

    波动率越大，滑点越大。
    """

    base_rate: float = 0.0003
    vol_multiplier: float = 0.5

    def estimate(
        self,
        direction: str,
        price: float,
        volume: int,
        daily_volume: float,
        volatility: float,
    ) -> float:
        impact = self.base_rate + self.vol_multiplier * volatility
        if direction == "buy":
            return price * (1 + impact)
        return price * (1 - impact)
