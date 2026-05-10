"""风控引擎测试"""

import pytest
import pandas as pd

from quantified.risk.engine import RiskEngine
from quantified.risk.protocol import RiskViolation
from quantified.risk.rules.position_limit import MaxPositionRule
from quantified.risk.rules.stop_loss import StopLossRule
from quantified.risk.rules.drawdown import MaxDrawdownRule
from quantified.risk.rules.liquidity import LiquidityRule
from quantified.strategy.protocol import Signal


class MockPortfolio:
    def __init__(self, cash=100000, holdings=None, high_water_mark=100000):
        self.cash = cash
        self.holdings = holdings or []
        self.high_water_mark = high_water_mark


class MockHolding:
    def __init__(self, cb_code, buy_price, volume):
        self.cb_code = cb_code
        self.buy_price = buy_price
        self.volume = volume


class MockConfig:
    class Risk:
        max_position_pct = 0.10
        stop_loss_pct = -0.15
        max_drawdown_pct = -0.10

    risk = Risk()


@pytest.fixture
def market_data():
    return pd.DataFrame({
        "cb_code": ["123001", "123002", "123003"],
        "cb_close": [105.0, 80.0, 120.0],
        "cb_volume": [1000, 2000, 500],
    })


@pytest.fixture
def config():
    return MockConfig()


class TestRiskEngine:
    def test_add_rule(self):
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())
        assert len(engine.rules) == 1

    def test_list_rules(self):
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())
        engine.add_rule(StopLossRule())
        rules = engine.list_rules()
        assert len(rules) == 2
        assert rules[0]["name"] == "max_position"

    def test_check_no_violations(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())

        portfolio = MockPortfolio()
        signals = [
            Signal(cb_code="123001", direction="buy", weight=0.08, score=100, reason="test"),
        ]

        violations = engine.check(portfolio, signals, market_data, config)
        assert len(violations) == 0

    def test_check_position_violation(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())

        portfolio = MockPortfolio()
        signals = [
            Signal(cb_code="123001", direction="buy", weight=0.15, score=100, reason="test"),
        ]

        violations = engine.check(portfolio, signals, market_data, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "max_position"

    def test_check_stop_loss(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(StopLossRule())

        # 持仓买入价 100，当前价 80 (123002)，亏损 20%
        portfolio = MockPortfolio(
            holdings=[MockHolding("123002", 100.0, 100)]
        )
        signals = []

        violations = engine.check(portfolio, signals, market_data, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "stop_loss"

    def test_check_drawdown(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(MaxDrawdownRule())

        # 高水位 100000，当前 85000，回撤 15%
        portfolio = MockPortfolio(
            cash=85000, high_water_mark=100000
        )
        signals = [Signal(cb_code="123001", direction="buy", weight=0.1, score=100, reason="test")]

        violations = engine.check(portfolio, signals, market_data, config)
        assert len(violations) == 1
        assert violations[0].rule_name == "max_drawdown"

    def test_check_liquidity(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(LiquidityRule())

        portfolio = MockPortfolio()
        # 123003 成交量 500，等于默认阈值 500，不触发违规
        signals = [
            Signal(cb_code="123003", direction="buy", weight=0.1, score=100, reason="test"),
        ]

        violations = engine.check(portfolio, signals, market_data, config)
        assert len(violations) == 0  # 500 >= 500, no violation

    def test_adjust_signals(self, market_data, config):
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())

        portfolio = MockPortfolio()
        signals = [
            Signal(cb_code="123001", direction="buy", weight=0.15, score=100, reason="test"),
        ]

        adjusted, violations = engine.check_and_adjust(portfolio, signals, market_data, config)
        assert len(violations) == 1
        assert len(adjusted) == 1
        assert adjusted[0].weight == 0.10  # 被限制到阈值


class TestVar:
    def test_var_historical(self):
        from quantified.risk.var import var_historical

        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15]
        var = var_historical(returns, 0.95)
        assert var > 0

    def test_var_parametric(self):
        from quantified.risk.var import var_parametric

        var = var_parametric(0.001, 0.02, 0.95)
        assert var > 0

    def test_var_monte_carlo(self):
        from quantified.risk.var import var_monte_carlo

        var = var_monte_carlo(0.001, 0.02, 0.95, n_simulations=10000, seed=42)
        assert var > 0

    def test_cvar_historical(self):
        from quantified.risk.var import cvar_historical

        returns = [-0.05, -0.03, -0.01, 0.01, 0.02, 0.03, 0.05, 0.08, 0.10, 0.15]
        cvar = cvar_historical(returns, 0.95)
        assert cvar > 0


class TestStressTest:
    def test_run_stress_test(self):
        from quantified.risk.stress_test import run_stress_test, StressScenario

        portfolio = MockPortfolio(
            holdings=[MockHolding("123001", 100.0, 1000)]
        )
        market_data = pd.DataFrame()

        results = run_stress_test(portfolio, market_data)
        assert len(results) > 0
        assert results[0].portfolio_loss < 0
