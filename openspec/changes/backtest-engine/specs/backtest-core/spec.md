## ADDED Requirements

### Requirement: BacktestEngine 回测主循环

系统 SHALL 提供 `BacktestEngine`，按交易日逐日模拟策略执行。输入为日期范围和配置，输出为逐日净值序列和交易记录。

#### Scenario: 完整回测流程

- **WHEN** 调用 `BacktestEngine.run(start_date="2023-01-01", end_date="2025-12-31")`
- **THEN** 系统 SHALL 对每个交易日执行：日初结算 → 事件检测 → 策略执行 → 信号生成 → 撮合成交 → 日终记账
- **THEN** 返回 BacktestResult（含逐日净值、交易记录、绩效指标）

#### Scenario: 无未来函数保证

- **WHEN** 在 T 日执行策略
- **THEN** align_universe 和 FilterChain SHALL 仅使用 T 日及之前的数据
- **THEN** 生成的买卖订单 SHALL 在 T+1 日按开盘价撮合

#### Scenario: T+1 日停牌取消订单

- **WHEN** T 日生成买入某转债的订单，但 T+1 日该转债停牌
- **THEN** 该订单 SHALL 自动取消，资金退回可用

### Requirement: 强赎/退市事件检测

每个交易日开始时，系统 SHALL 检查持仓中是否有转债状态变为 REDEEM_WARNING 或 DELISTED。

#### Scenario: 持仓转债触发强赎

- **WHEN** 某持仓转债 status 变为 DELISTED 且当日为最后交易日
- **THEN** 系统 SHALL 在策略信号之前生成强制卖出指令，优先级高于常规信号
