## Context

当前系统架构：

```
config.yaml → AppConfig (Pydantic)
     ↓
AkShareFetcher → [BondBasic, BondDaily, StockBasic, StockDaily] (SQLite)
     ↓
build_universe() → build_filtered_ranked() → FilterChain + Scoring
     ↓
Recommender → Action[] (buy/sell/hold/stop_loss)
     ↓
BacktestEngine → VirtualAccount → PerformanceStats
     ↓
Flask Web / CLI
```

现有模块职责清晰，但缺乏横向扩展能力。V2 设计目标：在不破坏现有接口的前提下，通过插件化和分层架构实现能力扩展。

## Goals / Non-Goals

**Goals:**
- 策略可插拔：新策略只需实现一个 Protocol，无需修改引擎代码
- 风控可配置：风控规则通过配置组合，而非硬编码
- 分析可扩展：新增指标只需注册到指标工厂
- 数据可追溯：每条数据可追溯到获取时间和来源
- 多组合隔离：不同组合的数据和计算完全隔离
- API 可版本化：v1/v2 接口可并存

**Non-Goals:**
- 不实现实时交易执行（仅模拟）
- 不实现分布式计算（单机足够）
- 不实现用户认证系统（个人工具）
- 不实现分钟级/tick 级数据
- 不实现机器学习预测模型

## Decisions

### D1: 策略框架架构

```python
# 策略 Protocol
class IStrategy(Protocol):
    name: str
    version: str

    def generate_signals(
        self, universe: pd.DataFrame, context: StrategyContext
    ) -> list[Signal]: ...

    def get_parameters(self) -> dict: ...

# 因子 Protocol
class IFactor(Protocol):
    name: str
    category: str  # "momentum" | "value" | "quality" | "technical"

    def compute(self, df: pd.DataFrame) -> pd.Series: ...

# 策略注册表
class StrategyRegistry:
    _strategies: dict[str, type[IStrategy]] = {}

    @classmethod
    def register(cls, name: str):
        def decorator(strategy_cls):
            cls._strategies[name] = strategy_cls
            return strategy_cls
        return decorator

    @classmethod
    def get(cls, name: str) -> IStrategy: ...
```

策略配置扩展：
```yaml
strategy:
  name: composite  # 使用组合策略
  strategies:
    - name: double_low
      weight: 0.6
      params: { ... }
    - name: momentum
      weight: 0.4
      params: { lookback_days: 20 }
  scoring:
    method: weighted_average  # 信号融合方法
```

### D2: 风控引擎分层

```python
class RiskEngine:
    """风控引擎：多层风控规则链"""

    def __init__(self, config: RiskConfig):
        self.rules: list[IRiskRule] = []
        self._load_rules(config)

    def check(
        self, portfolio: Portfolio, signals: list[Signal],
        market_data: pd.DataFrame
    ) -> list[RiskViolation]:
        """逐层检查，返回违规列表"""
        violations = []
        for rule in self.rules:
            violations.extend(rule.check(portfolio, signals, market_data))
        return violations

    def adjust(
        self, signals: list[Signal], violations: list[RiskViolation]
    ) -> list[Signal]:
        """根据违规调整信号（缩减仓位、移除标的等）"""
        adjusted = signals
        for violation in violations:
            adjusted = violation.rule.adjust(adjusted, violation)
        return adjusted


class IRiskRule(Protocol):
    name: str
    severity: str  # "hard" | "soft"

    def check(self, portfolio, signals, market_data) -> list[RiskViolation]: ...
    def adjust(self, signals, violation) -> list[Signal]: ...
```

风控规则清单：
| 规则 | 类型 | 说明 |
|------|------|------|
| MaxPositionRule | hard | 单只不超过总资产 X% |
| StopLossRule | hard | 亏损超阈值强制卖出 |
| MaxDrawdownRule | hard | 回撤超阈值暂停交易 |
| SectorConcentrationRule | soft | 单行业不超过 X% |
| CorrelationRule | soft | 持仓间相关性不超过 X |
| LiquidityRule | hard | 成交额不低于 X 万 |
| TurnoverRule | soft | 年换手率不超过 X 次 |
| VarLimitRule | soft | 组合 VaR 不超过 X% |

