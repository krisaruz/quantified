## ADDED Requirements

### Requirement: BondBasic 转债基础信息表

系统 SHALL 提供 `BondBasic` ORM 模型，存储可转债的静态属性。主键为 `cb_code`（转债代码，如 `"123001"`），MUST 包含以下字段：

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| cb_code | String(10) | PK | 转债代码 |
| cb_name | String(50) | NOT NULL | 转债名称 |
| stock_code | String(10) | FK → StockBasic, NOT NULL, UNIQUE | 对应正股代码（1:1） |
| list_date | Date | NOT NULL | 上市日期 |
| delist_date | Date | NULLABLE | 退市日期（未退市时为 NULL） |
| maturity_date | Date | NOT NULL | 到期日期 |
| conv_price_latest | Float | NOT NULL | 最新转股价 |
| issue_size | Float | NOT NULL | 发行规模（亿元） |
| redeem_trigger_price | Float | NULLABLE | 强赎触发价格 |
| credit_rating | String(10) | NULLABLE | 信用评级（AAA/AA+/AA/AA-等） |
| redeem_clause | String(100) | NULLABLE | 强赎条款文本（如"15/30 130%"） |
| status | Enum(BondStatus) | NOT NULL, DEFAULT=ACTIVE | 生命周期状态 |

#### Scenario: 转债与正股的 1:1 外键关联

- **WHEN** 创建一条 BondBasic 记录，其 stock_code 指向已有的 StockBasic 记录
- **THEN** 通过 ORM relationship 可直接访问 `bond.stock` 获取关联的 StockBasic 对象

#### Scenario: 转债代码唯一性

- **WHEN** 尝试插入一条 cb_code 与已有记录相同的 BondBasic
- **THEN** 数据库 SHALL 抛出唯一约束冲突异常

#### Scenario: stock_code 唯一约束保证 1:1

- **WHEN** 尝试为两只不同的转债设置相同的 stock_code
- **THEN** 数据库 SHALL 抛出唯一约束冲突异常（一只正股只对应一只在交转债）

---

### Requirement: StockBasic 正股基础信息表

系统 SHALL 提供 `StockBasic` ORM 模型，存储正股的静态属性。主键为 `stock_code`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| stock_code | String(10) | PK | 正股代码（如 `"600000"`） |
| stock_name | String(50) | NOT NULL | 正股名称 |
| industry | String(50) | NULLABLE | 所属行业 |
| list_date | Date | NULLABLE | 上市日期 |
| exchange | String(10) | NOT NULL | 交易所（SH/SZ） |
| is_st | Boolean | NOT NULL, DEFAULT=False | 是否 ST/*ST（排雷指标） |

#### Scenario: 正股记录独立于转债存在

- **WHEN** 一只正股的对应转债被删除
- **THEN** StockBasic 记录 SHALL 保留（不级联删除）

---

### Requirement: BondDaily 转债日线行情表

系统 SHALL 提供 `BondDaily` ORM 模型，存储转债的日频行情数据。复合主键为 `(cb_code, trade_date)`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| cb_code | String(10) | PK, FK → BondBasic | 转债代码 |
| trade_date | Date | PK | 交易日期 |
| open | Float | NOT NULL | 开盘价 |
| high | Float | NOT NULL | 最高价 |
| low | Float | NOT NULL | 最低价 |
| close | Float | NOT NULL | 收盘价 |
| volume | Float | NOT NULL | 成交量 |
| turnover | Float | NULLABLE | 成交额 |
| is_suspended | Boolean | NOT NULL, DEFAULT=False | 是否停牌 |

#### Scenario: 按日期查询转债行情

- **WHEN** 查询某只转债在日期范围 [start_date, end_date] 内的日线数据
- **THEN** 系统 SHALL 返回按 trade_date 升序排列的行情记录列表

#### Scenario: 同一转债同一日期不可重复

- **WHEN** 尝试插入相同 (cb_code, trade_date) 的记录
- **THEN** 数据库 SHALL 抛出主键冲突异常

---

### Requirement: StockDaily 正股日线行情表

系统 SHALL 提供 `StockDaily` ORM 模型，存储正股的日频行情数据。复合主键为 `(stock_code, trade_date)`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| stock_code | String(10) | PK, FK → StockBasic | 正股代码 |
| trade_date | Date | PK | 交易日期 |
| open | Float | NOT NULL | 开盘价 |
| high | Float | NOT NULL | 最高价 |
| low | Float | NOT NULL | 最低价 |
| close | Float | NOT NULL | 收盘价（前复权） |
| volume | Float | NOT NULL | 成交量 |
| turnover | Float | NULLABLE | 成交额 |
| adj_factor | Float | NULLABLE | 复权因子 |
| is_suspended | Boolean | NOT NULL, DEFAULT=False | 是否停牌 |

#### Scenario: 正股使用前复权价格

- **WHEN** 写入正股日线数据时
- **THEN** close 字段 SHALL 存储前复权价格，以保证时间序列连续可比

---

### Requirement: ConversionPriceHistory 转股价变动历史表

系统 SHALL 提供 `ConversionPriceHistory` ORM 模型，记录每只转债的历史转股价变动。复合主键为 `(cb_code, change_date)`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| cb_code | String(10) | PK, FK → BondBasic | 转债代码 |
| change_date | Date | PK | 转股价变动生效日期 |
| conversion_price | Float | NOT NULL | 变动后的转股价 |
| reason | String(100) | NULLABLE | 变动原因（下修/送股/配股等） |

#### Scenario: 查询某日生效的转股价

- **WHEN** 需要获取某只转债在 T 日的有效转股价
- **THEN** 系统 SHALL 返回 change_date <= T 的最近一条记录的 conversion_price

#### Scenario: 无变动记录时的回退

- **WHEN** 某只转债在 ConversionPriceHistory 中没有任何记录
- **THEN** 系统 SHALL 回退使用 BondBasic.conv_price_latest 作为近似值

---

### Requirement: DataMeta 数据同步元信息表

系统 SHALL 提供 `DataMeta` ORM 模型，记录数据同步状态和系统元信息。主键为 `key`。

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| key | String(200) | PK | 元信息键名 |
| value | String(500) | NOT NULL | 元信息值 |
| updated_at | DateTime | NOT NULL | 最后更新时间 |

#### Scenario: 记录增量同步水位线

- **WHEN** 某只转债的日线数据同步完成到 2026-04-25
- **THEN** DataMeta 中 SHALL 存在记录 `key="bond_daily:123001:last_date"`, `value="2026-04-25"`

#### Scenario: 记录 schema 版本

- **WHEN** 数据库初始化完成
- **THEN** DataMeta 中 SHALL 存在记录 `key="schema_version"`, `value="1"`

---

### Requirement: BondStatus 转债生命周期状态枚举

系统 SHALL 定义 `BondStatus` 枚举，包含三个状态值：

- `ACTIVE`: 正常交易中
- `REDEEM_WARNING`: 已触发强赎条件或已公告强赎
- `DELISTED`: 已退市

#### Scenario: 新上市转债默认状态

- **WHEN** 创建一条新的 BondBasic 记录且未指定 status
- **THEN** status SHALL 默认为 `ACTIVE`

#### Scenario: 状态转换合法性

- **WHEN** 一只 ACTIVE 状态的转债触发强赎条件
- **THEN** 系统 SHALL 允许将状态更新为 `REDEEM_WARNING`
