"""分析引擎测试"""

import math

import pytest

from vertexquant.analytics.engine import (
    AnalyticsEngine,
    DrawdownPeriod,
    RiskAdjustedMetrics,
)
from vertexquant.backtest.engine import BacktestResult, DailySnapshot


def _make_snapshots(values: list[float], start_date: str = "2024-01-02") -> list[DailySnapshot]:
    """辅助：生成日快照序列"""
    from datetime import date, timedelta

    base = date.fromisoformat(start_date)
    snaps = []
    for i, v in enumerate(values):
        d = (base + timedelta(days=i)).isoformat()
        snaps.append(DailySnapshot(
            date=d,
            net_value=v,
            cash=0,
            market_value=v * 10000,
            position_count=1,
        ))
    return snaps


def _make_result(values: list[float]) -> BacktestResult:
    """辅助：生成 BacktestResult"""
    snaps = _make_snapshots(values)
    return BacktestResult(
        start_date=snaps[0].date,
        end_date=snaps[-1].date,
        daily_snapshots=snaps,
        trades=[],
        initial_capital=100000,
        final_value=values[-1] * 10000,
    )


class TestRiskAdjustedMetrics:
    def test_sortino_ratio(self):
        result = _make_result([1.0, 1.02, 0.99, 1.03, 1.05, 1.08])
        engine = AnalyticsEngine(result)
        metrics = engine.compute_risk_adjusted_metrics()
        assert isinstance(metrics.sortino_ratio, float)

    def test_calmar_ratio(self):
        # 有明显回撤
        result = _make_result([1.0, 1.1, 0.9, 1.0, 1.15, 1.2])
        engine = AnalyticsEngine(result)
        metrics = engine.compute_risk_adjusted_metrics()
        assert isinstance(metrics.calmar_ratio, float)

    def test_omega_ratio(self):
        result = _make_result([1.0, 1.01, 0.99, 1.02, 1.03, 1.05])
        engine = AnalyticsEngine(result)
        metrics = engine.compute_risk_adjusted_metrics()
        assert metrics.omega_ratio > 0

    def test_tail_ratio(self):
        # 需要至少 20 个数据点
        import random
        random.seed(42)
        values = [1.0]
        for _ in range(30):
            values.append(values[-1] * (1 + random.uniform(-0.03, 0.03)))
        result = _make_result(values)
        engine = AnalyticsEngine(result)
        metrics = engine.compute_risk_adjusted_metrics()
        assert isinstance(metrics.tail_ratio, float)

    def test_insufficient_data(self):
        result = _make_result([1.0])
        engine = AnalyticsEngine(result)
        metrics = engine.compute_risk_adjusted_metrics()
        assert metrics.sortino_ratio == 0.0

    def test_with_benchmark(self):
        result = _make_result([1.0, 1.02, 1.01, 1.04, 1.05])
        benchmark = [0.01, -0.005, 0.02, 0.005]
        engine = AnalyticsEngine(result, benchmark)
        metrics = engine.compute_risk_adjusted_metrics()
        assert isinstance(metrics.information_ratio, float)


class TestDrawdownPeriods:
    def test_no_drawdown(self):
        result = _make_result([1.0, 1.1, 1.2, 1.3])
        engine = AnalyticsEngine(result)
        periods = engine.compute_drawdown_periods()
        assert len(periods) == 0

    def test_single_drawdown(self):
        result = _make_result([1.0, 1.1, 0.9, 1.0, 1.15])
        engine = AnalyticsEngine(result)
        periods = engine.compute_drawdown_periods()
        assert len(periods) >= 1
        worst = max(periods, key=lambda p: p.depth)
        assert worst.depth > 0.15  # 从 1.1 到 0.9

    def test_unrecovered_drawdown(self):
        result = _make_result([1.0, 1.1, 0.9, 0.95])
        engine = AnalyticsEngine(result)
        periods = engine.compute_drawdown_periods()
        assert any(p.end_date is None for p in periods)

    def test_multiple_drawdowns(self):
        result = _make_result([1.0, 1.1, 0.9, 1.2, 1.0, 1.3])
        engine = AnalyticsEngine(result)
        periods = engine.compute_drawdown_periods()
        assert len(periods) >= 2


class TestPeriodReturns:
    def test_monthly_returns(self):
        from datetime import date, timedelta

        # 生成跨月数据
        values = []
        base = date(2024, 1, 15)
        for i in range(60):
            values.append(1.0 + i * 0.001)
        snaps = []
        for i, v in enumerate(values):
            d = (base + timedelta(days=i)).isoformat()
            snaps.append(DailySnapshot(
                date=d, net_value=v, cash=0,
                market_value=v * 10000, position_count=1,
            ))
        result = BacktestResult(
            start_date=snaps[0].date,
            end_date=snaps[-1].date,
            daily_snapshots=snaps, trades=[],
            initial_capital=100000, final_value=values[-1] * 10000,
        )
        engine = AnalyticsEngine(result)
        monthly = engine.compute_monthly_returns()
        assert len(monthly) >= 2
        assert all(isinstance(v, float) for v in monthly.values())

    def test_annual_returns(self):
        result = _make_result([1.0, 1.1, 1.2])
        engine = AnalyticsEngine(result)
        annual = engine.compute_annual_returns()
        assert len(annual) >= 1
