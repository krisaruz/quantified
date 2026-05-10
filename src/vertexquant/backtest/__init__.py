"""回测引擎包

提供历史回测能力：虚拟账户、策略执行循环、绩效统计。
"""

from vertexquant.backtest.account import Position, VirtualAccount
from vertexquant.backtest.engine import BacktestEngine, BacktestResult
from vertexquant.backtest.stats import compute_stats, PerformanceStats

__all__ = [
    "Position",
    "VirtualAccount",
    "BacktestEngine",
    "BacktestResult",
    "compute_stats",
    "PerformanceStats",
]
