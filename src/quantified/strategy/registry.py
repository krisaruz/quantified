"""策略注册表

通过装饰器注册策略类，通过工厂方法获取策略实例。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class StrategyRegistry:
    """策略注册表"""

    _strategies: dict[str, type] = {}

    @classmethod
    def register(cls, name: str):
        """装饰器：注册策略类"""

        def decorator(strategy_cls: type) -> type:
            if name in cls._strategies:
                logger.warning("策略 '%s' 已存在，将被覆盖", name)
            cls._strategies[name] = strategy_cls
            logger.debug("注册策略: %s -> %s", name, strategy_cls.__name__)
            return strategy_cls

        return decorator

    @classmethod
    def get(cls, name: str, **kwargs: Any) -> Any:
        """获取策略实例"""
        if name not in cls._strategies:
            available = ", ".join(cls._strategies.keys()) or "(无)"
            raise KeyError(f"策略 '{name}' 未注册。可用策略: {available}")
        return cls._strategies[name](**kwargs)

    @classmethod
    def list_strategies(cls) -> list[str]:
        """列出所有已注册策略名称"""
        return list(cls._strategies.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """检查策略是否已注册"""
        return name in cls._strategies

    @classmethod
    def clear(cls) -> None:
        """清空注册表（仅用于测试）"""
        cls._strategies.clear()
