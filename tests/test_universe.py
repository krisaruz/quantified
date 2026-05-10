"""测试统一 universe 构建"""

import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from vertexquant.config import AppConfig


class TestBuildUniverse:
    """测试 build_universe 函数"""

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_returns_empty_when_no_data(self, mock_bb, mock_sb, mock_sd, mock_bd):
        from vertexquant.universe import build_universe

        session = MagicMock()
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = []

        result = build_universe(session, "2025-06-01")
        assert result.empty

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_computes_derived_metrics(self, mock_bb, mock_sb, mock_sd, mock_bd):
        from vertexquant.universe import build_universe

        session = MagicMock()
        rows = [
            ("CB001", "测试转债", "600001", 10.0, 5.0, "AA", "active",
             datetime.date(2028, 1, 1), 100.0, 1000, 15.0, False),
        ]
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = rows

        df = build_universe(session, "2025-06-01")
        assert len(df) == 1
        assert df.iloc[0]["cb_code"] == "CB001"
        assert df.iloc[0]["conversion_value"] == pytest.approx(150.0, rel=1e-2)
        assert bool(df.iloc[0]["trade_available"]) is True

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_trade_available_false_when_zero_volume(self, mock_bb, mock_sb, mock_sd, mock_bd):
        from vertexquant.universe import build_universe

        session = MagicMock()
        rows = [
            ("CB002", "停牌转债", "600002", 10.0, 5.0, "AA", "active",
             datetime.date(2028, 1, 1), 100.0, 0, 15.0, False),
        ]
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = rows

        df = build_universe(session, "2025-06-01")
        assert bool(df.iloc[0]["trade_available"]) is False


class TestBuildFilteredRanked:
    """测试 build_filtered_ranked"""

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_returns_sorted_by_composite_score(self, mock_bb, mock_sb, mock_sd, mock_bd):
        from vertexquant.universe import build_filtered_ranked

        session = MagicMock()
        rows = [
            ("CB001", "低双低", "600001", 10.0, 5.0, "AA", "active",
             datetime.date(2028, 1, 1), 95.0, 100, 12.0, False),
            ("CB002", "高双低", "600002", 8.0, 5.0, "AA", "active",
             datetime.date(2028, 1, 1), 120.0, 200, 10.0, False),
        ]
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = rows

        config = AppConfig()
        config.filters.min_turnover = 0
        _, filtered, audit = build_filtered_ranked(session, "2025-06-01", config)

        assert not filtered.empty
        assert len(audit) > 0
        assert "composite_score" in filtered.columns
        assert "risk_level" in filtered.columns
        assert "rank" in filtered.columns
        if len(filtered) > 1:
            assert filtered.iloc[0]["composite_score"] <= filtered.iloc[1]["composite_score"]

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_risk_level_assigned(self, mock_bb, mock_sb, mock_sd, mock_bd):
        from vertexquant.universe import build_filtered_ranked

        session = MagicMock()
        rows = [
            ("CB001", "安全转债", "600001", 10.0, 5.0, "AA", "active",
             datetime.date(2028, 1, 1), 105.0, 100, 12.0, False),
        ]
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = rows

        config = AppConfig()
        config.filters.min_turnover = 0
        _, filtered, _ = build_filtered_ranked(session, "2025-06-01", config)

        assert not filtered.empty
        assert filtered.iloc[0]["risk_level"] in ("low", "medium", "high")

    @patch("vertexquant.universe.BondDaily")
    @patch("vertexquant.universe.StockDaily")
    @patch("vertexquant.universe.StockBasic")
    @patch("vertexquant.universe.BondBasic")
    def test_aaa_ranks_higher_than_aa_minus(self, mock_bb, mock_sb, mock_sd, mock_bd):
        """AAA 评级转债综合评分应低于 AA- 评级（同等条件下）"""
        from vertexquant.universe import build_filtered_ranked

        session = MagicMock()
        rows = [
            ("CB001", "AAA转债", "600001", 10.0, 5.0, "AAA", "active",
             datetime.date(2028, 1, 1), 100.0, 100, 12.0, False),
            ("CB002", "AAminus", "600002", 10.0, 5.0, "AA-", "active",
             datetime.date(2028, 1, 1), 100.0, 200, 12.0, False),
        ]
        session.query.return_value.join.return_value.outerjoin.return_value.outerjoin.return_value.all.return_value = rows

        config = AppConfig()
        config.filters.min_turnover = 0
        _, filtered, _ = build_filtered_ranked(session, "2025-06-01", config)

        assert not filtered.empty
        assert len(filtered) == 2
        assert filtered.iloc[0]["cb_code"] == "CB001"
