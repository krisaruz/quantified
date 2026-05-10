"""因子库

内置因子：
- 价值因子：double_low, pure_bond_premium, ytm_approx
- 动量因子：momentum_5d, momentum_20d, momentum_60d, rsi_14
- 质量因子：credit_score, issue_size_score, maturity_score
- 技术因子：volatility_20d, turnover_rate, volume_price_divergence
- 复合因子：CompositeFactor
"""

from vertexquant.factors.composite import CompositeFactor
from vertexquant.factors.momentum import Momentum5dFactor, Momentum20dFactor, Momentum60dFactor, RSI14Factor
from vertexquant.factors.quality import CreditScoreFactor, IssueSizeScoreFactor, MaturityScoreFactor
from vertexquant.factors.technical import TurnoverRateFactor, Volatility20dFactor, VolumePriceDivergenceFactor
from vertexquant.factors.value import DoubleLowFactor, PureBondPremiumFactor, YTMApproxFactor

__all__ = [
    "CompositeFactor",
    "DoubleLowFactor",
    "PureBondPremiumFactor",
    "YTMApproxFactor",
    "Momentum5dFactor",
    "Momentum20dFactor",
    "Momentum60dFactor",
    "RSI14Factor",
    "CreditScoreFactor",
    "IssueSizeScoreFactor",
    "MaturityScoreFactor",
    "Volatility20dFactor",
    "TurnoverRateFactor",
    "VolumePriceDivergenceFactor",
]
