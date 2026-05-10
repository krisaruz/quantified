"""订单管理器

负责订单的创建、撮合和生命周期管理。
"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from vertexquant.execution.models import Fill, MarketBar, Order
from vertexquant.execution.slippage import FixedSlippageModel, SlippageModel


class OrderManager:
    """订单管理器"""

    def __init__(self, slippage_model: SlippageModel | None = None) -> None:
        self.orders: dict[str, Order] = {}
        self.slippage = slippage_model or FixedSlippageModel()

    def create_order(
        self,
        cb_code: str,
        cb_name: str,
        direction: str,
        volume: int,
        reason: str,
        limit_price: float | None = None,
        ttl_days: int = 3,
    ) -> Order:
        """创建订单"""
        order = Order(
            order_id=str(uuid4()),
            cb_code=cb_code,
            cb_name=cb_name,
            direction=direction,
            target_volume=volume,
            filled_volume=0,
            limit_price=limit_price,
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            fills=[],
            reason=reason,
            ttl_days=ttl_days,
        )
        self.orders[order.order_id] = order
        return order

    def match(
        self, market_data: dict[str, MarketBar]
    ) -> list[Fill]:
        """撮合所有活跃订单"""
        fills: list[Fill] = []
        for order in self.orders.values():
            if not order.is_active:
                continue
            bar = market_data.get(order.cb_code)
            if bar is None:
                continue
            fill = self._try_fill(order, bar)
            if fill:
                fills.append(fill)
        return fills

    def cancel_expired(self, now: datetime | None = None) -> list[Order]:
        """取消超时订单"""
        now = now or datetime.now()
        expired: list[Order] = []
        for order in self.orders.values():
            if not order.is_active:
                continue
            age = (now - order.created_at).days
            if age >= order.ttl_days:
                order.status = "expired"
                order.updated_at = now
                expired.append(order)
        return expired

    def cancel_order(self, order_id: str) -> bool:
        """手动取消订单"""
        order = self.orders.get(order_id)
        if order and order.is_active:
            order.status = "cancelled"
            order.updated_at = datetime.now()
            return True
        return False

    def get_active_orders(self) -> list[Order]:
        """获取所有活跃订单"""
        return [o for o in self.orders.values() if o.is_active]

    def get_filled_orders(self) -> list[Order]:
        """获取所有已成交订单"""
        return [o for o in self.orders.values() if o.status == "filled"]

    def get_order(self, order_id: str) -> Order | None:
        """获取单个订单"""
        return self.orders.get(order_id)

    def _try_fill(self, order: Order, bar: MarketBar) -> Fill | None:
        """尝试撮合单个订单"""
        if bar.is_suspended:
            return None

        # 限价单检查
        if order.limit_price is not None:
            if order.direction == "buy" and bar.open > order.limit_price:
                return None
            if order.direction == "sell" and bar.open < order.limit_price:
                return None

        # 计算成交量：最多吃 10% 日成交量
        max_volume = int(bar.volume * 0.1)
        volume = min(order.remaining_volume, max_volume)
        if volume <= 0:
            return None

        # 更新订单状态
        if volume < order.remaining_volume:
            order.status = "partial"
        else:
            order.status = "filled"
            order.filled_at = datetime.now()

        # 计算成交价（含滑点）
        volatility = (bar.high - bar.low) / bar.close if bar.close > 0 else 0
        exec_price = self.slippage.estimate(
            order.direction, bar.open, volume, bar.volume, volatility
        )

        # 可转债面值 100 元，每张 10 张为 1 手
        amount = exec_price * volume / 10
        fee = max(amount * 0.0002, 0.1)

        fill = Fill(
            fill_id=str(uuid4()),
            order_id=order.order_id,
            price=exec_price,
            volume=volume,
            amount=amount,
            fee=fee,
            timestamp=datetime.now(),
        )

        order.filled_volume += volume
        order.fills.append(fill)
        order.updated_at = datetime.now()

        return fill
