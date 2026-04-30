## Context

Phase A（数据层）和 Phase A+（可用性层）完成后，系统具备：历史数据存储、全市场截面扫描、过滤器链、用户配置。回测引擎在此基础上模拟历史交易，验证策略有效性。

核心约束回顾：
- **无未来函数**：T 日决策只用 T 日及之前数据，T+1 日执行
- **T+1 结算**：今日买入冻结，次日可卖
- **日频批处理**：每个交易日收盘后运行一次

## Goals / Non-Goals

**Goals:**
- 严格模拟日频交易流程：事件检测 → 策略信号 → 撮合成交 → 结算
- T+1 持仓状态机（available / frozen 双状态）
- 完整的绩效指标报告
- 与实盘使用完全相同的配置和过滤器

**Non-Goals:**
- 不支持分钟级或 tick 级回测
- 不支持做空或融券
- 不优化运行速度（日频数据量可接受）

## Decisions

### D1: 回测主循环架构

```
for each trading_day in [start_date ... end_date]:
    1. 日初结算：frozen_volume → available_volume
    2. 事件检测：强赎/退市 → 生成强制卖出指令
    3. 策略执行：align_universe → filter → rank → target_portfolio
    4. 信号生成：diff(target, current) → buy/sell orders
    5. 撮合成交：按当日收盘价（或次日开盘价）模拟成交
    6. 日终记账：更新持仓、资金、净值
```

### D2: 撮合价格 — 次日开盘价

为严格遵守"无未来函数"：T 日收盘后生成信号，T+1 日按开盘价成交。若 T+1 日开盘价缺失（停牌），则该订单取消。

### D3: 虚拟账户 — 双状态持仓

```python
class Position:
    cb_code: str
    available_volume: int   # 前日及之前买入，今日可卖
    frozen_volume: int      # 今日买入，今日不可卖
    avg_cost: float         # 持仓均价
```

每日结算时：`available_volume += frozen_volume; frozen_volume = 0`

### D4: 绩效指标

- 总收益率、年化收益率
- 最大回撤、最大回撤区间
- 夏普比率（无风险利率按 2% 年化）
- 总换手次数、年均换手次数
- 总交易费用

## Risks / Trade-offs

- **[回测与实盘偏差]** → 回测用收盘价/开盘价，实盘可能成交在不同价格。缓解：加滑点参数（默认 0.1%）。
- **[数据缺失导致跳日]** → 某些交易日数据不完整。缓解：遇到数据缺失的日期跳过，不生成信号。
