"""数据管道增强测试"""

import pytest
import pandas as pd

from vertexquant.pipeline.quality import DataQualityChecker, QualityCheck, QualityReport
from vertexquant.pipeline.sync_state import (
    InvalidSyncStateError,
    SyncError,
    SyncStateMachine,
    SyncStatus,
)
from vertexquant.pipeline.sync_queue import SyncTask, SyncTaskQueue
from vertexquant.pipeline.retry import RetryPolicy
from vertexquant.pipeline.data_source import DataSourceManager
from vertexquant.pipeline.lineage import LineageTracker


# ─────────────── DataQualityChecker ───────────────


class TestDataQualityChecker:
    @pytest.fixture
    def checker(self):
        return DataQualityChecker()

    @pytest.fixture
    def good_df(self):
        return pd.DataFrame({
            "trade_date": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "open": [100.0, 101.0, 102.0],
            "high": [105.0, 106.0, 107.0],
            "low": [99.0, 100.0, 101.0],
            "close": [102.0, 103.0, 104.0],
            "volume": [1000, 1200, 1100],
        })

    def test_bond_daily_pass(self, checker, good_df):
        report = checker.check_bond_daily(good_df, "2024-01-03")
        assert report.is_acceptable
        assert report.overall_score == 1.0

    def test_price_range_violation(self, checker):
        df = pd.DataFrame({
            "close": [100.0, 20.0, 600.0],
            "open": [100.0, 20.0, 600.0],
            "high": [100.0, 20.0, 600.0],
            "low": [100.0, 20.0, 600.0],
            "volume": [1000, 1000, 1000],
        })
        report = checker.check_bond_daily(df, "2024-01-01")
        price_check = next(c for c in report.checks if c.name == "price_range")
        assert not price_check.passed
        assert price_check.affected_rows == 2

    def test_ohlc_consistency_violation(self, checker):
        df = pd.DataFrame({
            "open": [100.0],
            "high": [95.0],  # high < open, 违规
            "low": [98.0],
            "close": [101.0],
            "volume": [1000],
        })
        report = checker.check_bond_daily(df, "2024-01-01")
        ohlc = next(c for c in report.checks if c.name == "ohlc_consistency")
        assert not ohlc.passed
        assert ohlc.severity == "error"

    def test_negative_volume(self, checker):
        df = pd.DataFrame({
            "close": [100.0],
            "volume": [-100],
        })
        report = checker.check_bond_daily(df, "2024-01-01")
        vol = next(c for c in report.checks if c.name == "volume_non_negative")
        assert not vol.passed

    def test_sudden_jump(self, checker):
        df = pd.DataFrame({
            "close": [100.0, 101.0, 150.0],  # 50% jump
            "volume": [1000, 1000, 1000],
        })
        report = checker.check_bond_daily(df, "2024-01-03")
        jump = next(c for c in report.checks if c.name == "sudden_jump")
        assert not jump.passed

    def test_quality_score(self, checker, good_df):
        report = checker.check_bond_daily(good_df, "2024-01-03")
        assert report.overall_score == 1.0
        assert report.is_acceptable

    def test_stock_daily(self, checker, good_df):
        report = checker.check_stock_daily(good_df, "2024-01-03")
        assert report.entity == "stock_daily"
        assert report.is_acceptable


# ─────────────── SyncStateMachine ───────────────


