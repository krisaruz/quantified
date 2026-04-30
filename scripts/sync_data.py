"""日常数据同步入口脚本

每日收盘后运行，拉取转债和正股数据到本地 SQLite。
数据源: AkShare → 东方财富

用法:
    python scripts/sync_data.py
    python scripts/sync_data.py --full   # 全量重新同步
"""

from __future__ import annotations

import argparse
import datetime
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pandas as pd
from sqlalchemy.orm import Session

from quantified.db import get_meta, init_db, set_meta
from quantified.models.base import get_session_factory
from quantified.models.bond import BondBasic, BondDaily, BondStatus
from quantified.models.stock import StockBasic, StockDaily

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

CB_DEFAULT_TERM_YEARS = 6


def _safe_ak_call(func_name: str, **kwargs):
    """安全调用 AkShare"""
    import akshare as ak
    func = getattr(ak, func_name)
    return func(**kwargs)


def _safe_float(v, default=0.0):
    """安全转换浮点数"""
    try:
        if v is None or v == "" or v == "-" or str(v) == "nan":
            return default
        if isinstance(v, str):
            v = v.replace(",", "").replace("%", "").strip()
            if not v or v == "-":
                return default
        result = float(v)
        if pd.isna(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def _parse_date(val, default: datetime.date | None = None) -> datetime.date | None:
    """安全解析日期"""
    # pd.isna 统一处理 None/NaN/NaT/empty string
    try:
        if pd.isna(val):
            return default
    except (TypeError, ValueError):
        pass  # pd.isna 不接受该类型，继续下面的解析
    if isinstance(val, datetime.datetime):
        return val.date()
    if isinstance(val, datetime.date):
        return val
    if isinstance(val, str):
        val = val.strip().replace("/", "-")
        if not val or val == "-":
            return default
        try:
            return datetime.date.fromisoformat(val[:10])
        except ValueError:
            pass
    try:
        ts = pd.Timestamp(val)
        if pd.isna(ts):
            return default
        return ts.date()
    except Exception:
        return default


def _estimate_maturity_date(list_date: datetime.date | None, today: datetime.date) -> datetime.date:
    """推算到期日（上市日 + 6 年，无上市日则默认今天 + 6 年）"""
    base = list_date if list_date else today
    try:
        return base.replace(year=base.year + CB_DEFAULT_TERM_YEARS)
    except ValueError:
        return base.replace(year=base.year + CB_DEFAULT_TERM_YEARS, day=28)


def _detect_redeem_status(row) -> BondStatus:
    """根据数据检测强赎状态"""
    name = str(row.get("cb_name", ""))
    if any(kw in name for kw in ("退市", "摘牌")):
        return BondStatus.DELISTED

    trigger = row.get("redeem_trigger_price")
    stock_close = _safe_float(row.get("stock_close"))
    trigger_val = _safe_float(trigger)
    if trigger_val > 0 and stock_close > 0 and stock_close >= trigger_val * 0.95:
        return BondStatus.REDEEM_WARNING

    return BondStatus.ACTIVE


def sync_bond_snapshot(session: Session) -> list[dict]:
    """同步转债快照数据（列表+实时行情）

    合并 bond_zh_cov() 和 bond_cov_comparison() 两个数据源。
    """
    logger.info("=== 同步转债快照 ===")

    logger.info("获取转债列表 (bond_zh_cov)...")
    list_df = _safe_ak_call("bond_zh_cov")
    logger.info("获取到 %d 只转债", len(list_df))

    logger.info("获取转债实时对比 (bond_cov_comparison)...")
    comp_df = _safe_ak_call("bond_cov_comparison")
    logger.info("获取到 %d 只在交转债", len(comp_df))

    list_df = list_df.rename(columns={
        "债券代码": "cb_code", "债券简称": "cb_name",
        "正股代码": "stock_code", "正股简称": "stock_name",
        "上市时间": "list_date", "转股价": "conv_price",
        "发行规模": "issue_size", "信用评级": "credit_rating",
    })

    comp_df = comp_df.rename(columns={
        "转债代码": "cb_code", "转债名称": "cb_name_comp",
        "转债最新价": "cb_close", "转债涨跌幅": "cb_change_pct",
        "正股代码": "stock_code_comp", "正股名称": "stock_name_comp",
        "正股最新价": "stock_close", "正股涨跌幅": "stock_change_pct",
        "转股价": "conv_price_comp", "转股价值": "conversion_value",
        "转股溢价率": "premium_rate",
        "强赎触发价": "redeem_trigger_price",
        "上市日期": "list_date_comp",
    })

    # 尝试提取成交额（如果存在）
    turnover_col = None
    for col_name in ("成交额", "成交额(万)", "成交金额"):
        if col_name in comp_df.columns:
            turnover_col = col_name
            break

    volume_col = None
    for col_name in ("成交量", "成交量(手)"):
        if col_name in comp_df.columns:
            volume_col = col_name
            break

    merge_cols = [
        "cb_code", "cb_close", "stock_code_comp", "stock_name_comp",
        "stock_close", "conv_price_comp", "conversion_value",
        "premium_rate", "redeem_trigger_price",
    ]
    if turnover_col:
        comp_df["_turnover"] = comp_df[turnover_col]
        merge_cols.append("_turnover")
    if volume_col:
        comp_df["_volume"] = comp_df[volume_col]
        merge_cols.append("_volume")

    merged = pd.merge(
        comp_df[merge_cols],
        list_df[["cb_code", "cb_name", "stock_code", "stock_name",
                 "list_date", "conv_price", "issue_size", "credit_rating"]],
        on="cb_code", how="left",
    )

    merged["stock_code"] = merged["stock_code"].fillna(merged["stock_code_comp"])
    merged["stock_name"] = merged["stock_name"].fillna(merged["stock_name_comp"])
    merged["conv_price"] = merged["conv_price"].fillna(merged["conv_price_comp"])

    today = datetime.date.today()
    records = []
    count = 0
    skipped = 0

    for _, row in merged.iterrows():
        cb_code = str(row.get("cb_code", ""))
        stock_code = str(row.get("stock_code", ""))
        if not cb_code or not stock_code or stock_code == "nan":
            skipped += 1
            continue

        existing_stock = session.get(StockBasic, stock_code)
        if existing_stock is None:
            exchange = "SH" if stock_code.startswith("6") else "SZ"
            session.merge(StockBasic(
                stock_code=stock_code,
                stock_name=str(row.get("stock_name", "")),
                exchange=exchange,
            ))

        list_date = _parse_date(row.get("list_date"), default=None)
        maturity_date = _estimate_maturity_date(list_date, today)
        bond_status = _detect_redeem_status(row)
        redeem_trigger = _safe_float(row.get("redeem_trigger_price"))

        session.merge(BondBasic(
            cb_code=cb_code,
            cb_name=str(row.get("cb_name", cb_code)),
            stock_code=stock_code,
            list_date=list_date if list_date else today,
            maturity_date=maturity_date,
            conv_price_latest=_safe_float(row.get("conv_price")),
            issue_size=_safe_float(row.get("issue_size")),
            credit_rating=str(row.get("credit_rating", "")) or None,
            redeem_trigger_price=redeem_trigger if redeem_trigger > 0 else None,
            status=bond_status,
        ))

        cb_close = _safe_float(row.get("cb_close"))
        stock_close = _safe_float(row.get("stock_close"))
        cb_volume = _safe_float(row.get("_volume")) if "_volume" in row.index else 0
        cb_turnover = _safe_float(row.get("_turnover")) if "_turnover" in row.index else 0

        if cb_close > 0:
            session.merge(BondDaily(
                cb_code=cb_code,
                trade_date=today,
                open=cb_close,
                high=cb_close,
                low=cb_close,
                close=cb_close,
                volume=cb_volume,
                turnover=cb_turnover,
            ))

        if stock_close > 0:
            session.merge(StockDaily(
                stock_code=stock_code,
                trade_date=today,
                open=stock_close,
                high=stock_close,
                low=stock_close,
                close=stock_close,
                volume=0,
            ))

        records.append({
            "cb_code": cb_code,
            "cb_name": str(row.get("cb_name", "")),
            "stock_code": stock_code,
            "cb_close": cb_close,
            "stock_close": stock_close,
            "premium_rate": _safe_float(row.get("premium_rate")),
            "conversion_value": _safe_float(row.get("conversion_value")),
            "credit_rating": str(row.get("credit_rating", "")),
            "issue_size": _safe_float(row.get("issue_size")),
        })
        count += 1

    session.commit()
    set_meta(session, "last_sync_bond_daily", today.isoformat())
    session.commit()
    logger.info("同步完成: %d 只转债 (跳过 %d)", count, skipped)
    return records


def sync_stock_history(
    session: Session,
    stock_codes: list[str],
    full: bool = False,
    days_back: int = 30,
) -> None:
    """同步正股近期日线行情"""
    logger.info("=== 同步正股历史日线 (%d 只) ===", len(stock_codes))
    today = datetime.date.today()
    default_start = (today - datetime.timedelta(days=days_back)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")

    success = 0
    for i, stock_code in enumerate(stock_codes):
        if i % 50 == 0:
            logger.info("进度: %d/%d", i, len(stock_codes))

        meta_key = f"stock_daily:{stock_code}:last_date"
        if not full:
            last = get_meta(session, meta_key)
            if last == today.isoformat():
                continue

        try:
            df = _safe_ak_call(
                "stock_zh_a_hist",
                symbol=stock_code, period="daily",
                start_date=default_start, end_date=end, adjust="qfq",
            )
            if df is None or df.empty:
                continue

            for _, row in df.iterrows():
                trade_date = row.get("日期")
                if isinstance(trade_date, str):
                    trade_date = datetime.date.fromisoformat(trade_date)
                session.merge(StockDaily(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    open=float(row.get("开盘", 0)),
                    high=float(row.get("最高", 0)),
                    low=float(row.get("最低", 0)),
                    close=float(row.get("收盘", 0)),
                    volume=float(row.get("成交量", 0)),
                    turnover=float(row.get("成交额", 0)),
                ))
            set_meta(session, meta_key, today.isoformat())
            success += 1
        except Exception as e:
            logger.debug("正股日线失败 %s: %s", stock_code, e)

        if (i + 1) % 20 == 0:
            session.commit()

    session.commit()
    logger.info("正股日线同步完成: %d/%d 成功", success, len(stock_codes))


def main() -> None:
    parser = argparse.ArgumentParser(description="量化系统数据同步")
    parser.add_argument("--full", action="store_true", help="全量重新同步")
    parser.add_argument("--db", type=str, default=None, help="数据库路径")
    parser.add_argument("--skip-stock-history", action="store_true", help="跳过正股历史日线")
    args = parser.parse_args()

    db_kwargs = {"db_path": args.db} if args.db else {}
    engine = init_db(**db_kwargs)
    session_factory = get_session_factory(engine)

    with session_factory() as session:
        records = sync_bond_snapshot(session)
        if not records:
            logger.error("无转债数据，退出")
            return

        if not args.skip_stock_history:
            stock_codes = list({r["stock_code"] for r in records})
            sync_stock_history(session, stock_codes, full=args.full)

    logger.info("=== 全部同步完成 ===")


if __name__ == "__main__":
    main()
