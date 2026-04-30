## ADDED Requirements

### Requirement: Recommender 推荐引擎

系统 SHALL 提供 Recommender，对比目标持仓与当前持仓，生成人类可读的操作建议。

#### Scenario: 生成调仓建议

- **WHEN** 目标持仓为 [A, B, C]，当前持仓为 [B, D]
- **THEN** 系统 SHALL 生成：买入 A 和 C，卖出 D，持有 B

#### Scenario: 无需调仓

- **WHEN** 目标持仓与当前持仓完全相同
- **THEN** 系统 SHALL 输出"无需调仓，继续持有"

#### Scenario: 输出格式包含关键信息

- **WHEN** 生成买入建议
- **THEN** 每条建议 SHALL 包含：转债名称、代码、当前价格、双低值、溢价率、信用评级

### Requirement: 本地持仓记录

系统 SHALL 在 `data/portfolio.json` 中维护当前持仓列表。

#### Scenario: 记录买入

- **WHEN** 用户确认执行买入操作
- **THEN** 系统 SHALL 在 portfolio.json 中新增该标的记录

#### Scenario: 记录卖出

- **WHEN** 用户确认执行卖出操作
- **THEN** 系统 SHALL 从 portfolio.json 中移除该标的记录
