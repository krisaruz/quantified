"""基准管理

提供基准数据加载、对齐和比较功能。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class BenchmarkComparison:
    """基准对比结果"""

    benchmark_name: str
    portfolio_annual_return: float
    benchmark_annual_return: float
    excess_return: float
    tracking_error: float
    information_ratio: float
    beta: float
    alpha: float
    correlation: float
    up_capture: float
    down_capture: float


class BenchmarkManager:
    """基准管理器

    管理基准净值序列的加载和对齐。
    支持内置基准和自定义基准。
    """

    BUILTIN_BENCHMARKS = {
        "csi_cb": "中证转债指数 (000832.CSI)",
        "csi300": "沪深300 (000300.SH)",
    }

    def __init__(self) -> None:
        self._benchmarks: dict[str, dict[str, float]] = {}

    def register_benchmark(
        self, name: str, nav_series: dict[str, float]
    ) -> None:
        """注册基准净值序列

        Args:
            name: 基准名称
            nav_series: {date: net_value} 净值序列
        """
        self._benchmarks[name] = dict(nav_series)

    def get_benchmark(self, name: str) -> dict[str, float] | None:
        """获取基准净值序列"""
        return self._benchmarks.get(name)

    def list_benchmarks(self) -> list[str]:
        """列出已注册的基准"""
        return list(self._benchmarks.keys())

    def align_with_portfolio(
        self,
        portfolio_nav: dict[str, float],
        benchmark_nav: dict[str, float],
    ) -> tuple[list[str], list[float], list[float]]:
        """对齐组合和基准的日期

        Returns:
            (dates, portfolio_values, benchmark_values) - 仅包含共同日期
        """
        common_dates = sorted(set(portfolio_nav) & set(benchmark_nav))
        p_values = [portfolio_nav[d] for d in common_dates]
        b_values = [benchmark_nav[d] for d in common_dates]
        return common_dates, p_values, b_values

    def compare(
        self,
        portfolio_nav: dict[str, float],
        benchmark_name: str,
        trading_days: int = 252,
    ) -> BenchmarkComparison | None:
        """生成基准对比分析

        Args:
            portfolio_nav: 组合净值序列
            benchmark_name: 基准名称
            trading_days: 年交易日数
        """
        benchmark_nav = self._benchmarks.get(benchmark_name)
        if not benchmark_nav:
            return None

        dates, p_vals, b_vals = self.align_with_portfolio(
            portfolio_nav, benchmark_nav
        )

        if len(dates) < 2:
            return None

        # 转为 numpy
        p = np.array(p_vals, dtype=float)
        b = np.array(b_vals, dtype=float)

        # 日收益率
        p_ret = np.diff(p) / p[:-1]
        b_ret = np.diff(b) / b[:-1]

        n = len(p_ret)

        # 年化收益
        p_annual = (p[-1] / p[0]) ** (trading_days / n) - 1
        b_annual = (b[-1] / b[0]) ** (trading_days / n) - 1

        # 超额收益
        excess = p_ret - b_ret
        tracking_error = float(np.std(excess, ddof=1) * np.sqrt(trading_days))
        info_ratio = (
            (p_annual - b_annual) / tracking_error if tracking_error > 0 else 0.0
        )

        # CAPM: alpha, beta
        cov_pb = np.cov(p_ret, b_ret, ddof=1)
        beta = float(cov_pb[0, 1] / cov_pb[1, 1]) if cov_pb[1, 1] > 0 else 0.0
        alpha = p_annual - beta * b_annual

        # 相关系数
        corr_matrix = np.corrcoef(p_ret, b_ret)
        correlation = float(corr_matrix[0, 1])

        # 上行/下行捕获率
        up_mask = b_ret > 0
        down_mask = b_ret < 0

        up_capture = (
            float(np.mean(p_ret[up_mask]) / np.mean(b_ret[up_mask]))
            if np.any(up_mask) and np.mean(b_ret[up_mask]) != 0
            else 0.0
        )
        down_capture = (
            float(np.mean(p_ret[down_mask]) / np.mean(b_ret[down_mask]))
            if np.any(down_mask) and np.mean(b_ret[down_mask]) != 0
            else 0.0
        )

        return BenchmarkComparison(
            benchmark_name=benchmark_name,
            portfolio_annual_return=p_annual,
            benchmark_annual_return=b_annual,
            excess_return=p_annual - b_annual,
            tracking_error=tracking_error,
            information_ratio=info_ratio,
            beta=beta,
            alpha=alpha,
            correlation=correlation,
            up_capture=up_capture,
            down_capture=down_capture,
        )
