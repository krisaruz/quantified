## Why

在用真金白银交易之前，必须用历史数据验证策略的有效性。回测引擎让用户看到"如果过去 3 年按这个策略操作，结果会怎样"，是建立信心的核心工具。没有回测就上实盘，等同于盲目赌博。

回测引擎依赖 Phase A 的历史数据 + Phase A+ 的过滤器和配置，是系统从"数据工具"进化为"可用交易系统"的最后关键一步。

## What Changes

- 新增回测引擎模块，模拟历史日期逐日执行策略（配置加载 → 过滤 → 排序 → 调仓 → 撮合 → 结算）
- 新增虚拟账户模型（资金、持仓、冻结头寸），严格执行 T+1 结算
- 新增撮合引擎，按次日开盘价模拟成交
- 新增绩效统计（总收益率、年化收益、最大回撤、夏普比率、换手次数、交易费用）
- CLI 新增 `quantified backtest` 子命令

## Capabilities

### New Capabilities

- `backtest-core`: 回测引擎核心（日期循环 + 事件检测 + 策略执行 + 撮合 + 结算）
- `virtual-account`: 虚拟账户模型（资金管理、T+1 持仓状态机、交易费用计算）
- `performance-stats`: 回测绩效统计与报告输出（收益率/回撤/夏普/换手率/交易费用）

### Modified Capabilities

- `cli-interface`: 新增 `backtest` 子命令

## Impact

- **新增模块**：`src/quantified/backtest/`（engine.py, account.py, stats.py）
- **复用模块**：DataAligner（数据对齐）、FilterChain（过滤）、Config（配置）
- **计算量**：3 年回测约需处理 ~750 个交易日 × ~500 只转债 = 37.5 万次截面计算，预计运行时间 1~5 分钟
