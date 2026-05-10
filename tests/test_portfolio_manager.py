"""多组合管理测试"""

import json
import tempfile
from pathlib import Path

import pytest

from vertexquant.portfolio_manager.manager import PortfolioManager
from vertexquant.portfolio_manager.snapshot import SnapshotManager
from vertexquant.portfolio_manager.comparison import PortfolioComparator
from vertexquant.portfolio_manager.models import (
    HoldingSnapshot,
    PortfolioSnapshot,
    PortfolioSummary,
)
from vertexquant.portfolio_manager.templates import (
    BUILTIN_TEMPLATES,
    apply_template,
    get_template,
    list_templates,
)


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def manager(tmp_dir):
    return PortfolioManager(tmp_dir / "portfolios")


# ─────────────── Templates ───────────────


class TestTemplates:
    def test_builtin_templates_exist(self):
        assert "conservative" in BUILTIN_TEMPLATES
        assert "balanced" in BUILTIN_TEMPLATES
        assert "aggressive" in BUILTIN_TEMPLATES

    def test_get_template(self):
        tpl = get_template("balanced")
        assert tpl is not None
        assert tpl.name == "均衡型"
        assert tpl.is_builtin

    def test_get_nonexistent_template(self):
        assert get_template("nonexistent") is None

    def test_list_templates(self):
        templates = list_templates()
        assert len(templates) == 3

    def test_apply_template(self):
        config = {"risk": {"max_position_pct": 0.15}}
        tpl = get_template("conservative")
        result = apply_template(config, tpl)
        assert result["risk"]["max_position_pct"] == 0.06


# ─────────────── PortfolioManager ───────────────


class TestPortfolioManager:
    def test_create_portfolio(self, manager):
        summary = manager.create("test", "balanced", 100000)
        assert summary.name == "test"
        assert summary.cash == 100000
        assert summary.holding_count == 0

    def test_create_duplicate_raises(self, manager):
        manager.create("test")
        with pytest.raises(ValueError, match="已存在"):
            manager.create("test")

    def test_load_portfolio(self, manager):
        manager.create("test", "balanced", 100000)
        data = manager.load("test")
        assert data["cash"] == 100000
        assert data["holdings"] == []

    def test_load_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.load("nonexistent")

    def test_save_portfolio(self, manager):
        manager.create("test")
        data = manager.load("test")
        data["cash"] = 95000
        manager.save("test", data)

        reloaded = manager.load("test")
        assert reloaded["cash"] == 95000

    def test_list_portfolios(self, manager):
        manager.create("port_a", "conservative")
        manager.create("port_b", "aggressive")

        portfolios = manager.list_portfolios()
        assert len(portfolios) == 2
        names = [p.name for p in portfolios]
        assert "port_a" in names
        assert "port_b" in names

    def test_delete_portfolio(self, manager):
        manager.create("test")
        manager.delete("test")
        assert len(manager.list_portfolios()) == 0

    def test_rename_portfolio(self, manager):
        manager.create("old_name")
        manager.rename("old_name", "new_name")

        portfolios = manager.list_portfolios()
        assert len(portfolios) == 1
        assert portfolios[0].name == "new_name"

    def test_rename_nonexistent_raises(self, manager):
        with pytest.raises(FileNotFoundError):
            manager.rename("nonexistent", "new")

    def test_duplicate_portfolio(self, manager):
        manager.create("source", "balanced", 100000)
        manager.duplicate("source", "target")

        portfolios = manager.list_portfolios()
        assert len(portfolios) == 2
        names = [p.name for p in portfolios]
        assert "source" in names
        assert "target" in names

    def test_snapshot_manager(self, manager):
        manager.create("test")
        sm = manager.get_snapshot_manager("test")

        snap = PortfolioSnapshot(
            date="2024-01-15",
            portfolio_name="test",
            cash=50000,
            holdings=[
                HoldingSnapshot(
                    cb_code="123001", cb_name="转债A", volume=100,
                    avg_cost=100.0, current_price=105.0,
                    market_value=10500, pnl=500, pnl_pct=0.05, weight=0.1,
                )
            ],
            total_assets=105000,
            total_pnl_pct=0.05,
            high_water_mark=105000,
        )

        sm.save(snap)
        loaded = sm.load("2024-01-15")
        assert loaded is not None
        assert loaded.total_assets == 105000
        assert len(loaded.holdings) == 1

    def test_snapshot_list_dates(self, manager):
        manager.create("test")
        sm = manager.get_snapshot_manager("test")

        for date in ["2024-01-15", "2024-01-16", "2024-01-17"]:
            sm.save(PortfolioSnapshot(
                date=date, portfolio_name="test", cash=50000,
                holdings=[], total_assets=100000,
                total_pnl_pct=0.0, high_water_mark=100000,
            ))

        dates = sm.list_dates()
        assert dates == ["2024-01-15", "2024-01-16", "2024-01-17"]


# ─────────────── Comparison ───────────────


class TestComparison:
    def test_compare_snapshots(self):
        comparator = PortfolioComparator()

        snap_a = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="A", cash=10000,
            holdings=[
                HoldingSnapshot("123001", "转债A", 100, 100, 105, 10500, 500, 0.05, 0.5),
                HoldingSnapshot("123002", "转债B", 100, 100, 102, 10200, 200, 0.02, 0.48),
            ],
            total_assets=110000, total_pnl_pct=0.10, high_water_mark=110000,
        )

        snap_b = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="B", cash=20000,
            holdings=[
                HoldingSnapshot("123001", "转债A", 50, 100, 105, 5250, 250, 0.05, 0.25),
                HoldingSnapshot("123003", "转债C", 100, 100, 98, 9800, -200, -0.02, 0.47),
            ],
            total_assets=105000, total_pnl_pct=0.05, high_water_mark=105000,
        )

        result = comparator.compare_snapshots({"A": snap_a, "B": snap_b})

        assert result.portfolios == ["A", "B"]
        assert result.ranking[0][0] == "A"  # A has higher return
        assert "A vs B" in result.holdings_overlap
        assert result.holdings_overlap["A vs B"] == pytest.approx(0.5)  # 1 shared / min(2,2)

    def test_no_overlap(self):
        comparator = PortfolioComparator()

        snap_a = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="A", cash=0,
            holdings=[
                HoldingSnapshot("123001", "转债A", 100, 100, 105, 10500, 500, 0.05, 1.0),
            ],
            total_assets=105000, total_pnl_pct=0.05, high_water_mark=105000,
        )

        snap_b = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="B", cash=0,
            holdings=[
                HoldingSnapshot("123002", "转债B", 100, 100, 98, 9800, -200, -0.02, 1.0),
            ],
            total_assets=98000, total_pnl_pct=-0.02, high_water_mark=98000,
        )

        result = comparator.compare_snapshots({"A": snap_a, "B": snap_b})
        assert result.holdings_overlap["A vs B"] == 0.0

    def test_generate_report(self):
        comparator = PortfolioComparator()

        snap_a = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="A", cash=10000,
            holdings=[], total_assets=110000, total_pnl_pct=0.10,
            high_water_mark=110000,
        )
        snap_b = PortfolioSnapshot(
            date="2024-01-15", portfolio_name="B", cash=20000,
            holdings=[], total_assets=105000, total_pnl_pct=0.05,
            high_water_mark=105000,
        )

        result = comparator.compare_snapshots({"A": snap_a, "B": snap_b})
        report = comparator.generate_report(result)

        assert "组合对比报告" in report
        assert "A" in report
        assert "B" in report
