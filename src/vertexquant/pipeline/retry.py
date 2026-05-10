"""重试策略

指数退避重试策略。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    """重试策略

    使用指数退避算法计算重试延迟。
    """

    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0

    def get_delay(self, retry_count: int) -> float:
        """计算重试延迟

        公式: min(base * factor^count, max_delay)
        """
        delay = self.base_delay * (self.backoff_factor ** retry_count)
        return min(delay, self.max_delay)

    def should_retry(self, retry_count: int) -> bool:
        """是否应该重试"""
        return retry_count < self.max_retries

    def get_all_delays(self) -> list[float]:
        """获取所有重试的延迟时间"""
        return [self.get_delay(i) for i in range(self.max_retries)]
