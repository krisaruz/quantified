## ADDED Requirements

### Requirement: FilterChain 可配置过滤器链

系统 SHALL 提供 FilterChain，按配置规则逐层过滤全市场转债截面 DataFrame。每个过滤器 MUST 是独立函数，可通过配置开关启用或禁用。

内置过滤器：
1. **exclude_delisted**: 排除 status != ACTIVE
2. **exclude_st**: 排除 is_st=True 的正股对应转债
3. **min_issue_size**: 排除发行规模 < 阈值
4. **min_remaining_years**: 排除剩余期限 < 阈值
5. **max_price**: 排除当前价格 > 阈值
6. **min_credit_rating**: 排除信用评级低于阈值
7. **exclude_redeeming**: 排除 status=REDEEM_WARNING
8. **exclude_suspended**: 排除 trade_available=False

#### Scenario: 正常过滤流程

- **WHEN** 全市场 500 只转债经过 FilterChain 处理
- **THEN** 每个启用的过滤器 SHALL 依次执行，输出缩减后的 DataFrame

#### Scenario: 过滤审计日志

- **WHEN** FilterChain 执行完毕
- **THEN** 系统 SHALL 返回每步的过滤记录（过滤器名称、过滤前数量、过滤后数量、被过滤的标的列表）

#### Scenario: 所有过滤器禁用

- **WHEN** 配置中所有过滤器均禁用
- **THEN** FilterChain SHALL 返回原始 DataFrame 不做任何修改
