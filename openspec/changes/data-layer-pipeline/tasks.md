## 1. 项目骨架与依赖

- [ ] 1.1 创建 `pyproject.toml`，声明项目元信息和依赖（sqlalchemy, akshare, pandas, numpy），配置 src layout
- [ ] 1.2 创建包目录结构：`src/quantified/{__init__, models/, fetcher/, aligner/}`，每个子包含 `__init__.py`
- [ ] 1.3 创建 `data/` 目录（gitignore）和 `.gitignore` 文件

## 2. 数据库基础设施

- [ ] 2.1 实现 `src/quantified/models/base.py`：DeclarativeBase、engine 工厂函数（接收 db_path 参数，默认 `data/quantified.db`）、Session 工厂
- [ ] 2.2 实现 `src/quantified/db.py`：DataMeta ORM 模型 + `get_meta(key)` / `set_meta(key, value)` 辅助函数 + `init_db()` 建表函数

## 3. 核心 ORM 模型

- [ ] 3.1 实现 `src/quantified/models/stock.py`：StockBasic（含 is_st 字段）和 StockDaily 两个 ORM 模型，含字段定义、类型约束、关系
- [ ] 3.2 实现 `src/quantified/models/bond.py`：BondStatus 枚举 + BondBasic（含 credit_rating、redeem_clause 字段）、BondDaily、ConversionPriceHistory 三个 ORM 模型，含外键 `stock_code → StockBasic`、1:1 relationship、复合主键
- [ ] 3.3 在 `src/quantified/models/__init__.py` 中统一导出所有模型，确保 `init_db()` 能发现并创建全部 6 张表

## 4. 数据获取层

- [ ] 4.1 实现 `src/quantified/fetcher/protocol.py`：IDataFetcher Protocol 定义（runtime_checkable）+ DataFetchError 自定义异常
- [ ] 4.2 实现 `src/quantified/fetcher/akshare_impl.py`：AkShareFetcher 类，包含列名映射常量字典
- [ ] 4.3 实现 `AkShareFetcher.fetch_bond_list()`：调用 AkShare 接口获取全市场转债列表，标准化列名后返回 DataFrame
- [ ] 4.4 实现 `AkShareFetcher.fetch_bond_daily()`：调用 AkShare 接口获取单只转债日线行情
- [ ] 4.5 实现 `AkShareFetcher.fetch_stock_daily()`：调用 AkShare 接口获取单只正股前复权日线行情
- [ ] 4.6 实现 `AkShareFetcher.fetch_conv_price_history()`：调用 AkShare 接口获取转股价变动历史
- [ ] 4.7 为所有 AkShareFetcher 方法添加异常捕获（网络错误 → DataFetchError）和日志记录

## 5. 数据对齐与衍生指标

- [ ] 5.1 实现 `src/quantified/aligner/core.py`：DataAligner 类骨架，构造函数接收 Session（用于查询 ORM 数据）
- [ ] 5.2 实现 `DataAligner.align(cb_code, start_date, end_date)`：从数据库查询转债+正股日线，按日期 outer join，ffill 停牌缺失值，生成 cb_suspended / stock_suspended / cb_suspended_days / stock_suspended_days / trade_available 列
- [ ] 5.3 实现衍生指标计算逻辑：查询 ConversionPriceHistory 获取每日有效转股价，计算 conversion_value 和 premium_rate 列，处理除零防御
- [ ] 5.4 实现 `DataAligner.align_universe(date)`：全市场截面扫描，返回所有 ACTIVE 转债在指定日期的截面 DataFrame（含 double_low 列），按 double_low 升序

## 6. 数据同步入口脚本

- [ ] 6.1 创建 `scripts/sync_data.py`：读取 DataMeta 水位线，调用 AkShareFetcher 增量拉取数据，写入数据库，更新水位线
- [ ] 6.2 实现同步流程：先同步 BondBasic/StockBasic 基础信息 → 再同步 ConversionPriceHistory → 最后同步 BondDaily/StockDaily 日线行情

## 7. 测试与验证

- [ ] 7.1 编写 `tests/test_models.py`：测试 ORM 模型的建表、CRUD、外键关联、唯一约束冲突
- [ ] 7.2 编写 `tests/test_aligner.py`：用 fixture 数据测试 DataAligner 的四种停牌场景对齐结果和衍生指标计算
- [ ] 7.3 编写 `tests/test_fetcher.py`：mock AkShare 接口，测试 AkShareFetcher 的列名映射和异常处理
