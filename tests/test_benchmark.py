"""基准管理测试"""

import pytest

from vertexquant.analytics.benchmark import BenchmarkComparison, BenchmarkManager


class TestBenchmarkManager:
    def test_register_and_get(self):
        mgr = BenchmarkManager()
        nav = {"2024-01-01": 1.0, "2024-01-02": 1.01, "2024-01-03": 1.02}
        mgr.register_benchmark("test", nav)

        assert mgr.get_benchmark("test") == nav
        assert mgr.get_benchmark("nonexistent") is None

    def test_list_benchmarks(self):
        mgr = BenchmarkManager()
        mgr.register_benchmark("a", {"2024-01-01": 1.0})
        mgr.register_benchmark("b", {"2024-01-01": 1.0})

        names = mgr.list_benchmarks()
        assert set(names) == {"a", "b"}

    def test_align_with_portfolio(self):
        mgr = BenchmarkManager()
        portfolio = {
            "2024-01-01": 1.0,
            "2024-01-02": 1.01,
            "2024-01-03": 1.02,
            "2024-01-04": 1.03,
        }
        benchmark = {
            "2024-01-02": 1.0,
            "2024-01-03": 1.005,
            "2024-01-04": 1.01,
            "2024-01-05": 1.02,
        }

        dates, p_vals, b_vals = mgr.align_with_portfolio(portfolio, benchmark)
        assert dates == ["2024-01-02", "2024-01-03", "2024-01-04"]
        assert len(p_vals) == 3
        assert len(b_vals) == 3

    def test_compare(self):
        mgr = BenchmarkManager()
        portfolio = {f"2024-01-{i:02d}": 1.0 + i * 0.005 for i in range(1, 31)}
        benchmark = {f"2024-01-{i:02d}": 1.0 + i * 0.003 for i in range(1, 31)}

        mgr.register_benchmark("bench", benchmark)
        result = mgr.compare(portfolio, "bench")

        assert isinstance(result, BenchmarkComparison)
        assert result.benchmark_name == "bench"
        assert result.portfolio_annual_return > 0
        assert result.benchmark_annual_return > 0
        assert result.beta > 0
        assert -1 <= result.correlation <= 1

    def test_compare_nonexistent(self):
        mgr = BenchmarkManager()
        portfolio = {"2024-01-01": 1.0, "2024-01-02": 1.01}
        result = mgr.compare(portfolio, "nonexistent")
        assert result is None

    def test_compare_insufficient_data(self):
        mgr = BenchmarkManager()
        mgr.register_benchmark("b", {"2024-01-01": 1.0})
        result = mgr.compare({"2024-01-01": 1.0}, "b")
        assert result is None
