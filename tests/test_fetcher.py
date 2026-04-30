"""AkShareFetcher 测试：列名映射、异常处理（mock AkShare 接口）"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from quantified.fetcher.akshare_impl import AkShareFetcher
from quantified.fetcher.protocol import DataFetchError, IDataFetcher


class TestProtocolCompliance:
    def test_akshare_fetcher_satisfies_protocol(self):
        """AkShareFetcher 满足 IDataFetcher 协议"""
        fetcher = AkShareFetcher()
        assert isinstance(fetcher, IDataFetcher)


class TestColumnRenaming:
    @patch("quantified.fetcher.akshare_impl.ak", create=True)
    def test_bond_list_renames_chinese_columns(self, mock_ak):
        """中文列名被正确映射为英文"""
        mock_ak.bond_cb_index_jsl = MagicMock(return_value=pd.DataFrame({
            "债券代码": ["123001"],
            "债券简称": ["蓝盾转债"],
            "正股代码": ["300297"],
            "正股简称": ["蓝盾股份"],
            "上市时间": ["2020-01-15"],
            "到期时间": ["2026-01-15"],
            "转股价": ["5.50"],
            "发行规模": ["3.0"],
            "债券评级": ["AA"],
        }))

        with patch("quantified.fetcher.akshare_impl._safe_akshare_call") as mock_call:
            mock_call.return_value = mock_ak.bond_cb_index_jsl()
            fetcher = AkShareFetcher()
            df = fetcher.fetch_bond_list()

        assert "cb_code" in df.columns
        assert "cb_name" in df.columns
        assert "credit_rating" in df.columns
        assert "债券代码" not in df.columns


class TestExceptionHandling:
    def test_network_error_raises_data_fetch_error(self):
        """两个 API 均失败时，fetch_bond_daily 返回空 DataFrame（优雅降级）"""
        with patch(
            "quantified.fetcher.akshare_impl._safe_akshare_call",
            side_effect=DataFetchError("网络超时"),
        ):
            fetcher = AkShareFetcher()
            df = fetcher.fetch_bond_daily("123001", "2025-01-01", "2025-12-31")
            assert isinstance(df, pd.DataFrame)
            assert df.empty

    def test_network_error_on_stock_daily_raises(self):
        """stock_daily 网络异常仍抛出 DataFetchError"""
        with patch(
            "quantified.fetcher.akshare_impl._safe_akshare_call",
            side_effect=DataFetchError("网络超时"),
        ):
            fetcher = AkShareFetcher()
            with pytest.raises(DataFetchError, match="网络超时"):
                fetcher.fetch_stock_daily("600000", "2025-01-01", "2025-12-31")

    def test_empty_return_is_not_exception(self):
        """空数据返回空 DataFrame，不抛异常"""
        with patch(
            "quantified.fetcher.akshare_impl._safe_akshare_call",
            return_value=pd.DataFrame(),
        ):
            fetcher = AkShareFetcher()
            df = fetcher.fetch_conv_price_history("123001")
            assert isinstance(df, pd.DataFrame)
            assert df.empty
