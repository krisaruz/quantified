"""数据获取层：可插拔的数据源抽象与 AkShare 实现"""

from quantified.fetcher.protocol import DataFetchError, IDataFetcher
from quantified.fetcher.akshare_impl import AkShareFetcher

__all__ = ["IDataFetcher", "DataFetchError", "AkShareFetcher"]
