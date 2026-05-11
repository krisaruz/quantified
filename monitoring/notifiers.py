"""告警通知器"""

from __future__ import annotations

import json
import logging
from typing import Any

from vertexquant.monitoring.models import Alert

logger = logging.getLogger(__name__)


class LogNotifier:
    """日志通知器"""

    def notify(self, alert: Alert) -> bool:
        level_map = {
            "info": logging.INFO,
            "warning": logging.WARNING,
            "critical": logging.CRITICAL,
        }
        level = level_map.get(alert.severity, logging.INFO)
        logger.log(level, "[%s] %s: %s", alert.severity.upper(), alert.title, alert.message)
        return True


class WebhookNotifier:
    """Webhook 通知器"""

    def __init__(self, url: str, timeout: int = 5) -> None:
        self._url = url
        self._timeout = timeout

    def notify(self, alert: Alert) -> bool:
        """发送 Webhook 通知"""
        payload = {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "current_value": alert.current_value,
            "threshold": alert.threshold,
            "timestamp": alert.timestamp.isoformat(),
            "cb_code": alert.cb_code,
        }

        try:
            import urllib.request

            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                self._url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                return resp.status < 400
        except Exception:
            return False


class CompositeNotifier:
    """组合通知器（同时通知多个渠道）"""

    def __init__(self, notifiers: list[Any]) -> None:
        self._notifiers = notifiers

    def notify(self, alert: Alert) -> bool:
        results = []
        for notifier in self._notifiers:
            try:
                result = notifier.notify(alert)
                results.append(result)
            except Exception:
                results.append(False)
        return any(results)
