"""DataAligner 测试：停牌对齐、衍生指标计算、截面扫描"""

from __future__ import annotations

import datetime

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from quantified.aligner.core import DataAligner
from quantified.models.base import Base
from quantified.models.bond import BondBasic, BondDaily, BondStatus, ConversionPriceHistory
from quantified.models.stock import StockBasic, StockDaily


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as sess:
        yield sess


def _seed_base(session: Session) -> None:
    """写入基础数据：1只正股 + 1只转债"""
    session.add(StockBasic(
        stock_code="600000", stock_name="浦发银行", exchange="SH", is_st=False,
    ))
    session.flush()
    session.add(BondBasic(
        cb_code="110059", cb_name="浦发转债", stock_code="600000",
        list_date=datetime.date(2023, 1, 1), maturity_date=datetime.date(2029, 1, 1),
        conv_price_latest=10.0, issue_size=50.0, credit_rating="AAA",
    ))
    session.add(ConversionPriceHistory(
        cb_code="110059", change_date=datetime.date(2023, 1, 1),
        conversion_price=10.0, reason="初始",
    ))
    session.commit()


def _add_daily(
    session: Session,
    dates: list[datetime.date],
    cb_prices: list[float | None],
    stock_prices: list[float | None],
) -> None:
    """批量写入日线数据，None 表示停牌（不写入记录）"""
    for d, cb_p, st_p in zip(dates, cb_prices, stock_prices):
        if cb_p is not None:
            session.add(BondDaily(
                cb_code="110059", trade_date=d,
                open=cb_p, high=cb_p, low=cb_p, close=cb_p, volume=1000,
            ))
        if st_p is not None:
            session.add(StockDaily(
                stock_code="600000", trade_date=d,
                open=st_p, high=st_p, low=st_p, close=st_p, volume=5000,
            ))
    session.commit()


class TestAlign:
    def test_both_normal(self, session: Session):
        """双方正常交易"""
        _seed_base(session)
        dates = [datetime.date(2025, 3, 10), datetime.date(2025, 3, 11)]
        _add_daily(session, dates, [108.0, 109.0], [15.0, 15.5])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-11")

        assert len(df) == 2
        assert df["trade_available"].all()
        assert df["cb_suspended_days"].tolist() == [0, 0]
        assert not df["conversion_value"].isna().any()

    def test_stock_suspended(self, session: Session):
        """正股停牌，转债正常"""
        _seed_base(session)
        dates = [datetime.date(2025, 3, 10), datetime.date(2025, 3, 11)]
        _add_daily(session, dates, [108.0, 109.0], [15.0, None])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-11")

        row = df[df["date"] == datetime.date(2025, 3, 11)].iloc[0]
        assert bool(row["stock_suspended"]) is True
        assert bool(row["cb_suspended"]) is False
        assert bool(row["trade_available"]) is False
        assert row["stock_close"] == 15.0  # ffill

    def test_bond_suspended(self, session: Session):
        """转债停牌，正股正常"""
        _seed_base(session)
        dates = [datetime.date(2025, 3, 10), datetime.date(2025, 3, 11)]
        _add_daily(session, dates, [108.0, None], [15.0, 15.5])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-11")

        row = df[df["date"] == datetime.date(2025, 3, 11)].iloc[0]
        assert bool(row["cb_suspended"]) is True
        assert bool(row["trade_available"]) is False
        assert row["cb_close"] == 108.0  # ffill

    def test_both_suspended(self, session: Session):
        """双方停牌：两边都无记录时，合并后只有第一天有数据"""
        _seed_base(session)
        dates = [datetime.date(2025, 3, 10), datetime.date(2025, 3, 11)]
        _add_daily(session, dates, [108.0, None], [15.0, None])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-11")

        # 第一天双方正常
        assert len(df) >= 1
        # 第二天双方都没记录，outer join 不会产生新行
        # 但第一天是正常的
        row0 = df.iloc[0]
        assert bool(row0["trade_available"]) is True


class TestDerivedMetrics:
    def test_conversion_value_and_premium(self, session: Session):
        """转股价值 = 100/转股价 * 正股价; 溢价率 = 转债价/转股价值 - 1"""
        _seed_base(session)
        dates = [datetime.date(2025, 3, 10)]
        _add_daily(session, dates, [110.0], [15.0])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-10")

        expected_cv = 100.0 / 10.0 * 15.0  # = 150.0
        expected_pr = 110.0 / 150.0 - 1.0  # ≈ -0.2667
        assert abs(df.iloc[0]["conversion_value"] - expected_cv) < 0.01
        assert abs(df.iloc[0]["premium_rate"] - expected_pr) < 0.01

    def test_zero_conv_price_gives_nan(self, session: Session):
        """转股价为0时衍生指标为 NaN"""
        _seed_base(session)
        bond = session.get(BondBasic, "110059")
        bond.conv_price_latest = 0.0
        # 删除已有的转股价历史
        for h in bond.conv_price_history:
            session.delete(h)
        session.add(ConversionPriceHistory(
            cb_code="110059", change_date=datetime.date(2023, 1, 1),
            conversion_price=0.0,
        ))
        session.commit()

        dates = [datetime.date(2025, 3, 10)]
        _add_daily(session, dates, [110.0], [15.0])

        aligner = DataAligner(session)
        df = aligner.align("110059", "2025-03-10", "2025-03-10")
        assert np.isnan(df.iloc[0]["conversion_value"])
        assert np.isnan(df.iloc[0]["premium_rate"])


class TestAlignUniverse:
    def test_universe_returns_active_bonds(self, session: Session):
        _seed_base(session)
        dates = [datetime.date(2025, 3, 15)]
        _add_daily(session, dates, [108.0], [15.0])

        aligner = DataAligner(session)
        df = aligner.align_universe("2025-03-15")

        assert len(df) == 1
        assert df.iloc[0]["cb_code"] == "110059"
        assert "double_low" in df.columns
        assert bool(df.iloc[0]["trade_available"]) is True
        assert df.iloc[0]["credit_rating"] == "AAA"
        assert bool(df.iloc[0]["is_st"]) is False
