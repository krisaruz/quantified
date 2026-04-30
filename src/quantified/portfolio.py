"""本地持仓记录管理

使用 JSON 文件存储当前持仓，支持买入/卖出/查询操作。
包含高水位标记用于回撤暂停机制。
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_PORTFOLIO_PATH = Path(__file__).resolve().parents[2] / "data" / "portfolio.json"


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


def save_portfolio(portfolio: Portfolio, path: Path | str | None = None) -> None:
    """保存持仓到 JSON 文件"""
    p = Path(path) if path else DEFAULT_PORTFOLIO_PATH
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "holdings": [asdict(h) for h in portfolio.holdings],
        "cash": portfolio.cash,
        "high_water_mark": portfolio.high_water_mark,
    }
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
