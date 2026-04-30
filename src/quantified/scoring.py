"""多因子综合评分与风险等级

替代简单的 double_low = price + premium_rate * 100 排名。
增加信用质量、到期时间、债底保护三个因子，提升选债准确性。
同时为每只转债标记风险等级 (low / medium / high)。
"""

from __future__ import annotations

import datetime

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
    scoring_cfg = getattr(config.strategy, "scoring", None) or {}
    credit_w = scoring_cfg.get("credit", {}) if isinstance(scoring_cfg, dict) else {}
    maturity_w = scoring_cfg.get("maturity", {}) if isinstance(scoring_cfg, dict) else {}
    floor_w = scoring_cfg.get("bond_floor", {}) if isinstance(scoring_cfg, dict) else {}

    ref = as_of or datetime.date.today()

    base = df["cb_close"] + df["premium_rate"].fillna(0) * 100

    credit = df["credit_rating"].apply(lambda r: _credit_penalty(r, credit_w))

    maturity = df["maturity_date"].apply(
        lambda d: _maturity_penalty(_remaining_years(d, ref), maturity_w)
    ) if "maturity_date" in df.columns else pd.Series(0, index=df.index)

    floor = df["cb_close"].apply(lambda p: _bond_floor_bonus(p, floor_w))

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
    results = []

    for _, row in df.iterrows():
        price = row.get("cb_close", 0) or 0
        prem = row.get("premium_rate", 0) or 0
        rating = row.get("credit_rating", "")
        maturity = row.get("maturity_date")
        remaining = _remaining_years(maturity, ref) if maturity else 999

        rating_idx = RATING_ORDER.index(rating) if rating in RATING_ORDER else 99

        is_high = (
            price > 130
            or prem > 0.6
            or rating_idx > RATING_ORDER.index("AA-")
            or remaining < 0.8
        )
        is_low = (
            price <= 110
            and prem <= 0.2
            and rating_idx <= RATING_ORDER.index("AA")
            and remaining >= 2
        )

        if is_high:
            results.append("high")
        elif is_low:
            results.append("low")
        else:
            results.append("medium")

    return pd.Series(results, index=df.index)


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
