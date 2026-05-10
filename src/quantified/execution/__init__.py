"""执行引擎

核心组件：
- OrderManager: 订单管理器
- SlippageModel: 滑点模型（Fixed, VolumeBased, Volatility）
- TransactionCostAnalyzer: 交易成本分析
"""

from quantified.execution.models import Fill, MarketBar, Order
from quantified.execution.order_manager import OrderManager
from quantified.execution.slippage import (
    FixedSlippageModel,
    SlippageModel,
    VolumeBasedSlippageModel,
    VolatilitySlippageModel,
)
from quantified.execution.tca import TCAResult, TransactionCostAnalyzer

__all__ = [
    "Fill",
    "FixedSlippageModel",
    "MarketBar",
    "Order",
    "OrderManager",
    "SlippageModel",
    "TCAResult",
    "TransactionCostAnalyzer",
    "VolumeBasedSlippageModel",
    "VolatilitySlippageModel",
]
