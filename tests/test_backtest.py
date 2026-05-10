"""回测引擎测试"""

from __future__ import annotations

import datetime

import pytest

from vertexquant.backtest.account import Position, VirtualAccount, TradeRecord
from vertexquant.backtest.stats import compute_stats, PerformanceStats
from vertexquant.backtest.engine import BacktestResult, DailySnapshot


class TestPosition:
    def test_total_volume(self):
        pos = Position(cb_code="123001", cb_name="测试转债", available=10, frozen=5, avg_cost=100.0)
        assert pos.total_volume == 15

    def test_market_value(self):
        pos = Position(cb_code="123001", cb_name="测试转债", available=10, frozen=0, avg_cost=100.0)
        assert pos.market_value(110.0) == 110.0 * 10 / 10


class TestVirtualAccount:
    def test_initial_state(self):
        acc = VirtualAccount(initial_capital=100000)
        assert acc.cash == 100000
        assert len(acc.positions) == 0

    def test_buy(self):
        acc = VirtualAccount(initial_capital=100000, slippage=0)
        trade = acc.buy("2024-01-01", "123001", "测试转债", 100.0, 10)
        assert trade is not None
        assert trade.direction == "buy"
        assert acc.positions["123001"].frozen == 10
        assert acc.positions["123001"].available == 0
        assert acc.cash < 100000

    def test_settle_unfreezes(self):
        acc = VirtualAccount(initial_capital=100000, slippage=0)
        acc.buy("2024-01-01", "123001", "测试转债", 100.0, 10)
        assert acc.positions["123001"].available == 0
        acc.settle()
        assert acc.positions["123001"].available == 10
        assert acc.positions["123001"].frozen == 0

    def test_sell_only_available(self):
        acc = VirtualAccount(initial_capital=100000, slippage=0)
        acc.buy("2024-01-01", "123001", "测试转债", 100.0, 10)
        result = acc.sell("2024-01-01", "123001", 105.0, 10)
        assert result is None  # frozen, can't sell

        acc.settle()
        result = acc.sell("2024-01-02", "123001", 105.0)
        assert result is not None
        assert result.direction == "sell"
        assert "123001" not in acc.positions

    def test_net_value(self):
        acc = VirtualAccount(initial_capital=100000, slippage=0, commission_rate=0)
        acc.buy("2024-01-01", "123001", "测试转债", 100.0, 100)
        acc.settle()
        nv = acc.net_value({"123001": 110.0})
        expected_cash = 100000 - 100.0 * 100 / 10
        expected_mkt = 110.0 * 100 / 10
        assert abs(nv - (expected_cash + expected_mkt)) < 1.0

    def test_insufficient_funds_reduces_volume(self):
        acc = VirtualAccount(initial_capital=200, slippage=0, commission_rate=0)
        trade = acc.buy("2024-01-01", "123001", "测试转债", 100.0, 100)
        assert trade is not None
        assert trade.volume < 100  # should buy fewer than requested

    def test_insufficient_funds_returns_none(self):
        acc = VirtualAccount(initial_capital=5, slippage=0, commission_rate=0)
        trade = acc.buy("2024-01-01", "123001", "测试转债", 100.0, 100)
        assert trade is None


class TestComputeStats:
    def _make_result(self, values: list[float], initial: float = 100000) -> BacktestResult:
        snaps = [
            DailySnapshot(
                date=f"2024-01-{i+1:02d}", net_value=v,
                cash=v * 0.5, market_value=v * 0.5, position_count=5,
            )
            for i, v in enumerate(values)
        ]
        return BacktestResult(
            start_date="2024-01-01", end_date=f"2024-01-{len(values):02d}",
            initial_capital=initial, final_value=values[-1],
            daily_snapshots=snaps, trades=[], trading_days=len(values),
        )

    def test_total_return(self):
        result = self._make_result([100000, 105000, 110000])
        stats = compute_stats(result)
        assert abs(stats.total_return - 0.10) < 0.001

    def test_zero_trades(self):
        result = self._make_result([100000, 100000])
        stats = compute_stats(result)
        assert stats.total_return == 0

    def test_max_drawdown(self):
        result = self._make_result([100000, 110000, 99000, 105000])
        stats = compute_stats(result)
        assert stats.max_drawdown > 0

    def test_empty_snapshots(self):
        result = BacktestResult(
            start_date="2024-01-01", end_date="2024-01-01",
            initial_capital=100000, final_value=100000,
        )
        stats = compute_stats(result)
        assert stats.trading_days == 0

    def test_win_rate(self):
        result = self._make_result([100000, 105000])
        result.trades = [
            TradeRecord(date="2024-01-01", cb_code="A", cb_name="A", direction="buy", price=100, volume=10, amount=100, fee=0),
            TradeRecord(date="2024-01-02", cb_code="A", cb_name="A", direction="sell", price=110, volume=10, amount=110, fee=0),
            TradeRecord(date="2024-01-01", cb_code="B", cb_name="B", direction="buy", price=100, volume=10, amount=100, fee=0),
            TradeRecord(date="2024-01-02", cb_code="B", cb_name="B", direction="sell", price=90, volume=10, amount=90, fee=0),
        ]
        stats = compute_stats(result)
        assert stats.win_rate == 0.5

    def test_format_report(self):
        result = self._make_result([100000, 108000])
        stats = compute_stats(result)
        report = stats.format_report()
        assert "总收益率" in report
        assert "年化收益率" in report
        assert "最大回撤" in report
        assert "夏普比率" in report
