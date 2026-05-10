# Execution Engine Spec

## 概述

执行引擎负责订单管理、滑点建模、成交撮合和交易成本分析，提供更真实的交易模拟。

## 订单管理

### Order 模型
```python
@dataclass
class Order:
    order_id: str           # UUID
    cb_code: str
    cb_name: str
    direction: str          # "buy" | "sell"
    target_volume: int      # 目标数量
    filled_volume: int      # 已成交数量
    limit_price: float | None  # 限价（None = 市价单）
    status: str             # "pending" | "partial" | "filled" | "cancelled" | "expired"
    created_at: datetime
    updated_at: datetime
    filled_at: datetime | None
    fills: list[Fill]
    reason: str
    ttl_days: int = 3       # 订单有效期（天）

    @property
    def remaining_volume(self) -> int:
        return self.target_volume - self.filled_volume

    @property
    def is_active(self) -> bool:
        return self.status in ("pending", "partial")

    @property
    def avg_fill_price(self) -> float:
        if not self.fills:
            return 0.0
        total_amount = sum(f.price * f.volume for f in self.fills)
        total_volume = sum(f.volume for f in self.fills)
        return total_amount / total_volume if total_volume > 0 else 0.0


@dataclass(frozen=True)
class Fill:
    fill_id: str
    order_id: str
    price: float
    volume: int
    amount: float
    fee: float
    timestamp: datetime
```

### OrderManager
```python
class OrderManager:
    def __init__(self, slippage_model: SlippageModel):
        self.orders: dict[str, Order] = {}
        self.slippage = slippage_model

    def create_order(
        self, cb_code: str, cb_name: str, direction: str,
        volume: int, reason: str, limit_price: float | None = None,
    ) -> Order:
        """创建订单"""
        order = Order(
            order_id=str(uuid4()),
            cb_code=cb_code, cb_name=cb_name,
            direction=direction, target_volume=volume,
            filled_volume=0, limit_price=limit_price,
            status="pending", created_at=datetime.now(),
            updated_at=datetime.now(), fills=[],
            reason=reason,
        )
        self.orders[order.order_id] = order
        return order

    def match(
        self, market_data: dict[str, MarketBar]
    ) -> list[Fill]:
        """撮合所有活跃订单"""
        fills = []
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

    def cancel_expired(self) -> list[Order]:
        """取消超时订单"""
        now = datetime.now()
        expired = []
        for order in self.orders.values():
            if not order.is_active:
                continue
            age = (now - order.created_at).days
            if age >= order.ttl_days:
                order.status = "expired"
                order.updated_at = now
                expired.append(order)
        return expired

    def get_active_orders(self) -> list[Order]:
        return [o for o in self.orders.values() if o.is_active]

    def get_filled_orders(self) -> list[Order]:
        return [o for o in self.orders.values() if o.status == "filled"]
```

### MarketBar
```python
@dataclass(frozen=True)
class MarketBar:
    cb_code: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    turnover: float
    is_suspended: bool
```

## 滑点模型

### Protocol
```python
class SlippageModel(Protocol):
    def estimate(
        self,
        direction: str,
        price: float,
        volume: int,
        daily_volume: float,
        volatility: float,
    ) -> float:
        """估算成交价格（含滑点）"""
        ...
```

### FixedSlippageModel
```python
class FixedSlippageModel:
    """固定比例滑点"""
    rate: float = 0.001  # 0.1%

    def estimate(self, direction, price, volume, daily_volume, volatility):
        if direction == "buy":
            return price * (1 + self.rate)
        else:
            return price * (1 - self.rate)
```

### VolumeBasedSlippageModel
```python
class VolumeBasedSlippageModel:
    """基于成交量的滑点：成交量占比越大，滑点越大"""
    base_rate: float = 0.0005
    impact_factor: float = 0.1

    def estimate(self, direction, price, volume, daily_volume, volatility):
        participation = volume / max(daily_volume, 1)
        impact = self.base_rate + self.impact_factor * participation
        if direction == "buy":
            return price * (1 + impact)
        else:
            return price * (1 - impact)
```

### VolatilitySlippageModel
```python
class VolatilitySlippageModel:
    """基于波动率的滑点：波动率越大，滑点越大"""
    base_rate: float = 0.0003
    vol_multiplier: float = 0.5

    def estimate(self, direction, price, volume, daily_volume, volatility):
        impact = self.base_rate + self.vol_multiplier * volatility
        if direction == "buy":
            return price * (1 + impact)
        else:
            return price * (1 - impact)
```

## 撮合逻辑

```python
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

    # 计算成交量
    volume = min(order.remaining_volume, int(bar.volume * 0.1))  # 最多吃 10% 日成交量
    if volume <= 0:
        return None

    # 部分成交
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
```

## 交易成本分析 (TCA)

### TransactionCostAnalyzer
```python
@dataclass
class TCAResult:
    order_id: str
    cb_code: str
    direction: str
    decision_price: float       # 决策时价格
    execution_price: float      # 实际成交价
    benchmark_price: float      # 基准价（VWAP 或开盘价）
    volume: int

    implementation_shortfall: float  # 实现差额
    market_impact: float             # 市场冲击
    timing_cost: float               # 时机成本
    spread_cost: float               # 价差成本
    commission: float                # 佣金
    total_cost: float                # 总成本

    @property
    def cost_bps(self) -> float:
        """成本（基点）"""
        notional = self.execution_price * self.volume / 10
        return self.total_cost / notional * 10000 if notional > 0 else 0


class TransactionCostAnalyzer:
    def analyze(self, order: Order, decision_price: float) -> TCAResult:
        """分析单笔交易的执行成本"""
        avg_price = order.avg_fill_price
        volume = order.filled_volume
        benchmark = decision_price  # 简化：用决策价作为基准

        shortfall = (avg_price - decision_price) * volume / 10
        if order.direction == "sell":
            shortfall = -shortfall

        market_impact = abs(avg_price - decision_price) / decision_price
        timing_cost = 0  # 需要 VWAP 数据才能计算
        spread_cost = 0  # 需要 bid/ask 数据才能计算
        commission = sum(f.fee for f in order.fills)

        return TCAResult(
            order_id=order.order_id,
            cb_code=order.cb_code,
            direction=order.direction,
            decision_price=decision_price,
            execution_price=avg_price,
            benchmark_price=benchmark,
            volume=volume,
            implementation_shortfall=shortfall,
            market_impact=market_impact,
            timing_cost=timing_cost,
            spread_cost=spread_cost,
            commission=commission,
            total_cost=abs(shortfall) + commission,
        )

    def generate_report(self, results: list[TCAResult]) -> str:
        """生成 TCA 报告"""
```

## 与 BacktestEngine 集成

现有 BacktestEngine 的 `_execute_orders` 方法重构为使用 OrderManager：

```python
# 旧代码
account.buy(date, code, name, price, volume, reason)

# 新代码
order = order_manager.create_order(code, name, "buy", volume, reason)
fills = order_manager.match(market_data)
for fill in fills:
    account.apply_fill(fill)
```

保留旧接口的向后兼容：VirtualAccount 的 buy/sell 方法内部委托给 OrderManager。
