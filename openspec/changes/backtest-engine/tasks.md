## 1. 虚拟账户

- [ ] 1.1 实现 `src/quantified/backtest/__init__.py` 和 `src/quantified/backtest/account.py`：Position 数据类 + VirtualAccount 类（资金管理、T+1 持仓状态机、交易费用）
- [ ] 1.2 编写 `tests/test_account.py`：测试买入/卖出/结算/T+1 冻结/费用计算

## 2. 回测引擎核心

- [ ] 2.1 实现 `src/quantified/backtest/engine.py`：BacktestEngine 主循环（日期迭代 + 日初结算 + 事件检测 + 策略执行 + 撮合 + 日终记账）
- [ ] 2.2 实现撮合逻辑：按 T+1 开盘价成交，停牌时取消订单
- [ ] 2.3 实现事件检测：检查持仓转债是否触发 DELISTED，生成强制卖出指令

## 3. 绩效统计

- [ ] 3.1 实现 `src/quantified/backtest/stats.py`：从逐日净值序列计算收益率/最大回撤/夏普比率/换手率/费用
- [ ] 3.2 实现报告格式化输出（人话文本）

## 4. CLI 集成

- [ ] 4.1 在 `src/quantified/cli.py` 中新增 `backtest` 子命令，接收 --start / --end 参数

## 5. 测试

- [ ] 5.1 编写 `tests/test_backtest.py`：用 fixture 数据（5只转债×20天）测试完整回测流程
- [ ] 5.2 验证无未来函数：T日信号只用T日数据，T+1日成交
