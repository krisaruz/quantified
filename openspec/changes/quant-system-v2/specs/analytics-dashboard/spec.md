# Analytics Dashboard Spec

## 概述

分析仪表盘提供深度绩效分析、归因分析、基准对比和自动报告生成功能。

## 核心指标扩展

在现有 `PerformanceStats` 基础上新增：

| 指标 | 公式 | 说明 |
|------|------|------|
| Sortino Ratio | (R - rf) / σ_downside | 仅惩罚下行波动 |
| Calmar Ratio | R_annual / MaxDrawdown | 收益/回撤比 |
| Information Ratio | (R_p - R_b) / TE | 超额收益/跟踪误差 |
| Omega Ratio | Σmax(R-rf,0) / Σmax(rf-R,0) | 收益/损失比 |
| Max Drawdown Duration | 从回撤开始到恢复的天数 | 回撤持续时间 |
| Recovery Factor | TotalReturn / MaxDrawdown | 收益/最大回撤 |
| Tail Ratio | P95 / P5 | 收益分布尾部比 |
| Common Sense Ratio | TailRatio * WinRate | 综合指标 |

## Brinson 归因模型

### 单期归因
```
配置效应 = Σ(wp,i - wb,i) × (Rb,i - Rb)
选股效应 = Σwb,i × (Rp,i - Rb,i)
交互效应 = Σ(wp,i - wb,i) × (Rp,i - Rb,i)
总超额 = 配置效应 + 选股效应 + 交互效应
```

### 多期归因（Carino 方法）
```
k_t = ln(1 + R_t) / R_t          # Carino 因子
K = ln(1 + R_total) / R_total

调整后各效应 = Σ(k_t / K) × 效应_t
```

### 归因输出
```python
@dataclass
class BrinsonResult:
    total_excess_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    by_sector: dict[str, SectorAttribution]   # 按行业分解
    by_period: list[PeriodAttribution]         # 按时间分解
```

## 基准管理

### 内置基准
- 中证转债指数 (000832.CSI)
- 沪深300 (000300.SH)
- 自定义基准（用户提供净值序列）

### 基准数据获取
```python
class BenchmarkManager:
    def get_benchmark(self, name: str, start: str, end: str) -> pd.Series:
        """获取基准净值序列"""

    def align_with_portfolio(
        self, portfolio_returns: pd.Series, benchmark_returns: pd.Series
    ) -> tuple[pd.Series, pd.Series]:
        """对齐组合和基准的日期"""
```

## 回撤分析

### 回撤区间检测
```python
@dataclass
class DrawdownPeriod:
    start_date: str         # 回撤开始
    trough_date: str        # 最低点
    end_date: str | None    # 恢复日期（未恢复为 None）
    depth: float            # 最大回撤幅度
    duration_days: int      # 持续天数
    recovery_days: int | None  # 恢复天数
```

### 水下曲线
```
underwater_i = (NV_i - Peak_i) / Peak_i
```

## 因子暴露分析

```python
@dataclass
class FactorExposure:
    factors: list[str]              # 因子名称
    exposures: list[float]          # 各因子暴露度
    returns_contribution: list[float]  # 各因子对收益的贡献
    t_statistics: list[float]       # 统计显著性
```

计算方法：横截面回归
```
R_i = α + β_1 * F_1,i + β_2 * F_2,i + ... + ε_i
```

## 报告模板

### 月度报告内容
1. 本月收益率 vs 基准
2. 持仓变动汇总
3. Top 5 贡献标的 / Bottom 5
4. 行业配置变动
5. 风险指标变化
6. 下月展望

### 报告格式
- Markdown：适合 CLI 输出和飞书文档
- HTML：适合 Web 展示（含图表）

## Web API 接口

```
GET /api/v2/analytics/metrics?portfolio={name}&start={date}&end={date}
GET /api/v2/analytics/attribution?portfolio={name}&start={date}&end={date}
GET /api/v2/analytics/drawdown?portfolio={name}
GET /api/v2/analytics/factor-exposure?portfolio={name}&date={date}
GET /api/v2/analytics/benchmark-comparison?portfolio={name}&benchmark={name}
GET /api/v2/analytics/report?portfolio={name}&period=monthly&year=2025&month=3
```

## 图表数据接口

为前端提供 JSON 格式的图表数据：

```python
class ChartData:
    @staticmethod
    def equity_curve(snapshots, benchmark=None) -> dict:
        """净值曲线"""

    @staticmethod
    def drawdown_curve(snapshots) -> dict:
        """水下曲线"""

    @staticmethod
    def monthly_returns_heatmap(snapshots) -> dict:
        """月度收益热力图"""

    @staticmethod
    def position_heatmap(holdings_history) -> dict:
        """持仓热力图"""

    @staticmethod
    def factor_radar(exposure) -> dict:
        """因子暴露雷达图"""

    @staticmethod
    def sector_pie(holdings, market_data) -> dict:
        """行业饼图"""
```
