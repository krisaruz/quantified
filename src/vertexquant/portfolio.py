"""本地持仓记录管理

使用 JSON 文件存储当前持仓，支持买入/卖出/查询操作。
包含高水位标记用于回撤暂停机制。
交易历史以 JSONL 格式追加写入 portfolio_history.jsonl。
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_PATH = Path(__file__).resolve().parents[2] / "data" / "portfolio.json"
DEFAULT_HISTORY_PATH = Path(__file__).resolve().parents[2] / "data" / "portfolio_history.jsonl"


@dataclass
class Holding:
    """单只持仓"""

    cb_code: str
    cb_name: str
    buy_date: str
    buy_price: float
    volume: int


@dataclass
class Portfolio:
    """持仓组合"""

    holdings: list[Holding] = field(default_factory=list)
    cash: float = 100000.0
    high_water_mark: float = 0.0

    @property
    def codes(self) -> set[str]:
        return {h.cb_code for h in self.holdings}

    def get_holding(self, cb_code: str) -> Holding | None:
        for h in self.holdings:
            if h.cb_code == cb_code:
                return h
        return None

    def add(self, holding: Holding, cost: float) -> None:
        self.holdings.append(holding)
        self.cash -= cost

    def remove(self, cb_code: str, proceeds: float) -> None:
        self.holdings = [h for h in self.holdings if h.cb_code != cb_code]
        self.cash += proceeds


def load_portfolio(path: Path | str | None = None) -> Portfolio:
    """加载持仓文件，不存在时返回空持仓"""
    p = Path(path) if path else DEFAULT_PORTFOLIO_PATH
    if not p.exists():
        return Portfolio()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        holdings = [Holding(**h) for h in data.get("holdings", [])]
        return Portfolio(
            holdings=holdings,
            cash=data.get("cash", 100000.0),
            high_water_mark=data.get("high_water_mark", 0.0),
        )
    except Exception as e:
        logger.warning("加载持仓文件失败: %s", e)
        return Portfolio()


def append_trade_history(
    action: str,
    cb_code: str,
    cb_name: str,
    price: float,
    volume: int,
    fee: float,
    path: Path | str | None = None,
) -> None:
    """追加一条交易记录到 JSONL 历史文件。"""
    p = Path(path) if path else DEFAULT_HISTORY_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.datetime.now().isoformat(),
        "action": action,
        "cb_code": cb_code,
        "cb_name": cb_name,
        "price": price,
        "volume": volume,
        "fee": round(fee, 2),
    }
    with open(p, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def load_trade_history(limit: int = 50, path: Path | str | None = None) -> list[dict]:
    """读取最近 N 条交易历史记录。"""
    p = Path(path) if path else DEFAULT_HISTORY_PATH
    if not p.exists():
        return []
    try:
        lines = p.read_text(encoding="utf-8").strip().splitlines()
        records = [json.loads(line) for line in lines if line.strip()]
        return records[-limit:][::-1]
    except Exception as e:
        logger.warning("读取交易历史失败: %s", e)
        return []


def save_portfolio(portfolio: Portfolio, path: Path | str | None = None) -> None:
    """保存持仓到 JSON 文件（原子写入：先写临时文件再 replace）。"""
    p = Path(path) if path else DEFAULT_PORTFOLIO_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "holdings": [asdict(h) for h in portfolio.holdings],
        "cash": portfolio.cash,
        "high_water_mark": portfolio.high_water_mark,
    }
    content = json.dumps(data, ensure_ascii=False, indent=2)
    fd, tmp_path = tempfile.mkstemp(dir=str(p.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp_path, str(p))
    except BaseException:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
