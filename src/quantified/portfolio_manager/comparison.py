"""组合对比分析"""

from __future__ import annotations

from quantified.portfolio_manager.models import ComparisonResult, PortfolioSnapshot


class PortfolioComparator:
    """组合对比器"""

    def compare_snapshots(
        self,
        snapshots: dict[str, PortfolioSnapshot],
    ) -> ComparisonResult:
        """对比多个组合的快照

        Args:
            snapshots: {portfolio_name: snapshot}
        """
        names = list(snapshots.keys())
        metrics: dict[str, list[float]] = {
            "total_assets": [],
            "total_pnl_pct": [],
            "cash_ratio": [],
            "holding_count": [],
        }

        for name in names:
            snap = snapshots[name]
            metrics["total_assets"].append(snap.total_assets)
            metrics["total_pnl_pct"].append(snap.total_pnl_pct)
            cash_ratio = snap.cash / snap.total_assets if snap.total_assets > 0 else 0
            metrics["cash_ratio"].append(cash_ratio)
            metrics["holding_count"].append(float(len(snap.holdings)))

        # 持仓重叠度
        holdings_overlap = self._compute_overlap(snapshots)

        # 综合排名（按收益率）
        ranking = sorted(
            [(name, snap.total_pnl_pct) for name, snap in snapshots.items()],
            key=lambda x: x[1],
            reverse=True,
        )

        return ComparisonResult(
            portfolios=names,
            metrics=metrics,
            holdings_overlap=holdings_overlap,
            ranking=ranking,
        )

    def _compute_overlap(
        self,
        snapshots: dict[str, PortfolioSnapshot],
    ) -> dict[str, float]:
        """计算组合间持仓重叠度

        overlap(A, B) = |A ∩ B| / min(|A|, |B|)
        """
        names = list(snapshots.keys())
        overlap: dict[str, float] = {}

        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                name_a, name_b = names[i], names[j]
                codes_a = {h.cb_code for h in snapshots[name_a].holdings}
                codes_b = {h.cb_code for h in snapshots[name_b].holdings}

                if not codes_a or not codes_b:
                    ratio = 0.0
                else:
                    intersection = len(codes_a & codes_b)
                    min_size = min(len(codes_a), len(codes_b))
                    ratio = intersection / min_size if min_size > 0 else 0.0

                key = f"{name_a} vs {name_b}"
                overlap[key] = ratio

        return overlap

    def generate_report(
        self,
        result: ComparisonResult,
    ) -> str:
        """生成对比报告"""
        lines: list[str] = []
        lines.append("# 组合对比报告\n")

        # 排名
        lines.append("## 综合排名\n")
        lines.append("| 排名 | 组合 | 收益率 |")
        lines.append("|------|------|--------|")
        for i, (name, pnl) in enumerate(result.ranking, 1):
            lines.append(f"| {i} | {name} | {pnl:+.2%} |")
        lines.append("")

        # 指标对比
        lines.append("## 指标对比\n")
        header = "| 指标 | " + " | ".join(result.portfolios) + " |"
        sep = "|------| " + " | ".join(["---" for _ in result.portfolios]) + " |"
        lines.append(header)
        lines.append(sep)

        metric_labels = {
            "total_assets": "总资产",
            "total_pnl_pct": "收益率",
            "cash_ratio": "现金比例",
            "holding_count": "持仓数",
        }

        for metric_key, label in metric_labels.items():
            values = result.metrics.get(metric_key, [])
            row = f"| {label} | "
            for v in values:
                if metric_key == "total_assets":
                    row += f"{v:,.0f} | "
                elif metric_key in ("total_pnl_pct", "cash_ratio"):
                    row += f"{v:.2%} | "
                else:
                    row += f"{int(v)} | "
            lines.append(row)
        lines.append("")

        # 持仓重叠
        if result.holdings_overlap:
            lines.append("## 持仓重叠度\n")
            lines.append("| 组合对 | 重叠度 |")
            lines.append("|--------|--------|")
            for pair, ratio in result.holdings_overlap.items():
                lines.append(f"| {pair} | {ratio:.1%} |")

        return "\n".join(lines)
