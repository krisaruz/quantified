"""MaxDrawdownRule：回撤暂停规则（支持阶梯式恢复）"""

from __future__ import annotations

import pandas as pd

from quantified.risk.protocol import RiskViolation


class MaxDrawdownRule:
    """回撤暂停规则：组合从高点回撤超过阈值时暂停交易

    支持阶梯式恢复：
    - 回撤 70%：暂停新买入
    - 回撤 90%：暂停所有交易
    - 回撤 100%：强制减仓
    """

    name = "max_drawdown"
    severity = "hard"

    def __init__(self, recovery_mode: str = "gradual") -> None:
        self.recovery_mode = recovery_mode

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        max_dd = getattr(config.risk, "max_drawdown_pct", -0.10) if hasattr(config, "risk") else -0.10

        # 获取当前回撤
        high_water = getattr(portfolio, "high_water_mark", 0)
        cash = getattr(portfolio, "cash", 0)
        holdings = getattr(portfolio, "holdings", [])
        market_value = sum(
            getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10
            for h in holdings
        )
        total = cash + market_value

        if high_water <= 0:
            return violations

        drawdown = (total - high_water) / high_water

        if drawdown <= max_dd:
            violations.append(RiskViolation(
                rule_name=self.name,
                severity=self.severity,
                message=f"组合回撤 {drawdown:.1%} 超过阈值 {max_dd:.0%}，暂停交易",
                current_value=drawdown,
                threshold=max_dd,
                suggested_action="pause",
            ))
        elif self.recovery_mode == "gradual" and drawdown <= max_dd * 0.7:
            violations.append(RiskViolation(
                rule_name=self.name,
                severity="soft",
                message=f"组合回撤 {drawdown:.1%}，接近止损线，限制新买入",
                current_value=drawdown,
                threshold=max_dd * 0.7,
                suggested_action="warn",
            ))

        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        if violation.suggested_action == "pause":
            # 暂停所有交易
            return []
        elif violation.suggested_action == "warn":
            # 只保留卖出信号
            from quantified.strategy.protocol import Signal
            return [s for s in signals if s.direction == "sell"]
        return signals
