"""测试推荐引擎"""

import datetime

import pandas as pd
import pytest

from quantified.config import AppConfig
from quantified.portfolio import Holding, Portfolio
from quantified.recommender import (
    Recommender,
    _build_summary,
    calc_fee,
    format_recommendation,
    is_rebalance_day,
)


def _make_universe(n=15):
    rows = []
    for i in range(n):
        rows.append({
            "cb_code": f"CB{i:03d}",
            "cb_name": f"转债{i}",
            "cb_close": 100 + i * 2,
            "premium_rate": 0.01 * (i + 1),
            "conversion_value": 100 - i,
            "credit_rating": "AA",
            "double_low": 100 + i * 2 + (i + 1),
            "composite_score": 100 + i * 2 + (i + 1),
            "risk_level": "low" if i < 5 else "medium",
            "maturity_date": datetime.date(2029, 1, 1),
            "trade_available": True,
        })
    df = pd.DataFrame(rows).sort_values("composite_score").reset_index(drop=True)
    return df


class TestCalcFee:
    def test_normal_fee(self):
        config = AppConfig()
        config.fees.commission_rate = 0.0002
        config.fees.min_commission = 0.1
        assert calc_fee(10000, config) == pytest.approx(2.0)

    def test_min_fee(self):
        config = AppConfig()
        config.fees.commission_rate = 0.0002
        config.fees.min_commission = 0.1
        assert calc_fee(100, config) == 0.1

    def test_zero_amount(self):
        config = AppConfig()
        assert calc_fee(0, config) == 0


class TestIsRebalanceDay:
    def test_friday_is_rebalance(self):
        config = AppConfig()
        config.strategy.rebalance_day = "friday"
        assert is_rebalance_day("2025-06-06", config) is True  # Friday

    def test_monday_is_not_rebalance(self):
        config = AppConfig()
        config.strategy.rebalance_day = "friday"
        assert is_rebalance_day("2025-06-02", config) is False  # Monday

    def test_invalid_day_always_rebalance(self):
        config = AppConfig()
        config.strategy.rebalance_day = "everyday"
        assert is_rebalance_day("2025-06-02", config) is True


class TestRecommender:
    def test_empty_portfolio_generates_buys(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)

        universe = _make_universe(10)
        portfolio = Portfolio()
        result = rec.generate(universe, portfolio, "2025-06-01")

        buys = [a for a in result.actions if a.type == "buy"]
        assert len(buys) == 3
        assert result.date == "2025-06-01"

    def test_hold_existing(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)

        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 100, 10), 100)

        result = rec.generate(universe, portfolio, "2025-06-01")
        holds = [a for a in result.actions if a.type == "hold"]
        assert any(a.cb_code == "CB000" for a in holds)

    def test_sell_when_rank_drops(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.buffer_rank = 2
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)

        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB009", "转债9", "2025-01-01", 118, 10), 118)

        result = rec.generate(universe, portfolio, "2025-06-01")
        sells = [a for a in result.actions if a.type == "sell"]
        assert any(a.cb_code == "CB009" for a in sells)

    def test_stop_loss(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.risk.stop_loss_pct = -0.10
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)

        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 200, 10), 200)

        result = rec.generate(universe, portfolio, "2025-06-01")
        stops = [a for a in result.actions if a.type == "stop_loss"]
        assert any(a.cb_code == "CB000" for a in stops)

    def test_non_rebalance_day_only_stoploss_and_observe(self):
        """非调仓日只执行止损和观察"""
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "friday"

        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 100, 10), 100)

        rec = Recommender(config)
        result = rec.generate(universe, portfolio, "2025-06-02")  # Monday

        assert result.is_rebalance_day is False
        types = {a.type for a in result.actions}
        assert "buy" not in types
        assert "sell" not in types

    def test_drawdown_pause(self):
        """回撤暂停测试"""
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        config.risk.max_drawdown_pct = -0.05
        config.capital.initial = 100000

        universe = _make_universe(10)
        portfolio = Portfolio(cash=50000, high_water_mark=120000)

        rec = Recommender(config)
        result = rec.generate(universe, portfolio, "2025-06-01")

        assert result.drawdown_paused is True

    def test_buy_includes_fee(self):
        """买入建议包含佣金"""
        config = AppConfig()
        config.strategy.hold_count = 1
        config.strategy.rebalance_day = "everyday"
        config.fees.commission_rate = 0.001
        config.fees.min_commission = 1.0

        universe = _make_universe(5)
        portfolio = Portfolio()

        rec = Recommender(config)
        result = rec.generate(universe, portfolio, "2025-06-01")

        buys = [a for a in result.actions if a.type == "buy"]
        assert len(buys) >= 1
        assert buys[0].estimated_fee > 0
        assert buys[0].estimated_cost > 0

    def test_total_pnl_uses_config_capital(self):
        """收益率计算使用配置的初始资金"""
        config = AppConfig()
        config.strategy.hold_count = 1
        config.strategy.rebalance_day = "everyday"
        config.capital.initial = 200000

        universe = _make_universe(5)
        portfolio = Portfolio(cash=200000)

        rec = Recommender(config)
        result = rec.generate(universe, portfolio, "2025-06-01")
        assert result.total_pnl_pct == pytest.approx(0.0, abs=0.01)


