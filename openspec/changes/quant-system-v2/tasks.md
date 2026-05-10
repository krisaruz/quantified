## Phase 1: 策略框架 (Strategy Framework)

### 1.1 基础架构
- [ ] 1.1.1 创建 `src/quantified/strategy/__init__.py`
- [ ] 1.1.2 实现 `src/quantified/strategy/protocol.py`：IStrategy、IFactor、Signal、StrategyContext Protocol 定义
- [ ] 1.1.3 实现 `src/quantified/strategy/registry.py`：StrategyRegistry 策略注册表（装饰器注册 + 工厂获取）
- [ ] 1.1.4 实现 `src/quantified/strategy/factor_registry.py`：FactorRegistry 因子注册表

### 1.2 因子库
- [ ] 1.2.1 实现 `src/quantified/factors/__init__.py`
- [ ] 1.2.2 实现 `src/quantified/factors/value.py`：价值因子（双低值、纯债溢价率、到期收益率）
- [ ] 1.2.3 实现 `src/quantified/factors/momentum.py`：动量因子（N 日涨幅、相对强弱、均线偏离）
- [ ] 1.2.4 实现 `src/quantified/factors/quality.py`：质量因子（信用评级得分、发行规模、剩余期限）
- [ ] 1.2.5 实现 `src/quantified/factors/technical.py`：技术因子（波动率、换手率、量价背离）
- [ ] 1.2.6 实现 `src/quantified/factors/composite.py`：CompositeFactor 多因子加权合成

### 1.3 策略实现
- [ ] 1.3.1 实现 `src/quantified/strategy/double_low.py`：将现有 double_low 逻辑封装为 IStrategy
- [ ] 1.3.2 实现 `src/quantified/strategy/momentum_strategy.py`：动量轮动策略
- [ ] 1.3.3 实现 `src/quantified/strategy/value_strategy.py`：价值精选策略
- [ ] 1.3.4 实现 `src/quantified/strategy/composite_strategy.py`：多策略组合器（加权融合、投票机制）
- [ ] 1.3.5 实现 `src/quantified/strategy/legacy_wrapper.py`：LegacyStrategy 包装现有配置

### 1.4 策略版本管理
- [ ] 1.4.1 实现 `src/quantified/strategy/versioning.py`：策略参数快照 + 版本号
- [ ] 1.4.2 在数据库中新增 `strategy_versions` 表，记录每次参数变更
- [ ] 1.4.3 实现策略版本对比功能

### 1.5 测试
- [ ] 1.5.1 编写 `tests/test_strategy_registry.py`：注册表注册/获取/列表
- [ ] 1.5.2 编写 `tests/test_factors.py`：各因子计算正确性
- [ ] 1.5.3 编写 `tests/test_composite_strategy.py`：组合策略信号融合
- [ ] 1.5.4 编写 `tests/test_double_low_migration.py`：现有 double_low 迁移后行为一致

---

## Phase 2: 风控引擎 (Risk Engine)

### 2.1 风控规则框架
- [ ] 2.1.1 创建 `src/quantified/risk/__init__.py`
- [ ] 2.1.2 实现 `src/quantified/risk/protocol.py`：IRiskRule、RiskViolation、RiskConfig Protocol
- [ ] 2.1.3 实现 `src/quantified/risk/engine.py`：RiskEngine 风控引擎（规则链执行 + 信号调整）

### 2.2 内置风控规则
- [ ] 2.2.1 实现 `src/quantified/risk/rules/position_limit.py`：MaxPositionRule 单只持仓上限
- [ ] 2.2.2 实现 `src/quantified/risk/rules/stop_loss.py`：StopLossRule 止损规则（支持移动止损）
- [ ] 2.2.3 实现 `src/quantified/risk/rules/drawdown.py`：MaxDrawdownRule 回撤暂停（支持阶梯式恢复）
- [ ] 2.2.4 实现 `src/quantified/risk/rules/sector_concentration.py`：SectorConcentrationRule 行业集中度
- [ ] 2.2.5 实现 `src/quantified/risk/rules/correlation.py`：CorrelationRule 持仓相关性
- [ ] 2.2.6 实现 `src/quantified/risk/rules/liquidity.py`：LiquidityRule 流动性要求
- [ ] 2.2.7 实现 `src/quantified/risk/rules/turnover.py`：TurnoverRule 换手率控制
- [ ] 2.2.8 实现 `src/quantified/risk/rules/var_limit.py`：VarLimitRule VaR 限制

