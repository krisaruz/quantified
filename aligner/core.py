"""数据对齐与衍生指标计算引擎

**注意：此模块当前未被 CLI 或 Web 流程使用。**

universe.py 中的 build_universe / build_filtered_ranked 直接查询数据库构建截面，
并未调用本模块的 DataAligner。本模块提供的功能（历史转股价序列构建、连续停牌天数
检测、转债-正股日线时间序列对齐）为未来功能预留（如回测引擎增强、多日截面分析）。

如需启用，可在 universe.py 或 backtest/engine.py 中替换相应的数据查询调用为
DataAligner.align() / DataAligner.align_universe()。

DataAligner:
  - align(): 将单只转债与正股日线按日期合并，处理停牌 ffill，计算衍生指标
  - align_universe(): 全市场截面扫描，输出指定日期所有 ACTIVE 转债的截面数据
"""

from __future__ import annotations

import datetime
import logging

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from vertexquant.models.bond import BondBasic, BondDaily, BondStatus, ConversionPriceHistory
from vertexquant.models.stock import StockBasic, StockDaily

logger = logging.getLogger(__name__)


class DataAligner:
    """数据对齐引擎

    将转债与正股日线按交易日期合并为单一 DataFrame，
    处理停牌场景（ffill），并计算转股价值、溢价率等衍生指标。
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def _query_bond_daily(
        self, cb_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """从数据库查询转债日线"""
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
        stmt = (
            select(BondDaily)
            .where(BondDaily.cb_code == cb_code)
            .where(BondDaily.trade_date >= start)
            .where(BondDaily.trade_date <= end)
            .order_by(BondDaily.trade_date)
        )
        rows = self._session.execute(stmt).scalars().all()
        if not rows:
            return pd.DataFrame()
        records = [
            {
                "date": r.trade_date,
                "cb_open": r.open,
                "cb_high": r.high,
                "cb_low": r.low,
                "cb_close": r.close,
                "cb_volume": r.volume,
                "cb_is_suspended": r.is_suspended,
            }
            for r in rows
        ]
        return pd.DataFrame(records)

    def _query_stock_daily(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """从数据库查询正股日线"""
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)
        stmt = (
            select(StockDaily)
            .where(StockDaily.stock_code == stock_code)
            .where(StockDaily.trade_date >= start)
            .where(StockDaily.trade_date <= end)
            .order_by(StockDaily.trade_date)
        )
        rows = self._session.execute(stmt).scalars().all()
        if not rows:
            return pd.DataFrame()
        records = [
            {
                "date": r.trade_date,
                "stock_open": r.open,
                "stock_high": r.high,
                "stock_low": r.low,
                "stock_close": r.close,
                "stock_volume": r.volume,
                "stock_is_suspended": r.is_suspended,
            }
            for r in rows
        ]
        return pd.DataFrame(records)

    def _get_conv_price_on_date(self, cb_code: str, target_date: datetime.date) -> float | None:
        """获取某日生效的转股价

        查询 change_date <= target_date 的最近一条记录。
        若无记录则 fallback 到 BondBasic.conv_price_latest。
        """
        stmt = (
            select(ConversionPriceHistory.conversion_price)
            .where(ConversionPriceHistory.cb_code == cb_code)
            .where(ConversionPriceHistory.change_date <= target_date)
            .order_by(ConversionPriceHistory.change_date.desc())
            .limit(1)
        )
        result = self._session.execute(stmt).scalar_one_or_none()
        if result is not None:
            return float(result)

        bond = self._session.get(BondBasic, cb_code)
        if bond is not None:
            return float(bond.conv_price_latest)
        return None

    def _build_conv_price_series(
        self, cb_code: str, dates: list[datetime.date]
    ) -> pd.Series:
        """为一组日期构建转股价序列

        查出所有历史变动记录，用 merge_asof 高效匹配每个日期对应的转股价。
        """
        stmt = (
            select(ConversionPriceHistory)
            .where(ConversionPriceHistory.cb_code == cb_code)
            .order_by(ConversionPriceHistory.change_date)
        )
        rows = self._session.execute(stmt).scalars().all()

        if rows:
            cp_df = pd.DataFrame(
                [{"date": r.change_date, "conv_price": r.conversion_price} for r in rows]
            )
            cp_df["date"] = pd.to_datetime(cp_df["date"])
            dates_df = pd.DataFrame({"date": pd.to_datetime(dates)})
            merged = pd.merge_asof(
                dates_df.sort_values("date"),
                cp_df.sort_values("date"),
                on="date",
                direction="backward",
            )
            conv_prices = merged["conv_price"]
        else:
            conv_prices = pd.Series([np.nan] * len(dates), dtype=float)

        # Fallback: 无历史记录的日期用 BondBasic.conv_price_latest 填充
        bond = self._session.get(BondBasic, cb_code)
        if bond is not None:
            conv_prices = conv_prices.fillna(bond.conv_price_latest)

        return conv_prices.reset_index(drop=True)

    @staticmethod
    def _calc_suspended_days(suspended_col: pd.Series) -> pd.Series:
        """计算连续停牌天数

        从 bool 列（True=停牌）计算截至每日的连续停牌天数。
        正常交易日为 0，停牌首日为 1，连续第二日为 2，以此类推。
        """
        groups = (~suspended_col).cumsum()
        return suspended_col.groupby(groups).cumsum().astype(int)

    def align(
        self, cb_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """将转债与正股日线按日期对齐

        合并策略：outer join → ffill 停牌缺失 → 计算衍生指标

        Args:
            cb_code: 转债代码
            start_date: 起始日期（含）
            end_date: 截止日期（含）

        Returns:
            对齐后的 DataFrame，包含价格、停牌标记、连续停牌天数、
            trade_available、conversion_value、premium_rate 列。
        """
        bond = self._session.get(BondBasic, cb_code)
        if bond is None:
            logger.warning("转债 %s 不存在", cb_code)
            return pd.DataFrame()

        cb_df = self._query_bond_daily(cb_code, start_date, end_date)
        stock_df = self._query_stock_daily(bond.stock_code, start_date, end_date)

        if cb_df.empty and stock_df.empty:
            return pd.DataFrame()

        # outer join 合并
        if cb_df.empty:
            merged = stock_df.copy()
            for col in ["cb_open", "cb_high", "cb_low", "cb_close", "cb_volume"]:
                merged[col] = np.nan
            merged["cb_is_suspended"] = True
        elif stock_df.empty:
            merged = cb_df.copy()
            for col in ["stock_open", "stock_high", "stock_low", "stock_close", "stock_volume"]:
                merged[col] = np.nan
            merged["stock_is_suspended"] = True
        else:
            merged = pd.merge(cb_df, stock_df, on="date", how="outer")

        merged = merged.sort_values("date").reset_index(drop=True)

        # 停牌标记：merge 后 NaN 的行即为停牌
        merged["cb_suspended"] = merged["cb_is_suspended"].fillna(True).astype(bool)
        merged["stock_suspended"] = merged["stock_is_suspended"].fillna(True).astype(bool)

        # 前值填充停牌价格
        price_cols = [
            "cb_open", "cb_high", "cb_low", "cb_close", "cb_volume",
            "stock_open", "stock_high", "stock_low", "stock_close", "stock_volume",
        ]
        for col in price_cols:
            if col in merged.columns:
                merged[col] = merged[col].ffill()

        # 连续停牌天数
        merged["cb_suspended_days"] = self._calc_suspended_days(merged["cb_suspended"])
        merged["stock_suspended_days"] = self._calc_suspended_days(merged["stock_suspended"])

        # 双方均未停牌时可交易
        merged["trade_available"] = ~merged["cb_suspended"] & ~merged["stock_suspended"]

        # 衍生指标：转股价值 & 溢价率
        conv_prices = self._build_conv_price_series(cb_code, merged["date"].tolist())
        # 防御除零
        safe_conv_price = conv_prices.replace(0, np.nan)
        merged["conversion_value"] = (100.0 / safe_conv_price) * merged["stock_close"]
        merged["premium_rate"] = merged["cb_close"] / merged["conversion_value"] - 1.0

        # 清理临时列
        merged = merged.drop(columns=["cb_is_suspended", "stock_is_suspended"], errors="ignore")

        return merged

    def align_universe(self, date: str) -> pd.DataFrame:
        """全市场截面扫描

        返回指定日期所有 ACTIVE 转债的截面数据，
        含双低值、停牌标记、基础信息，按 double_low 升序排列。

        使用批量查询替代 N+1 循环查询，提升性能。

        Args:
            date: 目标日期（如 "2025-03-15"）

        Returns:
            全市场截面 DataFrame
        """
        target = datetime.date.fromisoformat(date)

        # 批量查询所有 ACTIVE 转债
        stmt = select(BondBasic).where(BondBasic.status == BondStatus.ACTIVE)
        bonds = self._session.execute(stmt).scalars().all()
        if not bonds:
            return pd.DataFrame()

        bond_codes = [b.cb_code for b in bonds]
        stock_codes = list({b.stock_code for b in bonds})

        # 批量查询当日转债行情（每个 cb_code 取 trade_date <= target 的最新一条）
        cb_rows = {}
        for row in self._session.execute(
            select(BondDaily)
            .where(BondDaily.cb_code.in_(bond_codes))
            .where(BondDaily.trade_date <= target)
            .order_by(BondDaily.trade_date.desc())
        ).scalars().all():
            if row.cb_code not in cb_rows:
                cb_rows[row.cb_code] = row

        # 批量查询当日正股行情（每个 stock_code 取最新一条）
        stock_rows = {}
        for row in self._session.execute(
            select(StockDaily)
            .where(StockDaily.stock_code.in_(stock_codes))
            .where(StockDaily.trade_date <= target)
            .order_by(StockDaily.trade_date.desc())
        ).scalars().all():
            if row.stock_code not in stock_rows:
                stock_rows[row.stock_code] = row

        # 批量查询正股基础信息
        stock_basics = {
            sb.stock_code: sb
            for sb in self._session.execute(
                select(StockBasic).where(StockBasic.stock_code.in_(stock_codes))
            ).scalars().all()
        }

        # 批量查询转股价历史（取每个 cb_code 在 target 之前最新的）
        conv_prices = {}
        for row in self._session.execute(
            select(ConversionPriceHistory)
            .where(ConversionPriceHistory.cb_code.in_(bond_codes))
            .where(ConversionPriceHistory.change_date <= target)
            .order_by(ConversionPriceHistory.change_date.desc())
        ).scalars().all():
            if row.cb_code not in conv_prices:
                conv_prices[row.cb_code] = row.conversion_price

        # Fallback: 从 BondBasic 取最新转股价
        for bond in bonds:
            if bond.cb_code not in conv_prices and bond.conv_price_latest:
                conv_prices[bond.cb_code] = bond.conv_price_latest

        # 组装记录
        records: list[dict] = []
        for bond in bonds:
            cb_row = cb_rows.get(bond.cb_code)
            stock_row = stock_rows.get(bond.stock_code)

            if cb_row is None or stock_row is None:
                continue

            cb_suspended = cb_row.is_suspended or (cb_row.trade_date != target)
            stock_suspended = stock_row.is_suspended or (stock_row.trade_date != target)
            trade_available = not cb_suspended and not stock_suspended

            conv_price = conv_prices.get(bond.cb_code)
            if conv_price and conv_price > 0:
                conversion_value = (100.0 / conv_price) * stock_row.close
                premium_rate = cb_row.close / conversion_value - 1.0
            else:
                conversion_value = np.nan
                premium_rate = np.nan

            double_low = cb_row.close + premium_rate * 100 if not np.isnan(premium_rate) else np.nan

            stock_basic = stock_basics.get(bond.stock_code)

            records.append(
                {
                    "cb_code": bond.cb_code,
                    "cb_name": bond.cb_name,
                    "cb_close": cb_row.close,
                    "stock_close": stock_row.close,
                    "conversion_value": conversion_value,
                    "premium_rate": premium_rate,
                    "double_low": double_low,
                    "trade_available": trade_available,
                    "maturity_date": bond.maturity_date,
                    "issue_size": bond.issue_size,
                    "credit_rating": bond.credit_rating,
                    "is_st": stock_basic.is_st if stock_basic else None,
                    "cb_suspended_days": 0 if not cb_suspended else 1,
                    "stock_suspended_days": 0 if not stock_suspended else 1,
                }
            )

        if not records:
            return pd.DataFrame()

        result = pd.DataFrame(records)
        result = result.sort_values("double_low", ascending=True, na_position="last")
        result = result.reset_index(drop=True)

        logger.info("截面扫描 %s: %d 只 ACTIVE 转债", date, len(result))
        return result
