"""绩效统计 —— 从逐日净值序列计算关键指标

支持的指标：
- 总收益率 / 年化收益率
- 最大回撤 / 最大回撤区间
- 夏普比率 / 年化波动率
- 胜率 / 盈亏比
- 总换手次数 / 交易费用
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from quantified.backtest.account import TradeRecord
from quantified.backtest.engine import BacktestResult, DailySnapshot

RISK_FREE_RATE = 0.02
TRADING_DAYS_PER_YEAR = 244


@dataclass
class PerformanceStats:
    """绩效指标"""
    total_return: float = 0.0
    annualized_return: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_start: str = ""
    max_drawdown_end: str = ""
    sharpe_ratio: float = 0.0
    annualized_volatility: float = 0.0
    total_trades: int = 0
    buy_trades: int = 0
    sell_trades: int = 0
    win_rate: float = 0.0
    profit_loss_ratio: float = 0.0
    total_fees: float = 0.0
    trading_days: int = 0
    avg_positions: float = 0.0

    def format_report(self) -> str:
        """格式化为人话报告"""
        lines = [
            "",
            "=" * 50,
            "  回测绩效报告",
            "=" * 50,
            "",
            f"  总收益率:       {self.total_return:+.2%}",
            f"  年化收益率:     {self.annualized_return:+.2%}",
            f"  最大回撤:       {self.max_drawdown:.2%}",
        ]
        if self.max_drawdown_start:
            lines.append(f"  回撤区间:       {self.max_drawdown_start} ~ {self.max_drawdown_end}")
        lines += [
            f"  夏普比率:       {self.sharpe_ratio:.2f}",
            f"  年化波动率:     {self.annualized_volatility:.2%}",
            "",
            f"  交易日数:       {self.trading_days}",
            f"  平均持仓只数:   {self.avg_positions:.1f}",
            f"  总交易次数:     {self.total_trades} (买{self.buy_trades} + 卖{self.sell_trades})",
            f"  胜率:           {self.win_rate:.1%}",
            f"  盈亏比:         {self.profit_loss_ratio:.2f}",
            f"  总交易费用:     {self.total_fees:,.2f} 元",
            "",
        ]
        verdict = _verdict(self)
        if verdict:
            lines.append(f"  综合评价: {verdict}")
            lines.append("")
        return "\n".join(lines)


def _verdict(s: PerformanceStats) -> str:
    if s.trading_days == 0:
        return "回测期间无交易数据"
    if s.total_trades == 0:
        return "回测期间未产生任何交易"
    parts = []
    if s.annualized_return > 0.15:
        parts.append("年化收益优秀")
    elif s.annualized_return > 0.08:
        parts.append("年化收益良好")
    elif s.annualized_return > 0:
        parts.append("年化收益一般")
    else:
        parts.append("策略亏损")

    if s.max_drawdown < 0.05:
        parts.append("回撤控制极佳")
    elif s.max_drawdown < 0.10:
        parts.append("回撤控制良好")
    elif s.max_drawdown < 0.20:
        parts.append("回撤尚可")
    else:
        parts.append("回撤偏大")

    if s.sharpe_ratio > 1.5:
        parts.append("夏普比率优秀")
    elif s.sharpe_ratio > 1.0:
        parts.append("夏普比率良好")
    elif s.sharpe_ratio > 0.5:
        parts.append("夏普比率一般")

    return "，".join(parts)


def compute_stats(result: BacktestResult) -> PerformanceStats:
    """从回测结果计算绩效指标"""
    stats = PerformanceStats()
    snaps = result.daily_snapshots
    trades = result.trades

    if not snaps:
        return stats

    stats.trading_days = len(snaps)

    # 总收益率
    stats.total_return = (result.final_value / result.initial_capital) - 1

    # 年化收益率
    years = stats.trading_days / TRADING_DAYS_PER_YEAR
    if years > 0 and result.final_value > 0:
        stats.annualized_return = (result.final_value / result.initial_capital) ** (1 / years) - 1
    else:
        stats.annualized_return = 0.0

    # 最大回撤
    peak = snaps[0].net_value
    max_dd = 0.0
    dd_start = snaps[0].date
    dd_end = snaps[0].date
    temp_start = snaps[0].date
    for snap in snaps:
        if snap.net_value > peak:
            peak = snap.net_value
            temp_start = snap.date
        dd = (peak - snap.net_value) / peak if peak > 0 else 0
        if dd > max_dd:
            max_dd = dd
            dd_start = temp_start
            dd_end = snap.date

    stats.max_drawdown = max_dd
    stats.max_drawdown_start = dd_start
    stats.max_drawdown_end = dd_end

    # 日收益率序列
    daily_returns = []
    for i in range(1, len(snaps)):
        prev_nv = snaps[i - 1].net_value
        if prev_nv > 0:
            daily_returns.append(snaps[i].net_value / prev_nv - 1)

    # 年化波动率
    if len(daily_returns) > 1:
        mean_r = sum(daily_returns) / len(daily_returns)
        var = sum((r - mean_r) ** 2 for r in daily_returns) / (len(daily_returns) - 1)
        daily_vol = math.sqrt(var)
        stats.annualized_volatility = daily_vol * math.sqrt(TRADING_DAYS_PER_YEAR)
    else:
        stats.annualized_volatility = 0.0

    # 夏普比率
    if stats.annualized_volatility > 0:
        stats.sharpe_ratio = (stats.annualized_return - RISK_FREE_RATE) / stats.annualized_volatility
    else:
        stats.sharpe_ratio = 0.0

    # 交易统计
    stats.total_trades = len(trades)
    stats.buy_trades = sum(1 for t in trades if t.direction == "buy")
    stats.sell_trades = sum(1 for t in trades if t.direction == "sell")
    stats.total_fees = sum(t.fee for t in trades)

    # 胜率 + 盈亏比（按完成的买卖配对计算）
    _win, _loss, wins, losses = _compute_trade_pnl(trades)
    total_closed = wins + losses
    stats.win_rate = wins / total_closed if total_closed > 0 else 0.0
    if losses > 0 and _loss != 0:
        avg_win = _win / wins if wins > 0 else 0
        avg_loss = abs(_loss) / losses if losses > 0 else 1
        stats.profit_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 0.0
    else:
        stats.profit_loss_ratio = float("inf") if wins > 0 else 0.0

    # 平均持仓只数
    if snaps:
        stats.avg_positions = sum(s.position_count for s in snaps) / len(snaps)

    return stats


def _compute_trade_pnl(
    trades: list[TradeRecord],
) -> tuple[float, float, int, int]:
    """从交易记录推算胜率：按 code 配对 buy/sell"""
    cost_map: dict[str, list[float]] = {}
    total_profit = 0.0
    total_loss = 0.0
    win_count = 0
    loss_count = 0

    for t in trades:
        if t.direction == "buy":
            cost_map.setdefault(t.cb_code, []).append(t.price)
        elif t.direction == "sell":
            buys = cost_map.get(t.cb_code, [])
            if buys:
                avg_buy = sum(buys) / len(buys)
                pnl_per_unit = t.price - avg_buy
                if pnl_per_unit > 0:
                    total_profit += pnl_per_unit * t.volume / 10
                    win_count += 1
                else:
                    total_loss += pnl_per_unit * t.volume / 10
                    loss_count += 1
                cost_map[t.cb_code] = []

    return total_profit, total_loss, win_count, loss_count
