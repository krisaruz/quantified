"""Flask 中间件

认证和限流的 Flask 集成。
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable

from quantified.api_gateway.auth import APIKeyManager
from quantified.api_gateway.rate_limiter import RateLimiter, get_rate_limit
from quantified.api_gateway.response import unauthorized_error, rate_limited_error


def require_auth(
    key_manager: APIKeyManager,
    scope: str | None = None,
) -> Callable:
    """认证装饰器

    Args:
        key_manager: API Key 管理器
        scope: 所需权限范围（None = 仅验证身份）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from flask import request

            # 从 Header 或 Query 获取 API Key
            api_key = request.headers.get("X-API-Key") or request.args.get("api_key")

            if not api_key:
                return unauthorized_error("缺少 API Key")

            info = key_manager.validate(api_key)
            if not info:
                return unauthorized_error("API Key 无效或已吊销")

            if scope and not key_manager.has_scope(api_key, scope):
                from quantified.api_gateway.response import forbidden_error
                return forbidden_error(f"缺少权限: {scope}")

            return f(*args, **kwargs)
        return wrapper
    return decorator


def rate_limit(
    limiter: RateLimiter,
    endpoint_type: str = "default",
) -> Callable:
    """限流装饰器

    Args:
        limiter: 限流器
        endpoint_type: 端点类型（决定限流策略）
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            from flask import request, make_response

            # 用 API Key 或 IP 作为限流 Key
            api_key = request.headers.get("X-API-Key") or request.args.get("api_key")
            limit_key = api_key or request.remote_addr or "unknown"

            limit, window = get_rate_limit(endpoint_type)
            result = limiter.check(limit_key, limit, window)

            if not result.allowed:
                resp_data, status = rate_limited_error(int(result.reset_at - __import__("time").time()))
                resp = make_response(resp_data, status)
                resp.headers["X-RateLimit-Limit"] = str(result.limit)
                resp.headers["X-RateLimit-Remaining"] = str(result.remaining)
                resp.headers["X-RateLimit-Reset"] = str(int(result.reset_at))
                return resp

            # 正常请求也添加限流头
            resp = make_response(f(*args, **kwargs))
            if hasattr(resp, "headers"):
                resp.headers["X-RateLimit-Limit"] = str(result.limit)
                resp.headers["X-RateLimit-Remaining"] = str(result.remaining)
                resp.headers["X-RateLimit-Reset"] = str(int(result.reset_at))
            return resp
        return wrapper
    return decorator
