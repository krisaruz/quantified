"""测试持仓管理"""

import json
from pathlib import Path

from quantified.portfolio import Holding, Portfolio, load_portfolio, save_portfolio


class TestPortfolio:
    def test_empty_portfolio(self):
        p = Portfolio()
        assert len(p.holdings) == 0
        assert p.cash == 100000.0
        assert p.high_water_mark == 0.0

    def test_add_and_remove(self):
        p = Portfolio()
        h = Holding(cb_code="123456", cb_name="测试转债", buy_date="2025-01-01",
                    buy_price=100.0, volume=10)
        p.add(h, cost=100.0)
        assert len(p.holdings) == 1
        assert p.cash == 99900.0
        assert "123456" in p.codes

        p.remove("123456", proceeds=110.0)
        assert len(p.holdings) == 0
        assert p.cash == 100010.0

    def test_get_holding(self):
        p = Portfolio()
        p.add(Holding("A", "债A", "2025-01-01", 100, 10), 100)
        p.add(Holding("B", "债B", "2025-01-01", 110, 20), 220)

        h = p.get_holding("A")
        assert h is not None
        assert h.cb_name == "债A"
        assert p.get_holding("Z") is None

    def test_high_water_mark(self):
        p = Portfolio(high_water_mark=120000)
        assert p.high_water_mark == 120000


class TestPortfolioPersistence:
    def test_save_and_load(self, tmp_path):
        path = tmp_path / "test_portfolio.json"
        p = Portfolio(cash=50000.0, high_water_mark=60000.0)
        p.add(Holding("X", "测试X", "2025-06-01", 105.5, 10), 105.5)
        save_portfolio(p, path)

        loaded = load_portfolio(path)
        assert loaded.cash == p.cash
        assert loaded.high_water_mark == 60000.0
        assert len(loaded.holdings) == 1
        assert loaded.holdings[0].cb_code == "X"

    def test_load_nonexistent(self, tmp_path):
        p = load_portfolio(tmp_path / "nope.json")
        assert len(p.holdings) == 0
        assert p.cash == 100000.0

    def test_load_legacy_without_high_water(self, tmp_path):
        """兼容旧版本没有 high_water_mark 字段的 JSON"""
        path = tmp_path / "legacy.json"
        data = {"holdings": [], "cash": 80000}
        path.write_text(json.dumps(data), encoding="utf-8")
        p = load_portfolio(path)
        assert p.high_water_mark == 0.0
