"""技术因子

volatility_20d: 20日波动率
turnover_rate: 换手率
volume_price_divergence: 量价背离
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from quantified.strategy.factor_registry import FactorRegistry


@FactorRegistry.register("volatility_20d", category="technical")
class Volatility20dFactor:
    """20日波动率因子：过去20个交易日收益率的标准差

    波动率越低越稳定，得分越低（越好）。
    """

    name = "volatility_20d"
    category = "technical"
    description = "20日波动率，越低越稳定"

    period: int = 20

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        returns = df["cb_close"].pct_change()
        return returns.rolling(window=self.period, min_periods=self.period).std()

    def compute_single(self, row: pd.Series) -> float:
        val = row.get("volatility_20d")
        return float(val) if val is not None and not np.isnan(val) else 0.0


@FactorRegistry.register("turnover_rate", category="technical")
class TurnoverRateFactor:
    """换手率因子：成交量 / 流通规模

    换手率适中（0.5%-5%）为好，过高或过低都不利。
    """

    name = "turnover_rate"
    category = "technical"
    description = "换手率，适中为好"

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_volume" not in df.columns or "issue_size" not in df.columns:
            return pd.Series(np.nan, index=df.index)
        # issue_size 单位为亿，volume 单位为手（10张）
        # 换手率 = 成交量(张) / 发行规模(张)
        volume_in_zhang = df["cb_volume"] * 10  # 手 -> 张
        issue_in_zhang = df["issue_size"] * 1e8 / 100  # 亿 -> 张
        return volume_in_zhang / issue_in_zhang.replace(0, np.nan)

    def compute_single(self, row: pd.Series) -> float:
        volume = row.get("cb_volume", 0) or 0
        issue = row.get("issue_size", 0) or 0
        if issue <= 0:
            return 0.0
        return (volume * 10) / (issue * 1e8 / 100)


@FactorRegistry.register("volume_price_divergence", category="technical")
class VolumePriceDivergenceFactor:
    """量价背离因子

    价格上涨但成交量萎缩 = 顶背离（负信号）
    价格下跌但成交量萎缩 = 底背离（正信号）
    """

    name = "volume_price_divergence"
    category = "technical"
    description = "量价背离信号"

    period: int = 10

    def compute(self, df: pd.DataFrame) -> pd.Series:
        if "cb_close" not in df.columns or "cb_volume" not in df.columns:
            return pd.Series(np.nan, index=df.index)

        price_change = df["cb_close"].pct_change(self.period)
        volume_change = df["cb_volume"].pct_change(self.period)

        # 背离 = 价格变化方向与成交量变化方向相反
        # 正值 = 量价同向（健康），负值 = 量价背离（风险）
        divergence = price_change * volume_change
        return divergence

    def compute_single(self, row: pd.Series) -> float:
        val = row.get("volume_price_divergence")
        return float(val) if val is not None and not np.isnan(val) else 0.0
