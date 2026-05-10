"""统一响应格式"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PaginationMeta:
    """分页元数据"""

    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_prev: bool


@dataclass
class ErrorDetail:
    """错误详情"""

    code: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def success_response(
    data: Any,
    meta: PaginationMeta | None = None,
) -> dict[str, Any]:
    """成功响应"""
    resp: dict[str, Any] = {
        "status": "ok",
        "data": data,
    }
    if meta:
        resp["meta"] = {
            "page": meta.page,
            "page_size": meta.page_size,
            "total": meta.total,
            "total_pages": meta.total_pages,
            "has_next": meta.has_next,
            "has_prev": meta.has_prev,
        }
    return resp


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
    http_status: int = 400,
) -> tuple[dict[str, Any], int]:
    """错误响应"""
    resp = {
        "status": "error",
        "error": {
            "code": code,
            "message": message,
        },
    }
    if details:
        resp["error"]["details"] = details
    return resp, http_status


# 常用错误响应快捷函数
def validation_error(
    message: str, field_name: str | None = None, value: Any = None
) -> tuple[dict[str, Any], int]:
    details = {}
    if field_name:
        details["field"] = field_name
    if value is not None:
        details["value"] = value
    return error_response("VALIDATION_ERROR", message, details, 400)


def not_found_error(resource: str, identifier: str) -> tuple[dict[str, Any], int]:
    return error_response(
        "NOT_FOUND",
        f"{resource} '{identifier}' 不存在",
        {"resource": resource, "identifier": identifier},
        404,
    )


def unauthorized_error(message: str = "未认证") -> tuple[dict[str, Any], int]:
    return error_response("UNAUTHORIZED", message, http_status=401)


def forbidden_error(message: str = "无权限") -> tuple[dict[str, Any], int]:
    return error_response("FORBIDDEN", message, http_status=403)


def rate_limited_error(
    retry_after: int,
) -> tuple[dict[str, Any], int]:
    return error_response(
        "RATE_LIMITED",
        f"请求过于频繁，请 {retry_after} 秒后重试",
        {"retry_after": retry_after},
        429,
    )


def internal_error(message: str = "服务器内部错误") -> tuple[dict[str, Any], int]:
    return error_response("INTERNAL_ERROR", message, http_status=500)


def compute_pagination(
    page: int, page_size: int, total: int
) -> PaginationMeta:
    """计算分页元数据"""
    total_pages = max(1, (total + page_size - 1) // page_size)
    return PaginationMeta(
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
