## ADDED Requirements

### Requirement: 深浅模式切换

系统 SHALL 支持深色和浅色两种主题。

#### Scenario: 切换到浅色模式

- **WHEN** 用户点击 Header 右上角的主题切换按钮
- **THEN** 系统 SHALL 切换到浅色主题
- **AND** 背景变为浅色（#f8f9fa），文字变为深色
- **AND** 所有卡片和组件颜色 SHALL 相应调整

#### Scenario: 主题偏好持久化

- **WHEN** 用户切换主题
- **THEN** 偏好 SHALL 存储到 localStorage
- **AND** 下次访问时自动应用

### Requirement: 数据过期 Tab 角标

系统 SHALL 在 Tab 上显示数据过期指示。

#### Scenario: 过期角标显示

- **WHEN** 数据过期超过 3 天
- **THEN** Dashboard Tab 右上角 SHALL 显示红色小圆点

### Requirement: 盈亏数字发光效果

系统 SHALL 给盈亏数字添加微妙的发光效果。

#### Scenario: 盈利数字发光

- **WHEN** 显示盈利数值
- **THEN** 数字 SHALL 有微弱的绿色 text-shadow 发光效果

#### Scenario: 亏损数字发光

- **WHEN** 显示亏损数值
- **THEN** 数字 SHALL 有微弱的红色 text-shadow 发光效果

### Requirement: 交易历史记录

系统 SHALL 记录所有交易并提供查询。

#### Scenario: 交易历史存储

- **WHEN** 用户执行买入或卖出操作
- **THEN** 系统 SHALL 追加一条记录到 `data/portfolio_history.jsonl`
- **AND** 记录包含：时间戳、操作类型、代码、名称、价格、数量、费用

#### Scenario: 交易历史查询

- **WHEN** 用户访问 Portfolio Tab
- **THEN** 页面 SHALL 显示"交易历史"折叠区
- **AND** 展开后显示最近 50 条交易记录

### Requirement: 回测进度条

系统 SHALL 在回测运行时显示进度指示。

#### Scenario: 回测进度显示

- **WHEN** 回测正在运行
- **THEN** 按钮 SHALL 变为禁用状态
- **AND** 按钮文字变为"回测中..."
- **AND** 旁边 SHALL 显示不确定进度条动画（来回流动的条）