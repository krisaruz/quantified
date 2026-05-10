"""因子计算测试"""

import datetime

import numpy as np
import pandas as pd
import pytest

from quantified.factors.value import DoubleLowFactor, PureBondPremiumFactor
from quantified.factors.quality import CreditScoreFactor, MaturityScoreFactor
from quantified.factors.technical import Volatility20dFactor


class TestDoubleLowFactor:
    def test_compute_basic(self):
        df = pd.DataFrame({
            "cb_close": [105.0, 110.0, 120.0],
            "premium_rate": [0.1, 0.2, 0.3],
        })
        factor = DoubleLowFactor()
        result = factor.compute(df)
        expected = pd.Series([115.0, 130.0, 150.0])
        pd.testing.assert_series_equal(result, expected)

    def test_compute_with_nan_premium(self):
        df = pd.DataFrame({
            "cb_close": [100.0, 110.0],
            "premium_rate": [np.nan, 0.1],
        })
        factor = DoubleLowFactor()
        result = factor.compute(df)
        assert result.iloc[0] == 100.0  # NaN premium treated as 0
        assert result.iloc[1] == 120.0

    def test_compute_single(self):
        factor = DoubleLowFactor()
        row = pd.Series({"cb_close": 105.0, "premium_rate": 0.1})
        assert factor.compute_single(row) == 115.0


class TestPureBondPremiumFactor:
    def test_compute(self):
        df = pd.DataFrame({"cb_close": [95.0, 100.0, 110.0]})
        factor = PureBondPremiumFactor()
        result = factor.compute(df)
        assert result.iloc[0] == pytest.approx(-0.05)
        assert result.iloc[1] == pytest.approx(0.0)
        assert result.iloc[2] == pytest.approx(0.1)


class TestCreditScoreFactor:
    def test_compute(self):
        df = pd.DataFrame({"credit_rating": ["AAA", "AA", "A+", None]})
        factor = CreditScoreFactor()
        result = factor.compute(df)
        assert result.iloc[0] == 0  # AAA best
        assert result.iloc[1] == 2  # AA
        assert result.iloc[2] == 4  # A+
        assert result.iloc[3] == 10  # None -> worst

    def test_compute_missing_column(self):
        df = pd.DataFrame({"other_col": [1, 2, 3]})
        factor = CreditScoreFactor()
        result = factor.compute(df)
        assert result.isna().all()


class TestMaturityScoreFactor:
    def test_compute(self):
        today = datetime.date.today()
        df = pd.DataFrame({
            "maturity_date": [
                today + datetime.timedelta(days=365 * 5),  # >4 years
                today + datetime.timedelta(days=365 * 3),  # 2-4 years
                today + datetime.timedelta(days=365 * 1.5),  # 1-2 years
                today + datetime.timedelta(days=100),  # <1 year
            ]
        })
        factor = MaturityScoreFactor()
        result = factor.compute(df)
        assert result.iloc[0] == -2.0  # long: bonus
        assert result.iloc[1] == 0.0  # medium: neutral
        assert result.iloc[2] == 3.0  # short: penalty
        assert result.iloc[3] == 8.0  # very_short: heavy penalty


class TestVolatility20dFactor:
    def test_compute_with_enough_data(self):
        # 30 days of price data
        prices = [100 + i * 0.5 + np.random.randn() * 2 for i in range(30)]
        df = pd.DataFrame({"cb_close": prices})
        factor = Volatility20dFactor()
        result = factor.compute(df)
        # First 19 values should be NaN (not enough data for 20-day window)
        assert result.iloc[:19].isna().all()
        # Last value should be a valid positive number
        assert result.iloc[-1] > 0

    def test_compute_insufficient_data(self):
        df = pd.DataFrame({"cb_close": [100.0, 101.0, 102.0]})
        factor = Volatility20dFactor()
        result = factor.compute(df)
        assert result.isna().all()
