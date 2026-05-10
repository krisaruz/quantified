"""测试过滤器链"""

import datetime

import pandas as pd

from vertexquant.config import AppConfig
from vertexquant.filter import (
    FilterChain,
    filter_credit_rating,
    filter_delisted,
    filter_max_price,
    filter_min_turnover,
    filter_redeeming,
    filter_remaining_years,
    filter_st,
    filter_suspended,
)


def _make_df(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


class TestIndividualFilters:
    def test_filter_st_removes_st(self):
        df = _make_df([
            {"cb_code": "A", "is_st": True},
            {"cb_code": "B", "is_st": False},
        ])
        config = AppConfig()
        result = filter_st(df, config)
        assert list(result["cb_code"]) == ["B"]

    def test_filter_st_disabled(self):
        df = _make_df([
            {"cb_code": "A", "is_st": True},
            {"cb_code": "B", "is_st": False},
        ])
        config = AppConfig()
        config.filters.exclude_st = False
        result = filter_st(df, config)
        assert len(result) == 2

    def test_filter_max_price(self):
        df = _make_df([
            {"cb_code": "A", "cb_close": 100},
            {"cb_code": "B", "cb_close": 150},
            {"cb_code": "C", "cb_close": 130},
        ])
        config = AppConfig()
        config.filters.max_price = 130
        result = filter_max_price(df, config)
        assert set(result["cb_code"]) == {"A", "C"}

    def test_filter_credit_rating(self):
        df = _make_df([
            {"cb_code": "A", "credit_rating": "AAA"},
            {"cb_code": "B", "credit_rating": "A+"},
            {"cb_code": "C", "credit_rating": "AA"},
        ])
        config = AppConfig()
        config.filters.min_credit_rating = "AA-"
        result = filter_credit_rating(df, config)
        assert set(result["cb_code"]) == {"A", "C"}

    def test_filter_delisted(self):
        df = _make_df([
            {"cb_code": "A", "status": "active"},
            {"cb_code": "B", "status": "delisted"},
            {"cb_code": "C", "status": "redeem_warning"},
        ])
        config = AppConfig()
        result = filter_delisted(df, config)
        assert set(result["cb_code"]) == {"A", "C"}

    def test_filter_redeeming_excludes(self):
        df = _make_df([
            {"cb_code": "A", "status": "active"},
            {"cb_code": "B", "status": "redeem_warning"},
        ])
        config = AppConfig()
        config.filters.exclude_redeeming = True
        result = filter_redeeming(df, config)
        assert set(result["cb_code"]) == {"A"}

    def test_filter_redeeming_disabled(self):
        df = _make_df([
            {"cb_code": "A", "status": "active"},
            {"cb_code": "B", "status": "redeem_warning"},
        ])
        config = AppConfig()
        config.filters.exclude_redeeming = False
        result = filter_redeeming(df, config)
        assert len(result) == 2

    def test_filter_suspended(self):
        df = _make_df([
            {"cb_code": "A", "trade_available": True},
            {"cb_code": "B", "trade_available": False},
            {"cb_code": "C", "trade_available": None},
        ])
        config = AppConfig()
        result = filter_suspended(df, config)
        assert set(result["cb_code"]) == {"A"}

    def test_filter_suspended_disabled(self):
        df = _make_df([
            {"cb_code": "A", "trade_available": True},
            {"cb_code": "B", "trade_available": False},
        ])
        config = AppConfig()
        config.filters.exclude_suspended = False
        result = filter_suspended(df, config)
        assert len(result) == 2

    def test_filter_remaining_years(self):
        today = datetime.date.today()
        df = _make_df([
            {"cb_code": "A", "maturity_date": today + datetime.timedelta(days=365)},
            {"cb_code": "B", "maturity_date": today + datetime.timedelta(days=30)},
        ])
        config = AppConfig()
        config.filters.min_remaining_years = 0.5
        result = filter_remaining_years(df, config)
        assert set(result["cb_code"]) == {"A"}

    def test_filter_remaining_years_no_column(self):
        df = _make_df([{"cb_code": "A"}])
        config = AppConfig()
        result = filter_remaining_years(df, config)
        assert len(result) == 1

    def test_filter_min_turnover(self):
        df = _make_df([
            {"cb_code": "A", "cb_volume": 1000},
            {"cb_code": "B", "cb_volume": 100},
            {"cb_code": "C", "cb_volume": 0},
        ])
        config = AppConfig()
        config.filters.min_turnover = 500
        result = filter_min_turnover(df, config)
        assert set(result["cb_code"]) == {"A"}

    def test_filter_min_turnover_zero_allows_all(self):
        df = _make_df([
            {"cb_code": "A", "cb_volume": 1000},
            {"cb_code": "B", "cb_volume": 0},
        ])
        config = AppConfig()
        config.filters.min_turnover = 0
        result = filter_min_turnover(df, config)
        assert len(result) == 2


class TestFilterChain:
    def test_full_chain(self):
        df = _make_df([
            {"cb_code": "GOOD", "is_st": False, "status": "active",
             "cb_close": 100, "credit_rating": "AA", "trade_available": True, "cb_volume": 1000},
            {"cb_code": "BAD_ST", "is_st": True, "status": "active",
             "cb_close": 100, "credit_rating": "AA", "trade_available": True, "cb_volume": 1000},
            {"cb_code": "BAD_PRICE", "is_st": False, "status": "active",
             "cb_close": 200, "credit_rating": "AA", "trade_available": True, "cb_volume": 1000},
        ])
        config = AppConfig()
        config.filters.min_turnover = 0
        chain = FilterChain(config)
        result, audit = chain.apply(df)

        assert "GOOD" in set(result["cb_code"])
        assert "BAD_ST" not in set(result["cb_code"])
        assert "BAD_PRICE" not in set(result["cb_code"])
        assert len(audit) > 0

    def test_audit_records(self):
        df = _make_df([
            {"cb_code": "A", "is_st": True, "status": "active"},
            {"cb_code": "B", "is_st": False, "status": "active"},
        ])
        config = AppConfig()
        config.filters.min_turnover = 0
        chain = FilterChain(config)
        _, audit = chain.apply(df)

        st_step = next(s for s in audit if s.name == "排除ST正股")
        assert st_step.before_count == 2
        assert st_step.after_count == 1
        assert "A" in st_step.removed

    def test_liquidity_filter_in_chain(self):
        df = _make_df([
            {"cb_code": "GOOD", "is_st": False, "status": "active",
             "cb_close": 100, "credit_rating": "AA", "trade_available": True, "cb_volume": 1000},
            {"cb_code": "LOW_LIQ", "is_st": False, "status": "active",
             "cb_close": 100, "credit_rating": "AA", "trade_available": True, "cb_volume": 10},
        ])
        config = AppConfig()
        config.filters.min_turnover = 500
        chain = FilterChain(config)
        result, audit = chain.apply(df)

        assert "GOOD" in set(result["cb_code"])
        assert "LOW_LIQ" not in set(result["cb_code"])

        liq_step = next(s for s in audit if s.name == "排除流动性不足")
        assert liq_step.before_count > liq_step.after_count
