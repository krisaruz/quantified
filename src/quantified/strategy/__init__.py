"""策略框架

Protocol 定义：IStrategy, IFactor, Signal, StrategyContext
注册表：StrategyRegistry, FactorRegistry
内置策略：double_low, momentum, value, composite, legacy
版本管理：VersionManager
"""

# 导入触发装饰器注册
import quantified.factors  # noqa: F401
import quantified.strategy.double_low  # noqa: F401
import quantified.strategy.composite_strategy  # noqa: F401
import quantified.strategy.momentum_strategy  # noqa: F401
import quantified.strategy.value_strategy  # noqa: F401
import quantified.strategy.legacy_wrapper  # noqa: F401

from quantified.strategy.factor_registry import FactorRegistry
from quantified.strategy.protocol import IStrategy, Signal, StrategyContext
from quantified.strategy.registry import StrategyRegistry
from quantified.strategy.versioning import StrategyVersion, VersionManager

__all__ = [
    "FactorRegistry",
    "IStrategy",
    "Signal",
    "StrategyContext",
    "StrategyRegistry",
    "StrategyVersion",
    "VersionManager",
]
