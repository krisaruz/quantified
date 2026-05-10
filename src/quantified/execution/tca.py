"""交易成本分析 (TCA)

分析订单的执行成本，包括实现差额、市场冲击等。
"""

from __future__ import annotations

from dataclasses import dataclass

from quantified.execution.models import Fill, Order


@dataclass(frozen=True)
class TCAResult:
    """TCA 分析结果"""

    order_id: str
    cb_code: str
    direction: str
    decision_price: float
    execution_price: float
    benchmark_price: float
    volume: int
    implementation_shortfall: float
    market_impact: float
    timing_cost: float
    spread_cost: float
    commission: float
    total_cost: float

    @property
    def cost_bps(self) -> float:
        """成本（基点）"""
        notional = self.execution_price * self.volume / 10
        return self.total_cost / notional * 10000 if notional > 0 else 0


class TransactionCostAnalyzer:
    """交易成本分析器"""

    def analyze(
        self,
        order: Order,
        decision_price: float,
    ) -> TCAResult | None:
        """分析单笔交易的执行成本

        Args:
            order: 已完成的订单
            decision_price: 决策时的价格
        """
        if not order.fills:
            return None

        avg_price = order.avg_fill_price
        volume = order.filled_volume
        benchmark = decision_price

        # 实现差额
        shortfall = (avg_price - decision_price) * volume / 10
        if order.direction == "sell":
            shortfall = -shortfall

        # 市场冲击
        market_impact = abs(avg_price - decision_price) / decision_price

        # 佣金
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
            timing_cost=0.0,
            spread_cost=0.0,
            commission=commission,
            total_cost=abs(shortfall) + commission,
        )

    def analyze_batch(
        self,
        orders: list[Order],
        decision_prices: dict[str, float],
    ) -> list[TCAResult]:
        """批量分析订单执行成本"""
        results: list[TCAResult] = []
        for order in orders:
            price = decision_prices.get(order.order_id)
            if price is not None:
                result = self.analyze(order, price)
                if result:
                    results.append(result)
        return results

    def generate_report(self, results: list[TCAResult]) -> str:
        """生成 TCA 报告"""
        if not results:
            return "无交易记录"

        lines: list[str] = []
        lines.append("# 交易成本分析报告\n")
        lines.append(f"共 {len(results)} 笔交易\n")

        # 汇总
        total_cost = sum(r.total_cost for r in results)
        total_commission = sum(r.commission for r in results)
        total_shortfall = sum(r.implementation_shortfall for r in results)
        avg_bps = sum(r.cost_bps for r in results) / len(results)

        lines.append("## 汇总\n")
        lines.append("| 指标 | 值 |")
        lines.append("|------|-----|")
        lines.append(f"| 总成本 | {total_cost:.2f} |")
        lines.append(f"| 总佣金 | {total_commission:.2f} |")
        lines.append(f"| 总实现差额 | {total_shortfall:+.2f} |")
        lines.append(f"| 平均成本(bps) | {avg_bps:.1f} |")
        lines.append("")

        # 明细
        lines.append("## 明细\n")
        lines.append("| 订单 | 标的 | 方向 | 决策价 | 成交价 | 数量 | 成本(bps) |")
        lines.append("|------|------|------|--------|--------|------|-----------|")
        for r in results:
            lines.append(
                f"| {r.order_id[:8]} | {r.cb_code} | {r.direction} | "
                f"{r.decision_price:.2f} | {r.execution_price:.2f} | "
                f"{r.volume} | {r.cost_bps:.1f} |"
            )

        return "\n".join(lines)
