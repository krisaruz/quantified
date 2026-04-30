## ADDED Requirements

### Requirement: 绩效统计

系统 SHALL 从逐日净值序列计算以下绩效指标：

- **总收益率**: (末日净值 / 初始资金) - 1
- **年化收益率**: (1 + 总收益率) ^ (365 / 总天数) - 1
- **最大回撤**: max(1 - 净值 / 历史最高净值)
- **夏普比率**: (年化收益 - 无风险利率) / 年化波动率
- **总换手次数**: 买入 + 卖出的总次数
- **总交易费用**: 所有交易费用之和

#### Scenario: 计算正常绩效

- **WHEN** 3 年回测产生逐日净值序列
- **THEN** 系统 SHALL 输出上述全部指标，格式化为人类可读的文本报告

#### Scenario: 回测期间无交易

- **WHEN** 过滤后无合格标的，整个回测期间未产生任何交易
- **THEN** 总收益率 SHALL 为 0，夏普比率 SHALL 为 NaN，输出提示"无交易记录"

### Requirement: CLI backtest 输出

`quantified backtest --start YYYY-MM-DD --end YYYY-MM-DD` SHALL 输出格式化的回测报告。

#### Scenario: 标准回测输出

- **WHEN** 运行 `quantified backtest --start 2023-01-01 --end 2025-12-31`
- **THEN** 输出 SHALL 包含：回测区间、总收益率、年化收益率、最大回撤、夏普比率、换手次数、交易费用
