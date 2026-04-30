## Why

Phase A 数据管道已跑通（6 张 ORM 表 + AkShare 获取 + 数据对齐），但系统对非金融背景用户完全不可用——没有命令行界面、没有操作建议输出、没有过滤规则、没有风险管理。用户面对的是原始 DataFrame 和 Python 函数调用，不知道该买什么、卖什么、持有什么。

双低轮动策略的效果 70% 取决于过滤条件（排除 ST、小规模、强赎中等垃圾标的），当前数据层有数据但没有过滤逻辑。

## What Changes

- 新增 YAML 配置文件（策略参数、过滤规则、风控参数），用户通过修改配置控制策略行为
- 新增 CLI 命令行工具（sync / recommend / status / filter-check），每周运行一次即可
- 新增 FilterChain 过滤器链，按可配置规则逐层筛除不合格标的
- 新增 Recommender 推荐引擎，对比目标持仓与当前持仓，生成人话买卖建议
- 新增本地持仓记录（JSON 文件），跟踪用户实际持仓状态

## Capabilities

### New Capabilities

- `user-config`: YAML 配置文件加载与校验（策略参数、过滤规则、风控参数、初始资金）
- `filter-chain`: 可插拔过滤器链，支持 8 种内置过滤规则（ST/规模/价格/评级/到期/强赎/停牌/成交量），通过配置开关组合
- `recommender`: 推荐引擎，将双低排序结果与当前持仓做 diff，输出买入/卖出/持有的人类可读操作建议
- `cli-interface`: Click 命令行工具，提供 sync / recommend / status / filter-check 四个子命令

### Modified Capabilities

（无）

## Impact

- **新增依赖**：click（CLI）、pyyaml（配置）
- **新增文件**：`config.yaml`（用户配置）、`data/portfolio.json`（持仓记录）
- **新增模块**：`src/quantified/config.py`、`src/quantified/filter.py`、`src/quantified/recommender.py`、`src/quantified/cli.py`
