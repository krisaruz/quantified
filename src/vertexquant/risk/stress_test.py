"""压力测试框架"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import numpy as np


@dataclass
class StressScenario:
    """压力测试场景"""

    name: str
    description: str
    market_shock: float  # 全市场跌幅（负数）
    sector_shocks: dict[str, float] = field(default_factory=dict)  # 行业特定冲击
    duration_days: int = 1


@dataclass
class StressResult:
    """压力测试结果"""

    scenario: str
    portfolio_loss: float
    max_drawdown: float
    worst_holding: str
    worst_holding_loss: float


# 内置场景
BUILTIN_SCENARIOS = [
    StressScenario(
        name="market_crash",
        description="全市场暴跌（参照2015年股灾）",
        market_shock=-0.08,
        duration_days=1,
    ),
    StressScenario(
        name="rate_spike",
        description="利率快速上升（参照2022年债灾）",
        market_shock=-0.03,
        sector_shocks={"金融": -0.05, "地产": -0.08},
        duration_days=5,
    ),
    StressScenario(
        name="credit_event",
        description="信用事件冲击",
        market_shock=-0.02,
        sector_shocks={"低评级": -0.15},
        duration_days=1,
    ),
    StressScenario(
        name="liquidity_crisis",
        description="流动性枯竭",
        market_shock=-0.05,
        duration_days=3,
    ),
]


def run_stress_test(
    portfolio: object,
    market_data: object,
    scenarios: list[StressScenario] | None = None,
) -> list[StressResult]:
    """执行压力测试

    Args:
        portfolio: 持仓组合
        market_data: 市场数据
        scenarios: 测试场景列表（默认使用内置场景）

    Returns:
        各场景的测试结果
    """
    if scenarios is None:
        scenarios = BUILTIN_SCENARIOS

    results: list[StressResult] = []
    holdings = getattr(portfolio, "holdings", [])

    for scenario in scenarios:
        total_loss = 0.0
        worst_code = ""
        worst_loss = 0.0

        for h in holdings:
            code = getattr(h, "cb_code", "")
            buy_price = getattr(h, "buy_price", 0)
            volume = getattr(h, "volume", 0)
            mv = buy_price * volume / 10

            # 应用市场冲击
            shock = scenario.market_shock
            loss = mv * shock

            total_loss += loss
            if shock < worst_loss:
                worst_loss = shock
                worst_code = code

        results.append(StressResult(
            scenario=scenario.name,
            portfolio_loss=total_loss,
            max_drawdown=abs(total_loss),
            worst_holding=worst_code,
            worst_holding_loss=worst_loss,
        ))

    return results
