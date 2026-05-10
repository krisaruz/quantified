"""质量因子

credit_score: 信用评级得分
issue_size_score: 发行规模得分
maturity_score: 剩余期限得分
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from vertexquant.config import RATING_ORDER
from vertexquant.strategy.factor_registry import FactorRegistry


@FactorRegistry.register("credit_score", category="quality")
class CreditScoreFactor:
    """信用评级因子：评级越高（AAA 最好），得分越低"""

    name = "credit_score"
    category = "quality"
    description = "信用评级得分，越低越好"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "credit_rating" not in df.columns:
            return pd.Series(np.nan, index=df.index)

        def _rating_to_score(rating: str | None) -> float:
            if not rating or rating not in RATING_ORDER:
                return len(RATING_ORDER)  # 无评级给最差分
            return RATING_ORDER.index(rating)

        return df["credit_rating"].apply(_rating_to_score)

    def compute_single(self, row: pd.Series) -> float:
        rating = row.get("credit_rating")
        if not rating or rating not in RATING_ORDER:
            return float(len(RATING_ORDER))
        return float(RATING_ORDER.index(rating))


@FactorRegistry.register("issue_size_score", category="quality")
class IssueSizeScoreFactor:
    """发行规模因子：规模越大流动性越好，得分越低"""

    name = "issue_size_score"
    category = "quality"
    description = "发行规模得分，规模越大越好（得分越低）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "issue_size" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        # 取负值，规模越大得分越低
        return -df["issue_size"].fillna(0)

    def compute_single(self, row: pd.Series) -> float:
        return -(row.get("issue_size", 0) or 0)


@FactorRegistry.register("maturity_score", category="quality")
class MaturityScoreFactor:
    """剩余期限因子：期限越长时间价值越高，得分越低

    期限 < 1 年：重罚
    期限 1-2 年：小罚
    期限 2-4 年：中性
    期限 > 4 年：奖励
    """

    name = "maturity_score"
    category = "quality"
    description = "剩余期限得分，越长越好（得分越低）"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "maturity_date" not in df.columns:
            return pd.Series(0.0, index=df.index)

        today = datetime.date.today()

        def _maturity_penalty(d: datetime.date | None) -> float:
            if not isinstance(d, datetime.date):
                return 8.0
            remaining = (d - today).days / 365.25
            if remaining > 4:
                return -2.0
            if remaining > 2:
                return 0.0
            if remaining > 1:
                return 3.0
            return 8.0

        return df["maturity_date"].apply(_maturity_penalty)

    def compute_single(self, row: pd.Series) -> float:
        maturity = row.get("maturity_date")
        if not isinstance(maturity, datetime.date):
            return 8.0
        remaining = (maturity - datetime.date.today()).days / 365.25
        if remaining > 4:
            return -2.0
        if remaining > 2:
            return 0.0
        if remaining > 1:
            return 3.0
        return 8.0
