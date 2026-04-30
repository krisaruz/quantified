## 1. 配置系统

- [ ] 1.1 添加 click、pyyaml 依赖到 `pyproject.toml`
- [ ] 1.2 创建 `config.yaml` 默认配置模板（策略参数 + 过滤规则 + 风控参数 + 资金）
- [ ] 1.3 实现 `src/quantified/config.py`：Pydantic 模型定义 + YAML 加载 + 默认值 + 校验错误友好提示

## 2. 过滤器链

- [ ] 2.1 实现 `src/quantified/filter.py`：8 个独立过滤函数 + FilterChain 类 + 审计日志记录
- [ ] 2.2 编写 `tests/test_filter.py`：测试每个过滤器的独立行为和组合行为

## 3. 推荐引擎

- [ ] 3.1 实现 `src/quantified/recommender.py`：Recommender 类 + 目标持仓 vs 当前持仓 diff + 人话输出格式化
- [ ] 3.2 实现 `src/quantified/portfolio.py`：本地持仓 JSON 读写 + 买入/卖出记录
- [ ] 3.3 编写 `tests/test_recommender.py`：测试 diff 逻辑和输出格式

## 4. CLI 命令行

- [ ] 4.1 实现 `src/quantified/cli.py`：Click 应用 + sync / recommend / status / filter-check 四个子命令
- [ ] 4.2 更新 `pyproject.toml` 的 `[project.scripts]` 入口点

## 5. 集成测试

- [ ] 5.1 编写端到端测试：从配置加载到推荐输出的完整流程（使用 fixture 数据）
