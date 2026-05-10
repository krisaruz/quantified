"""限流器

基于滑动窗口的请求限流。
"""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass(frozen=True)
class RateLimitResult:
    """限流检查结果"""

    allowed: bool
    limit: int
    remaining: int
    reset_at: float  # Unix timestamp


class RateLimiter:
    """滑动窗口限流器（内存实现）"""

    def __init__(self) -> None:
        self._windows: dict[str, list[float]] = {}

    def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> bool:
        """检查是否允许请求"""
        result = self.check(key, limit, window_seconds)
        return result.allowed

    def check(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> RateLimitResult:
        """详细检查限流状态"""
        now = time.time()
        window_start = now - window_seconds

        # 获取或初始化窗口
        if key not in self._windows:
            self._windows[key] = []

        # 清理过期请求
        timestamps = self._windows[key]
        self._windows[key] = [t for t in timestamps if t > window_start]

        current_count = len(self._windows[key])
        allowed = current_count < limit

        if allowed:
            self._windows[key].append(now)

        # 计算重置时间
        if self._windows[key]:
            reset_at = self._windows[key][0] + window_seconds
        else:
            reset_at = now + window_seconds

        remaining = max(0, limit - current_count - (1 if allowed else 0))

        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_at=reset_at,
        )

    def get_remaining(
        self,
        key: str,
        limit: int,
        window_seconds: int,
    ) -> int:
        """获取剩余请求数"""
        result = self.check(key, limit, window_seconds)
        return result.remaining

    def reset(self, key: str) -> None:
        """重置指定 Key 的限流窗口"""
        self._windows.pop(key, None)

    def reset_all(self) -> None:
        """重置所有限流窗口"""
        self._windows.clear()


# 默认限流策略
DEFAULT_RATE_LIMITS: dict[str, tuple[int, int]] = {
    "default": (100, 60),  # 100/分钟
    "backtest": (10, 60),  # 10/分钟
    "analytics": (30, 60),  # 30/分钟
    "portfolio_write": (20, 60),  # 20/分钟
}


def get_rate_limit(endpoint_type: str) -> tuple[int, int]:
    """获取端点的限流配置

    Returns:
        (limit, window_seconds)
    """
    return DEFAULT_RATE_LIMITS.get(endpoint_type, DEFAULT_RATE_LIMITS["default"])
