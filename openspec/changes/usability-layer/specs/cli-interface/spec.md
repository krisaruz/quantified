## ADDED Requirements

### Requirement: CLI 命令行入口

系统 SHALL 提供 `quantified` 命令行工具，包含四个子命令。

#### Scenario: quantified sync

- **WHEN** 用户运行 `quantified sync`
- **THEN** 系统 SHALL 执行数据同步流程（等同于 scripts/sync_data.py），并输出同步进度和结果

#### Scenario: quantified recommend

- **WHEN** 用户运行 `quantified recommend`
- **THEN** 系统 SHALL 执行：加载配置 → 获取最新截面 → 过滤 → 排序 → 对比持仓 → 输出调仓建议

#### Scenario: quantified status

- **WHEN** 用户运行 `quantified status`
- **THEN** 系统 SHALL 展示当前持仓列表、各标的最新价格和收益率、总资产概况

#### Scenario: quantified filter-check

- **WHEN** 用户运行 `quantified filter-check`
- **THEN** 系统 SHALL 展示 FilterChain 的审计日志：每步过滤器名称、过滤前后数量、被排除的标的
