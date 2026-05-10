"""报告生成测试"""

import pytest

from vertexquant.analytics.engine import RiskAdjustedMetrics
from vertexquant.analytics.drawdown import DrawdownStats
from vertexquant.analytics.report import HoldingPerformance, ReportGenerator


@pytest.fixture
def generator():
    return ReportGenerator()


@pytest.fixture
def metrics():
    return RiskAdjustedMetrics(
        sortino_ratio=1.5,
        calmar_ratio=2.0,
        information_ratio=0.8,
        omega_ratio=1.3,
        max_drawdown_duration=15,
        recovery_factor=3.0,
        tail_ratio=1.2,
        common_sense_ratio=0.7,
    )


@pytest.fixture
def drawdown_stats():
    return DrawdownStats(
        max_drawdown=0.10,
        avg_drawdown=0.05,
        max_duration_days=15,
        avg_duration_days=8,
        total_periods=3,
        current_drawdown=0.03,
        current_depth_pct=0.3,
    )


@pytest.fixture
def holdings():
    gainers = [
        HoldingPerformance("123001", "转债A", 500.0, 0.05, 0.3),
        HoldingPerformance("123002", "转债B", 300.0, 0.03, 0.2),
    ]
    losers = [
        HoldingPerformance("123003", "转债C", -200.0, -0.02, 0.2),
        HoldingPerformance("123004", "转债D", -100.0, -0.01, 0.15),
    ]
    return gainers, losers


class TestMonthlyReport:
    def test_basic_report(self, generator, metrics, drawdown_stats, holdings):
        gainers, losers = holdings
        report = generator.generate_monthly_report(
            portfolio_name="测试组合",
            year=2024,
            month=3,
            metrics=metrics,
            monthly_return=0.05,
            benchmark_return=0.03,
            top_gainers=gainers,
            top_losers=losers,
            drawdown_stats=drawdown_stats,
        )

        assert "测试组合" in report
        assert "2024年3月" in report
        assert "5.00%" in report
        assert "Sortino Ratio" in report
        assert "转债A" in report
        assert "转债C" in report

    def test_no_benchmark(self, generator, metrics, drawdown_stats, holdings):
        gainers, losers = holdings
        report = generator.generate_monthly_report(
            portfolio_name="P",
            year=2024,
            month=1,
            metrics=metrics,
            monthly_return=0.02,
            benchmark_return=None,
            top_gainers=gainers,
            top_losers=losers,
            drawdown_stats=drawdown_stats,
        )
        assert "超额收益" not in report


class TestAnnualReport:
    def test_basic_annual(self, generator, metrics, drawdown_stats):
        monthly = {
            "2024-01": 0.03,
            "2024-02": -0.01,
            "2024-03": 0.05,
        }

        report = generator.generate_annual_summary(
            portfolio_name="测试组合",
            year=2024,
            annual_return=0.15,
            benchmark_return=0.10,
            metrics=metrics,
            monthly_returns=monthly,
            drawdown_stats=drawdown_stats,
        )

        assert "2024年度报告" in report
        assert "15.00%" in report
        assert "01月" in report
