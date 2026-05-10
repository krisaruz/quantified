"""策略框架

Protocol 定义：IStrategy, IFactor, Signal, StrategyContext
注册表：StrategyRegistry, FactorRegistry
内置策略：double_low, momentum, value, composite, legacy
版本管理：VersionManager
"""

# 导入触发装饰器注册
import vertexquant.factors  # noqa: F401
import vertexquant.strategy.double_low  # noqa: F401
import vertexquant.strategy.composite_strategy  # noqa: F401
import vertexquant.strategy.momentum_strategy  # noqa: F401
import vertexquant.strategy.value_strategy  # noqa: F401
import vertexquant.strategy.legacy_wrapper  # noqa: F401

from vertexquant.strategy.factor_registry import FactorRegistry
from vertexquant.strategy.protocol import IStrategy, Signal, StrategyContext
from vertexquant.strategy.registry import StrategyRegistry
from vertexquant.strategy.versioning import StrategyVersion, VersionManager

__all__ = [
    "FactorRegistry",
    "IStrategy",
    "Signal",
    "StrategyContext",
    "StrategyRegistry",
    "StrategyVersion",
    "VersionManager",
]
