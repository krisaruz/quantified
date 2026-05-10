"""分页工具"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class PageRequest:
    """分页请求"""

    page: int = 1
    page_size: int = 20
    sort: str | None = None
    order: str = "asc"

    def validate(self) -> PageRequest:
        """校验并规范化"""
        page = max(1, self.page)
        page_size = max(1, min(200, self.page_size))
        order = self.order if self.order in ("asc", "desc") else "asc"
        return PageRequest(
            page=page,
            page_size=page_size,
            sort=self.sort,
            order=order,
        )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


def paginate_list(
    items: list[Any],
    page: int = 1,
    page_size: int = 20,
    sort_key: str | None = None,
    reverse: bool = False,
) -> tuple[list[Any], int]:
    """对列表进行分页

    Args:
        items: 待分页数据
        page: 页码（从 1 开始）
        page_size: 每页大小
        sort_key: 排序字段（dict 的 key）
        reverse: 是否降序

    Returns:
        (分页数据, 总数)
    """
    total = len(items)

    # 排序
    if sort_key and items:
        try:
            items = sorted(
                items,
                key=lambda x: x.get(sort_key, 0) if isinstance(x, dict) else getattr(x, sort_key, 0),
                reverse=reverse,
            )
        except (KeyError, AttributeError, TypeError):
            pass

    # 分页
    start = (page - 1) * page_size
    end = start + page_size
    return items[start:end], total
