"""虚拟账户 —— T+1 持仓状态机

严格模拟 A 股可转债 T+0 交易规则：
- 转债实际是 T+0，但为保守策略设计，本系统按 T+1 模拟
- 买入后当日冻结，次日可卖
- 卖出只能卖 available 部分
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class Position:
    """单只持仓"""

    cb_code: str
    cb_name: str
    available: int = 0
    frozen: int = 0
    avg_cost: float = 0.0
    total_cost: float = 0.0

    @property
    def total_volume(self) -> int:
        return self.available + self.frozen

    def market_value(self, price: float) -> float:
        return price * self.total_volume / 10


class InsufficientFundsError(Exception):
    pass


class InsufficientVolumeError(Exception):
    pass


@dataclass
class TradeRecord:
    """单笔交易记录"""

    date: str
    cb_code: str
    cb_name: str
    direction: str  # "buy" or "sell"
    price: float
    volume: int
    amount: float
    fee: float
    reason: str = ""


class VirtualAccount:
    """虚拟交易账户"""

    def __init__(
        self,
        initial_capital: float = 100000.0,
        commission_rate: float = 0.0002,
        min_commission: float = 0.1,
        slippage: float = 0.001,
    ) -> None:
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.min_commission = min_commission
        self.slippage = slippage
        self.positions: dict[str, Position] = {}
        self.trades: list[TradeRecord] = []
        self.total_fees = 0.0

    def settle(self) -> None:
        """日初结算：frozen -> available"""
        for pos in self.positions.values():
            pos.available += pos.frozen
            pos.frozen = 0

    def _calc_fee(self, amount: float) -> float:
        fee = amount * self.commission_rate
        return max(fee, self.min_commission) if amount > 0 else 0.0

    def buy(
        self,
        date: str,
        cb_code: str,
        cb_name: str,
        price: float,
        volume: int,
        reason: str = "",
    ) -> TradeRecord | None:
        """买入（含滑点），资金不足时尽量买入能买的最大量"""
        exec_price = price * (1 + self.slippage)
        amount = exec_price * volume / 10
        fee = self._calc_fee(amount)
        total = amount + fee

        if total > self.cash:
            max_vol = int(self.cash / (exec_price / 10 + self._calc_fee(exec_price / 10)))
            max_vol = (max_vol // 10) * 10
            if max_vol <= 0:
                return None
            volume = max_vol
            amount = exec_price * volume / 10
            fee = self._calc_fee(amount)
            total = amount + fee

        self.cash -= total
        self.total_fees += fee

        if cb_code in self.positions:
            pos = self.positions[cb_code]
            old_total = pos.total_cost
            pos.total_cost = old_total + amount
            pos.frozen += volume
            pos.avg_cost = pos.total_cost / (pos.total_volume / 10) if pos.total_volume > 0 else exec_price
        else:
            self.positions[cb_code] = Position(
                cb_code=cb_code,
                cb_name=cb_name,
                available=0,
                frozen=volume,
                avg_cost=exec_price,
                total_cost=amount,
            )

        trade = TradeRecord(
            date=date, cb_code=cb_code, cb_name=cb_name,
            direction="buy", price=exec_price, volume=volume,
            amount=amount, fee=fee, reason=reason,
        )
        self.trades.append(trade)
        return trade

    def sell(
        self,
        date: str,
        cb_code: str,
        price: float,
        volume: int | None = None,
        reason: str = "",
    ) -> TradeRecord | None:
        """卖出（含滑点），默认全部卖出 available"""
        if cb_code not in self.positions:
            return None
        pos = self.positions[cb_code]
        if volume is None:
            volume = pos.available
        if volume <= 0 or pos.available < volume:
            return None

        exec_price = price * (1 - self.slippage)
        amount = exec_price * volume / 10
        fee = self._calc_fee(amount)
        net = amount - fee

        self.cash += net
        self.total_fees += fee

        cost_per_unit = pos.avg_cost / 10
        pos.total_cost -= cost_per_unit * volume
        pos.available -= volume

        trade = TradeRecord(
            date=date, cb_code=cb_code, cb_name=pos.cb_name,
            direction="sell", price=exec_price, volume=volume,
            amount=amount, fee=fee, reason=reason,
        )
        self.trades.append(trade)

        if pos.total_volume == 0:
            del self.positions[cb_code]

        return trade

    def net_value(self, prices: dict[str, float]) -> float:
        """按市价计算总净值"""
        market = sum(
            pos.market_value(prices.get(code, pos.avg_cost))
            for code, pos in self.positions.items()
        )
        return self.cash + market

    def holding_codes(self) -> set[str]:
        return set(self.positions.keys())

    def position_summary(self, prices: dict[str, float]) -> list[dict]:
        """当前持仓摘要"""
        result = []
        for code, pos in self.positions.items():
            price = prices.get(code, pos.avg_cost)
            mv = pos.market_value(price)
            pnl = mv - pos.total_cost
            result.append({
                "cb_code": code,
                "cb_name": pos.cb_name,
                "volume": pos.total_volume,
                "avg_cost": round(pos.avg_cost, 3),
                "current_price": price,
                "market_value": round(mv, 2),
                "pnl": round(pnl, 2),
            })
        return result
