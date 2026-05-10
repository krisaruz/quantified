"""内置告警规则"""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4

from quantified.monitoring.models import Alert, MonitorContext


class PnLAlert:
    """单日亏损告警"""

    name = "pnl_alert"
    warning_threshold: float = -0.03
    critical_threshold: float = -0.05

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        snaps = ctx.recent_snapshots
        if len(snaps) < 2:
            return None

        today = snaps[-1]
        yesterday = snaps[-2]
        prev_nv = getattr(yesterday, "net_value", 0)
        curr_nv = getattr(today, "net_value", 0)

        if prev_nv <= 0:
            return None

        daily_return = curr_nv / prev_nv - 1

        if daily_return <= self.critical_threshold:
            return self._make_alert("critical", daily_return, ctx.date)
        if daily_return <= self.warning_threshold:
            return self._make_alert("warning", daily_return, ctx.date)
        return None

    def _make_alert(self, severity: str, value: float, date: str) -> Alert:
        threshold = (
            self.critical_threshold if severity == "critical" else self.warning_threshold
        )
        return Alert(
            alert_id=str(uuid4()),
            rule_name=self.name,
            severity=severity,
            title=f"单日亏损告警 ({severity})",
            message=f"日期 {date} 单日收益 {value:+.2%}，阈值 {threshold:+.2%}",
            current_value=value,
            threshold=threshold,
            timestamp=datetime.now(),
        )


class ConcentrationAlert:
    """持仓集中度告警"""

    name = "concentration_alert"
    warning_threshold: float = 0.15
    critical_threshold: float = 0.25

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        total = ctx.cash
        for h in ctx.holdings:
            buy_price = getattr(h, "buy_price", 0)
            volume = getattr(h, "volume", 0)
            total += buy_price * volume / 10

        if total <= 0:
            return None

        for h in ctx.holdings:
            buy_price = getattr(h, "buy_price", 0)
            volume = getattr(h, "volume", 0)
            weight = (buy_price * volume / 10) / total

            cb_code = getattr(h, "cb_code", "unknown")

            if weight >= self.critical_threshold:
                return Alert(
                    alert_id=str(uuid4()),
                    rule_name=self.name,
                    severity="critical",
                    title="持仓集中度过高 (critical)",
                    message=f"{cb_code} 占比 {weight:.1%}，超过 {self.critical_threshold:.0%} 阈值",
                    current_value=weight,
                    threshold=self.critical_threshold,
                    timestamp=datetime.now(),
                    cb_code=cb_code,
                )
            if weight >= self.warning_threshold:
                return Alert(
                    alert_id=str(uuid4()),
                    rule_name=self.name,
                    severity="warning",
                    title="持仓集中度偏高 (warning)",
                    message=f"{cb_code} 占比 {weight:.1%}，超过 {self.warning_threshold:.0%} 阈值",
                    current_value=weight,
                    threshold=self.warning_threshold,
                    timestamp=datetime.now(),
                    cb_code=cb_code,
                )
        return None


class DataFreshnessAlert:
    """数据新鲜度告警"""

    name = "data_freshness"
    warning_days: int = 3
    critical_days: int = 7

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        last_sync = ctx.data_meta.get("last_sync_bond_daily")
        if not last_sync:
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="critical",
                title="数据从未同步",
                message="从未同步过转债日线数据",
                current_value=0,
                threshold=self.critical_days,
                timestamp=datetime.now(),
            )

        try:
            last_date = datetime.fromisoformat(last_sync).date()
            age = (datetime.now().date() - last_date).days
        except (ValueError, TypeError):
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="critical",
                title="数据日期格式错误",
                message=f"无法解析同步日期: {last_sync}",
                current_value=0,
                threshold=self.critical_days,
                timestamp=datetime.now(),
            )

        if age >= self.critical_days:
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="critical",
                title="数据严重过期 (critical)",
                message=f"数据已 {age} 天未更新，超过 {self.critical_days} 天阈值",
                current_value=float(age),
                threshold=float(self.critical_days),
                timestamp=datetime.now(),
            )
        if age >= self.warning_days:
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="warning",
                title="数据过期 (warning)",
                message=f"数据已 {age} 天未更新，超过 {self.warning_days} 天阈值",
                current_value=float(age),
                threshold=float(self.warning_days),
                timestamp=datetime.now(),
            )
        return None


class DrawdownAlert:
    """回撤预警"""

    name = "drawdown_alert"
    warning_pct: float = -0.07
    critical_pct: float = -0.09

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        snaps = ctx.recent_snapshots
        if len(snaps) < 2:
            return None

        # 计算当前回撤
        peak = max(getattr(s, "net_value", 0) for s in snaps)
        current = getattr(snaps[-1], "net_value", 0)

        if peak <= 0:
            return None

        drawdown = (current - peak) / peak

        if drawdown <= self.critical_pct:
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="critical",
                title="回撤预警 (critical)",
                message=f"当前回撤 {drawdown:+.2%}，超过 {self.critical_pct:+.2%} 阈值",
                current_value=drawdown,
                threshold=self.critical_pct,
                timestamp=datetime.now(),
            )
        if drawdown <= self.warning_pct:
            return Alert(
                alert_id=str(uuid4()),
                rule_name=self.name,
                severity="warning",
                title="回撤预警 (warning)",
                message=f"当前回撤 {drawdown:+.2%}，超过 {self.warning_pct:+.2%} 阈值",
                current_value=drawdown,
                threshold=self.warning_pct,
                timestamp=datetime.now(),
            )
        return None
