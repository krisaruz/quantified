"""因子注册表

通过装饰器注册因子类，支持按类别查询。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class FactorRegistry:
    """因子注册表"""

    _factors: dict[str, type] = {}

    @classmethod
    def register(cls, name: str, category: str):
        """装饰器：注册因子类"""

        def decorator(factor_cls: type) -> type:
            if name in cls._factors:
                logger.warning("因子 '%s' 已存在，将被覆盖", name)
            cls._factors[name] = factor_cls
            factor_cls._registered_name = name
            factor_cls._registered_category = category
            logger.debug("注册因子: %s (%s) -> %s", name, category, factor_cls.__name__)
            return factor_cls

        return decorator

    @classmethod
    def get(cls, name: str, **kwargs: Any) -> Any:
        """获取因子实例"""
        if name not in cls._factors:
            available = ", ".join(cls._factors.keys()) or "(无)"
            raise KeyError(f"因子 '{name}' 未注册。可用因子: {available}")
        return cls._factors[name](**kwargs)

    @classmethod
    def list_factors(cls) -> list[str]:
        """列出所有已注册因子名称"""
        return list(cls._factors.keys())

    @classmethod
    def list_by_category(cls, category: str) -> list[str]:
        """按类别列出因子"""
        return [
            name
            for name, factor_cls in cls._factors.items()
            if getattr(factor_cls, "_registered_category", None) == category
        ]

    @classmethod
    def has(cls, name: str) -> bool:
        """检查因子是否已注册"""
        return name in cls._factors

    @classmethod
    def clear(cls) -> None:
        """清空注册表（仅用于测试）"""
        cls._factors.clear()
