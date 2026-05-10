"""数据库会话管理与元信息表

DataMeta: 记录同步水位线、schema 版本等系统元信息
init_db(): 初始化数据库（建表 + 写入初始 schema 版本）
"""

from __future__ import annotations

import datetime
from pathlib import Path
from datetime import timezone

from sqlalchemy import DateTime, String, select
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Mapped, Session, mapped_column

from vertexquant.models.base import (
    DEFAULT_DB_PATH,
    Base,
    create_engine_factory,
    get_session_factory,
)

SCHEMA_VERSION = "1"


class DataMeta(Base):
    """数据同步元信息表

    通用 KV 存储，用于：
    - 同步水位线: key="bond_daily:123001:last_date", value="2026-04-25"
    - Schema 版本: key="schema_version", value="1"
    - AkShare 版本: key="akshare_version", value="1.14.56"
    """

    __tablename__ = "data_meta"

    key: Mapped[str] = mapped_column(String(200), primary_key=True)
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )


def get_meta(session: Session, key: str) -> str | None:
    """读取元信息值，不存在时返回 None"""
    row = session.execute(select(DataMeta).where(DataMeta.key == key)).scalar_one_or_none()
    return row.value if row else None


def set_meta(session: Session, key: str, value: str) -> None:
    """写入或更新元信息值"""
    row = session.execute(select(DataMeta).where(DataMeta.key == key)).scalar_one_or_none()
    if row:
        row.value = value
        row.updated_at = datetime.datetime.utcnow()
    else:
        session.add(DataMeta(key=key, value=value, updated_at=datetime.datetime.utcnow()))
    session.commit()


def init_db(db_path: Path | str = DEFAULT_DB_PATH) -> Engine:
    """初始化数据库：建表 + 写入 schema 版本

    Returns:
        已初始化的 Engine 实例
    """
    engine = create_engine_factory(db_path)
    Base.metadata.create_all(engine)

    session_factory = get_session_factory(engine)
    with session_factory() as session:
        if get_meta(session, "schema_version") is None:
            set_meta(session, "schema_version", SCHEMA_VERSION)

    return engine
