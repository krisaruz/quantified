"""分析仪表盘

核心组件：
- AnalyticsEngine: 分析引擎（风险调整指标、回撤检测、月度/年度收益）
- BrinsonAttribution: Brinson 归因模型
- BenchmarkManager: 基准管理与对比
- DrawdownAnalyzer: 回撤分析
- ReportGenerator: 报告生成
- ChartData: 图表数据准备
"""

from quantified.analytics.attribution import (
    BrinsonAttribution,
    BrinsonResult,
    PeriodAttribution,
    SectorAttribution,
)
from quantified.analytics.benchmark import BenchmarkComparison, BenchmarkManager
from quantified.analytics.charts import ChartData
from quantified.analytics.drawdown import DrawdownAnalyzer, DrawdownStats, UnderwaterPoint
from quantified.analytics.engine import (
    AnalyticsEngine,
    DrawdownPeriod,
    RiskAdjustedMetrics,
)
from quantified.analytics.report import HoldingPerformance, ReportGenerator

__all__ = [
    "AnalyticsEngine",
    "BenchmarkComparison",
    "BenchmarkManager",
    "BrinsonAttribution",
    "BrinsonResult",
    "ChartData",
    "DrawdownAnalyzer",
    "DrawdownPeriod",
    "DrawdownStats",
    "HoldingPerformance",
    "PeriodAttribution",
    "ReportGenerator",
    "RiskAdjustedMetrics",
    "SectorAttribution",
    "UnderwaterPoint",
]
