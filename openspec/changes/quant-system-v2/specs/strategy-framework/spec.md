# Strategy Framework Spec

## 概述

策略框架是系统的核心扩展点，通过 Protocol 定义策略接口，支持动态注册、组合和版本管理。

## 数据模型

### Signal（策略信号）
```python
@dataclass(frozen=True)
class Signal:
    cb_code: str
    direction: str          # "buy" | "sell" | "hold"
    weight: float           # 0.0 ~ 1.0，目标仓位权重
    score: float            # 策略评分（越高越优先）
    reason: str             # 信号原因
    metadata: dict = field(default_factory=dict)  # 策略特定数据
```

### StrategyContext（策略上下文）
```python
@dataclass
class StrategyContext:
    date: str
    universe: pd.DataFrame          # 全市场截面
    portfolio: Portfolio            # 当前持仓
    market_history: pd.DataFrame    # 历史行情（用于动量等）
    config: AppConfig
```

## Protocol 定义

### IStrategy
```python
class IStrategy(Protocol):
    name: str
    version: str
    description: str

    def generate_signals(
        self, context: StrategyContext
    ) -> list[Signal]:
        """生成交易信号"""
        ...

    def get_parameters(self) -> dict:
        """返回当前参数快照"""
        ...

    def set_parameters(self, params: dict) -> None:
        """更新参数"""
        ...
```

### IFactor
```python
class IFactor(Protocol):
    name: str
    category: str   # "value" | "momentum" | "quality" | "technical"
    description: str

    def compute(self, df: pd.DataFrame) -> pd.Series:
        """计算因子值，返回与 df 同 index 的 Series"""
        ...

    def compute_single(self, row: pd.Series) -> float:
        """计算单行因子值"""
        ...
```

## 注册机制

```python
# 使用装饰器注册策略
@StrategyRegistry.register("double_low")
class DoubleLowStrategy:
    ...

# 使用装饰器注册因子
@FactorRegistry.register("momentum_20d", category="momentum")
class Momentum20dFactor:
    ...
```

## 策略组合器

### 加权融合模式
```python
class WeightedCompositeStrategy:
    def generate_signals(self, context):
        all_signals = {}
        for strategy, weight in self.strategies:
            signals = strategy.generate_signals(context)
            for sig in signals:
                key = (sig.cb_code, sig.direction)
                if key not in all_signals:
                    all_signals[key] = []
                all_signals[key].append((sig, weight))

        # 加权合并
        merged = []
        for (code, direction), pairs in all_signals.items():
            avg_score = sum(s.score * w for s, w in pairs) / sum(w for _, w in pairs)
            total_weight = sum(w for _, w in pairs)
            merged.append(Signal(
                cb_code=code, direction=direction,
                weight=total_weight, score=avg_score,
                reason=f"组合策略({len(pairs)}个子策略)",
            ))
        return sorted(merged, key=lambda s: s.score, reverse=True)
```

### 投票机制模式
```python
class VotingCompositeStrategy:
    """多数投票：超过半数策略同意才生成信号"""
    threshold: float = 0.5
```

## 策略版本管理

每次策略参数变更时，自动保存快照：

```python
@dataclass
class StrategyVersion:
    strategy_name: str
    version: str            # semver
    parameters: dict
    created_at: datetime
    description: str
    backtest_result: dict | None  # 关联的回测结果
```

## 配置格式

```yaml
strategy:
  name: composite
  version: "1.0.0"
  strategies:
    - name: double_low
      weight: 0.6
      params:
        hold_count: 10
        buffer_rank: 5
    - name: momentum
      weight: 0.4
      params:
        lookback_days: 20
        top_n: 10
  scoring:
    method: weighted_average  # weighted_average | voting | ranked
```

## 内置因子清单

| 因子名 | 类别 | 计算方式 |
|--------|------|----------|
| double_low | value | cb_close + premium_rate * 100 |
| pure_bond_premium | value | cb_close / bond_floor - 1 |
| ytm | value | 到期收益率（近似） |
| momentum_5d | momentum | 5日涨跌幅 |
| momentum_20d | momentum | 20日涨跌幅 |
| momentum_60d | momentum | 60日涨跌幅 |
| rsi_14 | technical | 14日RSI |
| volatility_20d | technical | 20日波动率 |
| turnover_rate | technical | 换手率 |
| credit_score | quality | 信用评级得分 |
| issue_size_score | quality | 发行规模得分 |
| maturity_score | quality | 剩余期限得分 |