### 2.3 仓位管理
- [ ] 2.3.1 实现 `src/quantified/risk/position_sizer.py`：PositionSizer Protocol
- [ ] 2.3.2 实现 `src/quantified/risk/sizers/equal_weight.py`：EqualWeightSizer 等权分配
- [ ] 2.3.3 实现 `src/quantified/risk/sizers/risk_parity.py`：RiskParitySizer 风险平价（需 scipy）
- [ ] 2.3.4 实现 `src/quantified/risk/sizers/kelly.py`：KellySizer 凯利公式
- [ ] 2.3.5 实现 `src/quantified/risk/sizers/max_sharpe.py`：MaxSharpeSizer 最大夏普优化

### 2.4 VaR/CVaR 计算
- [ ] 2.4.1 实现 `src/quantified/risk/var.py`：历史模拟法 VaR + 参数法 VaR + Monte Carlo VaR
- [ ] 2.4.2 实现 `src/quantified/risk/cvar.py`：条件 VaR (Expected Shortfall)
- [ ] 2.4.3 实现 `src/quantified/risk/stress_test.py`：压力测试框架（历史场景 + 自定义场景）

### 2.5 配置扩展
- [ ] 2.5.1 扩展 `config.yaml` 风控配置：增加规则开关、阈值、仓位管理方式
- [ ] 2.5.2 扩展 AppConfig Pydantic 模型，支持新风控参数

### 2.6 测试
- [ ] 2.6.1 编写 `tests/test_risk_engine.py`：规则链执行 + 信号调整
- [ ] 2.6.2 编写 `tests/test_position_sizers.py`：各仓位管理算法
- [ ] 2.6.3 编写 `tests/test_var.py`：VaR/CVaR 计算正确性
- [ ] 2.6.4 编写 `tests/test_stress_test.py`：压力测试场景

---

## Phase 3: 分析仪表盘 (Analytics Dashboard)

### 3.1 分析引擎核心
- [ ] 3.1.1 创建 `src/quantified/analytics/__init__.py`
- [ ] 3.1.2 实现 `src/quantified/analytics/engine.py`：AnalyticsEngine 主类
- [ ] 3.1.3 实现 `src/quantified/analytics/metrics.py`：扩展风险调整指标（Sortino、Calmar、信息比率、Omega 比率）

### 3.2 归因分析
- [ ] 3.2.1 实现 `src/quantified/analytics/attribution/brinson.py`：Brinson 归因模型
- [ ] 3.2.2 实现 `src/quantified/analytics/attribution/factor_attribution.py`：因子归因分析
- [ ] 3.2.3 实现 `src/quantified/analytics/attribution/interaction.py`：交互效应分解

### 3.3 基准对比
- [ ] 3.3.1 实现 `src/quantified/analytics/benchmark.py`：基准管理（加载、对齐、计算超额收益）
- [ ] 3.3.2 内置基准：中证转债指数、沪深300（从 AkShare 获取）
- [ ] 3.3.3 实现基准对比报告生成

### 3.4 回撤分析
- [ ] 3.4.1 实现 `src/quantified/analytics/drawdown.py`：回撤区间检测、恢复时间统计、水下曲线
- [ ] 3.4.2 实现回撤分布分析（频率、幅度、持续时间）

### 3.5 报告生成
- [ ] 3.5.1 实现 `src/quantified/analytics/report.py`：月度/季度/年度绩效报告模板
- [ ] 3.5.2 实现 `src/quantified/analytics/report_html.py`：HTML 报告生成（含图表）
- [ ] 3.5.3 实现 `src/quantified/analytics/report_markdown.py`：Markdown 报告生成

### 3.6 可视化数据接口
- [ ] 3.6.1 实现 `src/quantified/analytics/charts.py`：图表数据准备（净值曲线、回撤曲线、持仓热力图、因子暴露雷达图）
- [ ] 3.6.2 为 Web 前端提供 `/api/v2/analytics/*` 系列接口

