"""分析引擎核心"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from quantified.backtest.engine import BacktestResult, DailySnapshot
from quantified.backtest.stats import PerformanceStats, TRADING_DAYS_PER_YEAR


@dataclass
class RiskAdjustedMetrics:
    """扩展风险调整指标"""

    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    information_ratio: float = 0.0
    omega_ratio: float = 0.0
    max_drawdown_duration: int = 0
    recovery_factor: float = 0.0
    tail_ratio: float = 0.0
    common_sense_ratio: float = 0.0


@dataclass
class DrawdownPeriod:
    """回撤区间"""

    start_date: str
    trough_date: str
    end_date: str | None
    depth: float
    duration_days: int
    recovery_days: int | None


class AnalyticsEngine:
    """分析引擎：从回测结果计算各类分析指标"""

    def __init__(self, result: BacktestResult, benchmark_returns: list[float] | None = None) -> None:
        self.result = result
        self.benchmark_returns = benchmark_returns or []

    def compute_risk_adjusted_metrics(self) -> RiskAdjustedMetrics:
        """计算扩展风险调整指标"""
        metrics = RiskAdjustedMetrics()
        snaps = self.result.daily_snapshots

        if len(snaps) < 2:
            return metrics

        # 日收益率序列
        daily_returns = []
        for i in range(1, len(snaps)):
            prev = snaps[i - 1].net_value
            if prev > 0:
                daily_returns.append(snaps[i].net_value / prev - 1)

        if not daily_returns:
            return metrics

        mean_r = sum(daily_returns) / len(daily_returns)
        rf_daily = 0.02 / TRADING_DAYS_PER_YEAR

        # Sortino Ratio
        downside = [r for r in daily_returns if r < rf_daily]
        if downside:
            downside_var = sum((r - rf_daily) ** 2 for r in downside) / len(downside)
            downside_std = math.sqrt(downside_var) * math.sqrt(TRADING_DAYS_PER_YEAR)
            annual_return = (self.result.final_value / self.result.initial_capital) ** (
                TRADING_DAYS_PER_YEAR / len(snaps)
            ) - 1
            metrics.sortino_ratio = (annual_return - 0.02) / downside_std if downside_std > 0 else 0

        # 最大回撤和持续时间
        dd_periods = self.compute_drawdown_periods()
        if dd_periods:
            worst = max(dd_periods, key=lambda d: d.depth)
            metrics.max_drawdown_duration = worst.duration_days
            metrics.calmar_ratio = (
                annual_return / worst.depth if worst.depth > 0 else 0
            )
            # Recovery Factor
            total_return = self.result.final_value / self.result.initial_capital - 1
            metrics.recovery_factor = total_return / worst.depth if worst.depth > 0 else 0

        # Information Ratio
        if self.benchmark_returns and len(self.benchmark_returns) == len(daily_returns):
            excess = [r - b for r, b in zip(daily_returns, self.benchmark_returns)]
            tracking_error = math.sqrt(
                sum(e ** 2 for e in excess) / len(excess)
            ) * math.sqrt(TRADING_DAYS_PER_YEAR)
            metrics.information_ratio = (
                (annual_return - sum(self.benchmark_returns) * TRADING_DAYS_PER_YEAR) / tracking_error
                if tracking_error > 0 else 0
            )

        # Omega Ratio
        gains = sum(max(r - rf_daily, 0) for r in daily_returns)
        losses = sum(max(rf_daily - r, 0) for r in daily_returns)
        metrics.omega_ratio = gains / losses if losses > 0 else float("inf")

        # Tail Ratio
        sorted_r = sorted(daily_returns)
        n = len(sorted_r)
        if n >= 20:
            p95 = sorted_r[int(n * 0.95)]
            p5 = sorted_r[int(n * 0.05)]
            metrics.tail_ratio = abs(p95 / p5) if p5 != 0 else 0

        # Common Sense Ratio
        win_rate = sum(1 for r in daily_returns if r > 0) / len(daily_returns)
        metrics.common_sense_ratio = metrics.tail_ratio * win_rate

        return metrics

    def compute_drawdown_periods(self) -> list[DrawdownPeriod]:
        """检测所有回撤区间"""
        snaps = self.result.daily_snapshots
        if len(snaps) < 2:
            return []

        periods: list[DrawdownPeriod] = []
        peak = snaps[0].net_value
        peak_date = snaps[0].date
        in_drawdown = False
        dd_start = ""
        dd_trough = ""
        dd_depth = 0.0

        for snap in snaps:
            if snap.net_value > peak:
                if in_drawdown and dd_depth > 0.001:
                    # 回撤恢复
                    periods.append(DrawdownPeriod(
                        start_date=dd_start,
                        trough_date=dd_trough,
                        end_date=snap.date,
                        depth=dd_depth,
                        duration_days=self._days_between(dd_start, snap.date),
                        recovery_days=self._days_between(dd_trough, snap.date),
                    ))
                peak = snap.net_value
                peak_date = snap.date
                in_drawdown = False
                dd_depth = 0.0
            else:
                dd = (peak - snap.net_value) / peak
                if not in_drawdown:
                    in_drawdown = True
                    dd_start = peak_date
                    dd_trough = snap.date
                    dd_depth = dd
                elif dd > dd_depth:
                    dd_trough = snap.date
                    dd_depth = dd

        # 未恢复的回撤
        if in_drawdown and dd_depth > 0.001:
            periods.append(DrawdownPeriod(
                start_date=dd_start,
                trough_date=dd_trough,
                end_date=None,
                depth=dd_depth,
                duration_days=self._days_between(dd_start, snaps[-1].date),
                recovery_days=None,
            ))

        return periods

    def compute_monthly_returns(self) -> dict[str, float]:
        """计算月度收益率"""
        snaps = self.result.daily_snapshots
        if len(snaps) < 2:
            return {}

        monthly: dict[str, float] = {}
        month_start_nv = snaps[0].net_value
        current_month = snaps[0].date[:7]  # YYYY-MM

        for snap in snaps:
            month = snap.date[:7]
            if month != current_month:
                # 月度收益率
                monthly[current_month] = snap.net_value / month_start_nv - 1
                month_start_nv = snap.net_value
                current_month = month

        # 最后一个月
        monthly[current_month] = snaps[-1].net_value / month_start_nv - 1
        return monthly

    def compute_annual_returns(self) -> dict[str, float]:
        """计算年度收益率"""
        snaps = self.result.daily_snapshots
        if len(snaps) < 2:
            return {}

        annual: dict[str, float] = {}
        year_start_nv = snaps[0].net_value
        current_year = snaps[0].date[:4]

        for snap in snaps:
            year = snap.date[:4]
            if year != current_year:
                annual[current_year] = snap.net_value / year_start_nv - 1
                year_start_nv = snap.net_value
                current_year = year

        annual[current_year] = snaps[-1].net_value / year_start_nv - 1
        return annual

    @staticmethod
    def _days_between(d1: str, d2: str) -> int:
        from datetime import date
        try:
            return (date.fromisoformat(d2) - date.fromisoformat(d1)).days
        except (ValueError, TypeError):
            return 0
