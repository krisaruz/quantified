"""生成合成历史数据用于回测引擎验证

在网络不可用或 AkShare API 有问题时，用此脚本生成逼真的合成数据进行回测。
数据模拟了真实的转债市场特征：
- 价格围绕面值（100元）波动
- 溢价率随机分布
- 信用评级分布
- 正股联动
"""

from __future__ import annotations

import datetime
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0].parent / "src"))

import numpy as np

from quantified.db import init_db
from quantified.models.base import get_session_factory
from quantified.models.bond import BondBasic, BondDaily, BondStatus
from quantified.models.stock import StockBasic, StockDaily


def generate_trading_days(start: str, end: str) -> list[datetime.date]:
    """生成工作日列表（排除周末）"""
    sd = datetime.date.fromisoformat(start)
    ed = datetime.date.fromisoformat(end)
    days = []
    d = sd
    while d <= ed:
        if d.weekday() < 5:
            days.append(d)
        d += datetime.timedelta(days=1)
    return days


def generate_price_series(
    days: int,
    initial: float,
    drift: float = 0.0001,
    volatility: float = 0.015,
    mean_revert: float = 0.01,
    target: float = 100.0,
) -> list[float]:
    """生成带均值回复的价格序列"""
    prices = [initial]
    for _ in range(days - 1):
        prev = prices[-1]
        revert = mean_revert * (target - prev) / target
        ret = drift + revert + volatility * random.gauss(0, 1)
        prices.append(max(prev * (1 + ret), 50))
    return prices


def main():
    random.seed(42)
    np.random.seed(42)

    engine = init_db()
    sf = get_session_factory(engine)

    start = "2024-06-01"
    end = "2026-04-25"
    trading_days = generate_trading_days(start, end)
    n_days = len(trading_days)

    n_bonds = 50
    ratings = ["AAA"] * 5 + ["AA+"] * 15 + ["AA"] * 20 + ["AA-"] * 8 + ["A+"] * 2

    print(f"生成 {n_bonds} 只转债, {n_days} 个交易日的合成数据...")

    with sf() as session:
        for i in range(n_bonds):
            stock_code = f"{600000 + i:06d}"
            cb_code = f"{113000 + i:06d}"
            cb_name = f"测试转债{i+1:02d}"
            stock_name = f"测试正股{i+1:02d}"
            rating = ratings[i % len(ratings)]

            maturity_date = datetime.date(2028, 1, 1) + datetime.timedelta(days=i * 30)
            list_date = datetime.date(2023, 1, 1) + datetime.timedelta(days=i * 7)

            existing_stock = session.query(StockBasic).filter_by(stock_code=stock_code).first()
            if not existing_stock:
                session.add(StockBasic(
                    stock_code=stock_code,
                    stock_name=stock_name,
                    industry="测试行业",
                    exchange="SH" if i < 25 else "SZ",
                    is_st=False,
                ))

            existing_bond = session.query(BondBasic).filter_by(cb_code=cb_code).first()
            if not existing_bond:
                session.add(BondBasic(
                    cb_code=cb_code,
                    cb_name=cb_name,
                    stock_code=stock_code,
                    list_date=list_date,
                    maturity_date=maturity_date,
                    conv_price_latest=10.0 + random.uniform(-3, 3),
                    issue_size=random.uniform(2, 15),
                    credit_rating=rating,
                    status=BondStatus.ACTIVE,
                ))
            session.flush()

            stock_initial = 10 + random.uniform(-3, 5)
            stock_prices = generate_price_series(
                n_days, stock_initial,
                drift=0.0002, volatility=0.025, mean_revert=0.005,
                target=stock_initial,
            )

            bond_initial = 95 + random.uniform(-10, 25)
            bond_prices = generate_price_series(
                n_days, bond_initial,
                drift=0.00005, volatility=0.008, mean_revert=0.02,
                target=100,
            )

            for j, day in enumerate(trading_days):
                bp = bond_prices[j]
                bopen = bp * (1 + random.uniform(-0.005, 0.005))
                bhigh = bp * (1 + abs(random.gauss(0, 0.01)))
                blow = bp * (1 - abs(random.gauss(0, 0.01)))
                bvol = random.uniform(50000, 500000)

                session.merge(BondDaily(
                    cb_code=cb_code,
                    trade_date=day,
                    open=round(bopen, 3),
                    high=round(max(bhigh, bopen, bp), 3),
                    low=round(min(blow, bopen, bp), 3),
                    close=round(bp, 3),
                    volume=round(bvol, 0),
                    turnover=round(bvol * bp * 10, 2),
                ))

                sp = stock_prices[j]
                sopen = sp * (1 + random.uniform(-0.005, 0.005))
                shigh = sp * (1 + abs(random.gauss(0, 0.015)))
                slow = sp * (1 - abs(random.gauss(0, 0.015)))
                svol = random.uniform(100000, 2000000)

                session.merge(StockDaily(
                    stock_code=stock_code,
                    trade_date=day,
                    open=round(sopen, 3),
                    high=round(max(shigh, sopen, sp), 3),
                    low=round(min(slow, sopen, sp), 3),
                    close=round(sp, 3),
                    volume=round(svol, 0),
                    turnover=round(svol * sp, 2),
                ))

            if (i + 1) % 10 == 0:
                session.commit()
                print(f"  {i+1}/{n_bonds} 只完成...")

        session.commit()

    with sf() as session:
        bd_count = session.query(BondDaily).count()
        sd_count = session.query(StockDaily).count()
        bb_count = session.query(BondBasic).count()
        dates = session.query(BondDaily.trade_date).distinct().order_by(BondDaily.trade_date).all()
        print(f"\n合成数据生成完成:")
        print(f"  BondBasic: {bb_count}")
        print(f"  BondDaily: {bd_count}")
        print(f"  StockDaily: {sd_count}")
        print(f"  日期范围: {dates[0][0]} ~ {dates[-1][0]} ({len(dates)} 天)")


if __name__ == "__main__":
    main()