### 3.7 测试
- [ ] 3.7.1 编写 `tests/test_metrics.py`：各风险调整指标计算
- [ ] 3.7.2 编写 `tests/test_brinson.py`：Brinson 归因正确性
- [ ] 3.7.3 编写 `tests/test_drawdown.py`：回撤检测和统计

---

## Phase 4: 数据管道增强 (Data Pipeline V2)

### 4.1 数据质量校验
- [ ] 4.1.1 创建 `src/quantified/data_quality/__init__.py`
- [ ] 4.1.2 实现 `src/quantified/data_quality/checker.py`：DataQualityChecker 质量校验器
- [ ] 4.1.3 实现 `src/quantified/data_quality/checks/price_range.py`：价格合理性检查
- [ ] 4.1.4 实现 `src/quantified/data_quality/checks/ohlc_consistency.py`：OHLC 逻辑一致性
- [ ] 4.1.5 实现 `src/quantified/data_quality/checks/volume_sanity.py`：成交量异常检测
- [ ] 4.1.6 实现 `src/quantified/data_quality/checks/missing_dates.py`：交易日连续性检查
- [ ] 4.1.7 实现 `src/quantified/data_quality/checks/sudden_jumps.py`：价格突变检测
- [ ] 4.1.8 实现 `src/quantified/data_quality/report.py`：QualityReport 质量报告

### 4.2 增量同步状态机
- [ ] 4.2.1 实现 `src/quantified/sync/state.py`：SyncState 同步状态机（idle → syncing → paused/error）
- [ ] 4.2.2 实现 `src/quantified/sync/task_queue.py`：SyncTaskQueue 任务队列（断点续传）
- [ ] 4.2.3 实现 `src/quantified/sync/retry.py`：RetryPolicy 重试策略（指数退避）
- [ ] 4.2.4 实现 `src/quantified/sync/progress.py`：SyncProgress 进度追踪和报告

### 4.3 数据源管理
- [ ] 4.3.1 实现 `src/quantified/fetcher/source_manager.py`：DataSourceManager 多数据源管理
- [ ] 4.3.2 实现 `src/quantified/fetcher/fallback.py`：FallbackFetcher 容错回退
- [ ] 4.3.3 新增 `src/quantified/fetcher/tushare_impl.py`：Tushare 数据源实现（备用）

### 4.4 数据血缘
- [ ] 4.4.1 新增 `DataLineage` ORM 模型到 `src/quantified/models/`
- [ ] 4.4.2 在数据写入时自动记录血缘信息
- [ ] 4.4.3 实现数据血缘查询接口

### 4.5 重构同步脚本
- [ ] 4.5.1 重构 `scripts/sync_data.py`：使用 SyncState + DataQualityChecker
- [ ] 4.5.2 重构 `scripts/backfill_history.py`：支持断点续传 + 质量校验
- [ ] 4.5.3 新增 `scripts/data_quality_report.py`：生成数据质量报告

### 4.6 测试
- [ ] 4.6.1 编写 `tests/test_data_quality.py`：质量校验规则
- [ ] 4.6.2 编写 `tests/test_sync_state.py`：同步状态机转换
- [ ] 4.6.3 编写 `tests/test_retry.py`：重试策略

---

## Phase 5: 执行引擎 (Execution Engine)

### 5.1 订单管理
- [ ] 5.1.1 创建 `src/quantified/execution/__init__.py`
- [ ] 5.1.2 实现 `src/quantified/execution/order.py`：Order、Fill 数据模型
- [ ] 5.1.3 实现 `src/quantified/execution/oms.py`：OrderManager 订单管理系统
- [ ] 5.1.4 实现订单生命周期：pending → partial → filled / cancelled

### 5.2 滑点模型
- [ ] 5.2.1 实现 `src/quantified/execution/slippage.py`：SlippageModel Protocol
- [ ] 5.2.2 实现 `src/quantified/execution/slippage/fixed.py`：FixedSlippageModel
- [ ] 5.2.3 实现 `src/quantified/execution/slippage/volume_based.py`：VolumeBasedSlippageModel
- [ ] 5.2.4 实现 `src/quantified/execution/slippage/volatility.py`：VolatilitySlippageModel

