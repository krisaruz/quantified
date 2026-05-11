"""分析仪表盘

核心组件：
- AnalyticsEngine: 分析引擎（风险调整指标、回撤检测、月度/年度收益）
- BrinsonAttribution: Brinson 归因模型
- BenchmarkManager: 基准管理与对比
- DrawdownAnalyzer: 回撤分析
- ReportGenerator: 报告生成
- ChartData: 图表数据准备
"""

from vertexquant.analytics.attribution import (
    BrinsonAttribution,
    BrinsonResult,
    PeriodAttribution,
    SectorAttribution,
)
from vertexquant.analytics.benchmark import BenchmarkComparison, BenchmarkManager
from vertexquant.analytics.charts import ChartData
from vertexquant.analytics.drawdown import DrawdownAnalyzer, DrawdownStats, UnderwaterPoint
from vertexquant.analytics.engine import (
    AnalyticsEngine,
    DrawdownPeriod,
    RiskAdjustedMetrics,
)
from vertexquant.analytics.report import HoldingPerformance, ReportGenerator

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