class TestSyncStateMachine:
    def test_initial_state(self):
        sm = SyncStateMachine()
        assert sm.state == SyncStatus.IDLE

    def test_start_sync(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        assert sm.state == SyncStatus.SYNCING

    def test_complete_returns_to_idle(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        sm.complete("bond_daily")
        assert sm.state == SyncStatus.IDLE

    def test_error_transitions(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        sm.error("bond_daily", ValueError("test error"))
        assert sm.state == SyncStatus.ERROR
        assert len(sm.get_errors()) == 1

    def test_pause_resume(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        sm.pause()
        assert sm.state == SyncStatus.PAUSED
        sm.resume()
        assert sm.state == SyncStatus.SYNCING

    def test_invalid_transition(self):
        sm = SyncStateMachine()
        with pytest.raises(InvalidSyncStateError):
            sm.pause()  # idle -> paused 不合法

    def test_reset(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        sm.error("bond_daily", ValueError("test"))
        sm.reset()
        assert sm.state == SyncStatus.IDLE

    def test_mark_progress(self):
        sm = SyncStateMachine()
        sm.start("bond_daily")
        sm.mark_progress("bond_daily", "2024-01-15")
        prog = sm.get_progress("bond_daily")
        assert prog is not None
        assert prog.last_synced_date == "2024-01-15"


# ─────────────── SyncTaskQueue ───────────────


class TestSyncTaskQueue:
    def test_enqueue_dequeue(self):
        q = SyncTaskQueue()
        t1 = SyncTask("bond_daily", "123001", "2024-01-01", "2024-01-31", priority=1)
        t2 = SyncTask("bond_daily", "123002", "2024-01-01", "2024-01-31", priority=0)

        q.enqueue(t1)
        q.enqueue(t2)

        first = q.dequeue()
        assert first is not None
        assert first.cb_code == "123002"  # higher priority (lower number)
        assert first.status == "running"

    def test_mark_done(self):
        q = SyncTaskQueue()
        t = SyncTask("bond_daily", "123001", "2024-01-01", "2024-01-31")
        q.enqueue(t)
        task = q.dequeue()
        q.mark_done(task)
        assert task.status == "done"

    def test_mark_failed(self):
        q = SyncTaskQueue()
        t = SyncTask("bond_daily", "123001", "2024-01-01", "2024-01-31")
        q.enqueue(t)
        task = q.dequeue()
        q.mark_failed(task, ValueError("network error"))
        assert task.status == "failed"
        assert task.retry_count == 1

    def test_retry_failed(self):
        q = SyncTaskQueue()
        t = SyncTask("bond_daily", "123001", "2024-01-01", "2024-01-31")
        q.enqueue(t)
        task = q.dequeue()
        q.mark_failed(task, ValueError("error"))

        requeued = q.retry_failed(max_retries=3)
        assert requeued == 1
        assert task.status == "pending"

    def test_progress(self):
        q = SyncTaskQueue()
        q.enqueue(SyncTask("a", "1", "2024-01-01", "2024-01-31"))
        q.enqueue(SyncTask("b", "2", "2024-01-01", "2024-01-31"))

        t1 = q.dequeue()
        q.mark_done(t1)

        prog = q.get_progress()
        assert prog.total == 2
        assert prog.done == 1
        assert prog.pending == 1


# ─────────────── RetryPolicy ───────────────


class TestRetryPolicy:
    def test_exponential_backoff(self):
        policy = RetryPolicy(base_delay=1.0, backoff_factor=2.0, max_delay=60.0)
        assert policy.get_delay(0) == 1.0
        assert policy.get_delay(1) == 2.0
        assert policy.get_delay(2) == 4.0

    def test_max_delay_cap(self):
        policy = RetryPolicy(base_delay=10.0, backoff_factor=3.0, max_delay=50.0)
        assert policy.get_delay(0) == 10.0
        assert policy.get_delay(1) == 30.0
        assert policy.get_delay(2) == 50.0  # capped

    def test_should_retry(self):
        policy = RetryPolicy(max_retries=3)
        assert policy.should_retry(0)
        assert policy.should_retry(2)
        assert not policy.should_retry(3)

    def test_get_all_delays(self):
        policy = RetryPolicy(max_retries=3)
        delays = policy.get_all_delays()
        assert len(delays) == 3


# ─────────────── DataSourceManager ───────────────


class TestDataSourceManager:
    def test_first_source_succeeds(self):
        from unittest.mock import MagicMock

        s1 = MagicMock()
        s1.fetch_bond_list.return_value = pd.DataFrame({"code": ["123001"]})
        s2 = MagicMock()

        mgr = DataSourceManager([s1, s2], names=["primary", "backup"])
        result = mgr.fetch_bond_list()
        assert len(result) == 1
        s2.fetch_bond_list.assert_not_called()

    def test_fallback_to_second(self):
        from unittest.mock import MagicMock
        from vertexquant.fetcher.protocol import DataFetchError

        s1 = MagicMock()
        s1.fetch_bond_list.side_effect = DataFetchError("timeout")
        s2 = MagicMock()
        s2.fetch_bond_list.return_value = pd.DataFrame({"code": ["123001"]})

        mgr = DataSourceManager([s1, s2], names=["primary", "backup"])
        result = mgr.fetch_bond_list()
        assert len(result) == 1
        health = mgr.get_health_status()
        assert not health["primary"].is_healthy
        assert health["backup"].is_healthy

    def test_all_fail(self):
        from unittest.mock import MagicMock
        from vertexquant.fetcher.protocol import DataFetchError

        s1 = MagicMock()
        s1.fetch_bond_list.side_effect = DataFetchError("fail1")
        s2 = MagicMock()
        s2.fetch_bond_list.side_effect = DataFetchError("fail2")

        mgr = DataSourceManager([s1, s2], names=["a", "b"])
        with pytest.raises(DataFetchError):
            mgr.fetch_bond_list()


# ─────────────── LineageTracker ───────────────


class TestLineageTracker:
    def test_record(self):
        tracker = LineageTracker()
        rec = tracker.record(
            entity_type="bond_daily",
            entity_key="123001:2024-01-15",
            source="akshare:bond_zh_hs_cov_daily",
            row_count=100,
            quality_score=0.95,
        )
        assert rec.id == 1
        assert rec.entity_type == "bond_daily"

    def test_get_history(self):
        tracker = LineageTracker()
        tracker.record("bond_daily", "123001:2024-01-15", "akshare", 100, 0.95)
        tracker.record("bond_daily", "123001:2024-01-15", "akshare", 100, 0.98)

        history = tracker.get_history("bond_daily", "123001:2024-01-15")
        assert len(history) == 2

    def test_get_by_source(self):
        tracker = LineageTracker()
        tracker.record("bond_daily", "a", "akshare", 100, 0.95)
        tracker.record("bond_daily", "b", "tushare", 50, 0.90)
        tracker.record("stock_daily", "c", "akshare", 200, 0.92)

        results = tracker.get_by_source("akshare")
        assert len(results) == 2

    def test_get_stale_entities(self):
        from datetime import datetime, timedelta

        tracker = LineageTracker()
        # 手动设置一个旧记录
        rec = tracker.record("bond_daily", "123001", "akshare", 100, 0.95)
        # 修改 fetched_at 为 10 天前
        tracker._records[0] = type(rec)(
            id=rec.id,
            entity_type=rec.entity_type,
            entity_key=rec.entity_key,
            source=rec.source,
            fetched_at=(datetime.now() - timedelta(days=10)).isoformat(),
            row_count=rec.row_count,
            quality_score=rec.quality_score,
            quality_report=rec.quality_report,
        )

        stale = tracker.get_stale_entities(max_age_days=7)
        assert len(stale) == 1
        assert "bond_daily:123001" in stale[0]

    def test_stats(self):
        tracker = LineageTracker()
        tracker.record("bond_daily", "a", "akshare", 100, 0.95)
        tracker.record("bond_daily", "b", "akshare", 50, 0.90)

        stats = tracker.get_stats()
        assert stats["total_records"] == 2
        assert stats["total_rows"] == 150
        assert stats["by_source"]["akshare"] == 2
