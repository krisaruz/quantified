## ADDED Requirements

### Requirement: 数据过期提醒

系统 SHALL 在数据过期时显示明显警告。

#### Scenario: 数据过期警告条

- **WHEN** `/health` 返回 `data_stale: true`
- **THEN** Header 同步信息区域 SHALL 显示黄色警告条："数据已过期 X 天，请运行 quantified sync"
- **AND** 健康指示点 SHALL 变为黄色

### Requirement: 回测确认对话框

系统 SHALL 在运行回测前要求用户确认。

#### Scenario: 回测确认

- **WHEN** 用户点击"运行回测"按钮
- **THEN** 系统 SHALL 显示确认对话框，内容为："即将回测 2024-01-01 至 2026-05-03（约 XXX 交易日），确认继续？"
- **AND** 用户点击"确认"后才开始回测

### Requirement: 状态持久化

系统 SHALL 在页面刷新后恢复用户状态。

#### Scenario: Tab 状态恢复

- **WHEN** 用户刷新页面
- **THEN** 系统 SHALL 从 sessionStorage 恢复上次的 Tab 选择

#### Scenario: 排序状态恢复

- **WHEN** 用户刷新页面
- **THEN** 系统 SHALL 从 sessionStorage 恢复全市场表格的排序状态

#### Scenario: 主题偏好恢复

- **WHEN** 用户刷新页面
- **THEN** 系统 SHALL 从 localStorage 恢复主题偏好（深色/浅色）

### Requirement: CSV 文件名改进

系统 SHALL 导出带有前缀和时间戳的 CSV 文件。

#### Scenario: 导出文件命名

- **WHEN** 用户导出 CSV
- **THEN** 文件名 SHALL 为 `quantified_{type}_{date}.csv` 格式
- **EXAMPLE** `quantified_universe_2026-05-03.csv`

### Requirement: API 日期参数校验

系统 SHALL 校验 API 日期参数格式。

#### Scenario: 无效日期参数

- **WHEN** 请求 `/api/universe?date=invalid-date`
- **THEN** 系统 SHALL 返回 400 错误，消息为 "日期格式无效，请使用 YYYY-MM-DD 格式"

### Requirement: 快捷键帮助浮层

系统 SHALL 提供快捷键帮助。

#### Scenario: 显示快捷键帮助

- **WHEN** 用户按下 `?` 键（非输入框焦点时）
- **THEN** 系统 SHALL 显示快捷键帮助浮层，列出所有可用快捷键
- **AND** 用户按 `Esc` 或点击浮层外部关闭

### Requirement: 修复 debug 模式

系统 SHALL 默认关闭 Flask debug 模式。

#### Scenario: 生产模式运行

- **WHEN** 用户运行 `quantified web`
- **THEN** Flask SHALL 以 `debug=False` 模式运行
- **AND** 不暴露 Werkzeug 调试器