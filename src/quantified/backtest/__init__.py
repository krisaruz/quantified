"""回测引擎包

提供历史回测能力：虚拟账户、策略执行循环、绩效统计。
"""

from quantified.backtest.account import Position, VirtualAccount
from quantified.backtest.engine import BacktestEngine, BacktestResult
from quantified.backtest.stats import compute_stats, PerformanceStats

__all__ = [
    "Position",
    "VirtualAccount",
    "BacktestEngine",
    "BacktestResult",
    "compute_stats",
    "PerformanceStats",
]
