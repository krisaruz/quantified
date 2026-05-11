"""增量同步状态机

管理数据同步的状态转换和进度持久化。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class SyncStatus(str, Enum):
    """同步状态"""

    IDLE = "idle"
    SYNCING = "syncing"
    PAUSED = "paused"
    ERROR = "error"


# 合法的状态转换
_TRANSITIONS: dict[SyncStatus, set[SyncStatus]] = {
    SyncStatus.IDLE: {SyncStatus.SYNCING},
    SyncStatus.SYNCING: {SyncStatus.IDLE, SyncStatus.PAUSED, SyncStatus.ERROR},
    SyncStatus.PAUSED: {SyncStatus.SYNCING},
    SyncStatus.ERROR: {SyncStatus.SYNCING, SyncStatus.IDLE},
}


@dataclass(frozen=True)
class SyncError:
    """同步错误记录"""

    entity: str
    error_type: str
    message: str
    timestamp: str


@dataclass
class SyncProgress:
    """同步进度"""

    entity: str
    last_synced_date: str | None
    status: str
    updated_at: str | None


class SyncStateMachine:
    """同步状态机

    管理各实体（bond_daily, stock_daily 等）的同步状态。
    """

    def __init__(self) -> None:
        self._state = SyncStatus.IDLE
        self._progress: dict[str, SyncProgress] = {}
        self._errors: list[SyncError] = []

    @property
    def state(self) -> SyncStatus:
        return self._state

    def start(self, entity: str) -> None:
        """开始同步"""
        self._transition(SyncStatus.SYNCING)
        self._progress[entity] = SyncProgress(
            entity=entity,
            last_synced_date=None,
            status="syncing",
            updated_at=None,
        )

    def mark_progress(self, entity: str, last_date: str) -> None:
        """标记同步进度"""
        if self._state != SyncStatus.SYNCING:
            raise InvalidSyncStateError(f"Cannot mark progress in state {self._state}")

        existing = self._progress.get(entity)
        if existing:
            self._progress[entity] = SyncProgress(
                entity=entity,
                last_synced_date=last_date,
                status="syncing",
                updated_at=last_date,
            )

    def complete(self, entity: str) -> None:
        """完成同步"""
        existing = self._progress.get(entity)
        if existing:
            self._progress[entity] = SyncProgress(
                entity=entity,
                last_synced_date=existing.last_synced_date,
                status="done",
                updated_at=existing.updated_at,
            )

        # 如果没有其他实体在同步，回到 idle
        any_syncing = any(
            p.status == "syncing" for p in self._progress.values()
        )
        if not any_syncing:
            self._state = SyncStatus.IDLE

    def error(self, entity: str, exc: Exception) -> None:
        """记录同步错误"""
        from datetime import datetime

        self._state = SyncStatus.ERROR
        self._errors.append(SyncError(
            entity=entity,
            error_type=type(exc).__name__,
            message=str(exc),
            timestamp=datetime.now().isoformat(),
        ))

        existing = self._progress.get(entity)
        if existing:
            self._progress[entity] = SyncProgress(
                entity=entity,
                last_synced_date=existing.last_synced_date,
                status="error",
                updated_at=existing.updated_at,
            )

    def pause(self) -> None:
        """暂停同步"""
        self._transition(SyncStatus.PAUSED)

    def resume(self) -> None:
        """恢复同步"""
        self._transition(SyncStatus.SYNCING)

    def reset(self) -> None:
        """重置到 idle"""
        self._state = SyncStatus.IDLE

    def get_progress(self, entity: str) -> SyncProgress | None:
        """获取实体同步进度"""
        return self._progress.get(entity)

    def get_all_progress(self) -> dict[str, SyncProgress]:
        """获取所有实体同步进度"""
        return dict(self._progress)

    def get_errors(self) -> list[SyncError]:
        """获取所有错误"""
        return list(self._errors)

    def clear_errors(self) -> None:
        """清除错误记录"""
        self._errors.clear()

    def _transition(self, target: SyncStatus) -> None:
        allowed = _TRANSITIONS.get(self._state, set())
        if target not in allowed:
            raise InvalidSyncStateError(
                f"Cannot transition from {self._state} to {target}"
            )
        self._state = target


class InvalidSyncStateError(Exception):
    """非法状态转换"""
