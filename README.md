<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Flask-3.x-000000?style=for-the-badge&logo=flask&logoColor=white" alt="Flask" />
  <img src="https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?style=for-the-badge&logo=sqlalchemy&logoColor=white" alt="SQLAlchemy" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=for-the-badge" alt="License" />
  <img src="https://img.shields.io/badge/Tests-341+-brightgreen?style=for-the-badge&logo=pytest&logoColor=white" alt="Tests" />
</p>

<h1 align="center">VertexQuant</h1>
<h3 align="center">中国可转债量化轮动策略系统</h3>

<p align="center">
  <strong>多因子评分 · 智能风控 · T+1 回测 · 模拟交易 · Web 仪表盘</strong>
</p>

<p align="center">
  一套面向中国 A 股可转债市场的端到端量化系统，覆盖从数据采集、因子计算、策略信号生成、<br/>
  风险管理到回测验证、模拟交易的完整链路，并提供开箱即用的 Web 管理界面与 CLI 工具。
</p>

---

## ✨ 核心特性

<table>
<tr>
<td width="50%">

### 🎯 策略框架
- **双低轮动策略** — 经典 "价格+溢价率" 复合评分
- **多策略注册** — 价值、动量、复合等 5 种策略可插拔切换
- **缓冲排名机制** — 避免频繁换仓，降低交易摩擦
- **策略版本管理** — 参数快照 + 回测对比，可追溯演化

</td>
<td width="50%">

### 🛡️ 多层风控
- **仓位上限** — 单券持仓比例硬性约束
- **止损机制** — 个券止损 + 组合回撤熔断
- **行业集中度** — 防止单一行业过度暴露
- **流动性检查** — 低成交量标的自动过滤

</td>
</tr>
<tr>
<td width="50%">

### 📊 专业分析
- **风险调整指标** — Sharpe / Sortino / Calmar / Omega
- **归因分析** — Brinson 多期业绩归因（配置/选券/交互）
- **压力测试** — 市场崩盘 / 利率飙升 / 信用事件模拟
- **月度报告** — Markdown 格式自动化投资报告

</td>
<td width="50%">

### 🖥️ 交互界面
- **Web 仪表盘** — 深色/浅色主题，键盘快捷键
- **CLI 工具** — 一键同步、调仓、回测、启动服务
- **自然语言解释** — 每笔推荐附带评分因素说明
- **过滤器审计** — 完整的筛选链路可视化

</td>
</tr>
</table>

---

## 🏗️ 系统架构

```
                        ┌─────────────────────────────────────────┐
                        │              VertexQuant                 │
                        └─────────────────────────────────────────┘
                                          │
              ┌───────────────────────────┼───────────────────────────┐
              ▼                           ▼                           ▼
      ┌───────────────┐          ┌───────────────┐          ┌───────────────┐
      │   数据层       │          │   核心引擎     │          │   交互层       │
      │               │          │               │          │               │
      │ AkShare 采集   │────▶    │ 策略 → 过滤   │────▶    │ Web 仪表盘    │
      │ SQLite 存储    │         │ 评分 → 推荐   │         │ CLI 工具      │
      │ 质量检查       │         │ 风控 → 执行   │         │ REST API      │
      │ 血缘追踪       │         │ 回测 → 分析   │         │ 监控告警      │
      └───────────────┘          └───────────────┘          └───────────────┘
```

### 数据流水线

```
AkShare (东方财富 + 集思录)
    │
    ▼
[ 数据采集 ] ─→ [ 质量检查 ] ─→ [ SQLite ORM ] ─→ [ 全市场截面构建 ]
                  ├─ 价格区间                         ├─ 转股价值
                  ├─ OHLC 一致性                      ├─ 溢价率
                  ├─ 突变检测 (>30%)                   ├─ 交易可用状态
                  └─ 连续零成交                        └─ 过滤 + 排名
```

---

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/krisaruz/vertexquant.git
cd vertexquant
pip install -e .
```

### 三步启动

```bash
# ① 同步市场数据
vertexquant sync

# ② 查看今日调仓建议
vertexquant recommend

# ③ 启动 Web 管理界面
vertexquant web
```

浏览器打开 `http://localhost:5000` 即可进入管理界面。

---

## 📋 CLI 命令参考

