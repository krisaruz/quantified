"""策略健康度评估"""

from __future__ import annotations

from dataclasses import dataclass

from quantified.monitoring.models import MonitorContext


@dataclass(frozen=True)
class HealthBreakdown:
    """健康度分项评分"""

    data_freshness: float
    diversification: float
    stability: float
    drawdown: float
    execution: float
    total: float


class HealthScore:
    """策略健康度评分器（0-100）"""

    def calculate(self, ctx: MonitorContext) -> float:
        """计算策略健康度评分"""
        breakdown = self.calculate_breakdown(ctx)
        return breakdown.total

    def calculate_breakdown(self, ctx: MonitorContext) -> HealthBreakdown:
        """计算各维度健康度评分"""
        data_score = self._data_freshness_score(ctx)
        div_score = self._diversification_score(ctx)
        stab_score = self._return_stability_score(ctx)
        dd_score = self._drawdown_score(ctx)
        exec_score = self._execution_score(ctx)

        total = (
            data_score * 0.2
            + div_score * 0.2
            + stab_score * 0.2
            + dd_score * 0.2
            + exec_score * 0.2
        )

        return HealthBreakdown(
            data_freshness=data_score,
            diversification=div_score,
            stability=stab_score,
            drawdown=dd_score,
            execution=exec_score,
            total=round(total, 1),
        )

    def _data_freshness_score(self, ctx: MonitorContext) -> float:
        """数据新鲜度评分：0-100"""
        last_sync = ctx.data_meta.get("last_sync_bond_daily")
        if not last_sync:
            return 0

        try:
            from datetime import datetime

            last_date = datetime.fromisoformat(last_sync).date()
            age = (datetime.now().date() - last_date).days
        except (ValueError, TypeError):
            return 0

        if age == 0:
            return 100
        if age <= 1:
            return 90
        if age <= 3:
            return 70
        if age <= 7:
            return 40
        return 10

    def _diversification_score(self, ctx: MonitorContext) -> float:
        """持仓分散度评分：基于 Herfindahl 指数"""
        if not ctx.holdings:
            return 50

        total = ctx.cash
        for h in ctx.holdings:
            buy_price = getattr(h, "buy_price", 0)
            volume = getattr(h, "volume", 0)
            total += buy_price * volume / 10

        if total <= 0:
            return 50

        weights = []
        for h in ctx.holdings:
            buy_price = getattr(h, "buy_price", 0)
            volume = getattr(h, "volume", 0)
            w = (buy_price * volume / 10) / total
            weights.append(w)

        hhi = sum(w ** 2 for w in weights)
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 1

        if min_hhi >= 1:
            return 50

        score = (1 - (hhi - min_hhi) / (1 - min_hhi)) * 100
        return max(0, min(100, score))

    def _return_stability_score(self, ctx: MonitorContext) -> float:
        """收益稳定性评分：基于收益率的变异系数"""
        if len(ctx.recent_snapshots) < 10:
            return 50

        returns: list[float] = []
        for i in range(1, len(ctx.recent_snapshots)):
            prev = getattr(ctx.recent_snapshots[i - 1], "net_value", 0)
            curr = getattr(ctx.recent_snapshots[i], "net_value", 0)
            if prev > 0:
                returns.append(curr / prev - 1)

        if not returns:
            return 50

        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std = var ** 0.5
        cv = abs(std / mean_r) if mean_r != 0 else 999

        score = max(0, 100 - cv * 20)
        return min(100, score)

    def _drawdown_score(self, ctx: MonitorContext) -> float:
        """回撤控制评分"""
        if not ctx.recent_snapshots:
            return 50

        peak = getattr(ctx.recent_snapshots[0], "net_value", 0)
        max_dd = 0.0

        for s in ctx.recent_snapshots:
            nv = getattr(s, "net_value", 0)
            peak = max(peak, nv)
            dd = (peak - nv) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        if max_dd < 0.03:
            return 100
        if max_dd < 0.05:
            return 85
        if max_dd < 0.10:
            return 70
        if max_dd < 0.15:
            return 50
        return 20

    def _execution_score(self, ctx: MonitorContext) -> float:
        """执行质量评分"""
        return 70  # 默认值
