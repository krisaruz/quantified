"""MaxPositionRule：单只持仓上限"""

from __future__ import annotations

import pandas as pd

from quantified.risk.protocol import RiskViolation


class MaxPositionRule:
    """单只持仓占总资产比例不超过阈值"""

    name = "max_position"
    severity = "hard"

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        max_pct = getattr(config.risk, "max_position_pct", 0.10) if hasattr(config, "risk") else 0.10

        # 检查买入信号是否会导致超限
        total_assets = self._get_total_assets(portfolio, market_data)
        if total_assets <= 0:
            return violations

        for sig in signals:
            if sig.direction != "buy":
                continue
            weight = getattr(sig, "weight", 0)
            if weight > max_pct:
                violations.append(RiskViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    cb_code=sig.cb_code,
                    message=f"目标仓位 {weight:.1%} 超过上限 {max_pct:.1%}",
                    current_value=weight,
                    threshold=max_pct,
                    suggested_action="reduce",
                ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        adjusted = []
        for sig in signals:
            if sig.cb_code == violation.cb_code and sig.direction == "buy":
                from quantified.strategy.protocol import Signal
                adjusted.append(Signal(
                    cb_code=sig.cb_code,
                    direction=sig.direction,
                    weight=violation.threshold,
                    score=sig.score,
                    reason=sig.reason,
                    metadata=sig.metadata,
                ))
            else:
                adjusted.append(sig)
        return adjusted

    def _get_total_assets(self, portfolio: object, market_data: pd.DataFrame) -> float:
        cash = getattr(portfolio, "cash", 0)
        holdings = getattr(portfolio, "holdings", [])
        market_value = sum(
            getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10
            for h in holdings
        )
        return cash + market_value
