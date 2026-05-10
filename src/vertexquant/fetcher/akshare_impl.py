"""AkShare 数据获取实现

通过 AkShare 库从东方财富/集思录获取可转债和正股的行情数据。
所有返回的 DataFrame 列名统一为英文蛇形命名。
"""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from vertexquant.fetcher.protocol import DataFetchError

logger = logging.getLogger(__name__)

# ── AkShare 原始列名 → 标准英文列名 映射 ─────────────────────────

BOND_LIST_COLUMN_MAP: dict[str, str] = {
    "债券代码": "cb_code",
    "债券简称": "cb_name",
    "正股代码": "stock_code",
    "正股简称": "stock_name",
    "上市时间": "list_date",
    "转股价": "conv_price_latest",
    "发行规模": "issue_size",
    "信用评级": "credit_rating",
    "债现价": "current_price",
    "转股价值": "conversion_value",
    "转股溢价率": "premium_rate",
}

BOND_DAILY_COLUMN_MAP: dict[str, str] = {
    "日期": "trade_date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "turnover",
}

STOCK_DAILY_COLUMN_MAP: dict[str, str] = {
    "日期": "trade_date",
    "开盘": "open",
    "最高": "high",
    "最低": "low",
    "收盘": "close",
    "成交量": "volume",
    "成交额": "turnover",
}

CONV_PRICE_HISTORY_COLUMN_MAP: dict[str, str] = {
    "新转股价生效日期": "change_date",
    "下修后转股价": "conversion_price",
    "下修前转股价": "old_conversion_price",
    "下修底价": "floor_price",
    "股东大会日": "shareholder_meeting_date",
}


def _safe_akshare_call(func_name: str, **kwargs: Any) -> pd.DataFrame:
    """安全调用 AkShare 接口，统一异常处理"""
    try:
        import akshare as ak

        func = getattr(ak, func_name)
        result = func(**kwargs)
        if result is None or (isinstance(result, pd.DataFrame) and result.empty):
            logger.info("AkShare %s 返回空数据, params=%s", func_name, kwargs)
            return pd.DataFrame()
        return result
    except AttributeError:
        raise DataFetchError(f"AkShare 接口 {func_name} 不存在，可能版本不兼容")
    except Exception as e:
        logger.warning("AkShare %s 调用失败: %s, params=%s", func_name, e, kwargs)
        raise DataFetchError(f"数据获取失败 ({func_name}): {e}") from e


def _rename_columns(df: pd.DataFrame, column_map: dict[str, str]) -> pd.DataFrame:
    """按映射字典重命名列，未知列保留原名"""
    rename_dict = {k: v for k, v in column_map.items() if k in df.columns}
    unmapped = set(df.columns) - set(column_map.keys())
    if unmapped:
        logger.debug("未映射的列: %s", unmapped)
    return df.rename(columns=rename_dict)


class AkShareFetcher:
    """AkShare 数据获取实现

    实现 IDataFetcher 协议的全部方法。
    通过 AkShare 库访问东方财富、集思录等数据源。
    """

    def fetch_bond_list(self) -> pd.DataFrame:
        """获取全市场可转债基础信息列表

        使用 bond_zh_cov() 从东方财富获取转债列表（含已上市+待上市）。
        """
        df = _safe_akshare_call("bond_zh_cov")
        if df.empty:
            return df

        df = _rename_columns(df, BOND_LIST_COLUMN_MAP)

        if "list_date" in df.columns:
            df["list_date"] = pd.to_datetime(df["list_date"], errors="coerce").dt.date

        for col in ["conv_price_latest", "issue_size", "current_price", "conversion_value", "premium_rate"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        logger.info("获取转债列表: %d 条", len(df))
        return df

    def fetch_bond_daily(
        self, cb_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取单只转债的日线行情

        优先使用 bond_zh_hs_cov_daily()，若该 API 版本有 bug 则回退到
        stock_zh_a_hist()（东方财富的 stock 接口同样支持可转债代码）。
        """
        df = pd.DataFrame()
        try:
            df = _safe_akshare_call(
                "bond_zh_hs_cov_daily",
                symbol=cb_code,
            )
        except DataFetchError:
            pass

        if df.empty:
            try:
                df = _safe_akshare_call(
                    "stock_zh_a_hist",
                    symbol=cb_code,
                    period="daily",
                    start_date=start_date.replace("-", ""),
                    end_date=end_date.replace("-", ""),
                    adjust="",
                )
            except DataFetchError:
                return pd.DataFrame()

        if df.empty:
            return df

        df = _rename_columns(df, BOND_DAILY_COLUMN_MAP)

        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date
            mask = (df["trade_date"] >= pd.Timestamp(start_date).date()) & (
                df["trade_date"] <= pd.Timestamp(end_date).date()
            )
            df = df.loc[mask]

        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "trade_date" in df.columns:
            df = df.sort_values("trade_date").reset_index(drop=True)
        logger.info("获取转债日线 %s: %d 条 [%s ~ %s]", cb_code, len(df), start_date, end_date)
        return df

    def fetch_stock_daily(
        self, stock_code: str, start_date: str, end_date: str
    ) -> pd.DataFrame:
        """获取单只正股的前复权日线行情

        使用 stock_zh_a_hist() 获取正股日K（默认前复权）。
        """
        df = _safe_akshare_call(
            "stock_zh_a_hist",
            symbol=stock_code,
            period="daily",
            start_date=start_date.replace("-", ""),
            end_date=end_date.replace("-", ""),
            adjust="qfq",
        )
        if df.empty:
            return df

        df = _rename_columns(df, STOCK_DAILY_COLUMN_MAP)

        if "trade_date" in df.columns:
            df["trade_date"] = pd.to_datetime(df["trade_date"], errors="coerce").dt.date

        for col in ["open", "high", "low", "close", "volume", "turnover"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        df = df.sort_values("trade_date").reset_index(drop=True)
        logger.info("获取正股日线 %s: %d 条 [%s ~ %s]", stock_code, len(df), start_date, end_date)
        return df

    def fetch_conv_price_history(self, cb_code: str) -> pd.DataFrame:
        """获取转股价变动历史

        使用 bond_cb_adj_logs_jsl() 从集思录获取转股价变动记录。
        """
        df = _safe_akshare_call("bond_cb_adj_logs_jsl", symbol=cb_code)
        if df.empty:
            return df

        df = _rename_columns(df, CONV_PRICE_HISTORY_COLUMN_MAP)

        if "change_date" in df.columns:
            df["change_date"] = pd.to_datetime(df["change_date"], errors="coerce").dt.date

        if "conversion_price" in df.columns:
            df["conversion_price"] = pd.to_numeric(df["conversion_price"], errors="coerce")

        df = df.sort_values("change_date").reset_index(drop=True)
        logger.info("获取转股价变动 %s: %d 条", cb_code, len(df))
        return df
