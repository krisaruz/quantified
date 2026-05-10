## ADDED Requirements

### Requirement: 资产配置饼图

系统 SHALL 在 Dashboard 显示资产配置可视化。

#### Scenario: 资产配置展示

- **WHEN** 用户查看 Dashboard
- **THEN** 统计卡片区域 SHALL 显示一个小型 Canvas 饼图
- **AND** 饼图 SHALL 展示现金占比（灰色）和持仓占比（紫色）
- **AND** 鼠标悬停 SHALL 显示具体数值

### Requirement: 过滤漏斗可视化

系统 SHALL 在 Dashboard 显示过滤漏斗。

#### Scenario: 漏斗展示

- **WHEN** 用户查看 Dashboard
- **THEN** 在统计卡片下方 SHALL 显示紧凑的水平条形漏斗
- **AND** 每个条形 SHALL 对应一个过滤器步骤
- **AND** 条形宽度 SHALL 按比例反映通过数量
- **AND** 鼠标悬停 SHALL 显示过滤器名称和数量变化

### Requirement: 回测图表增强

系统 SHALL 提供更完善的回测图表交互。

#### Scenario: 十字光标线

- **WHEN** 用户鼠标悬停在回测图表上
- **THEN** 图表 SHALL 显示垂直虚线光标线，贯穿净值曲线区域

#### Scenario: 触摸事件支持

- **WHEN** 用户在触摸设备上滑动回测图表
- **THEN** tooltip SHALL 跟随触摸点移动

#### Scenario: 入场动画

- **WHEN** 回测结果加载完成
- **THEN** 净值曲线 SHALL 有从左到右的绘制动画（约 0.8 秒）