| 命令 | 说明 | 选项 |
|------|------|------|
| `vertexquant sync` | 同步最新市场数据 | `--full` 全量同步 · `--skip-stock-history` 跳过正股历史 |
| `vertexquant recommend` | 生成今日调仓建议 | — |
| `vertexquant status` | 查看持仓与盈亏 | — |
| `vertexquant filter-check` | 查看过滤器审计链 | — |
| `vertexquant backtest` | 运行策略回测 | `--start YYYY-MM-DD` · `--end YYYY-MM-DD` |
| `vertexquant backfill` | 历史数据回填 | `--start` · `--end` · `--only-bonds` · `--only-stocks` |
| `vertexquant web` | 启动 Web 界面 | `--port` (默认 5000) |

---

## 🎯 策略体系

### 内置策略

| 策略 | 标识 | 核心逻辑 |
|------|------|----------|
| **双低轮动** | `double_low` | 价格 + 溢价率×100 复合评分，持有 Top N，缓冲带换仓 |
| **价值策略** | `value` | 40% 价格 + 30% 信用 + 30% 溢价率加权评分 |
| **动量策略** | `momentum` | 20 日动量排名，价格上限过滤 |
| **复合策略** | `composite` | 子策略加权平均 / 投票融合 |
| **遗留兼容** | `legacy` | 向后兼容旧版 `AppConfig` 参数 |

### 复合评分模型

```
总分 = 双低基础分 + 信用评级调整 + 到期时间调整 + 纯债价值调整
        │               │               │               │
        ▼               ▼               ▼               ▼
   价格+溢价率×100   AAA→0, AA+→1    短期奖励      低于面值奖励
                      …BBB-→10      长期惩罚      高于面值惩罚
```

> **分数越低越好**，系统自动生成每笔推荐的自然语言评分因素说明，对非量化背景用户友好。

---

## 🛡️ 风控引擎

### 风控规则矩阵

| 规则 | 级别 | 触发条件 | 执行动作 |
|------|------|----------|----------|
| 单券仓位上限 | 🔴 硬性 | 持仓占比 > 10% | 限制买入权重 |
| 个券止损 | 🔴 硬性 | 浮亏 ≤ -15% | 强制卖出 |
| 组合回撤熔断 | 🔴 硬性 | 回撤 ≤ -10% | 暂停全部交易 |
| 行业集中度 | 🟡 软性 | 单行业 > 30% | 告警通知 |
| 流动性约束 | 🔴 硬性 | 日成交 < 500 手 | 移除买入信号 |
| 换手率约束 | 🟡 软性 | 年化换手超限 | 告警通知 |
| VaR 限制 | 🟡 软性 | 组合 VaR > 5% | 告警通知 |
| 相关性检查 | 🟡 软性 | 两两相关 > 0.8 | 告警通知 |

### 仓位管理

| 方法 | 说明 |
|------|------|
| **等权配置** | 买入信号均分权重 |
| **Kelly 公式** | 基于胜率和赔率的半 Kelly 仓位 |
| **风险平价** | 按波动率倒数分配，低波高配 |

### VaR 与压力测试

- **VaR 模型** — 历史模拟法 / 参数法 / 蒙特卡洛
- **CVaR** — 尾部风险度量
- **压力情景** — 市场崩盘 (-8%) / 利率飙升 / 信用事件 / 流动性危机

---

## 📈 回测引擎

### 严格 T+1 回测框架

```
每日循环:
  ├─ 1. 清算：冻结持仓 → 可用（模拟 T+1 交割）
  ├─ 2. 撮合：以今日开盘价执行昨日挂单
  ├─ 3. 构建截面：当日全市场过滤 + 排名（无未来数据）
  ├─ 4. 退市检查：强制卖出已退市标的
  ├─ 5. 回撤熔断：超阈值暂停信号生成
  ├─ 6. 止损扫描：触发止损挂单
  └─ 7. 轮动调仓：排名驱动的买卖信号（仅调仓日）
```

**回测保证：** T 日生成信号 → T+1 日开盘价执行 → 无未来函数 → 滑点模型 → 佣金扣除

### 回测输出指标

| 指标 | 说明 |
|------|------|
| 总收益率 / 年化收益率 | 基于 244 交易日年化 |
| 最大回撤 | 含回撤起止日期 |
| Sharpe 比率 | 无风险利率 2% |
| 年化波动率 | 日收益标准差 × √244 |
| 胜率 / 盈亏比 | 配对买卖统计 |
| 交易次数 / 总费用 | 含佣金明细 |

