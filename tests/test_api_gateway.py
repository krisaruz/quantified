"""API 网关测试"""

import time

import pytest

from quantified.api_gateway.auth import APIKeyManager
from quantified.api_gateway.pagination import PageRequest, paginate_list
from quantified.api_gateway.rate_limiter import RateLimiter, get_rate_limit
from quantified.api_gateway.response import (
    compute_pagination,
    error_response,
    not_found_error,
    success_response,
    validation_error,
)


# ─────────────── Response Format ───────────────


class TestResponse:
    def test_success_response(self):
        resp = success_response({"name": "test"})
        assert resp["status"] == "ok"
        assert resp["data"]["name"] == "test"
        assert "meta" not in resp

    def test_success_with_pagination(self):
        meta = compute_pagination(1, 20, 100)
        resp = success_response([1, 2, 3], meta)
        assert resp["meta"]["page"] == 1
        assert resp["meta"]["total"] == 100
        assert resp["meta"]["has_next"] is True
        assert resp["meta"]["has_prev"] is False

    def test_error_response(self):
        resp, status = error_response("TEST_ERROR", "test message", http_status=400)
        assert resp["status"] == "error"
        assert resp["error"]["code"] == "TEST_ERROR"
        assert status == 400

    def test_validation_error(self):
        resp, status = validation_error("日期格式无效", "date", "2025/01/01")
        assert resp["error"]["code"] == "VALIDATION_ERROR"
        assert resp["error"]["details"]["field"] == "date"
        assert status == 400

    def test_not_found_error(self):
        resp, status = not_found_error("组合", "my_port")
        assert resp["error"]["code"] == "NOT_FOUND"
        assert status == 404

    def test_pagination_meta(self):
        meta = compute_pagination(2, 20, 50)
        assert meta.page == 2
        assert meta.total_pages == 3
        assert meta.has_next is True
        assert meta.has_prev is True

    def test_pagination_last_page(self):
        meta = compute_pagination(3, 20, 50)
        assert meta.has_next is False
        assert meta.has_prev is True


# ─────────────── API Key Auth ───────────────


class TestAPIKeyManager:
    def test_generate_and_validate(self):
        mgr = APIKeyManager()
        key = mgr.generate("test_app", ["read:portfolio"])
        assert key.startswith("qf_")

        info = mgr.validate(key)
        assert info is not None
        assert info.name == "test_app"
        assert "read:portfolio" in info.scopes

    def test_validate_invalid_key(self):
        mgr = APIKeyManager()
        assert mgr.validate("invalid_key") is None

    def test_revoke_key(self):
        mgr = APIKeyManager()
        key = mgr.generate("test", ["read:portfolio"])
        assert mgr.revoke(key)
        assert mgr.validate(key) is None

    def test_revoke_nonexistent(self):
        mgr = APIKeyManager()
        assert not mgr.revoke("nonexistent")

    def test_list_keys(self):
        mgr = APIKeyManager()
        mgr.generate("app1", ["read:portfolio"])
        mgr.generate("app2", ["read:analytics"])

        keys = mgr.list_keys()
        assert len(keys) == 2

    def test_has_scope(self):
        mgr = APIKeyManager()
        key = mgr.generate("test", ["read:portfolio", "write:portfolio"])

        assert mgr.has_scope(key, "read:portfolio")
        assert mgr.has_scope(key, "write:portfolio")
        assert not mgr.has_scope(key, "admin")

    def test_admin_scope_grants_all(self):
        mgr = APIKeyManager()
        key = mgr.generate("admin", ["admin"])

        assert mgr.has_scope(key, "read:portfolio")
        assert mgr.has_scope(key, "write:portfolio")
        assert mgr.has_scope(key, "admin")

    def test_revoked_key_no_scope(self):
        mgr = APIKeyManager()
        key = mgr.generate("test", ["read:portfolio"])
        mgr.revoke(key)

        assert not mgr.has_scope(key, "read:portfolio")


# ─────────────── Rate Limiter ───────────────


class TestRateLimiter:
    def test_allows_within_limit(self):
        limiter = RateLimiter()
        for _ in range(5):
            assert limiter.is_allowed("test", limit=10, window_seconds=60)

    def test_blocks_over_limit(self):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.is_allowed("test", limit=10, window_seconds=60)

        assert not limiter.is_allowed("test", limit=10, window_seconds=60)

    def test_separate_keys(self):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.is_allowed("key_a", limit=10, window_seconds=60)

        assert limiter.is_allowed("key_b", limit=10, window_seconds=60)

    def test_remaining_count(self):
        limiter = RateLimiter()
        for _ in range(7):
            limiter.is_allowed("test", limit=10, window_seconds=60)

        remaining = limiter.get_remaining("test", limit=10, window_seconds=60)
        assert remaining == 2  # 10 - 7 - 1 (the check itself consumes one)

    def test_reset(self):
        limiter = RateLimiter()
        for _ in range(10):
            limiter.is_allowed("test", limit=10, window_seconds=60)

        limiter.reset("test")
        assert limiter.is_allowed("test", limit=10, window_seconds=60)

    def test_check_result(self):
        limiter = RateLimiter()
        result = limiter.check("test", limit=5, window_seconds=60)
        assert result.allowed
        assert result.limit == 5
        assert result.remaining == 4  # 5 - 0 (current) - 1 (consumed by this check)

    def test_default_rate_limits(self):
        assert get_rate_limit("default") == (100, 60)
        assert get_rate_limit("backtest") == (10, 60)
        assert get_rate_limit("analytics") == (30, 60)
        assert get_rate_limit("unknown") == (100, 60)  # fallback


# ─────────────── Pagination ───────────────


class TestPagination:
    def test_paginate_list_basic(self):
        items = list(range(100))
        page, total = paginate_list(items, page=1, page_size=20)
        assert len(page) == 20
        assert total == 100

    def test_paginate_list_last_page(self):
        items = list(range(55))
        page, total = paginate_list(items, page=3, page_size=20)
        assert len(page) == 15
        assert total == 55

    def test_paginate_list_empty(self):
        page, total = paginate_list([], page=1, page_size=20)
        assert len(page) == 0
        assert total == 0

    def test_paginate_with_sort(self):
        items = [{"score": 3}, {"score": 1}, {"score": 2}]
        page, total = paginate_list(items, page=1, page_size=10, sort_key="score")
        assert page[0]["score"] == 1
        assert page[1]["score"] == 2
        assert page[2]["score"] == 3

    def test_paginate_with_sort_desc(self):
        items = [{"score": 3}, {"score": 1}, {"score": 2}]
        page, total = paginate_list(
            items, page=1, page_size=10, sort_key="score", reverse=True
        )
        assert page[0]["score"] == 3

    def test_page_request_validate(self):
        req = PageRequest(page=-1, page_size=500)
        validated = req.validate()
        assert validated.page == 1
        assert validated.page_size == 200  # clamped

    def test_page_request_offset(self):
        req = PageRequest(page=3, page_size=20)
        assert req.offset == 40
        assert req.limit == 20
