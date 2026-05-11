"""价值精选策略：选择信用好、价格低、到期收益率高的转债"""

from __future__ import annotations

import logging

import pandas as pd

from vertexquant.strategy.protocol import Signal, StrategyContext
from vertexquant.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register("value")
class ValueStrategy:
    """价值精选策略

    策略逻辑：
    1. 综合信用评级、价格、到期收益率评分
    2. 偏好：高评级 + 低价格 + 高 YTM
    3. 排除高溢价率标的
    """

    name = "value"
    version = "1.0.0"
    description = "价值精选策略：高评级、低价格、高收益"

    def __init__(
        self,
        hold_count: int = 10,
        max_premium_rate: float = 0.5,
        min_credit_rating: str = "AA-",
        max_position_pct: float = 0.10,
    ) -> None:
        self.hold_count = hold_count
        self.max_premium_rate = max_premium_rate
        self.min_credit_rating = min_credit_rating
        self.max_position_pct = max_position_pct

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        df = context.universe
        if df.empty:
            return []

        candidates = df.copy()

        # 过滤高溢价率
        if "premium_rate" in candidates.columns:
            candidates = candidates[candidates["premium_rate"].fillna(0) <= self.max_premium_rate]

        if candidates.empty:
            return []

        # 计算价值得分
        scored = candidates.copy()

        # 价格因子：越低越好
        if "cb_close" in scored.columns:
            price_score = (scored["cb_close"].max() - scored["cb_close"]) / (
                scored["cb_close"].max() - scored["cb_close"].min() + 0.01
            )
        else:
            price_score = 0.0

        # 信用因子：评级越高越好
        from vertexquant.config import RATING_ORDER

        def rating_score(rating):
            if not rating or rating not in RATING_ORDER:
                return 0.0
            return 1.0 - RATING_ORDER.index(rating) / len(RATING_ORDER)

        if "credit_rating" in scored.columns:
            credit_score = scored["credit_rating"].apply(rating_score)
        else:
            credit_score = 0.0

        # 溢价率因子：越低越好
        if "premium_rate" in scored.columns:
            prem = scored["premium_rate"].fillna(0)
            prem_score = 1.0 - (prem - prem.min()) / (prem.max() - prem.min() + 0.01)
        else:
            prem_score = 0.5

        # 综合得分
        scored["value_score"] = price_score * 0.4 + credit_score * 0.3 + prem_score * 0.3
        scored = scored.sort_values("value_score", ascending=False).reset_index(drop=True)

        signals: list[Signal] = []
        current_codes = context.portfolio.codes if hasattr(context.portfolio, "codes") else set()
        target_codes = set(scored.head(self.hold_count)["cb_code"])

        # 卖出信号
        for code in current_codes:
            if code not in target_codes:
                signals.append(Signal(
                    cb_code=code, direction="sell", weight=0.0,
                    score=0.0, reason="价值排名下降，卖出",
                ))

        # 买入信号
        remaining = current_codes - {s.cb_code for s in signals if s.direction == "sell"}
        slots = max(0, self.hold_count - len(remaining))
        if slots > 0:
            buy_candidates = scored[~scored["cb_code"].isin(remaining)].head(slots)
            for idx, row in buy_candidates.iterrows():
                signals.append(Signal(
                    cb_code=str(row["cb_code"]),
                    direction="buy",
                    weight=self.max_position_pct,
                    score=float(row["value_score"]),
                    reason=f"价值排名第{idx + 1}",
                    metadata={
                        "value_score": float(row["value_score"]),
                        "cb_close": float(row.get("cb_close", 0)),
                        "credit_rating": str(row.get("credit_rating", "")),
                    },
                ))

        return signals

    def get_parameters(self) -> dict:
        return {
            "hold_count": self.hold_count,
            "max_premium_rate": self.max_premium_rate,
            "min_credit_rating": self.min_credit_rating,
            "max_position_pct": self.max_position_pct,
        }

    def set_parameters(self, params: dict) -> None:
        if "hold_count" in params:
            self.hold_count = int(params["hold_count"])
        if "max_premium_rate" in params:
            self.max_premium_rate = float(params["max_premium_rate"])
        if "min_credit_rating" in params:
            self.min_credit_rating = str(params["min_credit_rating"])
        if "max_position_pct" in params:
            self.max_position_pct = float(params["max_position_pct"])
