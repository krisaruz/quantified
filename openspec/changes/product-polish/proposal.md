## Why

Quantified 功能完整但视觉和体验停留在"原型"阶段：加载时只有转圈 spinner、空状态用 emoji 代替、没有 favicon、缺少深浅模式、回测图表粗糙、无交易历史、后端有竞态和安全隐患。用户希望交付的是一款**精致的产品**，而不只是一个能跑的项目。

## What Changes

5 个阶段共 25 项改进：

1. **视觉基础**（7 项）：Favicon、骨架屏、空状态 SVG 插图、统计卡片色条增强、Tab 切换动画、响应式断点、滚动条美化
2. **UX 完整性**（7 项）：数据过期提醒、回测确认对话框、状态持久化、CSV 文件名改进、API 日期校验、debug=True 修复、快捷键帮助浮层
3. **仪表板可视化**（3 项）：资产配置饼图、过滤漏斗可视化、回测图表增强
4. **精致打磨**（5 项）：深浅模式切换、数据过期 Tab 角标、盈亏数字发光、交易历史记录、回测进度条
5. **后端加固**（3 项）：Portfolio 文件竞态修复、回测超时处理、孤立代码文档化

## Capabilities

### New Capabilities

- `visual-foundation`: 视觉基础设施（Favicon、骨架屏、空状态、卡片增强、动画、响应式、滚动条）
- `ux-completeness`: UX 功能完整性（过期提醒、确认对话框、状态持久化、CSV 改进、日期校验、快捷键帮助）
- `dashboard-viz`: 仪表板数据可视化（资产饼图、过滤漏斗、图表增强）
- `delight-polish`: 精致打磨（深浅模式、角标、发光效果、交易历史、进度条）
- `backend-hardening`: 后端安全加固（原子写入、超时处理、文档化）

### Modified Capabilities

- `cli-interface`: 修复 `quantified web` 默认 debug=False
- `web-api`: 新增 `/api/portfolio/history` 端点、日期参数校验

## Impact

- **主改文件**：`src/quantified/web/templates/index.html`（~80% 变更量）
- **次改文件**：`src/quantified/web/app.py`（日期校验、交易历史端点、debug 修复）
- **次改文件**：`src/quantified/portfolio.py`（原子写入、交易记录日志）
- **无新依赖**：所有前端改动均为原生 CSS/JS/Canvas
- **无数据库迁移**：交易历史使用 JSONL 文件追加写入
