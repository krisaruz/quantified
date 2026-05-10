"""风控引擎

核心组件：
- RiskEngine: 风控引擎（规则链执行）
- 内置规则: MaxPositionRule, StopLossRule, MaxDrawdownRule, etc.
- 仓位管理: EqualWeightSizer, RiskParitySizer, KellySizer
- 风险度量: VaR, CVaR, 压力测试
"""

import quantified.risk.rules  # noqa: F401
import quantified.risk.sizers  # noqa: F401

from quantified.risk.engine import RiskEngine
from quantified.risk.protocol import IRiskRule, PositionSizer, RiskViolation
from quantified.risk.stress_test import StressResult, StressScenario, run_stress_test
from quantified.risk.var import cvar_historical, var_historical, var_monte_carlo, var_parametric

__all__ = [
    "IRiskRule",
    "PositionSizer",
    "RiskEngine",
    "RiskViolation",
    "StressResult",
    "StressScenario",
    "cvar_historical",
    "run_stress_test",
    "var_historical",
    "var_monte_carlo",
    "var_parametric",
]
