"""API Key 认证"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4


@dataclass(frozen=True)
class APIKeyInfo:
    """API Key 信息"""

    key: str
    name: str
    scopes: list[str]
    created_at: str
    is_active: bool = True


class APIKeyManager:
    """API Key 管理器"""

    def __init__(self) -> None:
        self._keys: dict[str, APIKeyInfo] = {}

    def generate(self, name: str, scopes: list[str]) -> str:
        """生成 API Key"""
        key = f"qf_{uuid4().hex}"
        info = APIKeyInfo(
            key=key,
            name=name,
            scopes=scopes,
            created_at=datetime.now().isoformat(),
            is_active=True,
        )
        self._keys[key] = info
        return key

    def validate(self, key: str) -> APIKeyInfo | None:
        """验证 API Key"""
        info = self._keys.get(key)
        if info and info.is_active:
            return info
        return None

    def revoke(self, key: str) -> bool:
        """吊销 API Key"""
        info = self._keys.get(key)
        if info:
            self._keys[key] = APIKeyInfo(
                key=info.key,
                name=info.name,
                scopes=info.scopes,
                created_at=info.created_at,
                is_active=False,
            )
            return True
        return False

    def list_keys(self) -> list[APIKeyInfo]:
        """列出所有 Key"""
        return list(self._keys.values())

    def has_scope(self, key: str, scope: str) -> bool:
        """检查 Key 是否拥有指定权限"""
        info = self.validate(key)
        if not info:
            return False
        if "admin" in info.scopes:
            return True
        return scope in info.scopes
