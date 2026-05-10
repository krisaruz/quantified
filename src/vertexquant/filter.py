"""过滤器链：按可配置规则逐层筛除不合格标的

每个过滤器是一个独立函数 (DataFrame, AppConfig) -> DataFrame。
FilterChain 按配置顺序依次执行，记录每步过滤审计日志。
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

import pandas as pd

from vertexquant.config import AppConfig, RATING_ORDER, rating_ge

logger = logging.getLogger(__name__)


@dataclass
class FilterStep:
    """一次过滤的审计记录"""

    name: str
    before_count: int
    after_count: int
    removed: list[str] = field(default_factory=list)


def filter_delisted(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if "status" not in df.columns:
        return df
    return df[df["status"] != "delisted"]


def filter_st(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if not config.filters.exclude_st:
        return df
    if "is_st" not in df.columns:
        return df
    return df[~df["is_st"].fillna(False).astype(bool)]


def filter_issue_size(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if "issue_size" not in df.columns:
        return df
    return df[df["issue_size"] >= config.filters.min_issue_size]


def filter_remaining_years(
    df: pd.DataFrame, config: AppConfig, *, as_of: datetime.date | None = None,
) -> pd.DataFrame:
    if "maturity_date" not in df.columns:
        return df
    ref = as_of or datetime.date.today()
    df = df.copy()
    df["_remaining_years"] = df["maturity_date"].apply(
        lambda d: (d - ref).days / 365.25 if isinstance(d, datetime.date) else 999
    )
    result = df[df["_remaining_years"] >= config.filters.min_remaining_years]
    return result.drop(columns=["_remaining_years"])

filter_remaining_years._date_aware = True


def filter_max_price(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if "cb_close" not in df.columns:
        return df
    return df[df["cb_close"] <= config.filters.max_price]


def filter_credit_rating(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if "credit_rating" not in df.columns:
        return df
    min_r = config.filters.min_credit_rating
    valid_ratings = set(RATING_ORDER[: RATING_ORDER.index(min_r) + 1])
    return df[df["credit_rating"].isin(valid_ratings)]


def filter_redeeming(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if not config.filters.exclude_redeeming:
        return df
    if "status" not in df.columns:
        return df
    return df[df["status"] != "redeem_warning"]


def filter_suspended(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    if not config.filters.exclude_suspended:
        return df
    if "trade_available" not in df.columns:
        return df
    return df[df["trade_available"].fillna(False).astype(bool)]


def filter_min_turnover(df: pd.DataFrame, config: AppConfig) -> pd.DataFrame:
    """排除成交额过低的标的（流动性不足）"""
    min_to = getattr(config.filters, "min_turnover", 0)
    if min_to <= 0:
        return df
    if "cb_volume" not in df.columns:
        return df
    # cb_volume 来自 BondDaily.volume，通过 universe 查询携带
    # 如果没有成交额，用成交量作为近似判断
    return df[df["cb_volume"].fillna(0) >= min_to]


ALL_FILTERS = [
    ("排除已退市", filter_delisted),
    ("排除ST正股", filter_st),
    ("排除规模过小", filter_issue_size),
    ("排除即将到期", filter_remaining_years),
    ("排除价格过高", filter_max_price),
    ("排除评级过低", filter_credit_rating),
    ("排除强赎中", filter_redeeming),
    ("排除停牌", filter_suspended),
    ("排除流动性不足", filter_min_turnover),
]


class FilterChain:
    """可配置过滤器链"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def apply(
        self, df: pd.DataFrame, *, as_of: datetime.date | None = None,
    ) -> tuple[pd.DataFrame, list[FilterStep]]:
        """执行全部过滤器，返回 (过滤后的 DataFrame, 审计日志)"""
        audit: list[FilterStep] = []
        result = df.copy()
        cb_code_col = "cb_code" if "cb_code" in result.columns else None

        for name, fn in ALL_FILTERS:
            before = len(result)
            before_codes = set(result[cb_code_col]) if cb_code_col else set()

            if getattr(fn, "_date_aware", False) and as_of is not None:
                result = fn(result, self.config, as_of=as_of)
            else:
                result = fn(result, self.config)
            result = result.reset_index(drop=True)

            after = len(result)
            after_codes = set(result[cb_code_col]) if cb_code_col else set()
            removed = sorted(before_codes - after_codes)

            audit.append(FilterStep(
                name=name, before_count=before, after_count=after, removed=removed,
            ))
            logger.debug("%s: %d → %d (-%d)", name, before, after, before - after)

        return result, audit
