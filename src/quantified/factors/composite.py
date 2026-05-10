"""复合因子：多因子加权合成"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from quantified.strategy.factor_registry import FactorRegistry

logger = logging.getLogger(__name__)


class CompositeFactor:
    """复合因子：多个因子加权合成

    用法：
        composite = CompositeFactor({
            "double_low": 0.4,
            "credit_score": 0.3,
            "momentum_20d": 0.2,
            "volatility_20d": 0.1,
        })
        scores = composite.compute(df)
    """

    def __init__(self, factor_weights: dict[str, float]) -> None:
        self.factor_weights = factor_weights
        self.name = "composite"
        self.category = "composite"
        self.description = f"复合因子({len(factor_weights)}个子因子)"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算复合因子值

        各因子先做截面标准化（z-score），再加权求和。
        """
        result = pd.Series(0.0, index=df.index)
        total_weight = 0.0

        for factor_name, weight in self.factor_weights.items():
            if weight == 0:
                continue
            try:
                factor = FactorRegistry.get(factor_name)
                values = factor.compute(df)
                # z-score 标准化
                mean = values.mean()
                std = values.std()
                if std > 0:
                    normalized = (values - mean) / std
                else:
                    normalized = 0.0
                result += normalized.fillna(0) * weight
                total_weight += abs(weight)
            except KeyError:
                logger.warning("因子 '%s' 未注册，跳过", factor_name)
            except Exception as e:
                logger.warning("因子 '%s' 计算失败: %s", factor_name, e)

        if total_weight > 0:
            result /= total_weight

        return result

    def compute_single(self, row: pd.Series) -> float:
        """计算单行复合因子值"""
        result = 0.0
        total_weight = 0.0

        for factor_name, weight in self.factor_weights.items():
            if weight == 0:
                continue
            try:
                factor = FactorRegistry.get(factor_name)
                result += factor.compute_single(row) * weight
                total_weight += abs(weight)
            except (KeyError, Exception):
                pass

        return result / total_weight if total_weight > 0 else 0.0
