## ADDED Requirements

### Requirement: Favicon

系统 SHALL 在浏览器标签页显示 Favicon。

#### Scenario: Favicon 显示

- **WHEN** 用户访问任何页面
- **THEN** 浏览器标签页 SHALL 显示紫色圆角方块背景 + 白色 "Q" 字母的 Favicon

### Requirement: 骨架屏加载状态

系统 SHALL 在数据加载时显示骨架屏动画，而非转圈 spinner。

#### Scenario: 表格加载骨架屏

- **WHEN** 表格数据正在加载中
- **THEN** 表格体 SHALL 显示若干行骨架行，每行包含若干灰度渐变的矩形块
- **AND** 矩形块 SHALL 有 shimmer 动画（从右向左流动的高光）

### Requirement: 空状态插图

系统 SHALL 在数据为空时显示 SVG 插图，而非 emoji。

#### Scenario: 持仓为空

- **WHEN** 用户查看持仓页面且无持仓
- **THEN** 页面 SHALL 显示 SVG 插图（文档/文件夹图标）+ "暂无持仓" 文字

#### Scenario: 无数据

- **WHEN** 数据库无转债数据
- **THEN** Dashboard Top 10 表格 SHALL 显示 SVG 插图 + "暂无数据，请先运行数据同步"

### Requirement: 统计卡片色条

系统 SHALL 在统计卡片顶部显示强调色条。

#### Scenario: 卡片色条默认显示

- **WHEN** 统计卡片渲染时
- **THEN** 卡片顶部 SHALL 显示 2px 高的色条（绿色/红色/蓝色/紫色根据卡片类型）
- **AND** hover 时色条 SHALL 更亮或更粗

### Requirement: Tab 切换动画

系统 SHALL 在 Tab 切换时显示流畅的过渡动画。

#### Scenario: 切换到新 Tab

- **WHEN** 用户点击另一个 Tab
- **THEN** 当前面板 SHALL 淡出（opacity 1→0, transform translateY(0)→translateY(-6px)）
- **AND** 新面板 SHALL 淡入（opacity 0→1, transform translateY(6px)→translateY(0)）

### Requirement: 响应式断点

系统 SHALL 在不同屏幕宽度下自适应布局。

#### Scenario: 平板视图 (≤1024px)

- **WHEN** 屏幕宽度 ≤ 1024px
- **THEN** 统计卡片网格 SHALL 变为 3 列
- **AND** 操作卡片 SHALL 更紧凑

#### Scenario: 手机视图 (≤480px)

- **WHEN** 屏幕宽度 ≤ 480px
- **THEN** 统计卡片网格 SHALL 变为 2 列
- **AND** Tab 标签 SHALL 更小
- **AND** 搜索框和日期选择器 SHALL 宽度 100%

### Requirement: 滚动条美化

系统 SHALL 显示与深色主题协调的滚动条。

#### Scenario: 深色滚动条

- **WHEN** 页面内容超出容器高度
- **THEN** 滚动条 SHALL 显示为深色细条（宽度 6px，颜色 var(--surface3)）
- **AND** 滚动条滑块 SHALL 在 hover 时变亮（颜色 var(--border-hover)）