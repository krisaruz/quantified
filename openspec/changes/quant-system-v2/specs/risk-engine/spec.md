# Risk Engine Spec

## 概述

风控引擎提供多层风控规则链、仓位管理算法和风险度量工具，确保组合在可控风险范围内运行。

## 架构

```
Strategy Signals → RiskEngine.check() → RiskViolations
                                         ↓
                 RiskEngine.adjust() → Adjusted Signals → Execution
```

## 数据模型

### RiskViolation（风控违规）
```python
@dataclass(frozen=True)
class RiskViolation:
    rule_name: str
    severity: str           # "hard" | "soft"
    cb_code: str | None     # 涉及的标的（组合级为 None）
    message: str
    current_value: float
    threshold: float
    suggested_action: str   # "reduce" | "remove" | "pause" | "warn"
    suggested_volume: int | None  # 建议调整到的仓位
```

### RiskConfig（风控配置）
```python
class RiskConfig(BaseModel):
    # 仓位限制
    max_position_pct: float = 0.10
    max_sector_pct: float = 0.30

    # 止损
    stop_loss_pct: float = -0.15
    trailing_stop: bool = False         # 移动止损
    trailing_stop_pct: float = -0.10

    # 回撤
    max_drawdown_pct: float = -0.10
    recovery_mode: str = "gradual"      # "immediate" | "gradual"
    recovery_steps: int = 3             # 阶梯恢复步数

    # 相关性
    max_correlation: float = 0.8
    correlation_lookback: int = 60      # 相关性计算回看天数

    # 流动性
    min_daily_volume: float = 500       # 最低日成交量（手）
    min_issue_size: float = 2.0         # 最低发行规模（亿）

    # 换手率
    max_annual_turnover: int = 52       # 最大年换手次数

    # VaR
    var_confidence: float = 0.95
    var_limit_pct: float = 0.05         # 组合 VaR 上限

    # 仓位管理
    position_sizer: str = "equal_weight"  # equal_weight | risk_parity | kelly | max_sharpe
```

## Protocol 定义

### IRiskRule
```python
class IRiskRule(Protocol):
    name: str
    severity: str  # "hard" | "soft"

    def check(
        self,
        portfolio: Portfolio,
        signals: list[Signal],
        market_data: pd.DataFrame,
        config: RiskConfig,
    ) -> list[RiskViolation]:
        """检查风控规则，返回违规列表"""
        ...

    def adjust(
        self,
        signals: list[Signal],
        violation: RiskViolation,
    ) -> list[Signal]:
        """根据违规调整信号"""
        ...
```

## 内置规则详情

### MaxPositionRule
- 检查：任何单只持仓占总资产比例超过阈值
- 调整：缩减买入量或生成卖出信号
- 硬规则，不可违反

### StopLossRule
- 检查：持仓亏损超过止损阈值
- 支持移动止损：从持仓最高点回撤超过阈值
- 调整：生成卖出信号
- 硬规则

### MaxDrawdownRule
- 检查：组合从高点回撤超过阈值
- 支持阶梯式恢复：
  - 回撤 10%：暂停新买入，允许卖出
  - 回撤 15%：暂停所有交易
  - 回撤 20%：强制减仓至半仓
- 硬规则

### SectorConcentrationRule
- 检查：单个行业持仓占比超过阈值
- 需要行业映射数据（stock_basic.industry）
- 调整：移除行业中排名最低的标的
- 软规则

### CorrelationRule
- 检查：任意两只持仓的相关性超过阈值
- 计算：基于 N 日收益率的 Pearson 相关系数
- 谻整：移除相关性最高的 pair 中排名较低的标的
- 软规则

### LiquidityRule
- 检查：标的日成交量低于阈值
- 调整：从候选列表中移除
- 硬规则

### TurnoverRule
- 检查：年化换手率超过阈值
- 计算：过去 N 天的交易次数 × 244 / N
- 调整：减少调仓频率或减少交易数量
- 软规则

### VarLimitRule
- 检查：组合 VaR 超过阈值
- 计算：历史模拟法或参数法
- 调整：缩减高风险标的仓位
- 软规则

## 仓位管理算法

### EqualWeightSizer
```
target_weight_i = 1 / N
```

### RiskParitySizer
```
求解：w_i 使得 w_i * (Σw)_i = target_risk / N
其中 Σ 是协方差矩阵
需要 scipy.optimize
```

### KellySizer
```
f* = (p * b - q) / b
其中 p = 胜率, b = 赔率, q = 1 - p
实际使用半凯利：f = f* / 2
```

### MaxSharpeSizer
```
求解：max (w^T μ - rf) / sqrt(w^T Σ w)
约束：Σw = 1, w >= 0
需要 scipy.optimize
```

## VaR 计算方法

### 历史模拟法
```
VaR_α = -Percentile(returns, α)
```

### 参数法
```
VaR_α = -(μ + z_α * σ)
其中 z_α 是标准正态分位数
```

### Monte Carlo
```
1. 估计收益率分布参数
2. 模拟 N 条路径（默认 10000）
3. VaR_α = -Percentile(simulated_returns, α)
```

## 压力测试场景

| 场景 | 描述 | 历史参照 |
|------|------|----------|
| market_crash | 全市场暴跌 | 2015年股灾、2020年疫情 |
| rate_spike | 利率快速上升 | 2022年债灾 |
| credit_event | 信用事件冲击 | 某大型企业违约 |
| liquidity_crisis | 流动性枯竭 | 成交量骤降 80% |
| sector_rotation | 板块极端轮动 | 行业指数单日涨跌 > 5% |

## 与现有系统的集成

现有 `config.yaml` 中的 `risk` 配置保持兼容，新增字段有默认值：

```yaml
risk:
  # 现有字段（保持不变）
  max_position_pct: 0.10
  stop_loss_pct: -0.15
  max_drawdown_pct: -0.10

  # 新增字段
  max_sector_pct: 0.30
  max_correlation: 0.8
  position_sizer: equal_weight
  var_confidence: 0.95
  var_limit_pct: 0.05
  recovery_mode: gradual
  trailing_stop: false
```

现有 BacktestEngine 中的 `_check_stop_loss` 和回撤检查逻辑将委托给 RiskEngine。
