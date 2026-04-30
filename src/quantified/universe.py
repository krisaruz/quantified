"""统一的转债截面数据构建

CLI 和 Web 共用同一个函数，避免数据不一致。
从数据库读取转债基础信息+日线行情，计算转股价值和溢价率。
"""

from __future__ import annotations

import datetime

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from quantified.models.bond import BondBasic, BondDaily
from quantified.models.stock import StockBasic, StockDaily


def build_universe(session: Session, trade_date: str) -> pd.DataFrame:
    """构建指定日期的全市场转债截面数据

    Args:
        session: SQLAlchemy session
        trade_date: ISO 格式日期字符串 (YYYY-MM-DD)

    Returns:
        DataFrame with columns: cb_code, cb_name, stock_code, conv_price_latest,
        issue_size, credit_rating, status, maturity_date, cb_close, cb_volume,
        stock_close, is_st, conversion_value, premium_rate, trade_available
    """
    td = datetime.date.fromisoformat(trade_date)

    rows = (
        session.query(
            BondBasic.cb_code,
            BondBasic.cb_name,
            BondBasic.stock_code,
            BondBasic.conv_price_latest,
            BondBasic.issue_size,
            BondBasic.credit_rating,
            BondBasic.status,
            BondBasic.maturity_date,
            BondDaily.close.label("cb_close"),
            BondDaily.volume.label("cb_volume"),
            StockDaily.close.label("stock_close"),
            StockBasic.is_st,
        )
        .join(BondDaily, (BondBasic.cb_code == BondDaily.cb_code) & (BondDaily.trade_date == td))
        .outerjoin(StockDaily, (BondBasic.stock_code == StockDaily.stock_code) & (StockDaily.trade_date == td))
        .outerjoin(StockBasic, BondBasic.stock_code == StockBasic.stock_code)
        .all()
    )

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=[
        "cb_code", "cb_name", "stock_code", "conv_price_latest",
        "issue_size", "credit_rating", "status", "maturity_date",
        "cb_close", "cb_volume", "stock_close", "is_st",
    ])

    valid = (
        df["conv_price_latest"].notna() & (df["conv_price_latest"] > 0)
        & df["stock_close"].notna() & (df["stock_close"] > 0)
    )
    df["conversion_value"] = np.where(
        valid,
        100.0 / df["conv_price_latest"] * df["stock_close"],
        np.nan,
    )
    cv_valid = valid & (df["conversion_value"] > 0)
    df["premium_rate"] = np.where(
        cv_valid,
        df["cb_close"] / df["conversion_value"] - 1.0,
        np.nan,
    )
    df["trade_available"] = df["cb_volume"].notna() & (df["cb_volume"] > 0)

    return df


def build_filtered_ranked(
    session: Session,
    trade_date: str,
    config,
) -> tuple[pd.DataFrame, pd.DataFrame, list]:
    """构建过滤+排序后的截面数据

    Returns:
        (universe_raw, filtered_ranked, filter_audit)
    """
    from quantified.filter import FilterChain

    universe = build_universe(session, trade_date)
    if universe.empty:
        return universe, universe, []

    td = datetime.date.fromisoformat(trade_date)

    chain = FilterChain(config)
    filtered, audit = chain.apply(universe, as_of=td)

    if not filtered.empty and "cb_close" in filtered.columns and "premium_rate" in filtered.columns:
        from quantified.scoring import compute_composite_score, assign_risk_level

        filtered = filtered.copy()
        filtered["double_low"] = filtered["cb_close"] + filtered["premium_rate"] * 100
        filtered["composite_score"] = compute_composite_score(filtered, config, as_of=td)
        filtered["risk_level"] = assign_risk_level(filtered, as_of=td)
        filtered = filtered.sort_values("composite_score").reset_index(drop=True)
        filtered["rank"] = range(1, len(filtered) + 1)

    return universe, filtered, audit
