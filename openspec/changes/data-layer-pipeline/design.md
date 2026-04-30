## Context

这是一个从零构建的可转债套利量化系统，当前阶段（Phase A）聚焦于数据基础设施。系统使用者没有金融背景，因此所有金融业务概念必须映射为标准软件工程模式（状态机、批处理管道、外键关联）。

核心约束：
- **无未来函数**：T 日计算只能使用 T 日及之前的数据
- **T+1 结算**：今日买入明日才可卖出（Phase B 账户模块负责，但数据层的时间戳设计必须支持）
- **日频批处理**：所有操作在收盘后触发，无实时数据需求
- **套利导向**：首选策略为双低轮动，对转股价精度和全市场截面扫描有硬性要求

当前无任何已有代码，项目根目录为 `c:\Users\admin\Desktop\quantified\`。

## Goals / Non-Goals

**Goals:**
- 建立 6 张 ORM 表的完整数据模型，正确表达转债-正股的 1:1 关联和转股价历史变动
- 实现可插拔的数据获取层，首版对接 AkShare，支持增量同步
- 实现数据对齐引擎，处理停牌场景并输出策略层可直接消费的 DataFrame
- 建立项目骨架（包结构、依赖管理、数据库初始化）

**Non-Goals:**
- 不涉及策略引擎、事件引擎、撮合引擎（Phase B+）
- 不涉及账户/持仓/订单模型（Phase B+）
- 不涉及 Web UI 或可视化
- 不涉及实时行情或盘中数据
- 不做多数据库支持（仅 SQLite，但 ORM 层保持可迁移性）

## Decisions

### D1: 项目结构 — src layout + 分层包

```
quantified/
├── pyproject.toml
├── data/                      # SQLite 数据库文件（gitignore）
├── src/
│   └── quantified/
│       ├── __init__.py
│       ├── models/            # SQLAlchemy ORM 模型
│       │   ├── __init__.py
│       │   ├── base.py        # DeclarativeBase + engine 工厂
│       │   ├── bond.py        # BondBasic, BondDaily, ConversionPriceHistory
│       │   └── stock.py       # StockBasic, StockDaily
│       ├── fetcher/           # 数据获取层
│       │   ├── __init__.py
│       │   ├── protocol.py    # IDataFetcher Protocol 定义
│       │   └── akshare_impl.py# AkShare 具体实现
│       ├── aligner/           # 数据对齐与校验
│       │   ├── __init__.py
│       │   └── core.py        # DataAligner + 衍生指标计算
│       └── db.py              # DataMeta 表 + 数据库会话管理
├── tests/
└── scripts/
    └── sync_data.py           # 日常数据同步入口脚本
```

**理由**: src layout 是 Python 现代最佳实践，避免包导入路径污染。三个子包（models/fetcher/aligner）对应数据层的三个正交关注点，各自可独立测试。

### D2: 转股价存储 — 双层方案

- `BondBasic.conv_price_latest`: 存最新转股价，供实盘/模拟盘快速查询
- `ConversionPriceHistory`: 独立时间序列表，存每次转股价变动记录，供回测使用

回测时通过 `SELECT ... WHERE change_date <= :target_date ORDER BY change_date DESC LIMIT 1` 获取某日生效的转股价。

**考虑的替代方案**: 只存 BondBasic 一个字段。否决理由：套利策略依赖溢价率精度，用最新转股价回测历史数据会产生虚假信号，违反"无未来函数"约束。

### D3: DataFetcher — Protocol 而非 ABC

使用 `typing.Protocol` 定义数据获取接口，而非 `abc.ABC`。

```python
class IDataFetcher(Protocol):
    def fetch_bond_list(self) -> pd.DataFrame: ...
    def fetch_stock_daily(self, code: str, start: str, end: str) -> pd.DataFrame: ...
    def fetch_bond_daily(self, code: str, start: str, end: str) -> pd.DataFrame: ...
    def fetch_conv_price_history(self, cb_code: str) -> pd.DataFrame: ...
```

**理由**: Protocol 是结构化子类型（structural subtyping），不要求显式继承，更轻量。未来替换 Tushare、集思录 API 时只需实现相同方法签名。

### D4: 数据对齐输出 — 带 trade_available 标志

`DataAligner.align()` 输出的 DataFrame 包含以下列：

| 列名 | 来源 | 说明 |
|------|------|------|
| date | 合并键 | 交易日期 |
| cb_close | BondDaily | 转债收盘价（停牌时 ffill） |
| stock_close | StockDaily | 正股收盘价（停牌时 ffill） |
| cb_suspended | BondDaily | 转债当日是否停牌 |
| stock_suspended | StockDaily | 正股当日是否停牌 |
| trade_available | 计算列 | 双方均未停牌时为 True |
| conversion_value | 计算列 | 转股价值 = 100 / 转股价 × 正股收盘价 |
| premium_rate | 计算列 | 溢价率 = 转债收盘价 / 转股价值 - 1 |

策略引擎只在 `trade_available=True` 的行上生成信号。

### D5: 增量同步 — DataMeta 表驱动

`DataMeta` 表记录每个数据源的同步水位线（last_sync_date），每次同步只拉取水位线之后的数据。

```
key: "bond_daily:{cb_code}:last_date"  →  value: "2026-04-25"
key: "schema_version"                  →  value: "1"
key: "akshare_version"                 →  value: "1.14.56"
```

### D6: 转债状态机 — 3 态枚举

```python
class BondStatus(str, Enum):
    ACTIVE = "active"              # 正常交易
    REDEEM_WARNING = "redeem_warning"  # 已触发强赎条件/公告强赎
    DELISTED = "delisted"          # 已退市
```

**理由**: 2 态（ACTIVE/DELISTED）不够——套利策略必须识别强赎预警期的转债以避免踩坑或捕捉最后窗口。但更细的状态（PENDING/MATURING/PUTTABLE）在 Phase A 数据层还用不到，Phase B 事件引擎可通过增加枚举值扩展。

## Risks / Trade-offs

- **[AkShare 接口不稳定]** → AkShare 是社区维护的开源库，接口签名和上游数据源可能变化。**缓解**: Protocol 抽象层隔离变化；sync 脚本加异常捕获和重试；DataMeta 记录 AkShare 版本便于排查。

- **[转股价历史数据不完整]** → AkShare 的 `bond_cb_adj_logs_jsl()` 可能不覆盖所有历史转债。**缓解**: 对于缺失转股价变动记录的转债，fallback 到 BondBasic.conv_price_latest（标记为近似值）；后续可接入 Tushare 补充。

- **[SQLite 单文件体积]** → 全市场历史数据可能达到 1~2GB。**缓解**: 日频数据增长缓慢（约 500 转债 × 250 交易日/年 = 12.5 万行/年），SQLite 处理百万级行无压力；未来可通过更换 engine URL 迁移到 PostgreSQL。

- **[停牌 ffill 可能引入偏差]** → 长期停牌（如正股停牌数月）时 ffill 的价格严重滞后。**缓解**: DataAligner 标记停牌天数，策略层可设置阈值（如停牌超过 5 天则排除）。
