"""ORM 模型测试：建表、CRUD、外键关联、唯一约束冲突"""

from __future__ import annotations

import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from quantified.db import DataMeta, get_meta, init_db, set_meta
from quantified.models.base import Base
from quantified.models.bond import BondBasic, BondDaily, BondStatus, ConversionPriceHistory
from quantified.models.stock import StockBasic, StockDaily


@pytest.fixture()
def session():
    """使用内存 SQLite 的测试会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as sess:
        yield sess


@pytest.fixture()
def populated_session(session: Session):
    """预填充测试数据的会话"""
    stock = StockBasic(
        stock_code="600000",
        stock_name="浦发银行",
        exchange="SH",
        is_st=False,
    )
    session.add(stock)
    session.flush()

    bond = BondBasic(
        cb_code="110059",
        cb_name="浦发转债",
        stock_code="600000",
        list_date=datetime.date(2023, 1, 1),
        maturity_date=datetime.date(2029, 1, 1),
        conv_price_latest=10.5,
        issue_size=50.0,
        credit_rating="AAA",
        status=BondStatus.ACTIVE,
    )
    session.add(bond)
    session.commit()
    return session


class TestStockBasic:
    def test_create_stock(self, session: Session):
        stock = StockBasic(
            stock_code="000001", stock_name="平安银行", exchange="SZ"
        )
        session.add(stock)
        session.commit()
        loaded = session.get(StockBasic, "000001")
        assert loaded is not None
        assert loaded.stock_name == "平安银行"
        assert loaded.is_st is False

    def test_st_flag(self, session: Session):
        stock = StockBasic(
            stock_code="000001", stock_name="*ST银行", exchange="SZ", is_st=True
        )
        session.add(stock)
        session.commit()
        assert session.get(StockBasic, "000001").is_st is True


class TestBondBasic:
    def test_create_bond_with_fk(self, populated_session: Session):
        bond = populated_session.get(BondBasic, "110059")
        assert bond is not None
        assert bond.stock.stock_name == "浦发银行"
        assert bond.credit_rating == "AAA"

    def test_default_status_is_active(self, populated_session: Session):
        bond = populated_session.get(BondBasic, "110059")
        assert bond.status == BondStatus.ACTIVE

    def test_duplicate_cb_code_raises(self, populated_session: Session):
        dup = BondBasic(
            cb_code="110059",
            cb_name="重复",
            stock_code="600000",
            list_date=datetime.date.today(),
            maturity_date=datetime.date.today(),
            conv_price_latest=1.0,
            issue_size=1.0,
        )
        populated_session.add(dup)
        with pytest.raises(IntegrityError):
            populated_session.flush()

    def test_unique_stock_code_constraint(self, populated_session: Session):
        stock2 = StockBasic(stock_code="600001", stock_name="另一只", exchange="SH")
        populated_session.add(stock2)
        populated_session.flush()

        bond2 = BondBasic(
            cb_code="110060",
            cb_name="另一转债",
            stock_code="600000",  # 已被 110059 占用
            list_date=datetime.date.today(),
            maturity_date=datetime.date.today(),
            conv_price_latest=1.0,
            issue_size=1.0,
        )
        populated_session.add(bond2)
        with pytest.raises(IntegrityError):
            populated_session.flush()


class TestBondDaily:
    def test_create_daily_quote(self, populated_session: Session):
        daily = BondDaily(
            cb_code="110059",
            trade_date=datetime.date(2025, 3, 15),
            open=108.0, high=110.0, low=107.0, close=109.5,
            volume=10000.0,
        )
        populated_session.add(daily)
        populated_session.commit()
        assert daily.bond.cb_name == "浦发转债"

    def test_duplicate_pk_raises(self, populated_session: Session):
        d = datetime.date(2025, 3, 15)
        populated_session.add(BondDaily(
            cb_code="110059", trade_date=d,
            open=108, high=110, low=107, close=109, volume=100,
        ))
        populated_session.flush()
        populated_session.add(BondDaily(
            cb_code="110059", trade_date=d,
            open=108, high=110, low=107, close=109, volume=100,
        ))
        with pytest.raises(IntegrityError):
            populated_session.flush()


class TestConversionPriceHistory:
    def test_create_history(self, populated_session: Session):
        h = ConversionPriceHistory(
            cb_code="110059",
            change_date=datetime.date(2024, 6, 1),
            conversion_price=9.8,
            reason="下修",
        )
        populated_session.add(h)
        populated_session.commit()
        bond = populated_session.get(BondBasic, "110059")
        assert len(bond.conv_price_history) == 1
        assert bond.conv_price_history[0].conversion_price == 9.8


class TestDataMeta:
    def test_set_and_get_meta(self, session: Session):
        set_meta(session, "test_key", "test_value")
        assert get_meta(session, "test_key") == "test_value"

    def test_update_meta(self, session: Session):
        set_meta(session, "key1", "v1")
        set_meta(session, "key1", "v2")
        assert get_meta(session, "key1") == "v2"

    def test_missing_key_returns_none(self, session: Session):
        assert get_meta(session, "nonexistent") is None
