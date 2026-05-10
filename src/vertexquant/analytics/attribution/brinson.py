"""Brinson 归因模型

支持单期和多期（Carino 方法）归因分析。
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SectorAttribution:
    """单个行业的归因分解"""

    sector: str
    portfolio_weight: float
    benchmark_weight: float
    portfolio_return: float
    benchmark_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float


@dataclass(frozen=True)
class PeriodAttribution:
    """单个时期的归因结果"""

    period: str
    portfolio_return: float
    benchmark_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    total_excess: float


@dataclass(frozen=True)
class BrinsonResult:
    """Brinson 归因结果"""

    total_excess_return: float
    allocation_effect: float
    selection_effect: float
    interaction_effect: float
    by_sector: dict[str, SectorAttribution]
    by_period: list[PeriodAttribution]


class BrinsonAttribution:
    """Brinson 归因分析器

    支持 BF (Brinson-Fachler) 模型的单期和多期归因。
    """

    def single_period(
        self,
        portfolio_weights: dict[str, float],
        benchmark_weights: dict[str, float],
        portfolio_returns: dict[str, float],
        benchmark_returns: dict[str, float],
    ) -> BrinsonResult:
        """单期 Brinson 归因

        Args:
            portfolio_weights: 组合各行业权重 {sector: weight}
            benchmark_weights: 基准各行业权重 {sector: weight}
            portfolio_returns: 组合各行业收益率 {sector: return}
            benchmark_returns: 基准各行业收益率 {sector: return}
        """
        sectors = set(portfolio_weights) | set(benchmark_weights)

        # 基准总收益
        benchmark_total = sum(
            benchmark_weights.get(s, 0.0) * benchmark_returns.get(s, 0.0)
            for s in sectors
        )

        by_sector: dict[str, SectorAttribution] = {}
        total_alloc = 0.0
        total_select = 0.0
        total_interact = 0.0

        for sector in sectors:
            wp = portfolio_weights.get(sector, 0.0)
            wb = benchmark_weights.get(sector, 0.0)
            rp = portfolio_returns.get(sector, 0.0)
            rb = benchmark_returns.get(sector, 0.0)

            # Brinson-Fachler 公式
            alloc = (wp - wb) * (rb - benchmark_total)
            select = wb * (rp - rb)
            interact = (wp - wb) * (rp - rb)

            by_sector[sector] = SectorAttribution(
                sector=sector,
                portfolio_weight=wp,
                benchmark_weight=wb,
                portfolio_return=rp,
                benchmark_return=rb,
                allocation_effect=alloc,
                selection_effect=select,
                interaction_effect=interact,
            )

            total_alloc += alloc
            total_select += select
            total_interact += interact

        portfolio_total = sum(
            portfolio_weights.get(s, 0.0) * portfolio_returns.get(s, 0.0)
            for s in sectors
        )

        return BrinsonResult(
            total_excess_return=portfolio_total - benchmark_total,
            allocation_effect=total_alloc,
            selection_effect=total_select,
            interaction_effect=total_interact,
            by_sector=by_sector,
            by_period=[],
        )

    def multi_period(
        self,
        period_data: list[dict],
    ) -> BrinsonResult:
        """多期 Brinson 归因（Carino 调整方法）

        Args:
            period_data: 每期数据列表，每项包含:
                - period: str (时期标识)
                - portfolio_weights: dict[str, float]
                - benchmark_weights: dict[str, float]
                - portfolio_returns: dict[str, float]
                - benchmark_returns: dict[str, float]
        """
        if not period_data:
            return BrinsonResult(
                total_excess_return=0.0,
                allocation_effect=0.0,
                selection_effect=0.0,
                interaction_effect=0.0,
                by_sector={},
                by_period=[],
            )

        # 先计算每期单期归因
        single_results: list[tuple[str, BrinsonResult]] = []
        for pd_item in period_data:
            result = self.single_period(
                pd_item["portfolio_weights"],
                pd_item["benchmark_weights"],
                pd_item["portfolio_returns"],
                pd_item["benchmark_returns"],
            )
            single_results.append((pd_item["period"], result))

        # 计算组合和基准的累计收益
        portfolio_cum = 1.0
        benchmark_cum = 1.0
        period_returns_p: list[float] = []
        period_returns_b: list[float] = []

        for pd_item in period_data:
            sectors = set(pd_item["portfolio_returns"])
            rp = sum(
                pd_item["portfolio_weights"].get(s, 0.0)
                * pd_item["portfolio_returns"].get(s, 0.0)
                for s in sectors
            )
            rb = sum(
                pd_item["benchmark_weights"].get(s, 0.0)
                * pd_item["benchmark_returns"].get(s, 0.0)
                for s in sectors
            )
            period_returns_p.append(rp)
            period_returns_b.append(rb)
            portfolio_cum *= 1 + rp
            benchmark_cum *= 1 + rb

        total_p = portfolio_cum - 1
        total_b = benchmark_cum - 1

        # Carino 调整因子
        def _carino_factor(r: float) -> float:
            if abs(r) < 1e-12:
                return 1.0
            return math.log(1 + r) / r

        k_total = _carino_factor(total_p - total_b)

        # 调整各期效应
        by_period: list[PeriodAttribution] = []
        adj_alloc = 0.0
        adj_select = 0.0
        adj_interact = 0.0

        for i, (period_label, sr) in enumerate(single_results):
            excess = sr.total_excess_return
            k_t = _carino_factor(excess)
            scale = k_t / k_total if abs(k_total) > 1e-12 else 1.0

            a = sr.allocation_effect * scale
            s = sr.selection_effect * scale
            it = sr.interaction_effect * scale

            by_period.append(PeriodAttribution(
                period=period_label,
                portfolio_return=period_returns_p[i],
                benchmark_return=period_returns_b[i],
                allocation_effect=a,
                selection_effect=s,
                interaction_effect=it,
                total_excess=a + s + it,
            ))

            adj_alloc += a
            adj_select += s
            adj_interact += it

        # 合并行业维度（取最后一期的行业明细，简化处理）
        _, last_result = single_results[-1]

        return BrinsonResult(
            total_excess_return=total_p - total_b,
            allocation_effect=adj_alloc,
            selection_effect=adj_select,
            interaction_effect=adj_interact,
            by_sector=last_result.by_sector,
            by_period=by_period,
        )
