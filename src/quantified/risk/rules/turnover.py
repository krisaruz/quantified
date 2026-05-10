"""TurnoverRule：换手率控制"""

from __future__ import annotations

import pandas as pd

from quantified.risk.protocol import RiskViolation


class TurnoverRule:
    """年化换手率不超过阈值"""

    name = "turnover"
    severity = "soft"

    def __init__(self, max_annual_turnover: int = 52) -> None:
        self.max_annual_turnover = max_annual_turnover

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        buy_sell_count = sum(1 for s in signals if s.direction in ("buy", "sell"))

        if buy_sell_count > self.max_annual_turnover / 52 * 4:  # 周均交易数
            violations.append(RiskViolation(
                rule_name=self.name,
                severity=self.severity,
                message=f"近期交易频率过高({buy_sell_count}笔/周)，超过年化{self.max_annual_turnover}次上限",
                current_value=float(buy_sell_count),
                threshold=float(self.max_annual_turnover),
                suggested_action="warn",
            ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        # 换手率违规时仅告警
        return signals
