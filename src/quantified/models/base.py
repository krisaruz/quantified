"""数据库引擎与会话工厂

提供 SQLAlchemy DeclarativeBase、引擎创建和会话管理。
默认使用 SQLite，通过替换 engine URL 可迁移到 PostgreSQL。
"""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DEFAULT_DB_DIR = Path(__file__).resolve().parents[3] / "data"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "quantified.db"


class Base(DeclarativeBase):
    """所有 ORM 模型的声明基类"""

    pass


def create_engine_factory(db_path: Path | str = DEFAULT_DB_PATH) -> Engine:
    """创建 SQLAlchemy 引擎

    Args:
        db_path: SQLite 数据库文件路径，默认 data/quantified.db
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f"sqlite:///{db_path}"
    return create_engine(url, echo=False)


def get_session_factory(engine: Engine) -> sessionmaker[Session]:
    """创建绑定到引擎的 Session 工厂"""
    return sessionmaker(bind=engine, expire_on_commit=False)
