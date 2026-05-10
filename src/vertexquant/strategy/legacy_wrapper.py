"""LegacyStrategy：包装现有配置为 IStrategy 接口

用于向后兼容：将 AppConfig 中的 strategy 配置转换为策略信号。
"""

from __future__ import annotations

import logging

from vertexquant.strategy.protocol import Signal, StrategyContext
from vertexquant.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register("legacy")
class LegacyStrategy:
    """Legacy 策略包装器

    直接使用 AppConfig 中的 strategy 配置，通过 DoubleLowStrategy 执行。
    用于保持现有配置文件的向后兼容。
    """

    name = "legacy"
    version = "1.0.0"
    description = "Legacy 配置兼容策略"

    def __init__(self, config: object = None) -> None:
        self._config = config
        self._inner = None

    def _ensure_inner(self, context: StrategyContext):
        if self._inner is not None:
            return

        config = self._config or context.config
        if config is None:
            raise ValueError("LegacyStrategy 需要 AppConfig 配置")

        from vertexquant.strategy.double_low import DoubleLowStrategy

        strategy_config = config.strategy
        self._inner = DoubleLowStrategy(
            hold_count=strategy_config.hold_count,
            buffer_rank=strategy_config.buffer_rank,
            max_position_pct=config.risk.max_position_pct,
        )

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        self._ensure_inner(context)
        return self._inner.generate_signals(context)

    def get_parameters(self) -> dict:
        if self._inner:
            return self._inner.get_parameters()
        return {"name": "legacy"}

    def set_parameters(self, params: dict) -> None:
        if self._inner:
            self._inner.set_parameters(params)
