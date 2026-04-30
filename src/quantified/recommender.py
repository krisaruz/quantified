"""推荐引擎：对比目标持仓与当前持仓，生成人话操作建议

支持：
- 调仓频率控制（仅指定工作日生成操作建议）
- 佣金计算（费用计入建议花费）
- 组合级回撤暂停（高水位跌破阈值时暂停交易）
- 止损 / 卖出 / 买入 / 持有四种操作
- 自然语言建议原因 + 每日操作摘要
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field

import pandas as pd

from quantified.config import AppConfig
from quantified.portfolio import Portfolio
from quantified.scoring import describe_score_factors

DAY_MAP = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}


def calc_fee(amount: float, config: AppConfig) -> float:
    """计算交易佣金"""
    if amount <= 0:
        return 0
    fee = amount * config.fees.commission_rate
    return max(fee, config.fees.min_commission)


def is_rebalance_day(date_str: str, config: AppConfig) -> bool:
    """判断给定日期是否为调仓日"""
    target = DAY_MAP.get(config.strategy.rebalance_day.lower())
    if target is None:
        return True
    dt = datetime.date.fromisoformat(date_str)
    return dt.weekday() == target


@dataclass
class Action:
    """一条操作建议"""

    type: str  # "buy" / "sell" / "hold" / "stop_loss" / "observe"
    cb_code: str
    cb_name: str
    price: float
    reason: str
    volume: int = 0
    double_low: float = 0.0
    premium_rate: float = 0.0
    credit_rating: str = ""
    estimated_cost: float = 0.0
    estimated_fee: float = 0.0


@dataclass
class Recommendation:
    """完整的调仓建议"""

    date: str
    actions: list[Action]
    target_count: int
    current_count: int
    cash: float
    total_value: float
    total_pnl_pct: float = 0.0
    is_rebalance_day: bool = True
    drawdown_paused: bool = False
    summary: str = ""


def _build_summary(rec_partial: dict) -> str:
    """根据建议结构生成自然语言操作摘要"""
    actions = rec_partial.get("actions", [])
    rebalance = rec_partial.get("is_rebalance_day", True)
    paused = rec_partial.get("drawdown_paused", False)
    rebalance_day_name = rec_partial.get("rebalance_day_name", "周五")

    if paused:
        dd = rec_partial.get("drawdown", 0)
        return f"系统检测到组合回撤{dd:.1%}，已超过安全阈值，自动暂停交易建议。请耐心等待市场恢复。"

    stop_count = sum(1 for a in actions if a.type == "stop_loss")
    sell_count = sum(1 for a in actions if a.type == "sell")
    buy_count = sum(1 for a in actions if a.type == "buy")
    hold_count = sum(1 for a in actions if a.type == "hold")

    if not rebalance:
        parts = [f"今天不是调仓日，无需操作。下次调仓日：本{rebalance_day_name}。"]
        if stop_count:
            parts.append(f"注意：{stop_count}只持仓触发止损线，需要立即处理。")
        near_stop = sum(
            1 for a in actions
            if a.type == "observe" and "接近止损" in a.reason
        )
        if near_stop:
            parts.append(f"提醒：{near_stop}只持仓接近止损线，请关注。")
        return "".join(parts)

    parts = [f"今天是调仓日（{rebalance_day_name}）。"]
    ops = []
    if stop_count:
        ops.append(f"止损卖出{stop_count}只")
    if sell_count:
        ops.append(f"卖出{sell_count}只")
    if buy_count:
        ops.append(f"买入{buy_count}只")
    if hold_count:
        ops.append(f"继续持有{hold_count}只")

    if ops:
        parts.append(f"系统建议：{'、'.join(ops)}。")
    else:
        parts.append("当前组合表现良好，无需调仓。")

    return "".join(parts)


_DAY_CN = {
    "monday": "周一", "tuesday": "周二", "wednesday": "周三",
    "thursday": "周四", "friday": "周五", "saturday": "周六", "sunday": "周日",
}


class Recommender:
    """推荐引擎"""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def generate(
        self,
        universe_df: pd.DataFrame,
        portfolio: Portfolio,
        date: str | None = None,
    ) -> Recommendation:
        date = date or datetime.date.today().isoformat()
        hold_count = self.config.strategy.hold_count
        buffer = self.config.strategy.buffer_rank
        rebalance = is_rebalance_day(date, self.config)
        initial_capital = self.config.capital.initial
        actions: list[Action] = []

        # 计算当前总资产（用于回撤检查）
        total = portfolio.cash
        for h in portfolio.holdings:
            row = universe_df[universe_df["cb_code"] == h.cb_code]
            if not row.empty:
                total += float(row.iloc[0]["cb_close"]) * h.volume / 10
            else:
                total += h.buy_price * h.volume / 10

        total_pnl_pct = (total - initial_capital) / initial_capital if initial_capital > 0 else 0

        # 回撤暂停检查
        high_water = max(total, portfolio.high_water_mark)
        portfolio.high_water_mark = high_water
        drawdown = (total - high_water) / high_water if high_water > 0 else 0
        drawdown_paused = drawdown <= self.config.risk.max_drawdown_pct

        rebalance_day_cn = _DAY_CN.get(self.config.strategy.rebalance_day.lower(), "周五")

        if drawdown_paused:
            pause_actions = [Action(
                type="observe", cb_code="", cb_name="",
                price=0,
                reason=f"组合回撤{drawdown:.1%}超过安全阈值{self.config.risk.max_drawdown_pct:.0%}，系统已自动暂停交易",
            )]
            summary = _build_summary({
                "actions": pause_actions, "is_rebalance_day": rebalance,
                "drawdown_paused": True, "drawdown": drawdown,
                "rebalance_day_name": rebalance_day_cn,
            })
            return Recommendation(
                date=date, actions=pause_actions,
                target_count=hold_count,
                current_count=len(portfolio.holdings),
                cash=portfolio.cash, total_value=total,
                total_pnl_pct=total_pnl_pct,
                is_rebalance_day=rebalance, drawdown_paused=True,
                summary=summary,
            )

        target_codes = set(universe_df.head(hold_count)["cb_code"]) if len(universe_df) > 0 else set()
        current_codes = portfolio.codes

        # 止损检查（不受 rebalance_day 限制，任何时候都执行）
        for h in portfolio.holdings:
            row = universe_df[universe_df["cb_code"] == h.cb_code]
            if not row.empty:
                current_price = float(row.iloc[0]["cb_close"])
                pnl_pct = (current_price - h.buy_price) / h.buy_price
                if pnl_pct <= self.config.risk.stop_loss_pct:
                    proceeds = current_price * h.volume / 10
                    fee = calc_fee(proceeds, self.config)
                    actions.append(Action(
                        type="stop_loss", cb_code=h.cb_code, cb_name=h.cb_name,
                        price=current_price, volume=h.volume,
                        reason=f"当前亏损{pnl_pct:.1%}，已超过{self.config.risk.stop_loss_pct:.0%}止损线，建议先卖出控制损失",
                        estimated_fee=round(fee, 2),
                    ))
                    current_codes.discard(h.cb_code)

        if not rebalance:
            for code in current_codes:
                if code in {a.cb_code for a in actions}:
                    continue
                h = portfolio.get_holding(code)
                row = universe_df[universe_df["cb_code"] == code]
                if h and not row.empty:
                    r = row.iloc[0]
                    cur_price = float(r["cb_close"])
                    pnl_pct = (cur_price - h.buy_price) / h.buy_price if h.buy_price > 0 else 0
                    near_stop = pnl_pct <= self.config.risk.stop_loss_pct * 0.7
                    reason_parts = [f"非调仓日，继续持有观察"]
                    if near_stop:
                        reason_parts.append(f"接近止损线(当前{pnl_pct:.1%})")
                    actions.append(Action(
                        type="observe", cb_code=code, cb_name=h.cb_name,
                        price=cur_price, volume=h.volume,
                        reason="，".join(reason_parts),
                        double_low=float(r.get("double_low", 0)),
                    ))

            sorted_actions = sorted(actions, key=lambda a: {"stop_loss": 0, "observe": 1}.get(a.type, 2))
            summary = _build_summary({
                "actions": sorted_actions, "is_rebalance_day": False,
                "drawdown_paused": False, "rebalance_day_name": rebalance_day_cn,
            })
            return Recommendation(
                date=date, actions=sorted_actions,
                target_count=len(target_codes),
                current_count=len(portfolio.holdings),
                cash=portfolio.cash, total_value=total,
                total_pnl_pct=total_pnl_pct,
                is_rebalance_day=False, drawdown_paused=False,
                summary=summary,
            )

        # --- 以下为调仓日逻辑 ---

        # 卖出：排名超出 hold_count + buffer 或已不在池中的
        sell_codes = set()
        for code in list(current_codes):
            if code in {a.cb_code for a in actions}:
                continue
            rank_rows = universe_df[universe_df["cb_code"] == code]
            if rank_rows.empty:
                h = portfolio.get_holding(code)
                if h:
                    proceeds = h.buy_price * h.volume / 10
                    fee = calc_fee(proceeds, self.config)
                    actions.append(Action(
                        type="sell", cb_code=code, cb_name=h.cb_name,
                        price=h.buy_price, volume=h.volume,
                        reason="该转债已不满足筛选条件（可能触发强赎/退市/评级下调），建议卖出",
                        estimated_fee=round(fee, 2),
                    ))
                    sell_codes.add(code)
            else:
                rank = rank_rows.index[0]
                if rank >= hold_count + buffer:
                    row = rank_rows.iloc[0]
                    h = portfolio.get_holding(code)
                    market_price = float(row["cb_close"])
                    proceeds = market_price * (h.volume if h else 0) / 10
                    fee = calc_fee(proceeds, self.config)
                    score_desc = describe_score_factors(row) if not row.empty else ""
                    actions.append(Action(
                        type="sell", cb_code=code, cb_name=str(row.get("cb_name", "")),
                        price=market_price, volume=h.volume if h else 0,
                        reason=f"综合排名跌至第{rank + 1}名(超出持仓阈值{hold_count + buffer})，{score_desc}，性价比不再突出",
                        double_low=float(row.get("double_low", 0)),
                        estimated_fee=round(fee, 2),
                    ))
                    sell_codes.add(code)

        # 买入
        remaining_current = current_codes - sell_codes - {a.cb_code for a in actions if a.type in ("sell", "stop_loss")}
        slots = hold_count - len(remaining_current)

        buy_candidates = universe_df[~universe_df["cb_code"].isin(remaining_current)].head(slots)
        for _, row in buy_candidates.iterrows():
            code = str(row["cb_code"])
            if code in current_codes:
                continue
            price = float(row["cb_close"])
            max_invest = portfolio.cash * self.config.risk.max_position_pct
            volume = max(int(max_invest / price / 10) * 10, 10)
            cost = price * volume / 10
            fee = calc_fee(cost, self.config)

            score_desc = describe_score_factors(row)
            rank_num = row.name + 1 if hasattr(row, "name") and isinstance(row.name, int) else 0
            actions.append(Action(
                type="buy", cb_code=code, cb_name=str(row.get("cb_name", "")),
                price=price, volume=volume,
                reason=f"综合评分全场第{rank_num}名：{score_desc}",
                double_low=float(row.get("double_low", 0)),
                premium_rate=float(row.get("premium_rate", 0)),
                credit_rating=str(row.get("credit_rating", "")),
                estimated_cost=round(cost + fee, 2),
                estimated_fee=round(fee, 2),
            ))

        for code in remaining_current:
            if code in {a.cb_code for a in actions}:
                continue
            h = portfolio.get_holding(code)
            row = universe_df[universe_df["cb_code"] == code]
            if h and not row.empty:
                r = row.iloc[0]
                rank_num = r.name + 1 if hasattr(r, "name") and isinstance(r.name, int) else 0
                actions.append(Action(
                    type="hold", cb_code=code, cb_name=h.cb_name,
                    price=float(r["cb_close"]), volume=h.volume,
                    reason=f"综合排名第{rank_num}名，保持在持仓范围内，继续持有",
                    double_low=float(r.get("double_low", 0)),
                ))

        type_order = {"stop_loss": 0, "sell": 1, "buy": 2, "hold": 3, "observe": 4}
        sorted_actions = sorted(actions, key=lambda a: type_order.get(a.type, 9))
        summary = _build_summary({
            "actions": sorted_actions, "is_rebalance_day": True,
            "drawdown_paused": False, "rebalance_day_name": rebalance_day_cn,
        })
        return Recommendation(
            date=date, actions=sorted_actions,
            target_count=len(target_codes),
            current_count=len(portfolio.holdings),
            cash=portfolio.cash, total_value=total,
            total_pnl_pct=total_pnl_pct,
            is_rebalance_day=True, drawdown_paused=False,
            summary=summary,
        )


def format_recommendation(rec: Recommendation, config: AppConfig | None = None) -> str:
    """将推荐结果格式化为人类可读文本"""
    lines = [f"\n{'='*50}", f"  {rec.date} 调仓建议", f"{'='*50}"]

    if not rec.is_rebalance_day:
        lines.append("  [非调仓日] 仅执行止损检查\n")
    if rec.drawdown_paused:
        lines.append("  [回撤暂停] 组合回撤触发阈值，暂停交易\n")

    stop_losses = [a for a in rec.actions if a.type == "stop_loss"]
    sells = [a for a in rec.actions if a.type == "sell"]
    buys = [a for a in rec.actions if a.type == "buy"]
    holds = [a for a in rec.actions if a.type == "hold"]
    observes = [a for a in rec.actions if a.type == "observe"]

    if stop_losses:
        lines.append(f"\n  [止损卖出] {len(stop_losses)} 只:")
        for a in stop_losses:
            lines.append(f"    {a.cb_name} ({a.cb_code})  {a.volume}张  现价{a.price:.1f}元")
            lines.append(f"    原因: {a.reason}")
            if a.estimated_fee > 0:
                lines.append(f"    佣金: {a.estimated_fee:.2f} 元")

    if sells:
        lines.append(f"\n  [卖出] {len(sells)} 只:")
        for a in sells:
            lines.append(f"    {a.cb_name} ({a.cb_code})  {a.volume}张  现价{a.price:.1f}元")
            lines.append(f"    原因: {a.reason}")

    if buys:
        lines.append(f"\n  [买入] {len(buys)} 只:")
        for a in buys:
            lines.append(f"    {a.cb_name} ({a.cb_code})  建议{a.volume}张  现价{a.price:.1f}元")
            lines.append(f"    {a.reason} | 溢价率{a.premium_rate:.1%} | {a.credit_rating}")
            lines.append(f"    预计花费: {a.estimated_cost:,.0f} 元 (含佣金 {a.estimated_fee:.2f})")

    if holds:
        lines.append(f"\n  [继续持有] {len(holds)} 只:")
        for a in holds:
            lines.append(f"    {a.cb_name} ({a.cb_code})  {a.volume}张  {a.reason}")

    if observes and not holds and not buys:
        lines.append(f"\n  [观察] {len(observes)} 只:")
        for a in observes:
            if a.cb_code:
                lines.append(f"    {a.cb_name} ({a.cb_code})  {a.reason}")
            else:
                lines.append(f"    {a.reason}")

    if not any([stop_losses, sells, buys]):
        lines.append("\n  无需调仓，继续持有当前组合")

    initial = config.capital.initial if config else 100000
    lines.append(f"\n  {'─'*46}")
    lines.append(f"  可用资金: {rec.cash:,.0f} 元 | 总资产: {rec.total_value:,.0f} 元")
    lines.append(f"  收益率: {rec.total_pnl_pct:+.2%}\n")

    return "\n".join(lines)
