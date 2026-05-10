"""VaR 计算：历史模拟法、参数法、Monte Carlo"""

from __future__ import annotations

import math
import random

import numpy as np


def var_historical(returns: list[float], confidence: float = 0.95) -> float:
    """历史模拟法 VaR

    Args:
        returns: 历史收益率序列
        confidence: 置信度（默认 95%）

    Returns:
        VaR 值（正数表示损失）
    """
    if not returns:
        return 0.0
    sorted_returns = sorted(returns)
    index = int((1 - confidence) * len(sorted_returns))
    index = max(0, min(index, len(sorted_returns) - 1))
    return -sorted_returns[index]


def var_parametric(
    mean: float, std: float, confidence: float = 0.95,
) -> float:
    """参数法 VaR（假设正态分布）

    Args:
        mean: 收益率均值
        std: 收益率标准差
        confidence: 置信度

    Returns:
        VaR 值（正数表示损失）
    """
    # z-score for confidence level
    z_scores = {0.90: 1.282, 0.95: 1.645, 0.99: 2.326}
    z = z_scores.get(confidence, 1.645)
    return -(mean - z * std)


def var_monte_carlo(
    mean: float, std: float, confidence: float = 0.95,
    n_simulations: int = 10000, seed: int | None = None,
) -> float:
    """Monte Carlo VaR

    Args:
        mean: 收益率均值
        std: 收益率标准差
        confidence: 置信度
        n_simulations: 模拟次数
        seed: 随机种子

    Returns:
        VaR 值（正数表示损失）
    """
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)

    simulated = np.random.normal(mean, std, n_simulations)
    return var_historical(simulated.tolist(), confidence)


def cvar_historical(returns: list[float], confidence: float = 0.95) -> float:
    """条件 VaR (Expected Shortfall)

    Args:
        returns: 历史收益率序列
        confidence: 置信度

    Returns:
        CVaR 值（正数表示损失）
    """
    if not returns:
        return 0.0
    var = var_historical(returns, confidence)
    tail = [r for r in returns if r <= -var]
    return -sum(tail) / len(tail) if tail else var
