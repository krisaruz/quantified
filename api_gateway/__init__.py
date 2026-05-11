"""API 网关

核心组件：
- 统一响应格式: success_response, error_response
- API Key 认证: APIKeyManager
- 限流: RateLimiter
- 分页: paginate_list, PageRequest
- Flask 中间件: require_auth, rate_limit
"""

from vertexquant.api_gateway.auth import APIKeyInfo, APIKeyManager
from vertexquant.api_gateway.pagination import PageRequest, paginate_list
from vertexquant.api_gateway.rate_limiter import RateLimitResult, RateLimiter, get_rate_limit
from vertexquant.api_gateway.response import (
    PaginationMeta,
    compute_pagination,
    error_response,
    forbidden_error,
    internal_error,
    not_found_error,
    rate_limited_error,
    success_response,
    unauthorized_error,
    validation_error,
)

__all__ = [
    "APIKeyInfo",
    "APIKeyManager",
    "PageRequest",
    "PaginationMeta",
    "RateLimitResult",
    "RateLimiter",
    "compute_pagination",
    "error_response",
    "forbidden_error",
    "get_rate_limit",
    "internal_error",
    "not_found_error",
    "paginate_list",
    "rate_limited_error",
    "success_response",
    "unauthorized_error",
    "validation_error",
]
