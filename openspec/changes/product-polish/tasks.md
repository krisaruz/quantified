## Phase 1: 视觉基础

- [x] 1.1 **Favicon** — 在 `<head>` 添加内联 SVG favicon，紫色圆角方块 + "Q" 字母
- [x] 1.2 **骨架屏** — 新增 `.skeleton-row` 和 `.skeleton` CSS，用 shimmer 动画替代表格中的 spinner
- [x] 1.3 **空状态插图** — 将 emoji 空状态（📭、📊、✨、📈）替换为内联 SVG 插图
- [x] 1.4 **统计卡片色条** — 完善 `.stat-card::before` 样式，让顶部的色条默认显示（非 hover 时也有）
- [x] 1.5 **Tab 切换动画** — 改进 `.panel.active` 动画，添加淡出效果，使切换更流畅
- [x] 1.6 **响应式断点** — 新增 `@media(max-width:1024px)` 和 `@media(max-width:480px)` 断点
- [x] 1.7 **滚动条美化** — 添加 `::-webkit-scrollbar` 系列样式

## Phase 2: UX 完整性

- [x] 2.1 **数据过期提醒** — 在 Header 显示黄色警告条（利用 `/health` 的 `data_stale` 字段）
- [x] 2.2 **回测确认对话框** — 点击"运行回测"时先显示日期范围确认对话框
- [x] 2.3 **状态持久化** — Tab 选择和排序状态存 `sessionStorage`，主题偏好存 `localStorage`
- [x] 2.4 **CSV 文件名改进** — 导出文件名加 `quantified_` 前缀和时间戳
- [x] 2.5 **API 日期参数校验** — 在 `/api/universe`、`/api/recommendation`、`/api/portfolio`、`/api/backtest` 添加日期格式校验
- [x] 2.6 **修复 debug=True** — 在 `app.py` 将 `debug=True` 改为 `debug=False`
- [x] 2.7 **快捷键帮助浮层** — 按 `?` 键显示快捷键帮助浮层，按 `Esc` 关闭

## Phase 3: 仪表板可视化

- [x] 3.1 **资产配置饼图** — 在 Dashboard 添加小型 Canvas 饼图，显示现金 vs 持仓占比
- [x] 3.2 **过滤漏斗可视化** — 在 Dashboard 添加紧凑的水平条形漏斗
- [x] 3.3 **回测图表增强** — 十字光标线、触摸事件支持、入场动画

## Phase 4: 精致打磨

- [x] 4.1 **深浅模式切换** — 新增 `[data-theme="light"]` CSS 变量覆盖，Header 右上角放切换按钮
- [x] 4.2 **数据过期 Tab 角标** — 数据过期时 Dashboard Tab 显示红点
- [x] 4.3 **盈亏数字发光** — 给 `.num-green` 和 `.num-red` 加微弱 `text-shadow`
- [x] 4.4 **交易历史记录** — 新增 `portfolio_history.jsonl` 追加写入，新增 `/api/portfolio/history` 端点，Portfolio Tab 添加交易历史折叠区
- [x] 4.5 **回测进度条** — 回测运行时显示不确定进度条动画

## Phase 5: 后端加固

- [x] 5.1 **Portfolio 文件竞态修复** — 用 `tempfile.NamedTemporaryFile` + `os.replace` 实现原子写入
- [x] 5.2 **回测超时处理** — 用 threading 设置 120 秒超时
- [x] 5.3 **孤立代码文档化** — 在 `aligner/core.py` 添加模块级 docstring 说明此模块未被使用
