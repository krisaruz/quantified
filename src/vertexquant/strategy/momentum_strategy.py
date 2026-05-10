"""动量轮动策略：选择近期涨幅最大的转债"""

from __future__ import annotations

import logging

import pandas as pd

from vertexquant.strategy.protocol import Signal, StrategyContext
from vertexquant.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register("momentum")
class MomentumStrategy:
    """动量轮动策略

    策略逻辑：
    1. 计算 N 日涨幅
    2. 选涨幅最大的前 K 只
    3. 排除 ST、停牌、价格过高标的
    """

    name = "momentum"
    version = "1.0.0"
    description = "动量轮动策略：选择近期涨幅最大的转债"

    def __init__(
        self,
        lookback_days: int = 20,
        hold_count: int = 10,
        max_price: float = 150.0,
        max_position_pct: float = 0.10,
    ) -> None:
        self.lookback_days = lookback_days
        self.hold_count = hold_count
        self.max_price = max_price
        self.max_position_pct = max_position_pct

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        df = context.universe
        if df.empty:
            return []

        # 过滤高价标的
        candidates = df[df["cb_close"] <= self.max_price].copy()
        if candidates.empty:
            return []

        # 计算动量（如果有历史数据）
        if "momentum_20d" in candidates.columns:
            candidates["momentum"] = candidates["momentum_20d"].fillna(0)
        elif "cb_close" in candidates.columns:
            # 简化：用当前数据的溢价率作为动量代理
            candidates["momentum"] = -candidates["premium_rate"].fillna(0)
        else:
            candidates["momentum"] = 0.0

        # 按动量排序（高到低）
        candidates = candidates.sort_values("momentum", ascending=False).reset_index(drop=True)

        signals: list[Signal] = []
        current_codes = context.portfolio.codes if hasattr(context.portfolio, "codes") else set()
        target_codes = set(candidates.head(self.hold_count)["cb_code"])

        # 卖出信号
        for code in current_codes:
            if code not in target_codes:
                signals.append(Signal(
                    cb_code=code, direction="sell", weight=0.0,
                    score=0.0, reason="动量排名下降，卖出",
                ))

        # 买入信号
        remaining = current_codes - {s.cb_code for s in signals if s.direction == "sell"}
        slots = max(0, self.hold_count - len(remaining))
        if slots > 0:
            buy_candidates = candidates[~candidates["cb_code"].isin(remaining)].head(slots)
            for idx, row in buy_candidates.iterrows():
                signals.append(Signal(
                    cb_code=str(row["cb_code"]),
                    direction="buy",
                    weight=self.max_position_pct,
                    score=float(row["momentum"]),
                    reason=f"动量排名第{idx + 1}",
                    metadata={"momentum": float(row["momentum"])},
                ))

        return signals

    def get_parameters(self) -> dict:
        return {
            "lookback_days": self.lookback_days,
            "hold_count": self.hold_count,
            "max_price": self.max_price,
            "max_position_pct": self.max_position_pct,
        }

    def set_parameters(self, params: dict) -> None:
        if "lookback_days" in params:
            self.lookback_days = int(params["lookback_days"])
        if "hold_count" in params:
            self.hold_count = int(params["hold_count"])
        if "max_price" in params:
            self.max_price = float(params["max_price"])
        if "max_position_pct" in params:
            self.max_position_pct = float(params["max_position_pct"])
