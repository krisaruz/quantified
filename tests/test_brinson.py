"""Brinson 归因测试"""

import pytest

from vertexquant.analytics.attribution.brinson import (
    BrinsonAttribution,
    BrinsonResult,
    PeriodAttribution,
    SectorAttribution,
)


class TestBrinsonSinglePeriod:
    def test_basic_attribution(self):
        attr = BrinsonAttribution()
        result = attr.single_period(
            portfolio_weights={"tech": 0.5, "finance": 0.3, "consumer": 0.2},
            benchmark_weights={"tech": 0.4, "finance": 0.4, "consumer": 0.2},
            portfolio_returns={"tech": 0.10, "finance": 0.05, "consumer": 0.03},
            benchmark_returns={"tech": 0.08, "finance": 0.06, "consumer": 0.04},
        )

        assert isinstance(result, BrinsonResult)
        assert len(result.by_sector) == 3
        # 总超额 = 配置 + 选股 + 交互
        total = result.allocation_effect + result.selection_effect + result.interaction_effect
        assert abs(total - result.total_excess_return) < 1e-10

    def test_zero_excess_when_matching(self):
        """当组合和基准完全一致时，超额收益为 0"""
        attr = BrinsonAttribution()
        weights = {"A": 0.5, "B": 0.5}
        returns = {"A": 0.10, "B": 0.05}

        result = attr.single_period(weights, weights, returns, returns)
        assert abs(result.total_excess_return) < 1e-10
        assert abs(result.allocation_effect) < 1e-10
        assert abs(result.selection_effect) < 1e-10

    def test_sector_detail(self):
        attr = BrinsonAttribution()
        result = attr.single_period(
            portfolio_weights={"tech": 0.6, "bank": 0.4},
            benchmark_weights={"tech": 0.5, "bank": 0.5},
            portfolio_returns={"tech": 0.12, "bank": 0.04},
            benchmark_returns={"tech": 0.10, "bank": 0.05},
        )

        tech = result.by_sector["tech"]
        assert isinstance(tech, SectorAttribution)
        assert tech.portfolio_weight == 0.6
        assert tech.benchmark_weight == 0.5


class TestBrinsonMultiPeriod:
    def test_multi_period_attribution(self):
        attr = BrinsonAttribution()
        period_data = [
            {
                "period": "2024-01",
                "portfolio_weights": {"A": 0.6, "B": 0.4},
                "benchmark_weights": {"A": 0.5, "B": 0.5},
                "portfolio_returns": {"A": 0.05, "B": 0.02},
                "benchmark_returns": {"A": 0.04, "B": 0.03},
            },
            {
                "period": "2024-02",
                "portfolio_weights": {"A": 0.5, "B": 0.5},
                "benchmark_weights": {"A": 0.5, "B": 0.5},
                "portfolio_returns": {"A": 0.03, "B": -0.01},
                "benchmark_returns": {"A": 0.02, "B": 0.01},
            },
        ]

        result = attr.multi_period(period_data)
        assert isinstance(result, BrinsonResult)
        assert len(result.by_period) == 2
        # Carino 调整后各期效应之和应接近总超额
        total_from_periods = sum(p.total_excess for p in result.by_period)
        assert abs(total_from_periods - result.total_excess_return) < 0.01

    def test_empty_periods(self):
        attr = BrinsonAttribution()
        result = attr.multi_period([])
        assert result.total_excess_return == 0.0

    def test_single_period_as_multi(self):
        attr = BrinsonAttribution()
        period_data = [
            {
                "period": "2024-01",
                "portfolio_weights": {"A": 0.6, "B": 0.4},
                "benchmark_weights": {"A": 0.5, "B": 0.5},
                "portfolio_returns": {"A": 0.05, "B": 0.02},
                "benchmark_returns": {"A": 0.04, "B": 0.03},
            },
        ]

        single = attr.single_period(
            {"A": 0.6, "B": 0.4},
            {"A": 0.5, "B": 0.5},
            {"A": 0.05, "B": 0.02},
            {"A": 0.04, "B": 0.03},
        )
        multi = attr.multi_period(period_data)

        assert abs(single.total_excess_return - multi.total_excess_return) < 1e-10
