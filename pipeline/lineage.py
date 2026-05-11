"""数据血缘追踪

记录数据的来源、质量和变更历史。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class LineageRecord:
    """数据血缘记录"""

    id: int
    entity_type: str
    entity_key: str
    source: str
    fetched_at: str
    row_count: int
    quality_score: float
    quality_report: str | None


class LineageTracker:
    """数据血缘追踪器（内存实现）

    记录每次数据获取和写入的血缘信息。
    生产环境可替换为数据库实现。
    """

    def __init__(self) -> None:
        self._records: list[LineageRecord] = []
        self._next_id = 1

    def record(
        self,
        entity_type: str,
        entity_key: str,
        source: str,
        row_count: int,
        quality_score: float,
        quality_report: str | None = None,
    ) -> LineageRecord:
        """记录一条血缘信息"""
        rec = LineageRecord(
            id=self._next_id,
            entity_type=entity_type,
            entity_key=entity_key,
            source=source,
            fetched_at=datetime.now().isoformat(),
            row_count=row_count,
            quality_score=quality_score,
            quality_report=quality_report,
        )
        self._records.append(rec)
        self._next_id += 1
        return rec

    def get_history(
        self, entity_type: str, entity_key: str
    ) -> list[LineageRecord]:
        """获取某实体的血缘历史"""
        return [
            r for r in self._records
            if r.entity_type == entity_type and r.entity_key == entity_key
        ]

    def get_by_source(
        self, source: str, limit: int = 100
    ) -> list[LineageRecord]:
        """按数据源查询血缘记录"""
        results = [r for r in self._records if r.source == source]
        return results[:limit]

    def get_stale_entities(
        self, max_age_days: int = 7
    ) -> list[str]:
        """获取超过指定天数未更新的实体

        Returns:
            过期实体的 entity_key 列表
        """
        now = datetime.now()
        stale: list[str] = []

        # 按 entity_key 分组，取最新的 fetched_at
        latest: dict[str, datetime] = {}
        for rec in self._records:
            fetched = datetime.fromisoformat(rec.fetched_at)
            key = f"{rec.entity_type}:{rec.entity_key}"
            if key not in latest or fetched > latest[key]:
                latest[key] = fetched

        for key, last_fetch in latest.items():
            age = (now - last_fetch).days
            if age > max_age_days:
                stale.append(key)

        return sorted(stale)

    def get_stats(self) -> dict[str, Any]:
        """获取血缘统计信息"""
        if not self._records:
            return {"total_records": 0}

        sources: dict[str, int] = {}
        entity_types: dict[str, int] = {}
        total_rows = 0
        total_quality = 0.0

        for rec in self._records:
            sources[rec.source] = sources.get(rec.source, 0) + 1
            entity_types[rec.entity_type] = entity_types.get(rec.entity_type, 0) + 1
            total_rows += rec.row_count
            total_quality += rec.quality_score

        return {
            "total_records": len(self._records),
            "total_rows": total_rows,
            "avg_quality_score": total_quality / len(self._records),
            "by_source": sources,
            "by_entity_type": entity_types,
        }

    def clear(self) -> None:
        """清空所有记录"""
        self._records.clear()
        self._next_id = 1
