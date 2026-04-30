## ADDED Requirements

### Requirement: VirtualAccount 虚拟账户

系统 SHALL 提供 `VirtualAccount` 类管理回测期间的资金和持仓。

#### Scenario: 初始化账户

- **WHEN** 创建 VirtualAccount(initial_capital=100000)
- **THEN** 账户可用资金 SHALL 为 100000，持仓列表为空

#### Scenario: 买入操作

- **WHEN** 按 102.5 元买入 10 张某转债
- **THEN** 可用资金 SHALL 减少 1025 元 + 交易费用
- **THEN** 该转债 frozen_volume SHALL 增加 10（当日不可卖）

#### Scenario: T+1 日初结算

- **WHEN** 新交易日开始执行日初结算
- **THEN** 所有持仓的 frozen_volume SHALL 转移到 available_volume
- **THEN** frozen_volume SHALL 归零

#### Scenario: 卖出只能卖 available

- **WHEN** 某转债 available_volume=5, frozen_volume=10，尝试卖出 8 张
- **THEN** 系统 SHALL 拒绝，最多只能卖出 5 张（available_volume）

### Requirement: 交易费用计算

系统 SHALL 按配置的费率计算交易费用（默认万分之 2）。

#### Scenario: 买入扣费

- **WHEN** 买入金额为 1025 元，费率为 0.0002
- **THEN** 交易费用 SHALL 为 max(1025 × 0.0002, 0.1) = 0.205 元（最低 0.1 元）
