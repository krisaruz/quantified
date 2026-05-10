"""组合策略测试"""

import pandas as pd
import pytest

from vertexquant.strategy.registry import StrategyRegistry
from vertexquant.strategy.protocol import Signal, StrategyContext


@pytest.fixture(autouse=True)
def setup_registries():
    """注册测试策略"""
    StrategyRegistry.clear()

    @StrategyRegistry.register("always_buy")
    class AlwaysBuyStrategy:
        name = "always_buy"
        version = "1.0.0"
        description = ""

        def generate_signals(self, context):
            signals = []
            for _, row in context.universe.head(5).iterrows():
                signals.append(Signal(
                    cb_code=str(row["cb_code"]),
                    direction="buy",
                    weight=0.1,
                    score=100.0,
                    reason="always buy",
                ))
            return signals

        def get_parameters(self):
            return {}

        def set_parameters(self, params):
            pass

    @StrategyRegistry.register("always_sell")
    class AlwaysSellStrategy:
        name = "always_sell"
        version = "1.0.0"
        description = ""

        def generate_signals(self, context):
            return [
                Signal(cb_code="123001", direction="sell", weight=0.0, score=0.0, reason="sell")
            ]

        def get_parameters(self):
            return {}

        def set_parameters(self, params):
            pass

    yield
    StrategyRegistry.clear()


@pytest.fixture
def sample_universe():
    return pd.DataFrame({
        "cb_code": ["123001", "123002", "123003", "123004", "123005"],
        "cb_name": ["转债A", "转债B", "转债C", "转债D", "转债E"],
        "cb_close": [105.0, 110.0, 115.0, 120.0, 125.0],
        "premium_rate": [0.1, 0.2, 0.15, 0.25, 0.3],
        "credit_rating": ["AA", "AA+", "AA-", "A+", "AA"],
    })


@pytest.fixture
def mock_portfolio():
    class MockPortfolio:
        codes = set()
    return MockPortfolio()


class TestCompositeStrategy:
    def test_weighted_average_merge(self, sample_universe, mock_portfolio):
        from vertexquant.strategy.composite_strategy import CompositeStrategy

        strategy = CompositeStrategy(
            strategies=[
                {"name": "always_buy", "weight": 0.6},
                {"name": "always_sell", "weight": 0.4},
            ],
            method="weighted_average",
        )

        context = StrategyContext(
            date="2025-01-15",
            universe=sample_universe,
            portfolio=mock_portfolio,
        )

        signals = strategy.generate_signals(context)
        assert len(signals) > 0

        # 123001 should be sell (sell signal from always_sell)
        sig_123001 = next((s for s in signals if s.cb_code == "123001"), None)
        assert sig_123001 is not None
        assert sig_123001.direction == "sell"

    def test_voting_merge(self, sample_universe, mock_portfolio):
        from vertexquant.strategy.composite_strategy import CompositeStrategy

        strategy = CompositeStrategy(
            strategies=[
                {"name": "always_buy", "weight": 1.0},
                {"name": "always_sell", "weight": 1.0},
            ],
            method="voting",
        )

        context = StrategyContext(
            date="2025-01-15",
            universe=sample_universe,
            portfolio=mock_portfolio,
        )

        signals = strategy.generate_signals(context)
        # With 2 strategies, need > 1 vote
        # always_buy votes buy for 123001-123005, always_sell votes sell for 123001
        # 123001: 1 buy vote, 1 sell vote -> neither passes threshold
        # 123002-123005: 1 buy vote -> doesn't pass threshold
        # So no signals should be generated with this threshold
        assert len(signals) == 0

    def test_get_parameters(self, sample_universe, mock_portfolio):
        from vertexquant.strategy.composite_strategy import CompositeStrategy

        strategy = CompositeStrategy(
            strategies=[
                {"name": "always_buy", "weight": 0.6},
                {"name": "always_sell", "weight": 0.4},
            ],
        )

        params = strategy.get_parameters()
        assert params["method"] == "weighted_average"
        assert len(params["strategies"]) == 2
