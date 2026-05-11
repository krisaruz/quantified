"""用户配置加载与校验

从 config.yaml 加载策略参数、过滤规则、风控参数。
使用 Pydantic 做类型校验，缺失时使用内置默认值。
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.yaml"

# 信用评级排序（越高越好）
RATING_ORDER = ["AAA", "AA+", "AA", "AA-", "A+", "A", "A-", "BBB+", "BBB", "BBB-"]


class FiltersConfig(BaseModel):
    exclude_st: bool = True
    min_issue_size: float = 2.0
    min_remaining_years: float = 0.5
    max_price: float = 130.0
    min_credit_rating: str = "AA-"
    exclude_redeeming: bool = True
    exclude_suspended: bool = True
    min_turnover: float = 500


class RiskConfig(BaseModel):
    max_position_pct: float = 0.10
    stop_loss_pct: float = -0.15
    max_drawdown_pct: float = -0.10


class CapitalConfig(BaseModel):
    initial: float = 100000.0


class FeesConfig(BaseModel):
    commission_rate: float = 0.0002
    min_commission: float = 0.1


class ScoringConfig(BaseModel):
    credit: dict = Field(default_factory=lambda: {"unknown": 5.0})
    maturity: dict = Field(default_factory=lambda: {
        "long": -2.0, "short": 3.0, "very_short": 8.0,
    })
    bond_floor: dict = Field(default_factory=lambda: {
        "below_par": -5.0, "near_par": -2.0, "above_scale": 0.15,
    })


class StrategyConfig(BaseModel):
    name: str = "double_low"
    hold_count: int = 10
    rebalance_day: str = "friday"
    buffer_rank: int = 5
    scoring: ScoringConfig = Field(default_factory=ScoringConfig)


class AppConfig(BaseModel):
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    filters: FiltersConfig = Field(default_factory=FiltersConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    capital: CapitalConfig = Field(default_factory=CapitalConfig)
    fees: FeesConfig = Field(default_factory=FeesConfig)


def load_config(config_path: Optional[Path | str] = None) -> AppConfig:
    """加载配置文件，不存在时使用默认值"""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return AppConfig(**data)
    return AppConfig()


def rating_ge(rating: str | None, min_rating: str) -> bool:
    """判断信用评级是否 >= 最低要求"""
    if not rating:
        return False
    try:
        return RATING_ORDER.index(rating) <= RATING_ORDER.index(min_rating)
    except ValueError:
        return False
