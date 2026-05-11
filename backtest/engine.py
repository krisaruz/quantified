"""回测引擎 —— 日频策略模拟

核心循环：
  for each trading_day in [start .. end]:
      1. 日初结算  (frozen -> available)
      2. 事件检测  (退市/强赎 -> 强制卖出)
      3. 策略执行  (build_filtered_ranked -> 排名)
      4. 信号生成  (diff target vs current -> buy/sell)
      5. 撮合成交  (T日信号, T+1日开盘价)
      6. 日终记账  (记录净值、持仓快照)

关键约束：
  - 无未来函数：T 日决策只用 T 日及以前数据
  - T+1 成交：信号在次日按开盘价撮合
  - 停牌跳过：无行情时取消订单
"""

from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field

import pandas as pd
from sqlalchemy.orm import Session

from vertexquant.backtest.account import TradeRecord, VirtualAccount
from vertexquant.config import AppConfig
from vertexquant.models.bond import BondDaily
from vertexquant.models.stock import StockDaily
from vertexquant.recommender import DAY_MAP

logger = logging.getLogger(__name__)


@dataclass
class DailySnapshot:
    """单日快照"""
    date: str
    net_value: float
    cash: float
    market_value: float
    position_count: int


@dataclass
class PendingOrder:
    """待执行订单（T日生成，T+1撮合）"""
    cb_code: str
    cb_name: str
    direction: str  # "buy" / "sell"
    target_volume: int
    reason: str


@dataclass
class BacktestResult:
    """回测结果"""
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    daily_snapshots: list[DailySnapshot] = field(default_factory=list)
    trades: list[TradeRecord] = field(default_factory=list)
    trading_days: int = 0
    skipped_days: int = 0


