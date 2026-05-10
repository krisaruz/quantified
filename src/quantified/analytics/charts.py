"""图表数据准备

为前端提供 JSON 格式的图表数据。
"""

from __future__ import annotations

from typing import Any

from quantified.analytics.engine import DrawdownPeriod


class ChartData:
    """图表数据生成器"""

    @staticmethod
    def equity_curve(
        dates: list[str],
        net_values: list[float],
        benchmark_values: list[float] | None = None,
        benchmark_label: str = "Benchmark",
    ) -> dict[str, Any]:
        """净值曲线数据"""
        datasets: list[dict[str, Any]] = [
            {
                "label": "Portfolio",
                "data": net_values,
                "borderColor": "#4A90D9",
                "fill": False,
            }
        ]

        if benchmark_values and len(benchmark_values) == len(dates):
            datasets.append({
                "label": benchmark_label,
                "data": benchmark_values,
                "borderColor": "#E0E0E0",
                "borderDash": [5, 5],
                "fill": False,
            })

        return {
            "type": "line",
            "labels": dates,
            "datasets": datasets,
        }

    @staticmethod
    def drawdown_curve(
        dates: list[str],
        net_values: list[float],
    ) -> dict[str, Any]:
        """水下曲线数据"""
        if not dates or not net_values:
            return {"type": "line", "labels": [], "datasets": []}

        peak = net_values[0]
        underwater: list[float] = []
        for nv in net_values:
            if nv > peak:
                peak = nv
            uw = (nv - peak) / peak * 100 if peak > 0 else 0.0
            underwater.append(uw)

        return {
            "type": "line",
            "labels": dates,
            "datasets": [
                {
                    "label": "Drawdown %",
                    "data": underwater,
                    "backgroundColor": "rgba(231, 76, 60, 0.3)",
                    "borderColor": "#E74C3C",
                    "fill": True,
                }
            ],
        }

    @staticmethod
    def monthly_returns_heatmap(
        monthly_returns: dict[str, float],
    ) -> dict[str, Any]:
        """月度收益热力图数据

        Args:
            monthly_returns: {"YYYY-MM": return_rate}
        """
        years: dict[str, dict[str, float]] = {}
        for ym, ret in monthly_returns.items():
            year = ym[:4]
            month = ym[5:7]
            if year not in years:
                years[year] = {}
            years[year][month] = ret

        months = [f"{m:02d}" for m in range(1, 13)]
        labels = sorted(years.keys())
        data: list[list[float | None]] = []

        for year in labels:
            row: list[float | None] = []
            for m in months:
                row.append(years[year].get(m))
            data.append(row)

        return {
            "type": "heatmap",
            "labels": labels,
            "months": months,
            "data": data,
        }

    @staticmethod
    def factor_radar(
        factor_names: list[str],
        factor_values: list[float],
    ) -> dict[str, Any]:
        """因子暴露雷达图数据"""
        return {
            "type": "radar",
            "labels": factor_names,
            "datasets": [
                {
                    "label": "Factor Exposure",
                    "data": factor_values,
                    "backgroundColor": "rgba(52, 152, 219, 0.2)",
                    "borderColor": "#3498DB",
                }
            ],
        }

    @staticmethod
    def sector_pie(
        sectors: dict[str, float],
    ) -> dict[str, Any]:
        """行业饼图数据

        Args:
            sectors: {sector_name: weight}
        """
        colors = [
            "#3498DB", "#E74C3C", "#2ECC71", "#F39C12", "#9B59B6",
            "#1ABC9C", "#E67E22", "#34495E", "#16A085", "#C0392B",
            "#8E44AD", "#27AE60",
        ]

        labels = list(sectors.keys())
        values = list(sectors.values())
        n = len(labels)

        return {
            "type": "pie",
            "labels": labels,
            "datasets": [
                {
                    "data": values,
                    "backgroundColor": colors[:n],
                }
            ],
        }

    @staticmethod
    def performance_summary(
        dates: list[str],
        net_values: list[float],
    ) -> dict[str, Any]:
        """累计收益与回撤的组合图数据"""
        if not dates or not net_values:
            return {"type": "mixed", "labels": [], "datasets": []}

        # 累计收益（百分比）
        base = net_values[0]
        cumulative = [(nv / base - 1) * 100 for nv in net_values]

        # 水下曲线
        peak = net_values[0]
        underwater: list[float] = []
        for nv in net_values:
            if nv > peak:
                peak = nv
            uw = (nv - peak) / peak * 100 if peak > 0 else 0.0
            underwater.append(uw)

        return {
            "type": "mixed",
            "labels": dates,
            "datasets": [
                {
                    "type": "line",
                    "label": "Cumulative Return %",
                    "data": cumulative,
                    "borderColor": "#4A90D9",
                    "yAxisID": "y",
                },
                {
                    "type": "bar",
                    "label": "Drawdown %",
                    "data": underwater,
                    "backgroundColor": "rgba(231, 76, 60, 0.3)",
                    "yAxisID": "y1",
                },
            ],
        }
