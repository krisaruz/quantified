# VertexQuant

可转债+股票双标的量化回测与模拟交易系统

## 特性

- 双低轮动策略框架，支持策略注册与版本管理
- 多层风控引擎：仓位限制、止损、回撤暂停、行业集中度
- 日频回测引擎，T+1撮合，无未来函数
- 因子库：价值、动量、质量、技术因子
- 分析引擎：Sortino、Calmar、Omega等风险调整指标
- 数据管道：多数据源容错、质量检查、血缘追踪
- 监控告警：规则引擎 + 通知分发
- Web界面 + CLI工具

## 安装

```bash
pip install -e .
```

## 使用

```bash
# 同步数据
vertexquant sync

# 查看调仓建议
vertexquant recommend

# 查看持仓状态
vertexquant status

# 运行回测
vertexquant backtest --start 2023-01-01

# 启动Web界面
vertexquant web
```

## 配置

编辑 `config.yaml` 调整策略参数：

```yaml
strategy:
  name: double_low
  hold_count: 10
  rebalance_day: friday

filters:
  max_price: 130
  min_credit_rating: AA-

risk:
  max_position_pct: 0.10
  stop_loss_pct: -0.15
```

## 项目结构

```
vertexquant/
├── strategy/      # 策略框架
├── risk/          # 风控引擎
├── backtest/      # 回测引擎
├── analytics/     # 分析引擎
├── factors/       # 因子库
├── pipeline/      # 数据管道
├── monitoring/    # 监控告警
├── execution/     # 执行引擎
├── fetcher/       # 数据获取
├── models/        # 数据模型
└── web/           # Web界面
```

## License

MIT