仓位管理算法：
```python
class PositionSizer(Protocol):
    def calculate_weights(
        self, signals: list[Signal], risk_budget: float
    ) -> dict[str, float]: ...

class EqualWeightSizer:
    """等权重分配"""

class RiskParitySizer:
    """风险平价：各标的对组合风险贡献相等"""

class KellySizer:
    """凯利公式：基于胜率和赔率的最优仓位"""
```

### D3: 分析引擎架构

```python
class AnalyticsEngine:
    """分析引擎：从回测结果计算各类分析指标"""

    def __init__(self, result: BacktestResult, benchmark: pd.Series | None = None):
        self.result = result
        self.benchmark = benchmark

    def brinson_attribution(self) -> BrinsonResult:
        """Brinson 归因：资产配置效应 + 选股效应 + 交互效应"""

    def factor_exposure(self, factor_data: pd.DataFrame) -> FactorExposure:
        """因子暴露：各因子对收益的贡献"""

    def risk_adjusted_metrics(self) -> RiskAdjustedMetrics:
        """风险调整指标：Sortino, Calmar, 信息比率, Omega比率"""

    def drawdown_analysis(self) -> list[DrawdownPeriod]:
        """回撤分析：所有回撤区间及其恢复时间"""

    def monthly_report(self, year: int, month: int) -> MonthlyReport:
        """月度报告：收益率、持仓变动、关键事件"""
```

Brinson 归因模型：
```
总超额收益 = 资产配置效应 + 选股效应 + 交互效应

配置效应 = Σ(wp,i - wb,i) × (Rb,i - Rb)
选股效应 = Σwb,i × (Rp,i - Rb,i)
交互效应 = Σ(wp,i - wb,i) × (Rp,i - Rb,i)

其中:
  wp,i = 组合中资产 i 的权重
  wb,i = 基准中资产 i 的权重
  Rp,i = 组合中资产 i 的收益率
  Rb,i = 基准中资产 i 的收益率
  Rb = 基准总收益率
```

### D4: 数据管道增强

```python
class DataQualityChecker:
    """数据质量校验层"""

    def check_bond_daily(self, df: pd.DataFrame) -> QualityReport:
        """校验转债日线数据质量"""
        checks = [
            self._check_price_range(df),      # 价格在合理范围 [50, 500]
            self._check_volume_sanity(df),     # 成交量非负且合理
            self._check_ohlc_consistency(df),  # open/high/low/close 逻辑一致
            self._check_missing_dates(df),     # 交易日连续性
            self._check_sudden_jumps(df),      # 价格突变检测（>30%）
        ]
        return QualityReport(checks=checks)


class SyncState:
    """增量同步状态机"""

    states = ["idle", "syncing", "paused", "error"]

    def __init__(self, db_path: Path):
        self.current_state = "idle"
        self._load_progress()

    def mark_progress(self, entity: str, last_date: str):
        """记录同步进度（断点续传）"""

    def retry_failed(self, max_retries: int = 3):
        """重试失败的同步任务"""
```

数据血缘模型：
```python
class DataLineage(Base):
    """数据血缘追踪"""
    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str]     # "bond_daily" | "stock_daily"
    entity_key: Mapped[str]      # "123001:2025-01-15"
    source: Mapped[str]          # "akshare:bond_zh_hs_cov_daily"
    fetched_at: Mapped[datetime]
    row_count: Mapped[int]
    quality_score: Mapped[float] # 0.0 ~ 1.0
```

### D5: 执行引擎增强

```python
class OrderManager:
    """订单管理系统"""

    def __init__(self):
        self.orders: dict[str, Order] = {}

    def create_order(self, signal: Signal) -> Order:
        """创建订单，进入 pending 状态"""

    def match(self, market_data: MarketData) -> list[Fill]:
        """撮合：根据市场数据匹配订单"""

    def cancel_expired(self, ttl_days: int = 3):
        """取消超时订单"""


class Order:
    order_id: str
    cb_code: str
    direction: str
    target_volume: int
    filled_volume: int
    status: str  # "pending" | "partial" | "filled" | "cancelled"
    created_at: datetime
    filled_at: datetime | None
    fills: list[Fill]


class SlippageModel(Protocol):
    """滑点模型"""
    def estimate(
        self, price: float, volume: int,
        daily_volume: float, volatility: float
    ) -> float: ...

class FixedSlippageModel:
    """固定比例滑点（当前实现）"""
    rate: float = 0.001

class VolumeBasedSlippageModel:
    """基于成交量的滑点：成交量越小，滑点越大"""
    base_rate: float = 0.0005
    impact_factor: float = 0.1

class VolatilitySlippageModel:
    """基于波动率的滑点：波动率越大，滑点越大"""
    base_rate: float = 0.0003
    vol_multiplier: float = 0.5
```

