## Why

从零构建一个可转债+股票双标的量化回测与模拟交易系统，首要任务是建立可靠的数据基础设施。没有准确、完整、时间对齐的行情数据，上层的策略引擎、事件检测、撮合引擎都无从谈起。当前目标是**可转债套利（以双低轮动为首选策略）**，这类策略对数据精度（尤其是转股价的历史准确性）要求极高——转股价用错一个百分点，就会产生虚假的套利信号。

## What Changes

- 新建项目骨架：Python 包结构、依赖管理（pyproject.toml）、SQLite 数据库
- 新建 6 张 SQLAlchemy ORM 数据表：`BondBasic`、`StockBasic`、`BondDaily`、`StockDaily`、`ConversionPriceHistory`、`DataMeta`
- 新建可插拔数据获取框架：`IDataFetcher` 协议 + `AkShareFetcher` 实现，封装 AkShare 库调用
- 新建数据对齐与校验模块：`DataAligner`，将转债与正股日线按日期对齐，处理停牌填充，输出含 `trade_available` 标志的合并 DataFrame
- 新建衍生指标计算：转股价值、转股溢价率、双低值的计算工具函数

## Capabilities

### New Capabilities

- `data-models`: SQLAlchemy ORM 数据模型定义（6 张表），含转债-正股 1:1 外键关联、转债生命周期状态机（ACTIVE/REDEEM_WARNING/DELISTED）、转股价历史变动序列
- `data-fetcher`: 可插拔的数据获取框架，基于 Python Protocol 的抽象接口 + AkShare 具体实现，支持转债列表、正股列表、日线行情、转股价变动历史的增量同步
- `data-aligner`: 数据对齐与校验引擎，将转债和正股日线按交易日期合并，处理三种停牌场景（单边停牌 ffill + 双边停牌标记），输出策略层可直接消费的干净 DataFrame

### Modified Capabilities

（无，全新项目）

## Impact

- **新增依赖**：sqlalchemy、akshare、pandas、numpy
- **新增目录结构**：`src/quantified/models/`、`src/quantified/fetcher/`、`src/quantified/aligner/`
- **数据文件**：本地生成 `data/quantified.db`（SQLite 数据库文件，约 100MB~2GB 取决于历史数据量）
- **网络访问**：DataFetcher 运行时需要访问 AkShare 的上游数据源（东方财富/集思录），受接口限流约束
