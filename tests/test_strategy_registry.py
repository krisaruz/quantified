"""策略注册表和因子注册表测试"""

import pytest
import pandas as pd

from vertexquant.strategy.registry import StrategyRegistry
from vertexquant.strategy.factor_registry import FactorRegistry
from vertexquant.strategy.protocol import Signal, StrategyContext


@pytest.fixture(autouse=True)
def clear_registries():
    """每个测试前后清空注册表"""
    StrategyRegistry.clear()
    FactorRegistry.clear()
    yield
    StrategyRegistry.clear()
    FactorRegistry.clear()


class TestStrategyRegistry:
    def test_register_and_get(self):
        @StrategyRegistry.register("test_strategy")
        class TestStrategy:
            name = "test_strategy"
            version = "1.0.0"
            description = "测试策略"

            def generate_signals(self, context):
                return []

            def get_parameters(self):
                return {}

            def set_parameters(self, params):
                pass

        assert StrategyRegistry.has("test_strategy")
        strategy = StrategyRegistry.get("test_strategy")
        assert strategy.name == "test_strategy"

    def test_list_strategies(self):
        @StrategyRegistry.register("strategy_a")
        class StrategyA:
            name = "strategy_a"
            version = "1.0.0"
            description = ""
            def generate_signals(self, context): return []
            def get_parameters(self): return {}
            def set_parameters(self, params): pass

        @StrategyRegistry.register("strategy_b")
        class StrategyB:
            name = "strategy_b"
            version = "1.0.0"
            description = ""
            def generate_signals(self, context): return []
            def get_parameters(self): return {}
            def set_parameters(self, params): pass

        strategies = StrategyRegistry.list_strategies()
        assert "strategy_a" in strategies
        assert "strategy_b" in strategies

    def test_get_unregistered_raises(self):
        with pytest.raises(KeyError, match="未注册"):
            StrategyRegistry.get("nonexistent")

    def test_register_with_kwargs(self):
        @StrategyRegistry.register("parameterized")
        class ParameterizedStrategy:
            name = "parameterized"
            version = "1.0.0"
            description = ""

            def __init__(self, param1=10, param2="hello"):
                self.param1 = param1
                self.param2 = param2

            def generate_signals(self, context): return []
            def get_parameters(self): return {"param1": self.param1}
            def set_parameters(self, params): pass

        strategy = StrategyRegistry.get("parameterized", param1=20, param2="world")
        assert strategy.param1 == 20
        assert strategy.param2 == "world"


class TestFactorRegistry:
    def test_register_and_get(self):
        @FactorRegistry.register("test_factor", category="test")
        class TestFactor:
            name = "test_factor"
            category = "test"
            description = "测试因子"

            def compute(self, df):
                return pd.Series([1.0] * len(df))

            def compute_single(self, row):
                return 1.0

        assert FactorRegistry.has("test_factor")
        factor = FactorRegistry.get("test_factor")
        assert factor.name == "test_factor"

    def test_list_by_category(self):
        @FactorRegistry.register("factor_a", category="value")
        class FactorA:
            name = "factor_a"
            category = "value"
            description = ""
            def compute(self, df): return pd.Series()
            def compute_single(self, row): return 0.0

        @FactorRegistry.register("factor_b", category="momentum")
        class FactorB:
            name = "factor_b"
            category = "momentum"
            description = ""
            def compute(self, df): return pd.Series()
            def compute_single(self, row): return 0.0

        value_factors = FactorRegistry.list_by_category("value")
        assert "factor_a" in value_factors
        assert "factor_b" not in value_factors

    def test_get_unregistered_raises(self):
        with pytest.raises(KeyError, match="未注册"):
            FactorRegistry.get("nonexistent")


class TestSignal:
    def test_signal_creation(self):
        sig = Signal(
            cb_code="123001",
            direction="buy",
            weight=0.1,
            score=150.0,
            reason="测试信号",
        )
        assert sig.cb_code == "123001"
        assert sig.direction == "buy"
        assert sig.metadata == {}

    def test_signal_immutable(self):
        sig = Signal(cb_code="123001", direction="buy", weight=0.1, score=150.0, reason="test")
        with pytest.raises(AttributeError):
            sig.cb_code = "999999"
