"""同步任务队列

管理同步任务的排队、执行和重试。
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SyncTask:
    """同步任务"""

    entity: str
    cb_code: str
    start_date: str
    end_date: str
    priority: int = 5  # 0=最高优先级
    retry_count: int = 0
    status: str = "pending"  # "pending" | "running" | "done" | "failed"
    error_message: str | None = None

    def __lt__(self, other: SyncTask) -> bool:
        return self.priority < other.priority


@dataclass
class SyncProgress:
    """队列进度统计"""

    total: int
    pending: int
    running: int
    done: int
    failed: int


class SyncTaskQueue:
    """同步任务队列（基于优先级堆）"""

    def __init__(self) -> None:
        self._heap: list[SyncTask] = []
        self._all_tasks: list[SyncTask] = []
        self._counter = 0

    def enqueue(self, task: SyncTask) -> None:
        """入队"""
        self._counter += 1
        heapq.heappush(self._heap, task)
        self._all_tasks.append(task)

    def dequeue(self) -> SyncTask | None:
        """出队（最高优先级）"""
        while self._heap:
            task = heapq.heappop(self._heap)
            if task.status == "pending":
                task.status = "running"
                return task
        return None

    def mark_done(self, task: SyncTask) -> None:
        """标记任务完成"""
        task.status = "done"
        task.error_message = None

    def mark_failed(self, task: SyncTask, error: Exception) -> None:
        """标记任务失败"""
        task.status = "failed"
        task.error_message = str(error)
        task.retry_count += 1

    def retry_failed(self, max_retries: int = 3) -> int:
        """重试失败的任务

        Returns:
            重新入队的任务数量
        """
        requeued = 0
        for task in self._all_tasks:
            if task.status == "failed" and task.retry_count < max_retries:
                task.status = "pending"
                heapq.heappush(self._heap, task)
                requeued += 1
        return requeued

    def get_progress(self) -> SyncProgress:
        """获取队列进度"""
        total = len(self._all_tasks)
        pending = sum(1 for t in self._all_tasks if t.status == "pending")
        running = sum(1 for t in self._all_tasks if t.status == "running")
        done = sum(1 for t in self._all_tasks if t.status == "done")
        failed = sum(1 for t in self._all_tasks if t.status == "failed")

        return SyncProgress(
            total=total,
            pending=pending,
            running=running,
            done=done,
            failed=failed,
        )

    def get_failed_tasks(self) -> list[SyncTask]:
        """获取所有失败的任务"""
        return [t for t in self._all_tasks if t.status == "failed"]

    def clear(self) -> None:
        """清空队列"""
        self._heap.clear()
        self._all_tasks.clear()
        self._counter = 0

    def __len__(self) -> int:
        return len(self._all_tasks)
