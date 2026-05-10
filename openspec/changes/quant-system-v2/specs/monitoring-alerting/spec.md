# Monitoring & Alerting Spec

## 概述

监控告警模块提供实时 P&L 监控、持仓风险告警、数据质量监控和策略健康度评估。

## 架构

```
MonitorContext (数据聚合)
    ↓
Monitor.check_all(context) → Alert[]
    ↓
Notifier.notify(alerts) → 飞书/Webhook/日志
```

## MonitorContext

```python
@dataclass
class MonitorContext:
    date: str
    portfolio: Portfolio
    market_data: pd.DataFrame           # 当日截面
    recent_snapshots: list[DailySnapshot]  # 最近 N 天快照
    recent_trades: list[TradeRecord]       # 最近 N 笔交易
    data_meta: dict[str, str]           # 数据同步元信息
    config: AppConfig
```

## Alert 模型

```python
@dataclass(frozen=True)
class Alert:
    alert_id: str
    rule_name: str
    severity: str           # "info" | "warning" | "critical"
    title: str
    message: str
    cb_code: str | None     # 相关标的
    current_value: float
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
```

## 内置告警规则

### PnLAlert（单日亏损告警）
```python
class PnLAlert:
    name = "pnl_alert"
    warning_threshold = -0.03   # 单日亏损 3%
    critical_threshold = -0.05  # 单日亏损 5%

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        if len(ctx.recent_snapshots) < 2:
            return None
        today = ctx.recent_snapshots[-1]
        yesterday = ctx.recent_snapshots[-2]
        daily_return = today.net_value / yesterday.net_value - 1
        if daily_return <= self.critical_threshold:
            return Alert(severity="critical", ...)
        if daily_return <= self.warning_threshold:
            return Alert(severity="warning", ...)
```

### ConcentrationAlert（持仓集中度告警）
```python
class ConcentrationAlert:
    name = "concentration_alert"
    warning_threshold = 0.15    # 单只占比超 15%
    critical_threshold = 0.25   # 单只占比超 25%

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        total = ctx.portfolio.cash + sum(...)
        for h in ctx.portfolio.holdings:
            weight = (h.buy_price * h.volume / 10) / total
            if weight >= self.critical_threshold:
                return Alert(severity="critical", ...)
```

### DataFreshnessAlert（数据新鲜度告警）
```python
class DataFreshnessAlert:
    name = "data_freshness"
    warning_days = 3
    critical_days = 7

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        last_sync = ctx.data_meta.get("last_sync_bond_daily")
        if not last_sync:
            return Alert(severity="critical", message="从未同步数据")
        age = (datetime.date.today() - datetime.date.fromisoformat(last_sync)).days
        if age >= self.critical_days:
            return Alert(severity="critical", ...)
        if age >= self.warning_days:
            return Alert(severity="warning", ...)
```

### VolumeAnomalyAlert（成交量异常告警）
```python
class VolumeAnomalyAlert:
    name = "volume_anomaly"
    spike_multiplier = 5.0      # 成交量突变 5 倍
    drop_multiplier = 0.2       # 成交量萎缩至 20%

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        for h in ctx.portfolio.holdings:
            row = ctx.market_data[ctx.market_data["cb_code"] == h.cb_code]
            if row.empty:
                continue
            current_vol = float(row.iloc[0]["cb_volume"])
            # 需要历史成交量数据来比较
            ...
```

### DrawdownAlert（回撤预警）
```python
class DrawdownAlert:
    name = "drawdown_alert"
    warning_pct = -0.07     # 接近止损线 70%
    critical_pct = -0.09    # 接近止损线 90%

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        limit = ctx.config.risk.max_drawdown_pct
        # 计算当前回撤
        peak = max(s.net_value for s in ctx.recent_snapshots)
        current = ctx.recent_snapshots[-1].net_value
        drawdown = (current - peak) / peak

        warning_line = limit * 0.7
        critical_line = limit * 0.9

        if drawdown <= critical_line:
            return Alert(severity="critical", ...)
        if drawdown <= warning_line:
            return Alert(severity="warning", ...)
```

### RatingDowngradeAlert（评级下调告警）
```python
class RatingDowngradeAlert:
    name = "rating_downgrade"

    def evaluate(self, ctx: MonitorContext) -> Alert | None:
        # 检查持仓标的的信用评级是否发生变化
        # 需要与历史评级数据对比
        ...
```

## 策略健康度

