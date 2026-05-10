"""分析报告生成

支持 Markdown 和 HTML 格式的月度/年度报告。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from quantified.analytics.engine import AnalyticsEngine, RiskAdjustedMetrics
from quantified.analytics.drawdown import DrawdownStats


@dataclass(frozen=True)
class HoldingPerformance:
    """单个持仓的绩效"""

    code: str
    name: str
    pnl: float
    pnl_pct: float
    weight: float


@dataclass(frozen=True)
class ReportSection:
    """报告段落"""

    title: str
    content: str
    data: dict[str, Any] = field(default_factory=dict)


class ReportGenerator:
    """报告生成器"""

    def generate_monthly_report(
        self,
        portfolio_name: str,
        year: int,
        month: int,
        metrics: RiskAdjustedMetrics,
        monthly_return: float,
        benchmark_return: float | None,
        top_gainers: list[HoldingPerformance],
        top_losers: list[HoldingPerformance],
        drawdown_stats: DrawdownStats,
    ) -> str:
        """生成月度报告（Markdown 格式）"""
        sections: list[str] = []

        # 标题
        sections.append(f"# {portfolio_name} 月度报告 - {year}年{month}月\n")

        # 收益概览
        excess = ""
        if benchmark_return is not None:
            diff = monthly_return - benchmark_return
            excess = f" | 超额收益: {diff:+.2%}"

        sections.append("## 收益概览\n")
        sections.append(f"| 指标 | 值 |")
        sections.append(f"|------|-----|")
        sections.append(f"| 本月收益 | {monthly_return:+.2%} |")
        if benchmark_return is not None:
            sections.append(f"| 基准收益 | {benchmark_return:+.2%} |")
            sections.append(f"| 超额收益 | {monthly_return - benchmark_return:+.2%} |")
        sections.append("")

        # 风险指标
        sections.append("## 风险指标\n")
        sections.append(f"| 指标 | 值 |")
        sections.append(f"|------|-----|")
        sections.append(f"| Sortino Ratio | {metrics.sortino_ratio:.2f} |")
        sections.append(f"| Calmar Ratio | {metrics.calmar_ratio:.2f} |")
        sections.append(f"| Information Ratio | {metrics.information_ratio:.2f} |")
        sections.append(f"| Omega Ratio | {metrics.omega_ratio:.2f} |")
        sections.append(f"| 最大回撤 | {drawdown_stats.max_drawdown:.2%} |")
        sections.append(f"| 当前回撤 | {drawdown_stats.current_drawdown:.2%} |")
        sections.append(f"| 回撤区间数 | {drawdown_stats.total_periods} |")
        sections.append("")

        # Top 贡献
        sections.append("## Top 贡献标的\n")
        sections.append("### 涨幅前5\n")
        sections.append("| 标的 | 名称 | 收益 | 收益率 | 权重 |")
        sections.append("|------|------|------|--------|------|")
        for h in top_gainers[:5]:
            sections.append(
                f"| {h.code} | {h.name} | {h.pnl:+.2f} | {h.pnl_pct:+.2%} | {h.weight:.1%} |"
            )
        sections.append("")

        sections.append("### 跌幅前5\n")
        sections.append("| 标的 | 名称 | 收益 | 收益率 | 权重 |")
        sections.append("|------|------|------|--------|------|")
        for h in top_losers[:5]:
            sections.append(
                f"| {h.code} | {h.name} | {h.pnl:+.2f} | {h.pnl_pct:+.2%} | {h.weight:.1%} |"
            )
        sections.append("")

        return "\n".join(sections)

    def generate_annual_summary(
        self,
        portfolio_name: str,
        year: int,
        annual_return: float,
        benchmark_return: float | None,
        metrics: RiskAdjustedMetrics,
        monthly_returns: dict[str, float],
        drawdown_stats: DrawdownStats,
    ) -> str:
        """生成年度总结报告"""
        sections: list[str] = []

        sections.append(f"# {portfolio_name} {year}年度报告\n")

        # 年度概览
        sections.append("## 年度概览\n")
        sections.append(f"| 指标 | 值 |")
        sections.append(f"|------|-----|")
        sections.append(f"| 年度收益 | {annual_return:+.2%} |")
        if benchmark_return is not None:
            sections.append(f"| 基准收益 | {benchmark_return:+.2%} |")
            sections.append(f"| 超额收益 | {annual_return - benchmark_return:+.2%} |")
        sections.append(f"| Sharpe Ratio | N/A |")
        sections.append(f"| Sortino Ratio | {metrics.sortino_ratio:.2f} |")
        sections.append(f"| Calmar Ratio | {metrics.calmar_ratio:.2f} |")
        sections.append(f"| 最大回撤 | {drawdown_stats.max_drawdown:.2%} |")
        sections.append(f"| 回撤持续最长 | {drawdown_stats.max_duration_days} 天 |")
        sections.append("")

        # 月度收益表
        sections.append("## 月度收益\n")
        year_monthly = {
            k: v for k, v in monthly_returns.items() if k.startswith(str(year))
        }
        if year_monthly:
            sections.append("| 月份 | 收益率 |")
            sections.append("|------|--------|")
            for ym in sorted(year_monthly):
                month_label = ym[5:]
                sections.append(f"| {month_label}月 | {year_monthly[ym]:+.2%} |")
            sections.append("")

        return "\n".join(sections)
