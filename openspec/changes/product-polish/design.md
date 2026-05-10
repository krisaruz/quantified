## Context

系统已具备完整功能：数据同步、全市场截面、过滤排序、调仓建议、持仓管理、回测引擎、Web 仪表板。但当前 UI 给人"原型"感——缺少视觉润色、UX 细节和产品级打磨。

核心约束：
- **单文件前端**：保持 `index.html` 单文件结构，不引入框架
- **零新依赖**：所有前端改动均为原生 CSS/JS/Canvas
- **中文 UI**：所有新增文本保持中文
- **向后兼容**：不破坏现有 API 契约

## Goals / Non-Goals

**Goals:**
- 让 UI 看起来像"交付的产品"而非"能跑的项目"
- 填补让用户感到"未完成"的功能缺口
- 增加数据可视化维度，减少"只有数字"的页面
- 修复后端竞态和安全隐患

**Non-Goals:**
- 不引入前端框架（React/Vue/Angular）
- 不拆分 index.html 为多文件
- 不做用户认证/权限系统（本地工具）
- 不做国际化（仅中文）
- 不做数据库迁移（交易历史用 JSONL）

## Decisions

### D1: 骨架屏替代 Spinner

用 CSS shimmer 动画的骨架行替代表格中的转圈 spinner。骨架行宽度按各列典型宽度比例设定，让用户预知数据布局。

### D2: 深浅模式 — CSS 变量切换

利用已有 `:root` 变量体系，新增 `[data-theme="light"]` 选择器覆盖颜色变量。通过 JS 切换 `<html>` 的 `data-theme` 属性。偏好存 `localStorage`。

### D3: 交易历史 — JSONL 追加写入

每次 buy/sell 操作追加一条 JSON 行到 `data/portfolio_history.jsonl`。不做数据库迁移，简单可靠。Web 端新增 `/api/portfolio/history` 读取最近 N 条。

### D4: Portfolio 原子写入

用 `tempfile.NamedTemporaryFile` + `os.replace` 替代直接 `json.dump` 到目标文件，避免并发写入损坏。

### D5: 回测图表增强

在现有 Canvas 绘制逻辑中添加：十字光标线（垂直虚线）、触摸事件支持（touchmove）、净值曲线入场动画（从左到右逐步绘制）。

## Risks / Trade-offs

- **[index.html 文件膨胀]** → 当前 1055 行，改动后预计 ~1400 行。可接受，单文件仍是该规模项目的最佳权衡。
- **[JSONL 无索引]** → 交易历史查询需全量读取。缓解：只读最近 200 条，文件大时可轮转。
- **[浅色模式维护成本]** → 需要同步维护两套颜色。缓解：基于现有变量体系，只需覆盖 `:root` 中的 ~15 个颜色变量。