class BacktestEngine:
    """日频回测引擎"""

    def __init__(self, config: AppConfig, session: Session) -> None:
        self.config = config
        self.session = session

    def run(self, start_date: str, end_date: str) -> BacktestResult:
        """执行回测"""
        account = VirtualAccount(
            initial_capital=self.config.capital.initial,
            commission_rate=self.config.fees.commission_rate,
            min_commission=self.config.fees.min_commission,
        )

        trading_days = self._get_trading_days(start_date, end_date)
        if not trading_days:
            logger.warning("回测区间内无交易日数据")
            return BacktestResult(
                start_date=start_date, end_date=end_date,
                initial_capital=self.config.capital.initial,
                final_value=self.config.capital.initial,
            )

        logger.info("回测区间: %s ~ %s, 共 %d 个交易日", start_date, end_date, len(trading_days))

        result = BacktestResult(
            start_date=start_date, end_date=end_date,
            initial_capital=self.config.capital.initial,
            final_value=self.config.capital.initial,
        )

        pending_orders: list[PendingOrder] = []
        high_water = self.config.capital.initial
        skipped = 0

        for i, day in enumerate(trading_days):
            day_str = day.isoformat()

            # 1. 日初结算
            account.settle()

            # 2. 撮合昨日挂单（用今日开盘价）
            if pending_orders:
                self._execute_orders(account, pending_orders, day_str)
                pending_orders = []

            # 3. 构建当日截面
            try:
                from vertexquant.universe import build_filtered_ranked
                universe, filtered, _ = build_filtered_ranked(
                    self.session, day_str, self.config,
                )
            except Exception:
                skipped += 1
                continue

            if universe.empty:
                skipped += 1
                continue

            # 获取当日价格映射
            prices = dict(zip(universe["cb_code"], universe["cb_close"]))

            # 4. 事件检测：退市持仓强制卖出
            self._handle_delisted(account, universe, day_str)

            # 5. 回撤暂停检查
            nv = account.net_value(prices)
            high_water = max(high_water, nv)
            drawdown = (nv - high_water) / high_water if high_water > 0 else 0

            if drawdown <= self.config.risk.max_drawdown_pct:
                snap = DailySnapshot(
                    date=day_str, net_value=nv, cash=account.cash,
                    market_value=nv - account.cash,
                    position_count=len(account.positions),
                )
                result.daily_snapshots.append(snap)
                continue

            # 6. 止损检查（每日）
            self._check_stop_loss(account, prices, day_str, pending_orders)

            # 7. 调仓信号（仅调仓日）
            if self._is_rebalance_day(day):
                self._generate_rebalance_signals(
                    account, filtered, prices, day_str, pending_orders,
                )

            # 8. 日终记账
            nv = account.net_value(prices)
            high_water = max(high_water, nv)
            snap = DailySnapshot(
                date=day_str, net_value=nv, cash=account.cash,
                market_value=nv - account.cash,
                position_count=len(account.positions),
            )
            result.daily_snapshots.append(snap)

            if (i + 1) % 50 == 0:
                logger.info(
                    "回测进度: %d/%d  净值: %.2f  持仓: %d只",
                    i + 1, len(trading_days), nv, len(account.positions),
                )

        result.final_value = result.daily_snapshots[-1].net_value if result.daily_snapshots else account.cash
        result.trades = account.trades
        result.trading_days = len(trading_days) - skipped
        result.skipped_days = skipped

        logger.info(
            "回测完成: %.2f -> %.2f (%.2f%%), %d笔交易, %d个交易日",
            result.initial_capital, result.final_value,
            (result.final_value / result.initial_capital - 1) * 100,
            len(result.trades), result.trading_days,
        )
        return result

    def _get_trading_days(self, start: str, end: str) -> list[datetime.date]:
        """从 BondDaily 表获取有数据的交易日列表"""
        sd = datetime.date.fromisoformat(start)
        ed = datetime.date.fromisoformat(end)
        rows = (
            self.session.query(BondDaily.trade_date)
            .filter(BondDaily.trade_date >= sd, BondDaily.trade_date <= ed)
            .distinct()
            .order_by(BondDaily.trade_date)
            .all()
        )
        return [r[0] for r in rows]

    def _execute_orders(
        self,
        account: VirtualAccount,
        orders: list[PendingOrder],
        today_str: str,
    ) -> None:
        """用今日开盘价撮合昨日挂单"""
        today = datetime.date.fromisoformat(today_str)
        for order in orders:
            if order.direction == "buy":
                row = (
                    self.session.query(BondDaily.open)
                    .filter(BondDaily.cb_code == order.cb_code, BondDaily.trade_date == today)
                    .first()
                )
                if not row or row[0] <= 0:
                    continue
                open_price = row[0]
                account.buy(
                    today_str, order.cb_code, order.cb_name,
                    open_price, order.target_volume, order.reason,
                )

            elif order.direction == "sell":
                row = (
                    self.session.query(BondDaily.open)
                    .filter(BondDaily.cb_code == order.cb_code, BondDaily.trade_date == today)
                    .first()
                )
                if not row or row[0] <= 0:
                    continue
                open_price = row[0]
                account.sell(
                    today_str, order.cb_code, open_price,
                    reason=order.reason,
                )

    def _handle_delisted(
        self, account: VirtualAccount, universe: pd.DataFrame, day_str: str,
    ) -> None:
        """强制卖出退市/不在池中的持仓"""
        for code in list(account.holding_codes()):
            row = universe[universe["cb_code"] == code]
            if row.empty:
                continue
            status = row.iloc[0].get("status", "")
            if status == "delisted":
                price = float(row.iloc[0]["cb_close"])
                account.sell(day_str, code, price, reason="退市强制卖出")

    def _check_stop_loss(
        self,
        account: VirtualAccount,
        prices: dict[str, float],
        day_str: str,
        pending: list[PendingOrder],
    ) -> None:
        """止损检查：亏损超阈值的持仓生成卖出订单"""
        stop_pct = self.config.risk.stop_loss_pct
        for code, pos in list(account.positions.items()):
            if pos.available <= 0:
                continue
            cur = prices.get(code, pos.avg_cost)
            pnl = (cur - pos.avg_cost) / pos.avg_cost if pos.avg_cost > 0 else 0
            if pnl <= stop_pct:
                pending.append(PendingOrder(
                    cb_code=code, cb_name=pos.cb_name,
                    direction="sell", target_volume=pos.available,
                    reason=f"止损({pnl:.1%})",
                ))

    def _generate_rebalance_signals(
        self,
        account: VirtualAccount,
        filtered: pd.DataFrame,
        prices: dict[str, float],
        day_str: str,
        pending: list[PendingOrder],
    ) -> None:
        """调仓日信号生成"""
        if filtered.empty:
            return

        hold_count = self.config.strategy.hold_count
        buffer = self.config.strategy.buffer_rank

        target_codes = set(filtered.head(hold_count)["cb_code"])
        current_codes = account.holding_codes()
        pending_sell_codes = {o.cb_code for o in pending if o.direction == "sell"}

        # 卖出信号
        for code in list(current_codes - pending_sell_codes):
            rank_rows = filtered[filtered["cb_code"] == code]
            should_sell = False
            if rank_rows.empty:
                should_sell = True
                reason = "不满足筛选条件"
            else:
                rank = rank_rows.index[0]
                if rank >= hold_count + buffer:
                    should_sell = True
                    reason = f"排名{rank+1}(超阈值{hold_count+buffer})"

            if should_sell:
                pos = account.positions.get(code)
                if pos and pos.available > 0:
                    pending.append(PendingOrder(
                        cb_code=code, cb_name=pos.cb_name,
                        direction="sell", target_volume=pos.available,
                        reason=reason,
                    ))

        # 买入信号
        remaining = current_codes - pending_sell_codes - {o.cb_code for o in pending if o.direction == "sell"}
        slots = max(0, hold_count - len(remaining))
        if slots <= 0:
            return

        candidates = filtered[~filtered["cb_code"].isin(remaining)].head(slots)
        for _, row in candidates.iterrows():
            code = str(row["cb_code"])
            if code in current_codes:
                continue
            price = float(row["cb_close"])
            if price <= 0:
                continue
            nv = account.net_value(prices)
            max_invest = nv * self.config.risk.max_position_pct
            volume = max(int(max_invest / price * 10 / 10) * 10, 10)

            pending.append(PendingOrder(
                cb_code=code,
                cb_name=str(row.get("cb_name", code)),
                direction="buy",
                target_volume=volume,
                reason=f"排名{row.name + 1 if isinstance(row.name, int) else '?'}",
            ))

    def _is_rebalance_day(self, day: datetime.date) -> bool:
        target = DAY_MAP.get(self.config.strategy.rebalance_day.lower())
        if target is None:
            return True
        return day.weekday() == target
