"""多数据源容错管理

提供数据源健康检查和自动故障转移。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd

from quantified.fetcher.protocol import DataFetchError, IDataFetcher


@dataclass(frozen=True)
class DataSourceHealth:
    """数据源健康状态"""

    name: str
    is_healthy: bool
    last_check: str | None
    consecutive_failures: int
    last_error: str | None


class DataSourceManager:
    """多数据源管理器

    按优先级依次尝试各数据源，第一个成功即返回。
    自动跟踪数据源健康状态。
    """

    def __init__(
        self,
        sources: list[IDataFetcher],
        names: list[str] | None = None,
    ) -> None:
        self.sources = sources
        self._names = names or [f"source_{i}" for i in range(len(sources))]
        self._health: dict[str, DataSourceHealth] = {}
        self._failures: dict[str, int] = {name: 0 for name in self._names}

    def fetch_bond_list(self) -> pd.DataFrame:
        """依次尝试获取转债列表"""
        return self._try_sources("fetch_bond_list")

    def fetch_bond_daily(
        self, cb_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """依次尝试获取转债日线"""
        return self._try_sources(
            "fetch_bond_daily", cb_code, start_date, end_date
        )

    def fetch_stock_daily(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """依次尝试获取股票日线"""
        return self._try_sources(
            "fetch_stock_daily", stock_code, start_date, end_date
        )

    def fetch_conv_price_history(self, cb_code: str) -> pd.DataFrame:
        """依次尝试获取转股价历史"""
        return self._try_sources("fetch_conv_price_history", cb_code)

    def get_health_status(self) -> dict[str, DataSourceHealth]:
        """获取所有数据源健康状态"""
        return dict(self._health)

    def get_healthy_sources(self) -> list[str]:
        """获取健康的数据源名称"""
        return [
            name for name, h in self._health.items()
            if h.is_healthy
        ]

    def _try_sources(
        self, method: str, *args: Any
    ) -> pd.DataFrame:
        """依次尝试各数据源"""
        last_error: Exception | None = None

        for source, name in zip(self.sources, self._names):
            try:
                fn = getattr(source, method)
                result = fn(*args)
                if isinstance(result, pd.DataFrame) and not result.empty:
                    self._mark_healthy(name)
                    return result
                elif isinstance(result, pd.DataFrame):
                    # 空结果不算失败，但跳过
                    continue
            except (DataFetchError, Exception) as e:
                self._mark_unhealthy(name, e)
                last_error = e
                continue

        raise DataFetchError(
            f"所有数据源均失败 (method={method}): {last_error}"
        )

    def _mark_healthy(self, name: str) -> None:
        """标记数据源健康"""
        self._failures[name] = 0
        from datetime import datetime

        self._health[name] = DataSourceHealth(
            name=name,
            is_healthy=True,
            last_check=datetime.now().isoformat(),
            consecutive_failures=0,
            last_error=None,
        )

    def _mark_unhealthy(self, name: str, error: Exception) -> None:
        """标记数据源不健康"""
        self._failures[name] = self._failures.get(name, 0) + 1
        from datetime import datetime

        self._health[name] = DataSourceHealth(
            name=name,
            is_healthy=False,
            last_check=datetime.now().isoformat(),
            consecutive_failures=self._failures[name],
            last_error=str(error),
        )
