"""价值因子

double_low: 双低值 = cb_close + premium_rate * 100
pure_bond_premium: 纯债溢价率
ytm: 到期收益率（近似）
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from vertexquant.strategy.factor_registry import FactorRegistry


@FactorRegistry.register("double_low", category="value")
class DoubleLowFactor:
    """双低值因子：价格 + 溢价率 * 100，越低越好"""

    name = "double_low"
    category = "value"
    description = "双低值 = 转债价格 + 转股溢价率 * 100"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        price = df["cb_close"]
        premium = df["premium_rate"].fillna(0)
        return price + premium * 100

    def compute_single(self, row: pd.Series) -> float:
        price = row.get("cb_close", 0)
        premium = row.get("premium_rate", 0) or 0
        return price + premium * 100


@FactorRegistry.register("pure_bond_premium", category="value")
class PureBondPremiumFactor:
    """纯债溢价率因子：(转债价格 - 纯债价值) / 纯债价值

    纯债价值近似为面值 100 元（简化模型）。
    越低表示越接近债底，安全边际越高。
    """

    name = "pure_bond_premium"
    category = "value"
    description = "纯债溢价率，越低越有安全边际"

    par_value: float = 100.0

    def compute(self, df: pd.DataFrame) -> pd.Series:
        price = df["cb_close"]
        return (price - self.par_value) / self.par_value

    def compute_single(self, row: pd.Series) -> float:
        price = row.get("cb_close", 0)
        return (price - self.par_value) / self.par_value


@FactorRegistry.register("ytm_approx", category="value")
class YTMApproxFactor:
    """到期收益率近似因子

    简化公式：YTM ≈ (面值 / 转债价格 - 1) / 剩余年限
    越高越好（收益率越高越有价值）。
    """

    name = "ytm_approx"
    category = "value"
    description = "到期收益率近似值"

    par_value: float = 100.0
    coupon_rate: float = 0.02  # 假设票面利率 2%

    def compute(self, df: pd.DataFrame) -> pd.Series:
        price = df["cb_close"]
        if "maturity_date" in df.columns:
            today = datetime.date.today()
            remaining = df["maturity_date"].apply(
                lambda d: max((d - today).days / 365.25, 0.1) if isinstance(d, datetime.date) else 5.0
            )
        else:
            remaining = 5.0
        # 简化 YTM 计算
        ytm = (self.par_value / price - 1 + self.coupon_rate * remaining) / remaining
        return ytm

    def compute_single(self, row: pd.Series) -> float:
        price = row.get("cb_close", 100)
        maturity = row.get("maturity_date")
        if isinstance(maturity, datetime.date):
            remaining = max((maturity - datetime.date.today()).days / 365.25, 0.1)
        else:
            remaining = 5.0
        return (self.par_value / price - 1 + self.coupon_rate * remaining) / remaining
