"""历史数据回填脚本

批量拉取转债日线、正股日线、转股价变动历史，写入本地 SQLite。
回测引擎依赖此数据运行。

用法:
    python scripts/backfill_history.py --start 2023-01-01
    python scripts/backfill_history.py --start 2023-01-01 --end 2025-12-31 --skip-existing
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[0].parent / "src"))

from sqlalchemy.orm import Session

from quantified.db import get_meta, init_db, set_meta
from quantified.fetcher.akshare_impl import AkShareFetcher
from quantified.models.base import get_session_factory
from quantified.models.bond import BondBasic, BondDaily, ConversionPriceHistory
from quantified.models.stock import StockBasic, StockDaily

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

REQUEST_DELAY = 0.3


def _ensure_bond_basics(session: Session, fetcher: AkShareFetcher) -> list[dict]:
    """确保 bond_basic 表有数据，返回转债列表"""
    bond_count = session.query(BondBasic).count()
    if bond_count > 0:
        logger.info("bond_basic 已有 %d 条记录，跳过基础数据同步", bond_count)
        rows = session.query(
            BondBasic.cb_code,
            BondBasic.cb_name,
            BondBasic.stock_code,
        ).all()
        return [{"cb_code": r[0], "cb_name": r[1], "stock_code": r[2]} for r in rows]

    logger.info("bond_basic 为空，先运行 sync_data.py 同步基础数据")
    from scripts.sync_data import sync_bond_snapshot
    records = sync_bond_snapshot(session)
    return records


def backfill_bond_daily(
    session: Session,
    fetcher: AkShareFetcher,
    bonds: list[dict],
    start: str,
    end: str,
    skip_existing: bool = True,
) -> None:
    """回填转债日线行情"""
    logger.info("=== 回填转债日线 [%s ~ %s] (%d 只) ===", start, end, len(bonds))
    success = 0
    skipped = 0
    total_rows = 0

    for i, bond in enumerate(bonds):
        cb_code = bond["cb_code"]

        if skip_existing:
            meta_key = f"backfill:bond_daily:{cb_code}"
            last = get_meta(session, meta_key)
            if last and last >= end:
                skipped += 1
                continue

        if (i + 1) % 20 == 0 or i == 0:
            logger.info("转债日线进度: %d/%d (成功%d, 跳过%d)", i + 1, len(bonds), success, skipped)

        try:
            df = fetcher.fetch_bond_daily(cb_code, start, end)
            if df.empty:
                time.sleep(REQUEST_DELAY)
                continue

            for _, row in df.iterrows():
                session.merge(BondDaily(
                    cb_code=cb_code,
                    trade_date=row["trade_date"],
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=float(row.get("volume", 0)),
                    turnover=float(row.get("turnover", 0)) if "turnover" in row.index else None,
                ))
            total_rows += len(df)

            if skip_existing:
                set_meta(session, f"backfill:bond_daily:{cb_code}", end)
            success += 1

        except Exception as e:
            logger.debug("转债日线失败 %s: %s", cb_code, e)

        if (i + 1) % 10 == 0:
            session.commit()

        time.sleep(REQUEST_DELAY)

    session.commit()
    logger.info("转债日线回填完成: %d/%d 成功, %d 跳过, 共 %d 条", success, len(bonds), skipped, total_rows)


def backfill_stock_daily(
    session: Session,
    fetcher: AkShareFetcher,
    stock_codes: list[str],
    start: str,
    end: str,
    skip_existing: bool = True,
) -> None:
    """回填正股日线行情"""
    logger.info("=== 回填正股日线 [%s ~ %s] (%d 只) ===", start, end, len(stock_codes))
    success = 0
    skipped = 0
    total_rows = 0

    for i, stock_code in enumerate(stock_codes):
        if skip_existing:
            meta_key = f"backfill:stock_daily:{stock_code}"
            last = get_meta(session, meta_key)
            if last and last >= end:
                skipped += 1
                continue

        if (i + 1) % 20 == 0 or i == 0:
            logger.info("正股日线进度: %d/%d (成功%d, 跳过%d)", i + 1, len(stock_codes), success, skipped)

        try:
            df = fetcher.fetch_stock_daily(stock_code, start, end)
            if df.empty:
                time.sleep(REQUEST_DELAY)
                continue

            for _, row in df.iterrows():
                session.merge(StockDaily(
                    stock_code=stock_code,
                    trade_date=row["trade_date"],
                    open=float(row.get("open", 0)),
                    high=float(row.get("high", 0)),
                    low=float(row.get("low", 0)),
                    close=float(row.get("close", 0)),
                    volume=float(row.get("volume", 0)),
                    turnover=float(row.get("turnover", 0)) if "turnover" in row.index else None,
                ))
            total_rows += len(df)

            if skip_existing:
                set_meta(session, f"backfill:stock_daily:{stock_code}", end)
            success += 1

        except Exception as e:
            logger.debug("正股日线失败 %s: %s", stock_code, e)

        if (i + 1) % 10 == 0:
            session.commit()

        time.sleep(REQUEST_DELAY)

    session.commit()
    logger.info("正股日线回填完成: %d/%d 成功, %d 跳过, 共 %d 条", success, len(stock_codes), skipped, total_rows)


def backfill_conv_price_history(
    session: Session,
    fetcher: AkShareFetcher,
    bonds: list[dict],
    skip_existing: bool = True,
) -> None:
    """回填转股价变动历史"""
    logger.info("=== 回填转股价变动历史 (%d 只) ===", len(bonds))
    success = 0
    skipped = 0
    total_rows = 0

    for i, bond in enumerate(bonds):
        cb_code = bond["cb_code"]

        if skip_existing:
            meta_key = f"backfill:conv_price:{cb_code}"
            last = get_meta(session, meta_key)
            if last:
                skipped += 1
                continue

        if (i + 1) % 50 == 0 or i == 0:
            logger.info("转股价进度: %d/%d (成功%d, 跳过%d)", i + 1, len(bonds), success, skipped)

        try:
            df = fetcher.fetch_conv_price_history(cb_code)
            if df.empty:
                if skip_existing:
                    set_meta(session, f"backfill:conv_price:{cb_code}", "done")
                time.sleep(REQUEST_DELAY)
                continue

            for _, row in df.iterrows():
                if row.get("change_date") and row.get("conversion_price"):
                    session.merge(ConversionPriceHistory(
                        cb_code=cb_code,
                        change_date=row["change_date"],
                        conversion_price=float(row["conversion_price"]),
                        reason=str(row.get("reason", "")) or None,
                    ))
            total_rows += len(df)

            if skip_existing:
                set_meta(session, f"backfill:conv_price:{cb_code}", "done")
            success += 1

        except Exception as e:
            logger.debug("转股价历史失败 %s: %s", cb_code, e)

        if (i + 1) % 20 == 0:
            session.commit()

        time.sleep(REQUEST_DELAY)

    session.commit()
    logger.info("转股价历史回填完成: %d/%d 成功, %d 跳过, 共 %d 条", success, len(bonds), skipped, total_rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="历史数据回填")
    parser.add_argument("--start", required=True, help="起始日期 (YYYY-MM-DD)")
    parser.add_argument("--end", default=None, help="截止日期 (YYYY-MM-DD)，默认今天")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--skip-existing", action="store_true", default=True, help="跳过已回填的(默认)")
    parser.add_argument("--no-skip", action="store_true", help="强制重新回填所有")
    parser.add_argument("--skip-conv-price", action="store_true", help="跳过转股价历史")
    parser.add_argument("--only-bonds", action="store_true", help="只回填转债日线")
    parser.add_argument("--only-stocks", action="store_true", help="只回填正股日线")
    args = parser.parse_args()

    start = args.start
    end = args.end or datetime.date.today().isoformat()
    skip_existing = not args.no_skip

    logger.info("=== 历史数据回填 [%s ~ %s] ===", start, end)

    db_kwargs = {"db_path": args.db} if args.db else {}
    engine = init_db(**db_kwargs)
    session_factory = get_session_factory(engine)
    fetcher = AkShareFetcher()

    with session_factory() as session:
        bonds = _ensure_bond_basics(session, fetcher)
        if not bonds:
            logger.error("无转债数据，请先运行 sync_data.py")
            return

        stock_codes = sorted({b["stock_code"] for b in bonds if b.get("stock_code")})
        logger.info("共 %d 只转债, %d 只正股", len(bonds), len(stock_codes))

        if not args.only_stocks:
            backfill_bond_daily(session, fetcher, bonds, start, end, skip_existing)

        if not args.only_bonds:
            backfill_stock_daily(session, fetcher, stock_codes, start, end, skip_existing)

        if not args.skip_conv_price and not args.only_bonds and not args.only_stocks:
            backfill_conv_price_history(session, fetcher, bonds, skip_existing)

        # Final commit ensures all pending merges are persisted
        session.commit()
        logger.info("=== 全部回填完成 ===")


if __name__ == "__main__":
    main()
