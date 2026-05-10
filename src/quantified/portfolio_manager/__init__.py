"""多组合管理

核心组件：
- PortfolioManager: 组合管理器
- SnapshotManager: 快照管理
- PortfolioComparator: 组合对比
- 模板系统: conservative, balanced, aggressive
"""

from quantified.portfolio_manager.comparison import PortfolioComparator
from quantified.portfolio_manager.manager import PortfolioManager
from quantified.portfolio_manager.models import (
    ComparisonResult,
    HoldingSnapshot,
    PortfolioSnapshot,
    PortfolioSummary,
    PortfolioTemplate,
)
from quantified.portfolio_manager.snapshot import SnapshotManager
from quantified.portfolio_manager.templates import (
    BUILTIN_TEMPLATES,
    apply_template,
    get_template,
    list_templates,
)

__all__ = [
    "BUILTIN_TEMPLATES",
    "ComparisonResult",
    "HoldingSnapshot",
    "PortfolioComparator",
    "PortfolioManager",
    "PortfolioSnapshot",
    "PortfolioSummary",
    "PortfolioTemplate",
    "SnapshotManager",
    "apply_template",
    "get_template",
    "list_templates",
]