### D6: 多组合管理

```python
class PortfolioManager:
    """多组合管理器"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir

    def create(self, name: str, template: str = "balanced") -> Portfolio:
        """创建组合（从模板初始化）"""

    def list(self) -> list[PortfolioSummary]:
        """列出所有组合"""

    def compare(self, names: list[str]) -> ComparisonResult:
        """对比多个组合的表现"""

    def snapshot(self, name: str) -> PortfolioSnapshot:
        """生成组合快照（用于历史回溯）"""


# 组合模板
TEMPLATES = {
    "conservative": {
        "hold_count": 15,
        "max_position_pct": 0.06,
        "stop_loss_pct": -0.10,
        "max_drawdown_pct": -0.06,
        "min_credit_rating": "AA",
    },
    "balanced": {
        "hold_count": 10,
        "max_position_pct": 0.10,
        "stop_loss_pct": -0.15,
        "max_drawdown_pct": -0.10,
        "min_credit_rating": "AA-",
    },
    "aggressive": {
        "hold_count": 5,
        "max_position_pct": 0.20,
        "stop_loss_pct": -0.25,
        "max_drawdown_pct": -0.15,
        "min_credit_rating": "A+",
    },
}
```

### D7: 监控告警

```python
class Monitor:
    """监控引擎"""

    def __init__(self, config: MonitorConfig):
        self.rules: list[AlertRule] = []
        self._load_rules(config)

    def check_all(self, context: MonitorContext) -> list[Alert]:
        """检查所有告警规则"""


class AlertRule(Protocol):
    name: str
    severity: str  # "info" | "warning" | "critical"

    def evaluate(self, context: MonitorContext) -> Alert | None: ...


# 内置告警规则
class PnLAlert:
    """单日亏损超过阈值"""

class ConcentrationAlert:
    """单只持仓占比超过阈值"""

class DataFreshnessAlert:
    """数据超过 N 天未更新"""

class VolumeAnomalyAlert:
    """成交量异常（日成交量突变 > 5x）"""

class DrawdownAlert:
    """回撤接近止损线"""


class HealthScore:
    """策略健康度评分（0-100）"""

    def calculate(self, context: MonitorContext) -> float:
        """
        评分维度：
        - 数据新鲜度 (20%)
        - 持仓分散度 (20%)
        - 收益稳定性 (20%)
        - 回撤控制 (20%)
        - 交易执行质量 (20%)
        """
```

### D8: API 网关

```python
# 路由版本化
@app.route("/api/v1/universe")
@app.route("/api/v2/universe")

# WebSocket 实时推送
@socketio.on("subscribe")
def handle_subscribe(portfolio_name):
    """客户端订阅组合更新"""
    join_room(f"portfolio:{portfolio_name}")

# 认证中间件
@app.before_request
def authenticate():
    """API Key 认证"""
    api_key = request.headers.get("X-API-Key")
    if not validate_api_key(api_key):
        return jsonify({"error": "unauthorized"}), 401

# 限流
@limiter.limit("100/minute")
def api_universe(): ...
```

## Risks / Trade-offs

- **[复杂度增加]** → 8 个新模块增加代码量和维护成本。缓解：每个模块独立，通过 Protocol 解耦，可按需启用。
- **[性能影响]** → 风控链和分析引擎增加计算量。缓解：缓存中间结果，懒加载分析模块。
- **[向后兼容]** → 新策略框架需要兼容现有 double_low 配置。缓解：内置 LegacyStrategy 包装器。
- **[依赖增加]** → scipy/statsmodels/plotly 增加安装体积。缓解：可选依赖，按需导入。
