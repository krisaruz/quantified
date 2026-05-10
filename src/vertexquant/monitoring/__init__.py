"""监控告警

核心组件：
- MonitorEngine: 监控引擎
- AlertRule: 告警规则协议
- 内置规则: PnLAlert, ConcentrationAlert, DataFreshnessAlert, DrawdownAlert
- HealthScore: 策略健康度评估
- Notifier: 通知器协议
- LogNotifier, WebhookNotifier, CompositeNotifier
"""

from vertexquant.monitoring.alert_rules import (
    ConcentrationAlert,
    DataFreshnessAlert,
    DrawdownAlert,
    PnLAlert,
)
from vertexquant.monitoring.engine import MonitorEngine
from vertexquant.monitoring.health import HealthBreakdown, HealthScore
from vertexquant.monitoring.models import Alert, AlertRule, MonitorContext, Notifier
from vertexquant.monitoring.notifiers import (
    CompositeNotifier,
    LogNotifier,
    WebhookNotifier,
)

__all__ = [
    "Alert",
    "AlertRule",
    "CompositeNotifier",
    "ConcentrationAlert",
    "DataFreshnessAlert",
    "DrawdownAlert",
    "HealthBreakdown",
    "HealthScore",
    "LogNotifier",
    "MonitorContext",
    "MonitorEngine",
    "Notifier",
    "PnLAlert",
    "WebhookNotifier",
]
