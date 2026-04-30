## ADDED Requirements

### Requirement: YAML 配置文件结构

系统 SHALL 从项目根目录的 `config.yaml` 加载策略配置。配置文件 MUST 包含以下三个顶级段：

- `strategy`: 策略参数（名称、持仓数量、轮动频率）
- `filters`: 过滤规则开关和阈值
- `risk`: 风控参数（仓位上限、止损线、最大回撤）
- `capital`: 资金参数（初始资金）

#### Scenario: 加载合法配置文件

- **WHEN** `config.yaml` 存在且内容合法
- **THEN** 系统 SHALL 返回类型安全的配置对象（Pydantic Model）

#### Scenario: 配置文件缺失时使用默认值

- **WHEN** `config.yaml` 不存在
- **THEN** 系统 SHALL 使用内置默认配置（hold_count=10, rebalance_day=friday 等）

#### Scenario: 配置项类型错误

- **WHEN** `config.yaml` 中 `hold_count` 不是整数
- **THEN** 系统 SHALL 抛出明确的校验错误信息，指出具体字段和期望类型
