"""监控引擎

聚合告警规则，执行检查，分发通知。
"""

from __future__ import annotations

from vertexquant.monitoring.models import Alert, AlertRule, MonitorContext, Notifier


class MonitorEngine:
    """监控引擎"""

    def __init__(self) -> None:
        self._rules: list[AlertRule] = []
        self._notifiers: list[Notifier] = []
        self._history: list[Alert] = []

    def add_rule(self, rule: AlertRule) -> None:
        """添加告警规则"""
        self._rules.append(rule)

    def add_notifier(self, notifier: Notifier) -> None:
        """添加通知器"""
        self._notifiers.append(notifier)

    def check_all(self, ctx: MonitorContext) -> list[Alert]:
        """运行所有告警规则"""
        alerts: list[Alert] = []

        for rule in self._rules:
            try:
                alert = rule.evaluate(ctx)
                if alert:
                    alerts.append(alert)
                    self._history.append(alert)
                    self._dispatch(alert)
            except Exception:
                pass

        return alerts

    def get_history(
        self,
        severity: str | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """获取告警历史"""
        filtered = self._history
        if severity:
            filtered = [a for a in filtered if a.severity == severity]
        return filtered[-limit:]

    def acknowledge(self, alert_id: str) -> bool:
        """确认告警"""
        for alert in self._history:
            if alert.alert_id == alert_id:
                # Alert 是 frozen，需要替换
                idx = self._history.index(alert)
                self._history[idx] = Alert(
                    alert_id=alert.alert_id,
                    rule_name=alert.rule_name,
                    severity=alert.severity,
                    title=alert.title,
                    message=alert.message,
                    current_value=alert.current_value,
                    threshold=alert.threshold,
                    timestamp=alert.timestamp,
                    cb_code=alert.cb_code,
                    acknowledged=True,
                )
                return True
        return False

    def clear_history(self) -> None:
        """清除告警历史"""
        self._history.clear()

    def _dispatch(self, alert: Alert) -> None:
        """分发告警到通知器"""
        for notifier in self._notifiers:
            try:
                notifier.notify(alert)
            except Exception:
                pass
