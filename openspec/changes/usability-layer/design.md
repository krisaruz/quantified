## Context

Phase A 数据层已实现：6 张 ORM 表、AkShare 数据获取、DataAligner 对齐引擎（含 align_universe 截面扫描）。本层在数据层之上构建面向终端用户的交互层。

目标用户画像：没有金融背景的开发者，希望每周花 10 分钟运行命令即可完成调仓操作。

## Goals / Non-Goals

**Goals:**
- 用户通过修改 `config.yaml` 控制策略（持仓数量、轮动频率、过滤条件、风控参数）
- 用户通过 `quantified recommend` 获取人话操作建议
- 过滤器链可灵活组合，每个过滤器独立且可开关
- 本地持仓记录跟踪实际买入状态

**Non-Goals:**
- 不涉及自动下单（用户手动在券商 APP 下单）
- 不涉及回测引擎（Phase B）
- 不涉及 Web UI

## Decisions

### D1: 配置文件格式 — YAML + Pydantic 校验

使用 YAML 作为配置文件，用 Pydantic BaseModel 做类型校验。配置项分三级：strategy / filters / risk。

### D2: FilterChain — 函数列表 + 日志审计

每个过滤器是一个 `(DataFrame, Config) -> DataFrame` 纯函数。FilterChain 按配置顺序依次执行，并记录每步过滤前后的数量变化，用于 `filter-check` 命令展示。

### D3: 持仓记录 — JSON 文件

`data/portfolio.json` 记录当前持仓列表（cb_code, buy_date, buy_price, volume）。选择 JSON 而非数据库表，是因为本阶段持仓管理极简（手动录入/自动追踪），后续 Phase B 会引入正式的 Account/Position ORM 表。

### D4: CLI — Click 库

使用 Click 构建 CLI，四个子命令：sync / recommend / status / filter-check。

## Risks / Trade-offs

- **[持仓记录与实际不同步]** → JSON 文件依赖用户按建议执行。缓解：recommend 输出时提示用户确认。
- **[过滤条件过严导致无标的]** → 缓解：filter-check 命令展示每步剩余数量，用户可调整。
