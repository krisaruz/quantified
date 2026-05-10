"""回撤分析扩展

水下曲线、回撤统计等。
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from vertexquant.analytics.engine import DrawdownPeriod


@dataclass(frozen=True)
class DrawdownStats:
    """回撤统计汇总"""

    max_drawdown: float
    avg_drawdown: float
    max_duration_days: int
    avg_duration_days: int
    total_periods: int
    current_drawdown: float
    current_depth_pct: float  # 当前处于历史最大回撤的百分位


@dataclass(frozen=True)
class UnderwaterPoint:
    """水下曲线数据点"""

    date: str
    underwater_pct: float  # 负值，表示低于高水位的百分比


class DrawdownAnalyzer:
    """回撤分析器"""

    def underwater_curve(
        self,
        dates: list[str],
        net_values: list[float],
    ) -> list[UnderwaterPoint]:
        """计算水下曲线

        underwater_i = (NV_i - Peak_i) / Peak_i
        """
        if not dates or not net_values:
            return []

        points: list[UnderwaterPoint] = []
        peak = net_values[0]

        for date, nv in zip(dates, net_values):
            if nv > peak:
                peak = nv
            underwater = (nv - peak) / peak if peak > 0 else 0.0
            points.append(UnderwaterPoint(
                date=date,
                underwater_pct=underwater,
            ))

        return points

    def compute_stats(
        self,
        periods: list[DrawdownPeriod],
        current_nav: float,
        high_water_mark: float,
    ) -> DrawdownStats:
        """汇总回撤统计"""
        if not periods:
            return DrawdownStats(
                max_drawdown=0.0,
                avg_drawdown=0.0,
                max_duration_days=0,
                avg_duration_days=0,
                total_periods=0,
                current_drawdown=0.0,
                current_depth_pct=0.0,
            )

        depths = [p.depth for p in periods]
        durations = [p.duration_days for p in periods]

        current_dd = (
            (high_water_mark - current_nav) / high_water_mark
            if high_water_mark > 0
            else 0.0
        )

        max_dd = max(depths)
        current_pct = current_dd / max_dd if max_dd > 0 else 0.0

        return DrawdownStats(
            max_drawdown=max_dd,
            avg_drawdown=float(np.mean(depths)),
            max_duration_days=max(durations),
            avg_duration_days=int(np.mean(durations)),
            total_periods=len(periods),
            current_drawdown=current_dd,
            current_depth_pct=current_pct,
        )

    def rolling_max_drawdown(
        self,
        net_values: list[float],
        window: int,
    ) -> list[float]:
        """滚动窗口最大回撤

        Args:
            net_values: 净值序列
            window: 窗口大小（天数）

        Returns:
            每个窗口的最大回撤序列
        """
        if len(net_values) < window:
            return []

        result: list[float] = []
        nv = np.array(net_values, dtype=float)

        for i in range(window, len(nv) + 1):
            window_nv = nv[i - window : i]
            peak = np.maximum.accumulate(window_nv)
            dd = (peak - window_nv) / peak
            result.append(float(np.max(dd)))

        return result

    def recovery_time_distribution(
        self,
        periods: list[DrawdownPeriod],
    ) -> dict[str, int]:
        """回撤恢复时间分布

        Returns:
            {"< 1 month": count, "1-3 months": count, ...}
        """
        buckets = {
            "< 1 month": 0,
            "1-3 months": 0,
            "3-6 months": 0,
            "6-12 months": 0,
            "> 1 year": 0,
            "unrecovered": 0,
        }

        for p in periods:
            if p.recovery_days is None:
                buckets["unrecovered"] += 1
            elif p.recovery_days < 30:
                buckets["< 1 month"] += 1
            elif p.recovery_days < 90:
                buckets["1-3 months"] += 1
            elif p.recovery_days < 180:
                buckets["3-6 months"] += 1
            elif p.recovery_days < 365:
                buckets["6-12 months"] += 1
            else:
                buckets["> 1 year"] += 1

        return buckets
