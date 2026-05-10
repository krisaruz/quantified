# Multi-Portfolio Spec

## 概述

多组合管理支持创建、对比、快照多个独立的投资组合，每个组合有独立的持仓、配置和历史。

## 目录结构

```
data/
  portfolios/
    default/               # 默认组合（迁移现有数据）
      portfolio.json
      history.jsonl
      snapshots/
        2025-01-15.json
        2025-01-16.json
    conservative/
      portfolio.json
      history.jsonl
      snapshots/
    aggressive/
      portfolio.json
      history.jsonl
      snapshots/
```

## 数据模型

### PortfolioManager
```python
class PortfolioManager:
    def __init__(self, data_dir: Path = Path("data/portfolios")):
        self.data_dir = data_dir

    def create(self, name: str, template: str = "balanced",
               initial_capital: float = 100000) -> Portfolio:
        """从模板创建组合"""

    def load(self, name: str) -> Portfolio:
        """加载组合"""

    def save(self, name: str, portfolio: Portfolio) -> None:
        """保存组合"""

    def list(self) -> list[PortfolioSummary]:
        """列出所有组合"""

    def delete(self, name: str) -> None:
        """删除组合（需确认）"""

    def rename(self, old_name: str, new_name: str) -> None:
        """重命名组合"""

    def duplicate(self, source: str, target: str) -> None:
        """复制组合"""
```

### PortfolioSummary
```python
@dataclass
class PortfolioSummary:
    name: str
    template: str
    created_at: str
    last_updated: str
    holding_count: int
    cash: float
    total_assets: float
    total_pnl_pct: float
```

## 组合模板

### 内置模板

```python
TEMPLATES = {
    "conservative": PortfolioTemplate(
        name="保守型",
        description="低风险、稳定收益，适合风险厌恶型投资者",
        config_overrides={
            "strategy.hold_count": 15,
            "strategy.scoring.credit.unknown": 8.0,
            "filters.min_credit_rating": "AA",
            "filters.max_price": 120,
            "risk.max_position_pct": 0.06,
            "risk.stop_loss_pct": -0.10,
            "risk.max_drawdown_pct": -0.06,
        },
    ),
    "balanced": PortfolioTemplate(
        name="均衡型",
        description="风险收益平衡，适合大多数投资者",
        config_overrides={
            "strategy.hold_count": 10,
            "filters.min_credit_rating": "AA-",
            "filters.max_price": 130,
            "risk.max_position_pct": 0.10,
            "risk.stop_loss_pct": -0.15,
            "risk.max_drawdown_pct": -0.10,
        },
    ),
    "aggressive": PortfolioTemplate(
        name="激进型",
        description="高风险高收益，适合风险偏好型投资者",
        config_overrides={
            "strategy.hold_count": 5,
            "strategy.scoring.credit.unknown": 3.0,
            "filters.min_credit_rating": "A+",
            "filters.max_price": 150,
            "risk.max_position_pct": 0.20,
            "risk.stop_loss_pct": -0.25,
            "risk.max_drawdown_pct": -0.15,
        },
    ),
}
```

### 自定义模板
```python
class PortfolioTemplate:
    name: str
    description: str
    config_overrides: dict
    created_at: datetime
    is_builtin: bool

    def apply(self, base_config: AppConfig) -> AppConfig:
        """将模板覆盖应用到基础配置"""
        data = base_config.model_dump()
        for key, value in self.config_overrides.items():
            _set_nested(data, key, value)
        return AppConfig(**data)
```

## 组合对比

### ComparisonResult
```python
@dataclass
class ComparisonResult:
    portfolios: list[str]
    metrics: dict[str, list[float]]     # metric_name → [value_for_each_portfolio]
    holdings_overlap: dict[str, float]  # pair → overlap_ratio
    correlation_matrix: list[list[float]]
    ranking: list[tuple[str, float]]    # (name, composite_score)
```

### 对比维度
| 维度 | 指标 |
|------|------|
| 收益 | 总收益率、年化收益率、月度收益分布 |
| 风险 | 最大回撤、波动率、VaR、CVaR |
| 效率 | 夏普比率、Sortino、Calmar |
| 交易 | 胜率、盈亏比、换手率 |
| 持仓 | 持仓重叠度、行业分布差异 |

### 持仓重叠度计算
```
overlap(A, B) = |A ∩ B| / min(|A|, |B|)
```

## 组合快照

### PortfolioSnapshot
```python
@dataclass
class PortfolioSnapshot:
    date: str
    portfolio_name: str
    cash: float
    holdings: list[HoldingSnapshot]
    total_assets: float
    total_pnl_pct: float
    high_water_mark: float

@dataclass
class HoldingSnapshot:
    cb_code: str
    cb_name: str
    volume: int
    avg_cost: float
    current_price: float
    market_value: float
    pnl: float
    pnl_pct: float
    weight: float       # 占总资产比例
```

### 快照策略
- 每次调仓后自动快照
- 每日收盘后快照（如果系统运行）
- 手动快照：`quantified portfolio snapshot <name>`

### 快照查询
```python
class SnapshotManager:
    def save(self, snapshot: PortfolioSnapshot) -> None: ...
    def load(self, portfolio_name: str, date: str) -> PortfolioSnapshot | None: ...
    def list_dates(self, portfolio_name: str) -> list[str]: ...
    def get_history(
        self, portfolio_name: str, start: str, end: str
    ) -> list[PortfolioSnapshot]: ...
```

## CLI 命令

```bash
# 组合管理
quantified portfolio list                        # 列出所有组合
quantified portfolio create my_port --template balanced  # 创建组合
quantified portfolio delete my_port              # 删除组合
quantified portfolio rename old_name new_name    # 重命名
quantified portfolio duplicate src_name dst_name # 复制

# 组合操作
quantified portfolio status --portfolio my_port  # 查看组合状态
quantified portfolio snapshot my_port            # 手动快照
quantified portfolio compare port1 port2         # 对比两个组合

# 默认组合
quantified recommend                             # 使用默认组合
quantified recommend --portfolio my_port         # 指定组合
```

## 迁移策略

现有 `data/portfolio.json` 和 `data/portfolio_history.jsonl` 自动迁移到 `data/portfolios/default/`。

迁移代码放在 `src/quantified/portfolio/migration.py`，首次加载时自动执行。