### HealthScore
```python
class HealthScore:
    def calculate(self, ctx: MonitorContext) -> float:
        """计算策略健康度评分（0-100）"""
        scores = []

        # 1. 数据新鲜度 (权重 20%)
        data_score = self._data_freshness_score(ctx)
        scores.append(("data_freshness", data_score, 0.2))

        # 2. 持仓分散度 (权重 20%)
        diversification_score = self._diversification_score(ctx)
        scores.append(("diversification", diversification_score, 0.2))

        # 3. 收益稳定性 (权重 20%)
        stability_score = self._return_stability_score(ctx)
        scores.append(("stability", stability_score, 0.2))

        # 4. 回撤控制 (权重 20%)
        drawdown_score = self._drawdown_score(ctx)
        scores.append(("drawdown", drawdown_score, 0.2))

        # 5. 执行质量 (权重 20%)
        execution_score = self._execution_score(ctx)
        scores.append(("execution", execution_score, 0.2))

        total = sum(score * weight for _, score, weight in scores)
        return round(total, 1)

    def _data_freshness_score(self, ctx) -> float:
        """数据新鲜度评分：0-100"""
        last_sync = ctx.data_meta.get("last_sync_bond_daily")
        if not last_sync:
            return 0
        age = (datetime.date.today() - datetime.date.fromisoformat(last_sync)).days
        if age == 0:
            return 100
        if age <= 1:
            return 90
        if age <= 3:
            return 70
        if age <= 7:
            return 40
        return 10

    def _diversification_score(self, ctx) -> float:
        """持仓分散度评分：基于 Herfindahl 指数"""
        if not ctx.portfolio.holdings:
            return 50
        total = ctx.portfolio.cash + sum(h.buy_price * h.volume / 10 for h in ctx.portfolio.holdings)
        weights = [(h.buy_price * h.volume / 10) / total for h in ctx.portfolio.holdings]
        hhi = sum(w ** 2 for w in weights)
        # HHI 范围 [1/N, 1]，越小越分散
        n = len(weights)
        min_hhi = 1 / n if n > 0 else 1
        score = (1 - (hhi - min_hhi) / (1 - min_hhi)) * 100 if min_hhi < 1 else 50
        return max(0, min(100, score))

    def _return_stability_score(self, ctx) -> float:
        """收益稳定性评分：基于收益率的变异系数"""
        if len(ctx.recent_snapshots) < 10:
            return 50
        returns = []
        for i in range(1, len(ctx.recent_snapshots)):
            prev = ctx.recent_snapshots[i-1].net_value
            if prev > 0:
                returns.append(ctx.recent_snapshots[i].net_value / prev - 1)
        if not returns:
            return 50
        mean_r = sum(returns) / len(returns)
        var = sum((r - mean_r) ** 2 for r in returns) / len(returns)
        std = var ** 0.5
        cv = abs(std / mean_r) if mean_r != 0 else 999
        # CV 越小越好
        score = max(0, 100 - cv * 20)
        return min(100, score)

    def _drawdown_score(self, ctx) -> float:
        """回撤控制评分"""
        if not ctx.recent_snapshots:
            return 50
        peak = ctx.recent_snapshots[0].net_value
        max_dd = 0
        for s in ctx.recent_snapshots:
            peak = max(peak, s.net_value)
            dd = (peak - s.net_value) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)
        if max_dd < 0.03:
            return 100
        if max_dd < 0.05:
            return 85
        if max_dd < 0.10:
            return 70
        if max_dd < 0.15:
            return 50
        return 20

    def _execution_score(self, ctx) -> float:
        """执行质量评分：基于滑点和成交率"""
        # 简化：基于最近交易的平均滑点
        return 70  # 默认
```

## 告警通知

### Notifier Protocol
```python
class Notifier(Protocol):
    def notify(self, alert: Alert) -> bool: ...
```

### LogNotifier
```python
class LogNotifier:
    def notify(self, alert: Alert) -> bool:
        logger.log(
            {"info": logging.INFO, "warning": logging.WARNING, "critical": logging.CRITICAL}[alert.severity],
            "[%s] %s: %s", alert.severity.upper(), alert.title, alert.message,
        )
        return True
```

### WebhookNotifier
```python
class WebhookNotifier:
    url: str

    def notify(self, alert: Alert) -> bool:
        payload = {
            "alert_id": alert.alert_id,
            "severity": alert.severity,
            "title": alert.title,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
        }
        resp = requests.post(self.url, json=payload, timeout=5)
        return resp.status_code < 400
```

### FeishuNotifier（可选）
```python
class FeishuNotifier:
    webhook_url: str    # 飞书机器人 webhook

    def notify(self, alert: Alert) -> bool:
        card = self._build_card(alert)
        resp = requests.post(self.webhook_url, json=card, timeout=5)
        return resp.status_code < 400
```

## CLI 命令

```bash
quantified monitor check                    # 运行所有告警检查
quantified monitor health                   # 显示策略健康度
quantified monitor history --days 30        # 告警历史
quantified monitor config                   # 告警配置
```

## Web API

```
GET /api/v2/monitor/alerts?severity=warning&limit=20
GET /api/v2/monitor/health
GET /api/v2/monitor/health/history?days=30
POST /api/v2/monitor/alerts/{id}/acknowledge
```