---

## 📊 分析引擎

### 风险调整指标

| 指标 | 说明 |
|------|------|
| **Sortino 比率** | 仅计下行偏差，更关注亏损风险 |
| **Calmar 比率** | 年化收益 / 最大回撤 |
| **Omega 比率** | 收益 / 亏损面积比 |
| **Information 比率** | 超额收益 / 跟踪误差 |
| **Tail 比率** | 95% 分位 / 5% 分位，衡量收益分布对称性 |
| **Recovery Factor** | 总收益 / 最大回撤 |
| **Common Sense 比率** | Tail 比率 × 胜率 |

### 高级分析

| 模块 | 能力 |
|------|------|
| **回撤分析器** | 水下曲线、滚动最大回撤、恢复时间分布 |
| **基准比较** | Alpha/Beta、上行/下行捕获率、跟踪误差 |
| **Brinson 归因** | 单期/多期（Carino 链接），配置/选券/交互效应分解 |
| **图表数据** | 净值曲线、回撤图、月度热力图、因子雷达图、行业饼图 |
| **自动化报告** | Markdown 月报/年报，含 Top 盈亏明细 |

---

## 📐 因子库

### 13 个预置因子，4 大类别

<table>
<tr>
<th>类别</th>
<th>因子</th>
<th>说明</th>
</tr>
<tr>
<td rowspan="3"><strong>价值</strong></td>
<td><code>double_low</code></td>
<td>价格 + 溢价率×100</td>
</tr>
<tr>
<td><code>pure_bond_premium</code></td>
<td>(价格 - 100) / 100，纯债溢价</td>
</tr>
<tr>
<td><code>ytm_approx</code></td>
<td>近似到期收益率（票面 2%）</td>
</tr>
<tr>
<td rowspan="4"><strong>动量</strong></td>
<td><code>momentum_5d</code></td>
<td>5 日涨跌幅</td>
</tr>
<tr>
<td><code>momentum_20d</code></td>
<td>20 日涨跌幅</td>
</tr>
<tr>
<td><code>momentum_60d</code></td>
<td>60 日涨跌幅</td>
</tr>
<tr>
<td><code>rsi_14</code></td>
<td>14 日相对强弱指数</td>
</tr>
<tr>
<td rowspan="3"><strong>质量</strong></td>
<td><code>credit_score</code></td>
<td>信用评级映射（AAA=0, …, BBB-=10）</td>
</tr>
<tr>
<td><code>issue_size_score</code></td>
<td>发行规模评分</td>
</tr>
<tr>
<td><code>maturity_score</code></td>
<td>到期时间分档评分</td>
</tr>
<tr>
<td rowspan="3"><strong>技术</strong></td>
<td><code>volatility_20d</code></td>
<td>20 日滚动波动率</td>
</tr>
<tr>
<td><code>turnover_rate</code></td>
<td>成交量 / 流通盘</td>
</tr>
<tr>
<td><code>volume_price_divergence</code></td>
<td>10 日量价背离度</td>
</tr>
</table>

> 支持 **复合因子** — Z-Score 标准化 + 自定义权重线性组合，以及 `@FactorRegistry.register` 装饰器扩展自定义因子。

---

## 🔍 过滤器链

9 级过滤器按序执行，每一级记录过滤前后数量与被排除标的：

```
全市场可转债
  │
  ├─ ① 退市过滤     → 移除已退市
  ├─ ② ST 过滤      → 移除 ST 正股
  ├─ ③ 发行规模     → ≥ 2 亿元
  ├─ ④ 剩余期限     → ≥ 0.5 年
  ├─ ⑤ 价格上限     → ≤ 130 元
  ├─ ⑥ 信用评级     → ≥ AA-
  ├─ ⑦ 赎回预警     → 排除强赎期
  ├─ ⑧ 停牌过滤     → 排除不可交易
  └─ ⑨ 成交量       → ≥ 500 手
  │
  ▼
候选池（进入评分排名）
```

---

## 🖥️ Web 界面

六大功能面板，支持深色/浅色主题切换与键盘快捷键 (1-6)：

| 面板 | 功能 |
|------|------|
| **总览** | 核心指标、资金/持仓占比图、推荐摘要 |
| **全市场** | 带评分与风险等级的可转债全表 |
| **调仓建议** | 买入/卖出/持有/止损/观察动作列表 |
| **持仓管理** | 当前持仓、模拟买卖、交易历史 |
| **过滤器** | 每级过滤器审计步骤可视化 |
| **回测** | 在线回测、指标面板、净值曲线 |

