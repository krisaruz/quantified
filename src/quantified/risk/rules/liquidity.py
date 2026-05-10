"""LiquidityRule：流动性要求"""

from __future__ import annotations

import pandas as pd

from quantified.risk.protocol import RiskViolation


class LiquidityRule:
    """标的日成交量不低于阈值"""

    name = "liquidity"
    severity = "hard"

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        min_volume = 500  # 默认最低 500 手

        for sig in signals:
            if sig.direction != "buy":
                continue
            volume = self._get_volume(market_data, sig.cb_code)
            if volume is not None and volume < min_volume:
                violations.append(RiskViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    cb_code=sig.cb_code,
                    message=f"成交量 {volume:.0f} 手低于下限 {min_volume} 手",
                    current_value=volume,
                    threshold=min_volume,
                    suggested_action="remove",
                ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        return [s for s in signals if s.cb_code != violation.cb_code]

    def _get_volume(self, market_data: pd.DataFrame, code: str) -> float | None:
        if market_data.empty:
            return None
        row = market_data[market_data["cb_code"] == code]
        if row.empty:
            return None
        return float(row.iloc[0].get("cb_volume", 0))
