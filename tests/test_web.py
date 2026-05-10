"""测试 Web 应用 API"""

import json
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from vertexquant.web.app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


class TestWebRoutes:
    def test_index(self, client):
        r = client.get("/")
        assert r.status_code == 200
        html = r.data.decode("utf-8")
        assert "双低" in html or "转债" in html

    def test_api_config(self, client):
        r = client.get("/api/config")
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert "config" in data
        assert data["config"]["strategy"]["hold_count"] == 10

    def test_api_portfolio_empty(self, client):
        with patch("vertexquant.web.app.load_portfolio") as mock_lp, \
             patch("vertexquant.web.app.build_universe") as mock_bu, \
             patch("vertexquant.web.app._get_session") as mock_sess:
            from vertexquant.portfolio import Portfolio
            mock_lp.return_value = Portfolio()
            mock_bu.return_value = pd.DataFrame()
            mock_sess.return_value = MagicMock()

            r = client.get("/api/portfolio")
            data = json.loads(r.data)
            assert data["status"] == "ok"
            assert data["count"] == 0
            assert "total_assets" in data

    @patch("vertexquant.web.app._get_session")
    @patch("vertexquant.db.get_meta", return_value="2025-06-01")
    def test_api_stats(self, mock_meta, mock_session, client):
        mock_sess = MagicMock()
        mock_sess.query.return_value.count.return_value = 42
        mock_session.return_value = mock_sess

        with patch("vertexquant.web.app.load_portfolio") as mock_lp:
            from vertexquant.portfolio import Portfolio
            mock_lp.return_value = Portfolio()

            r = client.get("/api/stats")
            data = json.loads(r.data)
            assert data["status"] == "ok"
            assert data["total_bonds"] == 42
            assert "version" in data

    @patch("vertexquant.web.app._get_session")
    @patch("vertexquant.web.app.build_filtered_ranked")
    def test_api_universe(self, mock_bfr, mock_session, client):
        mock_session.return_value = MagicMock()

        df = pd.DataFrame([{
            "cb_code": "CB001", "cb_name": "测试", "cb_close": 100,
            "premium_rate": 0.05, "double_low": 105, "rank": 1,
        }])
        from vertexquant.filter import FilterStep
        mock_bfr.return_value = (df, df, [FilterStep("test", 1, 1)])

        r = client.get("/api/universe")
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert len(data["items"]) == 1
        assert "version" in data

    @patch("vertexquant.web.app._get_session")
    @patch("vertexquant.web.app.build_filtered_ranked")
    @patch("vertexquant.web.app.load_portfolio")
    def test_api_recommendation(self, mock_lp, mock_bfr, mock_session, client):
        mock_session.return_value = MagicMock()

        df = pd.DataFrame([{
            "cb_code": "CB001", "cb_name": "测试", "cb_close": 100,
            "premium_rate": 0.05, "double_low": 105, "trade_available": True,
            "credit_rating": "AA",
        }])
        from vertexquant.filter import FilterStep
        from vertexquant.portfolio import Portfolio
        mock_bfr.return_value = (df, df, [FilterStep("test", 1, 1)])
        mock_lp.return_value = Portfolio()

        r = client.get("/api/recommendation")
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert "actions" in data
        assert "is_rebalance_day" in data

    @patch("vertexquant.web.app.load_portfolio")
    @patch("vertexquant.web.app.save_portfolio")
    def test_api_buy_missing_params(self, mock_save, mock_lp, client):
        r = client.post("/api/portfolio/buy", json={})
        assert r.status_code == 400

    @patch("vertexquant.web.app.load_portfolio")
    @patch("vertexquant.web.app.save_portfolio")
    def test_api_sell_not_held(self, mock_save, mock_lp, client):
        from vertexquant.portfolio import Portfolio
        mock_lp.return_value = Portfolio()

        r = client.post("/api/portfolio/sell", json={"cb_code": "X", "sell_price": 100})
        assert r.status_code == 404

    def test_health_endpoint(self, client):
        with patch("vertexquant.web.app._get_session") as mock_session, \
             patch("vertexquant.db.get_meta", return_value="2025-06-01"):
            mock_session.return_value = MagicMock()
            r = client.get("/health")
            data = json.loads(r.data)
            assert "status" in data
            assert "version" in data
            assert "database" in data


class TestWebPortfolioWithPnL:
    """测试持仓盈亏功能"""

    @patch("vertexquant.web.app._get_session")
    @patch("vertexquant.web.app.build_universe")
    @patch("vertexquant.web.app.load_portfolio")
    def test_portfolio_with_holdings(self, mock_lp, mock_bu, mock_session, client):
        from vertexquant.portfolio import Holding, Portfolio

        p = Portfolio(cash=90000)
        p.holdings = [Holding("CB001", "测试转债", "2025-01-01", 100.0, 10)]
        mock_lp.return_value = p

        df = pd.DataFrame([{
            "cb_code": "CB001", "cb_close": 110.0,
        }])
        mock_bu.return_value = df
        mock_session.return_value = MagicMock()

        r = client.get("/api/portfolio")
        data = json.loads(r.data)
        assert data["status"] == "ok"
        assert len(data["holdings"]) == 1
        h = data["holdings"][0]
        assert h["current_price"] == 110.0
        assert h["pnl"] > 0
        assert h["pnl_pct"] > 0
