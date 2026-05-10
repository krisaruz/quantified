"""监控告警测试"""

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from vertexquant.monitoring.alert_rules import (
    ConcentrationAlert,
    DataFreshnessAlert,
    DrawdownAlert,
    PnLAlert,
)
from vertexquant.monitoring.engine import MonitorEngine
from vertexquant.monitoring.health import HealthScore
from vertexquant.monitoring.models import Alert, MonitorContext
from vertexquant.monitoring.notifiers import LogNotifier, CompositeNotifier


def _make_snapshots(values: list[float]):
    """辅助：生成简易快照列表"""
    return [SimpleNamespace(net_value=v) for v in values]


def _make_holdings(holdings_data: list[tuple]):
    """辅助：生成简易持仓列表"""
    return [
        SimpleNamespace(cb_code=code, buy_price=price, volume=vol)
        for code, price, vol in holdings_data
    ]


# ─────────────── PnL Alert ───────────────


class TestPnLAlert:
    def test_no_alert_normal(self):
        rule = PnLAlert()
        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 1.01]),
            recent_trades=[], data_meta={},
        )
        assert rule.evaluate(ctx) is None

    def test_warning_alert(self):
        rule = PnLAlert()
        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.96]),
            recent_trades=[], data_meta={},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "warning"

    def test_critical_alert(self):
        rule = PnLAlert()
        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.94]),
            recent_trades=[], data_meta={},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "critical"

    def test_insufficient_data(self):
        rule = PnLAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0]),
            recent_trades=[], data_meta={},
        )
        assert rule.evaluate(ctx) is None


# ─────────────── Concentration Alert ───────────────


class TestConcentrationAlert:
    def test_no_alert_diversified(self):
        rule = ConcentrationAlert()
        holdings = _make_holdings([
            ("123001", 100, 100),  # 10000
            ("123002", 100, 100),  # 10000
            ("123003", 100, 100),  # 10000
        ])
        ctx = MonitorContext(
            date="2024-01-01", cash=70000, holdings=holdings,
            recent_snapshots=[], recent_trades=[], data_meta={},
        )
        assert rule.evaluate(ctx) is None

    def test_warning_concentration(self):
        rule = ConcentrationAlert()
        # value = 100 * 200 / 10 = 2000, total = 2000 + 8000 = 10000, weight = 20%
        holdings = _make_holdings([
            ("123001", 100, 200),
        ])
        ctx = MonitorContext(
            date="2024-01-01", cash=8000, holdings=holdings,
            recent_snapshots=[], recent_trades=[], data_meta={},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "warning"

    def test_critical_concentration(self):
        rule = ConcentrationAlert()
        # value = 100 * 300 / 10 = 3000, total = 3000 + 7000 = 10000, weight = 30%
        holdings = _make_holdings([
            ("123001", 100, 300),
        ])
        ctx = MonitorContext(
            date="2024-01-01", cash=7000, holdings=holdings,
            recent_snapshots=[], recent_trades=[], data_meta={},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "critical"


# ─────────────── Data Freshness Alert ───────────────


class TestDataFreshnessAlert:
    def test_fresh_data(self):
        rule = DataFreshnessAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=[], recent_trades=[],
            data_meta={"last_sync_bond_daily": datetime.now().isoformat()},
        )
        assert rule.evaluate(ctx) is None

    def test_no_sync_ever(self):
        rule = DataFreshnessAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=[], recent_trades=[], data_meta={},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "critical"

    def test_stale_data_warning(self):
        rule = DataFreshnessAlert()
        stale_date = (datetime.now() - timedelta(days=5)).isoformat()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=[], recent_trades=[],
            data_meta={"last_sync_bond_daily": stale_date},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "warning"

    def test_stale_data_critical(self):
        rule = DataFreshnessAlert()
        stale_date = (datetime.now() - timedelta(days=10)).isoformat()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=[], recent_trades=[],
            data_meta={"last_sync_bond_daily": stale_date},
        )
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "critical"


# ─────────────── Drawdown Alert ───────────────


class TestDrawdownAlert:
    def test_no_drawdown(self):
        rule = DrawdownAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 1.05, 1.1]),
            recent_trades=[], data_meta={},
        )
        assert rule.evaluate(ctx) is None

    def test_warning_drawdown(self):
        rule = DrawdownAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 1.1, 1.02]),
            recent_trades=[], data_meta={},
        )
        # drawdown from 1.1 to 1.02 = -7.3%
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "warning"

    def test_critical_drawdown(self):
        rule = DrawdownAlert()
        ctx = MonitorContext(
            date="2024-01-01", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 1.1, 1.0]),
            recent_trades=[], data_meta={},
        )
        # drawdown from 1.1 to 1.0 = -9.1%
        alert = rule.evaluate(ctx)
        assert alert is not None
        assert alert.severity == "critical"


# ─────────────── Monitor Engine ───────────────


class TestMonitorEngine:
    def test_check_all(self):
        engine = MonitorEngine()
        engine.add_rule(PnLAlert())

        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.94]),
            recent_trades=[], data_meta={},
        )

        alerts = engine.check_all(ctx)
        assert len(alerts) == 1
        assert alerts[0].severity == "critical"

    def test_history(self):
        engine = MonitorEngine()
        engine.add_rule(PnLAlert())

        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.94]),
            recent_trades=[], data_meta={},
        )

        engine.check_all(ctx)
        history = engine.get_history()
        assert len(history) == 1

    def test_acknowledge(self):
        engine = MonitorEngine()
        engine.add_rule(PnLAlert())

        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.94]),
            recent_trades=[], data_meta={},
        )

        alerts = engine.check_all(ctx)
        assert engine.acknowledge(alerts[0].alert_id)

        history = engine.get_history()
        assert history[0].acknowledged

    def test_notifier_called(self):
        engine = MonitorEngine()
        engine.add_rule(PnLAlert())

        notified = []

        class TestNotifier:
            def notify(self, alert):
                notified.append(alert)
                return True

        engine.add_notifier(TestNotifier())

        ctx = MonitorContext(
            date="2024-01-02", cash=0, holdings=[],
            recent_snapshots=_make_snapshots([1.0, 0.94]),
            recent_trades=[], data_meta={},
        )

        engine.check_all(ctx)
        assert len(notified) == 1


# ─────────────── Health Score ───────────────


class TestHealthScore:
    def test_basic_health(self):
        scorer = HealthScore()
        ctx = MonitorContext(
            date="2024-01-01", cash=50000,
            holdings=_make_holdings([
                ("123001", 100, 100),
                ("123002", 100, 100),
                ("123003", 100, 100),
            ]),
            recent_snapshots=_make_snapshots([1.0 + i * 0.001 for i in range(30)]),
            recent_trades=[], data_meta={},
        )

        score = scorer.calculate(ctx)
        assert 0 <= score <= 100

    def test_breakdown(self):
        scorer = HealthScore()
        ctx = MonitorContext(
            date="2024-01-01", cash=50000,
            holdings=_make_holdings([
                ("123001", 100, 100),
                ("123002", 100, 100),
            ]),
            recent_snapshots=_make_snapshots([1.0 + i * 0.001 for i in range(30)]),
            recent_trades=[], data_meta={},
        )

        breakdown = scorer.calculate_breakdown(ctx)
        assert 0 <= breakdown.data_freshness <= 100
        assert 0 <= breakdown.diversification <= 100
        assert 0 <= breakdown.stability <= 100
        assert 0 <= breakdown.drawdown <= 100
        assert 0 <= breakdown.execution <= 100
        assert 0 <= breakdown.total <= 100