### 5.3 成交模拟
- [ ] 5.3.1 实现 `src/quantified/execution/matcher.py`：Matcher 撮合引擎
- [ ] 5.3.2 支持部分成交：大单按成交量比例分批成交
- [ ] 5.3.3 支持挂单超时：超过 N 天未成交自动取消

### 5.4 执行成本分析 (TCA)
- [ ] 5.4.1 实现 `src/quantified/execution/tca.py`：TransactionCostAnalyzer
- [ ] 5.4.2 计算：实现差额、市场冲击、时机成本
- [ ] 5.4.3 生成 TCA 报告

### 5.5 集成
- [ ] 5.5.1 重构 BacktestEngine 使用新的 OrderManager + SlippageModel
- [ ] 5.5.2 保留旧接口的向后兼容

### 5.6 测试
- [ ] 5.6.1 编写 `tests/test_oms.py`：订单生命周期
- [ ] 5.6.2 编写 `tests/test_slippage.py`：各滑点模型
- [ ] 5.6.3 编写 `tests/test_matcher.py`：撮合逻辑

---

## Phase 6: 多组合管理 (Multi-Portfolio)

### 6.1 组合管理器
- [ ] 6.1.1 重构 `src/quantified/portfolio.py`：PortfolioManager 支持多组合
- [ ] 6.1.2 实现组合目录结构：`data/portfolios/{name}/portfolio.json`
- [ ] 6.1.3 实现组合 CRUD：创建、列表、删除、重命名

### 6.2 组合模板
- [ ] 6.2.1 实现 `src/quantified/portfolio/templates.py`：内置模板（conservative/balanced/aggressive）
- [ ] 6.2.2 支持自定义模板保存和加载
- [ ] 6.2.3 模板继承：基于模板创建时可覆盖部分参数

### 6.3 组合对比
- [ ] 6.3.1 实现 `src/quantified/portfolio/comparison.py`：PortfolioComparator
- [ ] 6.3.2 对比维度：收益率、波动率、夏普、最大回撤、持仓重叠度
- [ ] 6.3.3 生成对比报告（表格 + 图表数据）

### 6.4 组合快照
- [ ] 6.4.1 实现 `src/quantified/portfolio/snapshot.py`：PortfolioSnapshot 快照
- [ ] 6.4.2 每日自动快照（集成到推荐/回测流程）
- [ ] 6.4.3 快照历史查询和回溯

### 6.5 CLI 集成
- [ ] 6.5.1 新增 `quantified portfolio list` 命令
- [ ] 6.5.2 新增 `quantified portfolio create --template balanced` 命令
- [ ] 6.5.3 新增 `quantified portfolio compare p1 p2` 命令
- [ ] 6.5.4 重构现有命令支持 `--portfolio` 参数

### 6.6 测试
- [ ] 6.6.1 编写 `tests/test_portfolio_manager.py`：多组合 CRUD
- [ ] 6.6.2 编写 `tests/test_portfolio_comparison.py`：组合对比

---

## Phase 7: 监控告警 (Monitoring & Alerting)

### 7.1 监控框架
- [ ] 7.1.1 创建 `src/quantified/monitor/__init__.py`
- [ ] 7.1.2 实现 `src/quantified/monitor/protocol.py`：AlertRule、Alert Protocol
- [ ] 7.1.3 实现 `src/quantified/monitor/engine.py`：Monitor 监控引擎
- [ ] 7.1.4 实现 `src/quantified/monitor/context.py`：MonitorContext 监控上下文

### 7.2 内置告警规则
- [ ] 7.2.1 实现 `src/quantified/monitor/rules/pnl_alert.py`：单日亏损告警
- [ ] 7.2.2 实现 `src/quantified/monitor/rules/concentration_alert.py`：持仓集中度告警
- [ ] 7.2.3 实现 `src/quantified/monitor/rules/data_freshness.py`：数据新鲜度告警
- [ ] 7.2.4 实现 `src/quantified/monitor/rules/volume_anomaly.py`：成交量异常告警
- [ ] 7.2.5 实现 `src/quantified/monitor/rules/drawdown_alert.py`：回撤预警
- [ ] 7.2.6 实现 `src/quantified/monitor/rules/rating_downgrade.py`：评级下调告警

