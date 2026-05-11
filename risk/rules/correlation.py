"""CorrelationRule：持仓相关性控制"""

from __future__ import annotations

import pandas as pd

from vertexquant.risk.protocol import RiskViolation


class CorrelationRule:
    """任意两只持仓的相关性不超过阈值"""

    name = "correlation"
    severity = "soft"

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        max_corr = 0.8  # 默认

        holdings = getattr(portfolio, "holdings", [])
        if len(holdings) < 2:
            return violations

        codes = [getattr(h, "cb_code", "") for h in holdings]
        # 检查是否有相关性数据
        if "correlation" not in market_data.columns:
            return violations

        for i, code_a in enumerate(codes):
            for code_b in codes[i + 1:]:
                corr = self._get_correlation(market_data, code_a, code_b)
                if corr is not None and corr > max_corr:
                    violations.append(RiskViolation(
                        rule_name=self.name,
                        severity=self.severity,
                        cb_code=code_a,
                        message=f"持仓 {code_a} 与 {code_b} 相关性 {corr:.2f} 超过上限 {max_corr}",
                        current_value=corr,
                        threshold=max_corr,
                        suggested_action="warn",
                    ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        # 相关性违规时仅告警
        return signals

    def _get_correlation(self, market_data: pd.DataFrame, code_a: str, code_b: str) -> float | None:
        # 简化实现：返回 None
        return None
