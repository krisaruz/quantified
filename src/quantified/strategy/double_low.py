"""双低策略：将现有 double_low 逻辑封装为 IStrategy"""

from __future__ import annotations

import logging

import pandas as pd

from quantified.strategy.protocol import Signal, StrategyContext
from quantified.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register("double_low")
class DoubleLowStrategy:
    """双低轮动策略

    策略逻辑：
    1. 按双低值（价格 + 溢价率 * 100）排序
    2. 选前 N 只作为目标持仓
    3. 缓冲带：排名跌出 N + buffer 才卖出
    """

    name = "double_low"
    version = "1.0.0"
    description = "双低轮动策略：价格低 + 溢价率低"

    def __init__(
        self,
        hold_count: int = 10,
        buffer_rank: int = 5,
        max_position_pct: float = 0.10,
    ) -> None:
        self.hold_count = hold_count
        self.buffer_rank = buffer_rank
        self.max_position_pct = max_position_pct

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        df = context.universe
        if df.empty:
            return []

        # 计算双低值
        scored = df.copy()
        scored["double_low"] = scored["cb_close"] + scored["premium_rate"].fillna(0) * 100
        scored = scored.sort_values("double_low").reset_index(drop=True)
        scored["rank"] = range(1, len(scored) + 1)

        signals: list[Signal] = []
        target_codes = set(scored.head(self.hold_count)["cb_code"])
        current_codes = context.portfolio.codes if hasattr(context.portfolio, "codes") else set()

        # 卖出信号：排名跌出 hold_count + buffer 或不在池中
        for code in current_codes:
            rank_rows = scored[scored["cb_code"] == code]
            if rank_rows.empty:
                signals.append(Signal(
                    cb_code=code, direction="sell", weight=0.0,
                    score=0.0, reason="不满足筛选条件",
                ))
            else:
                rank = int(rank_rows.index[0])
                if rank >= self.hold_count + self.buffer_rank:
                    row = rank_rows.iloc[0]
                    signals.append(Signal(
                        cb_code=code, direction="sell", weight=0.0,
                        score=float(row["double_low"]),
                        reason=f"双低排名{rank + 1}(超阈值{self.hold_count + self.buffer_rank})",
                    ))

        # 买入信号
        remaining = current_codes - {s.cb_code for s in signals if s.direction == "sell"}
        slots = max(0, self.hold_count - len(remaining))
        if slots > 0:
            candidates = scored[~scored["cb_code"].isin(remaining)].head(slots)
            for idx, row in candidates.iterrows():
                signals.append(Signal(
                    cb_code=str(row["cb_code"]),
                    direction="buy",
                    weight=self.max_position_pct,
                    score=float(row["double_low"]),
                    reason=f"双低排名第{idx + 1}",
                    metadata={
                        "double_low": float(row["double_low"]),
                        "cb_close": float(row["cb_close"]),
                        "premium_rate": float(row.get("premium_rate", 0) or 0),
                    },
                ))

        # 持有信号
        for code in remaining:
            if code in {s.cb_code for s in signals}:
                continue
            rank_rows = scored[scored["cb_code"] == code]
            if not rank_rows.empty:
                rank = int(rank_rows.index[0])
                signals.append(Signal(
                    cb_code=code, direction="hold",
                    weight=self.max_position_pct,
                    score=float(rank_rows.iloc[0]["double_low"]),
                    reason=f"双低排名第{rank + 1}，继续持有",
                ))

        return signals

    def get_parameters(self) -> dict:
        return {
            "hold_count": self.hold_count,
            "buffer_rank": self.buffer_rank,
            "max_position_pct": self.max_position_pct,
        }

    def set_parameters(self, params: dict) -> None:
        if "hold_count" in params:
            self.hold_count = int(params["hold_count"])
        if "buffer_rank" in params:
            self.buffer_rank = int(params["buffer_rank"])
        if "max_position_pct" in params:
            self.max_position_pct = float(params["max_position_pct"])
