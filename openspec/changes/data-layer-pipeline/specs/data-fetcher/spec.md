## ADDED Requirements

### Requirement: IDataFetcher 可插拔数据获取协议

系统 SHALL 定义 `IDataFetcher` Protocol，声明以下方法签名：

- `fetch_bond_list() -> pd.DataFrame`: 获取全市场可转债基础信息列表
- `fetch_bond_daily(cb_code: str, start_date: str, end_date: str) -> pd.DataFrame`: 获取单只转债的日线行情
- `fetch_stock_daily(stock_code: str, start_date: str, end_date: str) -> pd.DataFrame`: 获取单只正股的日线行情
- `fetch_conv_price_history(cb_code: str) -> pd.DataFrame`: 获取单只转债的转股价变动历史

任何实现了上述方法签名的类 SHALL 被视为合法的 IDataFetcher，无需显式继承。

#### Scenario: 协议的结构化子类型检查

- **WHEN** 一个类实现了 IDataFetcher 要求的所有方法签名
- **THEN** `isinstance(instance, IDataFetcher)` SHALL 在 runtime_checkable 下返回 True，无需该类声明继承 IDataFetcher

---

### Requirement: AkShareFetcher 具体实现

系统 SHALL 提供 `AkShareFetcher` 类，实现 `IDataFetcher` 协议，通过 AkShare 库获取数据。

#### Scenario: 获取转债列表

- **WHEN** 调用 `AkShareFetcher.fetch_bond_list()`
- **THEN** 系统 SHALL 调用 AkShare 的转债接口，返回包含 cb_code、cb_name、stock_code、list_date、maturity_date、conv_price_latest、issue_size 等字段的 DataFrame
- **THEN** DataFrame 的列名 SHALL 统一为英文蛇形命名（如 `cb_code`），不保留 AkShare 原始中文列名

#### Scenario: 获取转债日线行情

- **WHEN** 调用 `AkShareFetcher.fetch_bond_daily("123001", "2025-01-01", "2025-12-31")`
- **THEN** 系统 SHALL 返回包含 trade_date、open、high、low、close、volume、turnover 字段的 DataFrame
- **THEN** trade_date 列 SHALL 为 `datetime.date` 类型，按升序排列

#### Scenario: 获取正股日线行情

- **WHEN** 调用 `AkShareFetcher.fetch_stock_daily("600000", "2025-01-01", "2025-12-31")`
- **THEN** 系统 SHALL 返回前复权价格的日线 DataFrame
- **THEN** 字段命名和类型 SHALL 与 fetch_bond_daily 保持一致

#### Scenario: 获取转股价变动历史

- **WHEN** 调用 `AkShareFetcher.fetch_conv_price_history("123001")`
- **THEN** 系统 SHALL 返回包含 change_date、conversion_price、reason 字段的 DataFrame
- **THEN** 若 AkShare 无该转债的变动记录，SHALL 返回空 DataFrame（不抛异常）

---

### Requirement: AkShare 调用异常处理

AkShareFetcher 的每个方法 SHALL 捕获网络错误和接口变更导致的异常，记录日志后抛出统一的 `DataFetchError` 自定义异常。

#### Scenario: 网络超时

- **WHEN** AkShare 接口因网络问题超时
- **THEN** 系统 SHALL 记录 WARNING 级别日志，并抛出 `DataFetchError`，包含原始异常信息

#### Scenario: 接口返回空数据

- **WHEN** AkShare 接口对合法参数返回空 DataFrame
- **THEN** 系统 SHALL 返回空 DataFrame（不视为异常），但记录 INFO 级别日志

---

### Requirement: DataFrame 列名标准化

AkShareFetcher 的每个方法 SHALL 在返回 DataFrame 前，将 AkShare 原始列名（通常为中文）映射为英文蛇形命名。列名映射关系 SHALL 在类内部以常量字典形式维护。

#### Scenario: 中文列名映射

- **WHEN** AkShare 返回的 DataFrame 包含列名"收盘价"
- **THEN** AkShareFetcher SHALL 将其重命名为 `close` 后返回

#### Scenario: 未知列名处理

- **WHEN** AkShare 返回的 DataFrame 包含映射字典中不存在的列
- **THEN** 系统 SHALL 保留该列的原始名称，并记录 DEBUG 级别日志
