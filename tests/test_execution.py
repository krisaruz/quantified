"""执行引擎测试"""

from datetime import datetime, timedelta

import pytest

from quantified.execution.models import Fill, MarketBar, Order
from quantified.execution.order_manager import OrderManager
from quantified.execution.slippage import (
    FixedSlippageModel,
    VolumeBasedSlippageModel,
    VolatilitySlippageModel,
)
from quantified.execution.tca import TCAResult, TransactionCostAnalyzer


# ─────────────── Slippage Models ───────────────


class TestFixedSlippage:
    def test_buy_slippage(self):
        model = FixedSlippageModel(rate=0.001)
        price = model.estimate("buy", 100.0, 100, 10000, 0.02)
        assert price == pytest.approx(100.1)

    def test_sell_slippage(self):
        model = FixedSlippageModel(rate=0.001)
        price = model.estimate("sell", 100.0, 100, 10000, 0.02)
        assert price == pytest.approx(99.9)


class TestVolumeBasedSlippage:
    def test_low_participation(self):
        model = VolumeBasedSlippageModel(base_rate=0.0005, impact_factor=0.1)
        price = model.estimate("buy", 100.0, 10, 10000, 0.02)
        # participation = 10/10000 = 0.001, impact = 0.0005 + 0.1 * 0.001 = 0.0006
        assert price == pytest.approx(100.06, abs=0.01)

    def test_high_participation(self):
        model = VolumeBasedSlippageModel(base_rate=0.0005, impact_factor=0.1)
        price = model.estimate("buy", 100.0, 5000, 10000, 0.02)
        # participation = 0.5, impact = 0.0005 + 0.1 * 0.5 = 0.0505
        assert price > 104.0


class TestVolatilitySlippage:
    def test_low_volatility(self):
        model = VolatilitySlippageModel(base_rate=0.0003, vol_multiplier=0.5)
        price = model.estimate("buy", 100.0, 100, 10000, 0.01)
        # impact = 0.0003 + 0.5 * 0.01 = 0.0053
        assert price == pytest.approx(100.53, abs=0.1)

    def test_high_volatility(self):
        model = VolatilitySlippageModel(base_rate=0.0003, vol_multiplier=0.5)
        price = model.estimate("buy", 100.0, 100, 10000, 0.10)
        # impact = 0.0003 + 0.5 * 0.10 = 0.0503
        assert price > 104.0


# ─────────────── OrderManager ───────────────


class TestOrderManager:
    def test_create_order(self):
        mgr = OrderManager()
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")
        assert order.status == "pending"
        assert order.target_volume == 100
        assert order.order_id in mgr.orders

    def test_match_buy_order(self):
        mgr = OrderManager(FixedSlippageModel(rate=0.001))
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=10000, turnover=1000000,
        )

        fills = mgr.match({"123001": bar})
        assert len(fills) == 1
        assert fills[0].price > 100.0  # buy slippage
        assert order.status == "filled"
        assert order.filled_volume == 100

    def test_partial_fill(self):
        mgr = OrderManager(FixedSlippageModel(rate=0.001))
        order = mgr.create_order("123001", "转债A", "buy", 1000, "test")

        # volume 1000, max fill = 1000 * 0.1 = 100
        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=1000, turnover=100000,
        )

        fills = mgr.match({"123001": bar})
        assert len(fills) == 1
        assert order.status == "partial"
        assert order.filled_volume == 100

    def test_limit_order_rejected(self):
        mgr = OrderManager()
        order = mgr.create_order(
            "123001", "转债A", "buy", 100, "test", limit_price=99.0
        )

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=10000, turnover=1000000,
        )

        fills = mgr.match({"123001": bar})
        assert len(fills) == 0  # open > limit_price

    def test_suspended_stock(self):
        mgr = OrderManager()
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=100.0, low=100.0, close=100.0,
            volume=0, turnover=0, is_suspended=True,
        )

        fills = mgr.match({"123001": bar})
        assert len(fills) == 0

    def test_cancel_expired(self):
        mgr = OrderManager()
        order = mgr.create_order("123001", "转债A", "buy", 100, "test", ttl_days=3)

        # 模拟 4 天后
        future = order.created_at + timedelta(days=4)
        expired = mgr.cancel_expired(now=future)
        assert len(expired) == 1
        assert order.status == "expired"

    def test_cancel_order(self):
        mgr = OrderManager()
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")
        assert mgr.cancel_order(order.order_id)
        assert order.status == "cancelled"
        assert not order.is_active

    def test_sell_order(self):
        mgr = OrderManager(FixedSlippageModel(rate=0.001))
        order = mgr.create_order("123001", "转债A", "sell", 100, "test")

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=10000, turnover=1000000,
        )

        fills = mgr.match({"123001": bar})
        assert len(fills) == 1
        assert fills[0].price < 100.0  # sell slippage


# ─────────────── TCA ───────────────


class TestTCA:
    def test_analyze_buy_order(self):
        mgr = OrderManager(FixedSlippageModel(rate=0.001))
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=10000, turnover=1000000,
        )
        mgr.match({"123001": bar})

        analyzer = TransactionCostAnalyzer()
        result = analyzer.analyze(order, decision_price=100.0)
        assert result is not None
        assert result.execution_price > 100.0
        assert result.commission > 0
        assert result.total_cost > 0

    def test_analyze_empty_order(self):
        mgr = OrderManager()
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")

        analyzer = TransactionCostAnalyzer()
        result = analyzer.analyze(order, decision_price=100.0)
        assert result is None

    def test_generate_report(self):
        mgr = OrderManager(FixedSlippageModel(rate=0.001))
        order = mgr.create_order("123001", "转债A", "buy", 100, "test")

        bar = MarketBar(
            cb_code="123001", date="2024-01-02",
            open=100.0, high=105.0, low=99.0, close=102.0,
            volume=10000, turnover=1000000,
        )
        mgr.match({"123001": bar})

        analyzer = TransactionCostAnalyzer()
        result = analyzer.analyze(order, decision_price=100.0)
        report = analyzer.generate_report([result])
        assert "交易成本分析报告" in report
        assert "123001" in report

    def test_cost_bps(self):
        result = TCAResult(
            order_id="test",
            cb_code="123001",
            direction="buy",
            decision_price=100.0,
            execution_price=100.1,
            benchmark_price=100.0,
            volume=100,
            implementation_shortfall=1.0,
            market_impact=0.001,
            timing_cost=0.0,
            spread_cost=0.0,
            commission=0.2,
            total_cost=1.2,
        )
        # notional = 100.1 * 100 / 10 = 1001
        # bps = 1.2 / 1001 * 10000 ≈ 11.99
        assert result.cost_bps > 10