class TestFormatRecommendation:
    def test_format_recommendation(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)
        universe = _make_universe(5)
        portfolio = Portfolio()
        result = rec.generate(universe, portfolio, "2025-06-01")
        text = format_recommendation(result, config)
        assert "调仓建议" in text
        assert "买入" in text

    def test_format_non_rebalance_day(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "friday"
        rec = Recommender(config)
        universe = _make_universe(5)
        portfolio = Portfolio()
        result = rec.generate(universe, portfolio, "2025-06-02")  # Monday
        text = format_recommendation(result, config)
        assert "非调仓日" in text


class TestSummary:
    def test_rebalance_day_summary_has_actions(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)
        universe = _make_universe(10)
        portfolio = Portfolio()
        result = rec.generate(universe, portfolio, "2025-06-01")
        assert result.summary != ""
        assert "调仓日" in result.summary
        assert "买入" in result.summary

    def test_non_rebalance_day_summary(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "friday"
        rec = Recommender(config)
        universe = _make_universe(5)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 100, 10), 100)
        result = rec.generate(universe, portfolio, "2025-06-02")
        assert result.summary != ""
        assert "不是调仓日" in result.summary

    def test_drawdown_paused_summary(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        config.risk.max_drawdown_pct = -0.05
        config.capital.initial = 100000
        universe = _make_universe(10)
        portfolio = Portfolio(cash=50000, high_water_mark=120000)
        rec = Recommender(config)
        result = rec.generate(universe, portfolio, "2025-06-01")
        assert result.drawdown_paused is True
        assert "回撤" in result.summary


class TestNaturalLanguageReasons:
    def test_buy_reason_has_descriptive_text(self):
        config = AppConfig()
        config.strategy.hold_count = 2
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)
        universe = _make_universe(5)
        portfolio = Portfolio()
        result = rec.generate(universe, portfolio, "2025-06-01")
        buys = [a for a in result.actions if a.type == "buy"]
        assert len(buys) >= 1
        assert "综合评分" in buys[0].reason
        assert "价格" in buys[0].reason

    def test_stop_loss_reason_has_percent(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.risk.stop_loss_pct = -0.10
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)
        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 200, 10), 200)
        result = rec.generate(universe, portfolio, "2025-06-01")
        stops = [a for a in result.actions if a.type == "stop_loss"]
        assert any("止损" in s.reason for s in stops)

    def test_hold_reason_mentions_ranking(self):
        config = AppConfig()
        config.strategy.hold_count = 3
        config.strategy.rebalance_day = "everyday"
        rec = Recommender(config)
        universe = _make_universe(10)
        portfolio = Portfolio()
        portfolio.add(Holding("CB000", "转债0", "2025-01-01", 100, 10), 100)
        result = rec.generate(universe, portfolio, "2025-06-01")
        holds = [a for a in result.actions if a.type == "hold"]
        assert any("排名" in h.reason for h in holds)


class TestBuildSummary:
    def test_paused(self):
        from quantified.recommender import Action
        summary = _build_summary({
            "actions": [], "is_rebalance_day": True,
            "drawdown_paused": True, "drawdown": -0.12,
            "rebalance_day_name": "周五",
        })
        assert "回撤" in summary

    def test_non_rebalance(self):
        summary = _build_summary({
            "actions": [], "is_rebalance_day": False,
            "drawdown_paused": False, "rebalance_day_name": "周五",
        })
        assert "不是调仓日" in summary

    def test_rebalance_with_actions(self):
        from quantified.recommender import Action
        actions = [
            Action(type="sell", cb_code="A", cb_name="A", price=100, reason="test"),
            Action(type="buy", cb_code="B", cb_name="B", price=100, reason="test"),
        ]
        summary = _build_summary({
            "actions": actions, "is_rebalance_day": True,
            "drawdown_paused": False, "rebalance_day_name": "周五",
        })
        assert "调仓日" in summary
        assert "卖出" in summary
        assert "买入" in summary
