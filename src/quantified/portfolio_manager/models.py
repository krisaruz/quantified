"""多组合管理数据模型"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class HoldingSnapshot:
    """持仓快照"""

    cb_code: str
    cb_name: str
    volume: int
    avg_cost: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float
    weight: float


@dataclass(frozen=True)
class PortfolioSnapshot:
    """组合快照"""

    date: str
    portfolio_name: str
    cash: float
    holdings: list[HoldingSnapshot]
    total_assets: float
    total_pnl_pct: float
    high_water_mark: float


@dataclass(frozen=True)
class PortfolioSummary:
    """组合摘要"""

    name: str
    template: str
    created_at: str
    last_updated: str
    holding_count: int
    cash: float
    total_assets: float
    total_pnl_pct: float


@dataclass(frozen=True)
class PortfolioTemplate:
    """组合模板"""

    name: str
    description: str
    config_overrides: dict[str, object]
    is_builtin: bool = True


@dataclass(frozen=True)
class ComparisonResult:
    """组合对比结果"""

    portfolios: list[str]
    metrics: dict[str, list[float]]
    holdings_overlap: dict[str, float]
    ranking: list[tuple[str, float]]
