"""回撤分析测试"""

import pytest

from vertexquant.analytics.drawdown import DrawdownAnalyzer, DrawdownStats, UnderwaterPoint
from vertexquant.analytics.engine import DrawdownPeriod


class TestUnderwaterCurve:
    def test_basic_curve(self):
        analyzer = DrawdownAnalyzer()
        dates = ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]
        values = [1.0, 1.05, 0.95, 1.02, 1.1]

        points = analyzer.underwater_curve(dates, values)
        assert len(points) == 5
        assert points[0].underwater_pct == 0.0  # 首日即高水位
        assert points[1].underwater_pct == 0.0  # 新高
        assert points[2].underwater_pct < 0     # 回撤
        assert points[4].underwater_pct == 0.0  # 新高

    def test_empty_input(self):
        analyzer = DrawdownAnalyzer()
        assert analyzer.underwater_curve([], []) == []

    def test_monotonic_increase(self):
        analyzer = DrawdownAnalyzer()
        dates = [f"2024-01-{i:02d}" for i in range(1, 6)]
        values = [1.0, 1.1, 1.2, 1.3, 1.4]

        points = analyzer.underwater_curve(dates, values)
        assert all(p.underwater_pct == 0.0 for p in points)


class TestDrawdownStats:
    def test_compute_stats(self):
        analyzer = DrawdownAnalyzer()
        periods = [
            DrawdownPeriod("2024-01-01", "2024-01-05", "2024-01-10", 0.1, 10, 5),
            DrawdownPeriod("2024-02-01", "2024-02-08", None, 0.15, 15, None),
        ]

        stats = analyzer.compute_stats(periods, current_nav=9000, high_water_mark=10000)
        assert stats.max_drawdown == 0.15
        assert stats.total_periods == 2
        assert stats.current_drawdown == pytest.approx(0.1)
        assert stats.max_duration_days == 15

    def test_empty_periods(self):
        analyzer = DrawdownAnalyzer()
        stats = analyzer.compute_stats([], 10000, 10000)
        assert stats.max_drawdown == 0.0
        assert stats.total_periods == 0


class TestRollingDrawdown:
    def test_rolling_max_drawdown(self):
        analyzer = DrawdownAnalyzer()
        values = [1.0, 1.1, 0.9, 1.0, 1.2, 1.0, 1.3]

        result = analyzer.rolling_max_drawdown(values, window=3)
        assert len(result) == 5  # 7 - 3 + 1
        assert all(isinstance(v, float) for v in result)
        assert all(v >= 0 for v in result)

    def test_window_too_large(self):
        analyzer = DrawdownAnalyzer()
        result = analyzer.rolling_max_drawdown([1.0, 1.1], window=5)
        assert result == []


class TestRecoveryDistribution:
    def test_distribution(self):
        analyzer = DrawdownAnalyzer()
        periods = [
            DrawdownPeriod("", "", "", 0.05, 10, 15),
            DrawdownPeriod("", "", "", 0.10, 30, 60),
            DrawdownPeriod("", "", "", 0.08, 20, 120),
            DrawdownPeriod("", "", "", 0.12, 40, 200),
            DrawdownPeriod("", "", "", 0.15, 50, 400),
            DrawdownPeriod("", "", "", 0.20, 60, None),
        ]

        dist = analyzer.recovery_time_distribution(periods)
        assert dist["< 1 month"] == 1
        assert dist["1-3 months"] == 1
        assert dist["3-6 months"] == 1
        assert dist["6-12 months"] == 1
        assert dist["> 1 year"] == 1
        assert dist["unrecovered"] == 1
