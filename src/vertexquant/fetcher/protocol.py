"""数据获取协议与异常定义

IDataFetcher: 可插拔数据源的 Protocol（结构化子类型），
              任何实现了相同方法签名的类自动满足协议，无需显式继承。
DataFetchError: 统一的数据获取异常，封装网络错误和接口变更。
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import pandas as pd


class DataFetchError(Exception):
    """数据获取异常

    封装 AkShare 或其他数据源的底层异常（网络超时、接口变更等），
    上层代码只需捕获此异常即可。
    """

    pass


@runtime_checkable
class IDataFetcher(Protocol):
    """数据获取协议

    定义四个核心方法，任何数据源实现（AkShare/Tushare/集思录）
    只需提供相同签名即可被策略层消费。

    返回的 DataFrame 列名统一为英文蛇形命名。
    """

    def fetch_bond_list(self) -> pd.DataFrame:
        """获取全市场可转债基础信息列表

        Returns:
            包含 cb_code, cb_name, stock_code, list_date, maturity_date,
            conv_price_latest, issue_size, credit_rating 等列的 DataFrame
        """
        ...

    def fetch_bond_daily(self, cb_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只转债的日线行情

        Args:
            cb_code: 转债代码（如 "123001"）
            start_date: 起始日期（如 "2025-01-01"）
            end_date: 截止日期（如 "2025-12-31"）

        Returns:
            包含 trade_date, open, high, low, close, volume, turnover 的 DataFrame，
            按 trade_date 升序。
        """
        ...

    def fetch_stock_daily(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """获取单只正股的前复权日线行情

        Args:
            stock_code: 正股代码（如 "600000"）
            start_date: 起始日期
            end_date: 截止日期

        Returns:
            包含 trade_date, open, high, low, close, volume, turnover, adj_factor 的 DataFrame
        """
        ...

    def fetch_conv_price_history(self, cb_code: str) -> pd.DataFrame:
        """获取单只转债的转股价变动历史

        Args:
            cb_code: 转债代码

        Returns:
            包含 change_date, conversion_price, reason 的 DataFrame。
            若无变动记录则返回空 DataFrame。
        """
        ...
