"""多因子综合评分与风险等级

替代简单的 double_low = price + premium_rate * 100 排名。
增加信用质量、到期时间、债底保护三个因子，提升选债准确性。
同时为每只转债标记风险等级 (low / medium / high)。
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd

from quantified.config import AppConfig, RATING_ORDER

CREDIT_SCORE_MAP: dict[str, float] = {
    "AAA": -3.0,
    "AA+": -1.5,
    "AA": 0.0,
    "AA-": 2.0,
    "A+": 5.0,
    "A": 7.0,
    "A-": 9.0,
    "BBB+": 12.0,
    "BBB": 15.0,
}


def _remaining_years(maturity_date, today: datetime.date | None = None) -> float:
    """计算剩余年限"""
    today = today or datetime.date.today()
    if isinstance(maturity_date, datetime.date):
        return (maturity_date - today).days / 365.25
    return 999.0


def _credit_penalty(rating: str | None, weights: dict) -> float:
    """信用因子：高评级奖励，低评级惩罚"""
    if not rating:
        return weights.get("unknown", 5.0)
    return CREDIT_SCORE_MAP.get(rating, weights.get("unknown", 5.0))


def _maturity_penalty(remaining: float, weights: dict) -> float:
    """到期日因子：短期转债惩罚（时间价值衰减）"""
    if remaining > 4:
        return weights.get("long", -2.0)
    if remaining > 2:
        return 0.0
    if remaining > 1:
        return weights.get("short", 3.0)
    return weights.get("very_short", 8.0)


def _bond_floor_bonus(price: float, weights: dict) -> float:
    """债底保护因子：低于面值的转债有强保底"""
    if price < 100:
        return weights.get("below_par", -5.0)
    if price <= 105:
        return weights.get("near_par", -2.0)
    if price <= 110:
        return 0.0
    return (price - 110) * weights.get("above_scale", 0.15)


def compute_composite_score(
    df: pd.DataFrame, config: AppConfig, *, as_of: datetime.date | None = None,
) -> pd.Series:
    """计算多因子综合评分

    composite_score = base_double_low + credit_penalty + maturity_penalty + bond_floor_bonus

    分数越低越好（和 double_low 一样），低分 = 高性价比。
    """
    scoring = config.strategy.scoring
    credit_w = scoring.credit
    maturity_w = scoring.maturity
    floor_w = scoring.bond_floor

    ref = as_of or datetime.date.today()

    base = df["cb_close"] + df["premium_rate"].fillna(0) * 100

    # Credit penalty: vectorized map
    unknown_credit = credit_w.get("unknown", 5.0) if isinstance(credit_w, dict) else 5.0
    credit = df["credit_rating"].map(CREDIT_SCORE_MAP).fillna(unknown_credit)

    # Maturity penalty: vectorized with np.select
    if "maturity_date" in df.columns:
        remaining_days = df["maturity_date"].apply(
            lambda d: (d - ref).days if isinstance(d, datetime.date) else 999 * 365
        )
        remaining_years = remaining_days / 365.25
        long_w = maturity_w.get("long", -2.0) if isinstance(maturity_w, dict) else -2.0
        short_w = maturity_w.get("short", 3.0) if isinstance(maturity_w, dict) else 3.0
        very_short_w = maturity_w.get("very_short", 8.0) if isinstance(maturity_w, dict) else 8.0
        maturity = np.select(
            [remaining_years > 4, remaining_years > 2, remaining_years > 1],
            [long_w, 0.0, short_w],
            default=very_short_w,
        ).astype(float)
    else:
        maturity = 0.0

    # Bond floor bonus: vectorized with np.select
    price = df["cb_close"]
    below_par_w = floor_w.get("below_par", -5.0) if isinstance(floor_w, dict) else -5.0
    near_par_w = floor_w.get("near_par", -2.0) if isinstance(floor_w, dict) else -2.0
    above_scale = floor_w.get("above_scale", 0.15) if isinstance(floor_w, dict) else 0.15
    floor = np.select(
        [price < 100, price <= 105, price <= 110],
        [below_par_w, near_par_w, 0.0],
        default=(price - 110) * above_scale,
    ).astype(float)

    return base + credit + maturity + floor


def assign_risk_level(
    df: pd.DataFrame, *, as_of: datetime.date | None = None,
) -> pd.Series:
    """为每只转债标记风险等级

    - low: 价格<=110, 溢价率<=20%, 信用>=AA, 剩余>=2年
    - high: 价格>130 或 溢价率>60% 或 信用<AA- 或 剩余<0.8年
    - medium: 其余
    """
    ref = as_of or datetime.date.today()

    price = df["cb_close"].fillna(0)
    prem = df["premium_rate"].fillna(0)

    # Rating index calculation
    def get_rating_idx(r):
        return RATING_ORDER.index(r) if r in RATING_ORDER else 99
    rating_idx = df["credit_rating"].fillna("").apply(get_rating_idx)

    # Remaining years calculation
    if "maturity_date" in df.columns:
        remaining_years = df["maturity_date"].apply(
            lambda d: (d - ref).days / 365.25 if isinstance(d, datetime.date) else 999
        )
    else:
        remaining_years = pd.Series(999.0, index=df.index)

    # Vectorized risk level assignment
    aa_idx = RATING_ORDER.index("AA")
    aa_minus_idx = RATING_ORDER.index("AA-")

    is_high = (
        (price > 130)
        | (prem > 0.6)
        | (rating_idx > aa_minus_idx)
        | (remaining_years < 0.8)
    )
    is_low = (
        (price <= 110)
        & (prem <= 0.2)
        & (rating_idx <= aa_idx)
        & (remaining_years >= 2)
    )

    return pd.Series(
        np.select([is_high, is_low], ["high", "low"], default="medium"),
        index=df.index,
    )


def describe_score_factors(row: pd.Series) -> str:
    """为一只转债生成自然语言的评分描述

    用于建议原因，让无金融背景用户也能理解。
    """
    parts = []
    price = row.get("cb_close", 0) or 0
    prem = row.get("premium_rate", 0) or 0
    rating = row.get("credit_rating", "")
    maturity = row.get("maturity_date")
    remaining = _remaining_years(maturity) if maturity else None

    if price < 100:
        parts.append(f"价格{price:.1f}元(低于面值，有保底)")
    elif price <= 110:
        parts.append(f"价格{price:.1f}元(便宜)")
    elif price <= 120:
        parts.append(f"价格{price:.1f}元(适中)")
    else:
        parts.append(f"价格{price:.1f}元(偏高)")

    if prem < 0:
        parts.append(f"溢价率{prem:.1%}(折价，有套利空间)")
    elif prem <= 0.1:
        parts.append(f"溢价率{prem:.1%}(很低)")
    elif prem <= 0.3:
        parts.append(f"溢价率{prem:.1%}(正常)")
    else:
        parts.append(f"溢价率{prem:.1%}(偏高)")

    if rating:
        if rating in ("AAA", "AA+"):
            parts.append(f"{rating}评级(优秀)")
        elif rating == "AA":
            parts.append(f"{rating}评级(良好)")
        else:
            parts.append(f"{rating}评级")

    if remaining is not None and remaining < 999:
        if remaining > 4:
            parts.append(f"剩余{remaining:.1f}年(充裕)")
        elif remaining > 2:
            parts.append(f"剩余{remaining:.1f}年")
        elif remaining > 1:
            parts.append(f"剩余{remaining:.1f}年(较短)")
        else:
            parts.append(f"剩余{remaining:.1f}年(即将到期)")

    return "、".join(parts)
