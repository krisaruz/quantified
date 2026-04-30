"""测试多因子评分与风险等级"""

import datetime

import pandas as pd
import pytest

from quantified.config import AppConfig
from quantified.scoring import (
    _bond_floor_bonus,
    _credit_penalty,
    _maturity_penalty,
    _remaining_years,
    assign_risk_level,
    compute_composite_score,
    describe_score_factors,
)


class TestRemainingYears:
    def test_normal(self):
        today = datetime.date(2025, 6, 1)
        maturity = datetime.date(2028, 6, 1)
        assert _remaining_years(maturity, today) == pytest.approx(3.0, abs=0.1)

    def test_none_returns_large_value(self):
        assert _remaining_years(None) == 999.0


class TestCreditPenalty:
    def test_aaa_rewarded(self):
        assert _credit_penalty("AAA", {}) == -3.0

    def test_aa_minus_penalized(self):
        assert _credit_penalty("AA-", {}) == 2.0

    def test_aa_is_baseline(self):
        assert _credit_penalty("AA", {}) == 0.0

    def test_none_uses_unknown(self):
        assert _credit_penalty(None, {"unknown": 7.0}) == 7.0

    def test_none_default_unknown(self):
        assert _credit_penalty(None, {}) == 5.0


class TestMaturityPenalty:
    def test_long_maturity_rewarded(self):
        assert _maturity_penalty(5.0, {}) == -2.0

    def test_medium_maturity(self):
        assert _maturity_penalty(3.0, {}) == 0.0

    def test_short_maturity_penalized(self):
        assert _maturity_penalty(1.5, {}) == 3.0

    def test_very_short_heavy_penalty(self):
        assert _maturity_penalty(0.5, {}) == 8.0

    def test_custom_weights(self):
        w = {"long": -4.0, "short": 5.0, "very_short": 12.0}
        assert _maturity_penalty(5.0, w) == -4.0
        assert _maturity_penalty(1.5, w) == 5.0
        assert _maturity_penalty(0.5, w) == 12.0


class TestBondFloorBonus:
    def test_below_par(self):
        assert _bond_floor_bonus(95.0, {}) == -5.0

    def test_near_par(self):
        assert _bond_floor_bonus(102.0, {}) == -2.0

    def test_at_110(self):
        assert _bond_floor_bonus(108.0, {}) == 0.0

    def test_above_110(self):
        result = _bond_floor_bonus(120.0, {})
        assert result == pytest.approx(1.5, abs=0.01)

    def test_custom_weights(self):
        w = {"below_par": -8.0, "near_par": -3.0, "above_scale": 0.2}
        assert _bond_floor_bonus(95.0, w) == -8.0


class TestCompositeScore:
    def _make_df(self, rows):
        return pd.DataFrame(rows)

    def test_basic_score(self):
        df = self._make_df([{
            "cb_close": 100.0,
            "premium_rate": 0.1,
            "credit_rating": "AA",
            "maturity_date": datetime.date(2030, 1, 1),
        }])
        config = AppConfig()
        scores = compute_composite_score(df, config)
        assert len(scores) == 1
        assert scores.iloc[0] < 200

    def test_aaa_scores_lower_than_aa_minus(self):
        df = self._make_df([
            {"cb_close": 100.0, "premium_rate": 0.1, "credit_rating": "AAA",
             "maturity_date": datetime.date(2030, 1, 1)},
            {"cb_close": 100.0, "premium_rate": 0.1, "credit_rating": "AA-",
             "maturity_date": datetime.date(2030, 1, 1)},
        ])
        config = AppConfig()
        scores = compute_composite_score(df, config)
        assert scores.iloc[0] < scores.iloc[1]

    def test_low_price_has_floor_bonus(self):
        df = self._make_df([
            {"cb_close": 95.0, "premium_rate": 0.1, "credit_rating": "AA",
             "maturity_date": datetime.date(2030, 1, 1)},
            {"cb_close": 120.0, "premium_rate": 0.1, "credit_rating": "AA",
             "maturity_date": datetime.date(2030, 1, 1)},
        ])
        config = AppConfig()
        scores = compute_composite_score(df, config)
        assert scores.iloc[0] < scores.iloc[1]


class TestAssignRiskLevel:
    def _make_df(self, rows):
        return pd.DataFrame(rows)

    def test_low_risk(self):
        df = self._make_df([{
            "cb_close": 105.0, "premium_rate": 0.1,
            "credit_rating": "AA", "maturity_date": datetime.date(2030, 1, 1),
        }])
        levels = assign_risk_level(df)
        assert levels.iloc[0] == "low"

    def test_high_risk_high_price(self):
        df = self._make_df([{
            "cb_close": 135.0, "premium_rate": 0.1,
            "credit_rating": "AA", "maturity_date": datetime.date(2028, 1, 1),
        }])
        levels = assign_risk_level(df)
        assert levels.iloc[0] == "high"

    def test_high_risk_high_premium(self):
        df = self._make_df([{
            "cb_close": 100.0, "premium_rate": 0.65,
            "credit_rating": "AA", "maturity_date": datetime.date(2028, 1, 1),
        }])
        levels = assign_risk_level(df)
        assert levels.iloc[0] == "high"

    def test_high_risk_short_maturity(self):
        df = self._make_df([{
            "cb_close": 100.0, "premium_rate": 0.1,
            "credit_rating": "AA", "maturity_date": datetime.date(2025, 12, 1),
        }])
        levels = assign_risk_level(df)
        assert levels.iloc[0] == "high"

    def test_medium_risk(self):
        df = self._make_df([{
            "cb_close": 115.0, "premium_rate": 0.25,
            "credit_rating": "AA", "maturity_date": datetime.date(2028, 1, 1),
        }])
        levels = assign_risk_level(df)
        assert levels.iloc[0] == "medium"


class TestDescribeScoreFactors:
    def test_low_price(self):
        row = pd.Series({
            "cb_close": 95.0, "premium_rate": 0.05,
            "credit_rating": "AAA", "maturity_date": datetime.date(2030, 1, 1),
        })
        desc = describe_score_factors(row)
        assert "保底" in desc
        assert "AAA" in desc

    def test_high_price(self):
        row = pd.Series({
            "cb_close": 125.0, "premium_rate": 0.4,
            "credit_rating": "AA-", "maturity_date": datetime.date(2027, 1, 1),
        })
        desc = describe_score_factors(row)
        assert "偏高" in desc

    def test_discount(self):
        row = pd.Series({
            "cb_close": 98.0, "premium_rate": -0.05,
            "credit_rating": "AA", "maturity_date": None,
        })
        desc = describe_score_factors(row)
        assert "折价" in desc
