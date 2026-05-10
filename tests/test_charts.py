"""图表数据测试"""

import pytest

from vertexquant.analytics.charts import ChartData


class TestEquityCurve:
    def test_basic(self):
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        values = [1.0, 1.02, 1.05]

        result = ChartData.equity_curve(dates, values)
        assert result["type"] == "line"
        assert result["labels"] == dates
        assert len(result["datasets"]) == 1
        assert result["datasets"][0]["label"] == "Portfolio"

    def test_with_benchmark(self):
        dates = ["2024-01-01", "2024-01-02"]
        values = [1.0, 1.02]
        benchmark = [1.0, 1.01]

        result = ChartData.equity_curve(dates, values, benchmark)
        assert len(result["datasets"]) == 2
        assert result["datasets"][1]["label"] == "Benchmark"


class TestDrawdownCurve:
    def test_basic(self):
        dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"]
        values = [1.0, 1.1, 0.95, 1.05]

        result = ChartData.drawdown_curve(dates, values)
        assert result["type"] == "line"
        assert len(result["datasets"][0]["data"]) == 4
        # 第一个点应该是 0（高水位）
        assert result["datasets"][0]["data"][0] == 0
        # 第三个点应该 < 0（回撤）
        assert result["datasets"][0]["data"][2] < 0

    def test_empty(self):
        result = ChartData.drawdown_curve([], [])
        assert result["labels"] == []


class TestMonthlyHeatmap:
    def test_basic(self):
        monthly = {
            "2024-01": 0.05,
            "2024-02": -0.02,
            "2024-03": 0.03,
            "2025-01": 0.01,
        }

        result = ChartData.monthly_returns_heatmap(monthly)
        assert result["type"] == "heatmap"
        assert "2024" in result["labels"]
        assert "2025" in result["labels"]
        assert len(result["months"]) == 12


class TestFactorRadar:
    def test_basic(self):
        names = ["value", "momentum", "quality", "volatility"]
        values = [0.8, 0.6, 0.9, 0.3]

        result = ChartData.factor_radar(names, values)
        assert result["type"] == "radar"
        assert result["labels"] == names
        assert result["datasets"][0]["data"] == values


class TestSectorPie:
    def test_basic(self):
        sectors = {"tech": 0.4, "finance": 0.3, "consumer": 0.3}

        result = ChartData.sector_pie(sectors)
        assert result["type"] == "pie"
        assert len(result["labels"]) == 3
        assert result["datasets"][0]["data"] == [0.4, 0.3, 0.3]


class TestPerformanceSummary:
    def test_basic(self):
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]
        values = [1.0, 1.05, 0.98]

        result = ChartData.performance_summary(dates, values)
        assert result["type"] == "mixed"
        assert len(result["datasets"]) == 2
