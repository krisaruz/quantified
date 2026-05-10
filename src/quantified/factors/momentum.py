"""动量因子

momentum_5d: 5日涨跌幅
momentum_20d: 20日涨跌幅
momentum_60d: 60日涨跌幅
rsi_14: 14日RSI
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantified.strategy.factor_registry import FactorRegistry


@FactorRegistry.register("momentum_5d", category="momentum")
class Momentum5dFactor:
    """5日动量因子：过去5个交易日的涨跌幅"""

    name = "momentum_5d"
    category = "momentum"
    description = "5日涨跌幅"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        return df["cb_close"].pct_change(periods=5)

    def compute_single(self, row: pd.Series) -> float:
        return float(row.get("momentum_5d", 0) or 0)


@FactorRegistry.register("momentum_20d", category="momentum")
class Momentum20dFactor:
    """20日动量因子：过去20个交易日的涨跌幅"""

    name = "momentum_20d"
    category = "momentum"
    description = "20日涨跌幅"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        return df["cb_close"].pct_change(periods=20)

    def compute_single(self, row: pd.Series) -> float:
        return float(row.get("momentum_20d", 0) or 0)


@FactorRegistry.register("momentum_60d", category="momentum")
class Momentum60dFactor:
    """60日动量因子：过去60个交易日的涨跌幅"""

    name = "momentum_60d"
    category = "momentum"
    description = "60日涨跌幅"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        return df["cb_close"].pct_change(periods=60)

    def compute_single(self, row: pd.Series) -> float:
        return float(row.get("momentum_60d", 0) or 0)


@FactorRegistry.register("rsi_14", category="momentum")
class RSI14Factor:
    """14日RSI因子

    RSI = 100 - 100 / (1 + RS)
    RS = 平均上涨幅度 / 平均下跌幅度
    """

    name = "rsi_14"
    category = "momentum"
    description = "14日相对强弱指标"

    period: int = 14

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns:
            return pd.Series(np.nan, index=df.index)

        delta = df["cb_close"].diff()
        gain = delta.where(delta > 0, 0.0)
        loss = (-delta).where(delta < 0, 0.0)

        avg_gain = gain.rolling(window=self.period, min_periods=self.period).mean()
        avg_loss = loss.rolling(window=self.period, min_periods=self.period).mean()

        rs = avg_gain / avg_loss.replace(0, np.nan)
        rsi = 100 - 100 / (1 + rs)
        return rsi

    def compute_single(self, row: pd.Series) -> float:
        val = row.get("rsi_14")
        return float(val) if val is not None and not np.isnan(val) else 50.0