### REST API

```
GET  /api/universe          全市场过滤排名数据
GET  /api/recommendation    今日调仓建议
GET  /api/portfolio         当前持仓与市值
POST /api/portfolio/buy     模拟买入
POST /api/portfolio/sell    模拟卖出
GET  /api/portfolio/history 交易历史
GET  /api/backtest          运行回测
GET  /api/config            系统配置
GET  /api/stats             统计摘要
GET  /health                健康检查
```

---

## 📡 监控告警

### 内置告警规则

| 规则 | 警告阈值 | 严重阈值 |
|------|----------|----------|
| 日收益异常 | ≤ -3% | ≤ -5% |
| 持仓集中度 | ≥ 15% | ≥ 25% |
| 数据时效性 | ≥ 3 天 | ≥ 7 天 |
| 组合回撤 | ≤ -7% | ≤ -9% |

### 通知渠道

- **日志通知** — 输出到系统日志
- **Webhook** — POST JSON 到自定义端点（支持企业微信、钉钉等）
- **组合通知** — 多渠道聚合分发

### 健康评分 (0-100)

五维加权评估：数据时效 (20%) · 持仓分散度 (20%) · 收益稳定性 (20%) · 回撤水平 (20%) · 执行状态 (20%)

---

## ⚙️ 配置参考

```yaml
# 策略配置
strategy:
  name: double_low            # 策略标识
  hold_count: 10              # 持仓数量
  rebalance_day: friday       # 调仓日 (monday-sunday)
  buffer_rank: 5              # 缓冲排名（减少频繁换仓）
  scoring:
    credit:
      unknown: 5.0            # 无评级惩罚
    maturity:
      long: -2.0              # 长期限奖励
      short: 3.0              # 短期限惩罚
      very_short: 8.0         # 极短期限惩罚
    bond_floor:
      below_par: -5.0         # 低于面值奖励
      near_par: -2.0          # 接近面值奖励
      above_scale: 0.15       # 高于面值惩罚系数

# 过滤器
filters:
  exclude_st: true            # 排除 ST 正股
  min_issue_size: 2.0         # 最小发行规模（亿元）
  min_remaining_years: 0.5    # 最小剩余期限（年）
  max_price: 130              # 最高价格（元）
  min_credit_rating: AA-      # 最低信用评级
  exclude_redeeming: true     # 排除强赎预警
  exclude_suspended: true     # 排除停牌
  min_turnover: 500           # 最低成交量（手）

# 风控参数
risk:
  max_position_pct: 0.10      # 单券最大仓位 10%
  stop_loss_pct: -0.15        # 个券止损线 -15%
  max_drawdown_pct: -0.10     # 组合回撤熔断 -10%

# 资金与费用
capital:
  initial: 100000             # 初始资金（元）
fees:
  commission_rate: 0.0002     # 佣金费率 0.02%
  min_commission: 0.1         # 最低佣金（元）
```

---

## 🗂️ 项目结构

