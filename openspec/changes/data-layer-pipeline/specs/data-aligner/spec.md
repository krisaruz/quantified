## ADDED Requirements

### Requirement: DataAligner 按日期对齐转债与正股数据

系统 SHALL 提供 `DataAligner` 类，其核心方法 `align(cb_code: str, start_date: str, end_date: str) -> pd.DataFrame` 将同一只转债及其正股的日线数据按交易日期合并为单一 DataFrame。

合并策略：
1. 以两者交易日期的**并集**为基准日期轴
2. 缺失值使用前值填充（forward fill）
3. 计算衍生指标列

#### Scenario: 正常对齐（双方均有数据）

- **WHEN** 转债 123001 和正股 600000 在 2025-03-01 到 2025-03-31 期间均有日线数据
- **THEN** `align("123001", "2025-03-01", "2025-03-31")` SHALL 返回包含以下列的 DataFrame：date, cb_open, cb_high, cb_low, cb_close, cb_volume, stock_open, stock_high, stock_low, stock_close, stock_volume, cb_suspended, stock_suspended, cb_suspended_days, stock_suspended_days, trade_available, conversion_value, premium_rate

#### Scenario: 输出 DataFrame 的日期排序

- **WHEN** 对齐完成
- **THEN** 输出 DataFrame SHALL 按 date 列升序排列，date 列类型为 `datetime.date`

---

### Requirement: 停牌场景的 ffill 处理

DataAligner SHALL 使用前值填充（ffill）处理单边或双边停牌导致的价格缺失。

#### Scenario: 正股停牌，转债正常交易

- **WHEN** 2025-03-15 正股停牌（StockDaily 无该日记录或 is_suspended=True），转债正常交易
- **THEN** 该日 stock_close 等价格字段 SHALL 使用前一个交易日的值填充
- **THEN** stock_suspended SHALL 为 True，cb_suspended SHALL 为 False
- **THEN** trade_available SHALL 为 False（正股停牌时无法完成套利闭环）

#### Scenario: 转债停牌，正股正常交易

- **WHEN** 2025-03-15 转债停牌，正股正常交易
- **THEN** 该日 cb_close 等价格字段 SHALL 使用前一个交易日的值填充
- **THEN** cb_suspended SHALL 为 True，stock_suspended SHALL 为 False
- **THEN** trade_available SHALL 为 False

#### Scenario: 双方停牌

- **WHEN** 2025-03-15 转债和正股均停牌
- **THEN** 双方价格字段 SHALL 使用各自前一个交易日的值填充
- **THEN** cb_suspended 和 stock_suspended 均为 True
- **THEN** trade_available SHALL 为 False

#### Scenario: 双方正常交易

- **WHEN** 2025-03-15 转债和正股均正常交易
- **THEN** 使用当日实际行情数据
- **THEN** cb_suspended 和 stock_suspended 均为 False
- **THEN** trade_available SHALL 为 True

---

### Requirement: 连续停牌天数计算

DataAligner SHALL 在对齐后的 DataFrame 上计算 `cb_suspended_days` 和 `stock_suspended_days` 列，表示截至当日的连续停牌天数。

#### Scenario: 连续停牌计数

- **WHEN** 正股从 2025-03-10 开始连续停牌至 2025-03-14（共 5 个交易日）
- **THEN** 2025-03-14 的 stock_suspended_days SHALL 为 5

#### Scenario: 停牌结束后归零

- **WHEN** 正股在 2025-03-15 复牌正常交易
- **THEN** 2025-03-15 的 stock_suspended_days SHALL 为 0

#### Scenario: 未停牌时为零

- **WHEN** 正股在某日正常交易（is_suspended=False）
- **THEN** 该日 stock_suspended_days SHALL 为 0

---

### Requirement: 衍生指标计算

DataAligner SHALL 在对齐后的 DataFrame 上计算以下衍生指标列：

- **conversion_value** = 100 / 当日有效转股价 × stock_close
- **premium_rate** = cb_close / conversion_value - 1

#### Scenario: 使用历史转股价计算

- **WHEN** 计算 T 日的 conversion_value
- **THEN** 系统 SHALL 使用 ConversionPriceHistory 中 change_date <= T 的最近一条转股价
- **THEN** 若无历史记录，SHALL 回退使用 BondBasic.conv_price_latest

#### Scenario: 转股价值为零的防御

- **WHEN** 转股价为 0 或 NULL
- **THEN** conversion_value 和 premium_rate SHALL 为 NaN，不抛出除零异常

---

### Requirement: 全市场截面扫描支持

系统 SHALL 提供 `align_universe(date: str) -> pd.DataFrame` 方法，返回指定日期全市场所有 ACTIVE 转债的截面数据，用于双低轮动等全市场筛选策略。

#### Scenario: 获取全市场某日截面

- **WHEN** 调用 `align_universe("2025-03-15")`
- **THEN** 系统 SHALL 返回包含以下列的 DataFrame：cb_code, cb_name, cb_close, stock_close, conversion_value, premium_rate, double_low（双低值 = cb_close + premium_rate × 100）, trade_available, maturity_date, issue_size, credit_rating, is_st, cb_suspended_days, stock_suspended_days
- **THEN** 仅包含 status=ACTIVE 的转债
- **THEN** 按 double_low 升序排列

#### Scenario: 截面数据排除停牌标的

- **WHEN** 获取全市场截面时，某只转债或其正股在该日停牌
- **THEN** 该标的 SHALL 仍出现在结果中，但 trade_available 为 False
- **THEN** 策略层可根据 trade_available 自行过滤
