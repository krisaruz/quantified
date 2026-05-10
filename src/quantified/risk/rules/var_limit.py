"""VarLimitRule：VaR 限制"""

from __future__ import annotations

import math

import pandas as pd

from quantified.risk.protocol import RiskViolation


class VarLimitRule:
    """组合 VaR 不超过阈值"""

    name = "var_limit"
    severity = "soft"

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        var_limit = 0.05  # 默认 5%

        # 简化 VaR 计算：基于持仓的价格分布
        holdings = getattr(portfolio, "holdings", [])
        if len(holdings) < 2:
            return violations

        total = sum(
            getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10
            for h in holdings
        )
        if total <= 0:
            return violations

        # 估算组合波动率（简化）
        weights = [
            getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10 / total
            for h in holdings
        ]
        # 假设平均日波动率 2%，简化计算
        avg_vol = 0.02
        portfolio_vol = avg_vol * math.sqrt(sum(w ** 2 for w in weights))

        # 95% VaR
        var_95 = portfolio_vol * 1.645

        if var_95 > var_limit:
            violations.append(RiskViolation(
                rule_name=self.name,
                severity=self.severity,
                message=f"组合 VaR {var_95:.2%} 超过上限 {var_limit:.0%}",
                current_value=var_95,
                threshold=var_limit,
                suggested_action="warn",
            ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        return signals