```
vertexquant/
│
├── 📊 核心模块
│   ├── universe.py             # 全市场截面构建
│   ├── filter.py               # 9 级过滤器链
│   ├── scoring.py              # 复合评分引擎
│   ├── recommender.py          # 调仓建议生成
│   └── portfolio.py            # 持仓管理与交易记录
│
├── 🎯 strategy/                # 策略框架
│   ├── protocol.py             # IStrategy / IFactor 协议
│   ├── registry.py             # 策略注册中心
│   ├── double_low.py           # 双低轮动策略
│   ├── value.py                # 价值策略
│   ├── momentum.py             # 动量策略
│   ├── composite.py            # 复合策略（加权/投票融合）
│   └── versioning.py           # 策略版本管理
│
├── 🛡️ risk/                    # 风控引擎
│   ├── engine.py               # 风控规则链
│   ├── rules/                  # 8 种风控规则
│   ├── sizers/                 # 仓位管理（等权/Kelly/风险平价）
│   ├── var.py                  # VaR 模型
│   └── stress_test.py          # 压力测试
│
├── 📈 backtest/                # 回测引擎
│   ├── engine.py               # T+1 日频回测
│   ├── virtual_account.py      # 虚拟账户（冻结/可用/滑点）
│   └── stats.py                # 回测统计
│
├── 📊 analytics/               # 分析引擎
│   ├── engine.py               # 风险调整指标
│   ├── drawdown.py             # 回撤分析器
│   ├── benchmark.py            # 基准比较 (Alpha/Beta)
│   ├── brinson.py              # Brinson 业绩归因
│   ├── charts.py               # 图表数据生成
│   └── report.py               # Markdown 报告
│
├── 📐 factors/                 # 因子库
│   ├── value.py                # 价值因子 (双低/纯债溢价/YTM)
│   ├── momentum.py             # 动量因子 (5d/20d/60d/RSI)
│   ├── quality.py              # 质量因子 (评级/规模/期限)
│   ├── technical.py            # 技术因子 (波动率/换手/量价背离)
│   └── composite.py            # 复合因子 (Z-Score 标准化)
│
├── 🔄 pipeline/                # 数据管道
│   ├── data_source.py          # 多数据源管理与容错
│   ├── quality.py              # 数据质量检查
│   ├── lineage.py              # 数据血缘追踪
│   ├── sync_queue.py           # 优先级同步队列
│   └── retry.py                # 指数退避重试
│
├── 📡 monitoring/              # 监控告警
│   ├── engine.py               # 监控引擎
│   ├── alert_rules.py          # 4 类告警规则
│   ├── notifiers.py            # 日志/Webhook/组合通知
│   └── health.py               # 健康评分 (0-100)
│
├── ⚡ execution/               # 执行引擎
│   ├── order_manager.py        # 订单生命周期管理
│   ├── slippage.py             # 滑点模型（固定/成交量/波动率）
│   └── tca.py                  # 交易成本分析 (TCA)
│
├── 🖥️ web/                     # Web 界面
│   ├── app.py                  # Flask 后端 + REST API
│   └── templates/index.html    # SPA 前端（深色/浅色主题）
│
├── 📦 其他
│   ├── fetcher/                # AkShare 数据采集器
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── aligner/                # 数据对齐器
│   ├── portfolio_manager/      # 多组合管理 + 模板
│   ├── api_gateway/            # API 鉴权 + 限流
│   ├── scripts/                # 同步/回填/测试数据脚本
│   └── tests/                  # 27 个测试模块, 341+ 测试用例
│
├── config.yaml                 # 策略与系统配置
├── cli.py                      # CLI 入口 (Click)
├── config.py                   # Pydantic 配置模型
├── db.py                       # 数据库初始化
└── pyproject.toml              # 项目元数据与依赖
```

---

## 🧪 开发指南

### 环境搭建

```bash
git clone https://github.com/krisaruz/vertexquant.git
cd vertexquant
pip install -e ".[dev]"
```

### 测试

```bash
# 运行全部测试
pytest tests/ -v

# 带覆盖率报告
pytest tests/ --cov=vertexquant --cov-report=term-missing
```

### 代码规范

| 工具 | 用途 | 命令 |
|------|------|------|
| **black** | 代码格式化 | `black .` |
| **ruff** | 静态检查 | `ruf check .` |
| **pytest** | 自动化测试 | `pytest tests/ -v` |

### 扩展因子

```python
from vertexquant.strategy import FactorRegistry

@FactorRegistry.register("my_factor", category="custom")
class MyFactor:
    def compute(self, df):
        df["my_factor"] = ...  # 你的因子逻辑
        return df
```

### 扩展策略

```python
from vertexquant.strategy import StrategyRegistry, IStrategy

@StrategyRegistry.register("my_strategy")
class MyStrategy(IStrategy):
    def generate_signals(self, context):
        # 你的策略逻辑
        return signals
```

---

## 🗺️ 技术栈

| 层 | 技术 |
|----|------|
| **语言** | Python 3.11+ |
| **数据框架** | pandas 2.0+ · numpy 1.24+ |
| **数据库** | SQLAlchemy 2.0 · SQLite |
| **行情数据** | AkShare（东方财富 + 集思录） |
| **Web** | Flask 3 · Vanilla JS · CSS Variables |
| **CLI** | Click 8+ |
| **配置** | YAML + Pydantic v2 |
| **测试** | pytest · pytest-cov |
| **代码质量** | black · ruff (line-length=100) |

---

## 📜 License

[MIT License](LICENSE) — 自由使用、修改与分发。