### 7.3 策略健康度
- [ ] 7.3.1 实现 `src/quantified/monitor/health.py`：HealthScore 健康度评分
- [ ] 7.3.2 评分维度：数据新鲜度、持仓分散度、收益稳定性、回撤控制、执行质量
- [ ] 7.3.3 健康度趋势追踪

### 7.4 告警通知
- [ ] 7.4.1 实现 `src/quantified/monitor/notifier.py`：Notifier Protocol
- [ ] 7.4.2 实现 `src/quantified/monitor/notifiers/log.py`：日志通知
- [ ] 7.4.3 实现 `src/quantified/monitor/notifiers/webhook.py`：Webhook 通知
- [ ] 7.4.4 实现 `src/quantified/monitor/notifiers/feishu.py`：飞书通知（可选）

### 7.5 CLI 集成
- [ ] 7.5.1 新增 `quantified monitor check` 命令：运行所有告警检查
- [ ] 7.5.2 新增 `quantified monitor health` 命令：显示策略健康度
- [ ] 7.5.3 新增 `quantified monitor history` 命令：告警历史

### 7.6 测试
- [ ] 7.6.1 编写 `tests/test_monitor.py`：监控引擎 + 告警触发
- [ ] 7.6.2 编写 `tests/test_health_score.py`：健康度评分

---

## Phase 8: API 网关 (API Gateway)

### 8.1 API 规范化
- [ ] 8.1.1 实现 `src/quantified/api/__init__.py`：API 版本管理
- [ ] 8.1.2 实现 `src/quantified/api/v2/` 路由模块
- [ ] 8.1.3 统一错误码和响应格式
- [ ] 8.1.4 实现分页支持（offset + limit + total）

### 8.2 认证与限流
- [ ] 8.2.1 实现 `src/quantified/api/auth.py`：API Key 认证中间件
- [ ] 8.2.2 实现 `src/quantified/api/rate_limit.py`：请求限流（基于时间窗口）
- [ ] 8.2.3 实现 `src/quantified/api/cors.py`：CORS 配置

### 8.3 WebSocket
- [ ] 8.3.1 集成 Flask-SocketIO
- [ ] 8.3.2 实现组合数据实时推送
- [ ] 8.3.3 实现告警实时推送

### 8.4 OpenAPI 文档
- [ ] 8.4.1 集成 flask-smorest 或 apispec
- [ ] 8.4.2 为所有 v2 端点添加 OpenAPI schema
- [ ] 8.4.3 实现 Swagger UI 访问路径 `/api/docs`

### 8.5 API 端点扩展
- [ ] 8.5.1 `/api/v2/strategies`：策略列表、详情、参数
- [ ] 8.5.2 `/api/v2/analytics/*`：分析引擎接口（归因、指标、报告）
- [ ] 8.5.3 `/api/v2/risk/*`：风控状态接口（VaR、违规、健康度）
- [ ] 8.5.4 `/api/v2/portfolios`：多组合管理接口
- [ ] 8.5.5 `/api/v2/monitor/*`：监控告警接口

### 8.6 测试
- [ ] 8.6.1 编写 `tests/test_api_v2.py`：v2 端点集成测试
- [ ] 8.6.2 编写 `tests/test_auth.py`：认证中间件
- [ ] 8.6.3 编写 `tests/test_rate_limit.py`：限流逻辑

---

## Cross-Cutting: 配置与文档

- [ ] C.1 扩展 `config.yaml`：增加策略框架、风控引擎、监控告警配置节
- [ ] C.2 扩展 AppConfig Pydantic 模型：支持所有新配置参数
- [ ] C.3 更新 `pyproject.toml`：新增 scipy、statsmodels、flask-socketio 依赖
- [ ] C.4 更新 CLI 帮助文档和命令分组
- [ ] C.5 集成测试：端到端流程（数据同步 → 策略执行 → 风控检查 → 回测 → 分析报告）
