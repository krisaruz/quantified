"""SectorConcentrationRule：行业集中度限制"""

from __future__ import annotations

import pandas as pd

from vertexquant.risk.protocol import RiskViolation


class SectorConcentrationRule:
    """单个行业持仓占比不超过阈值"""

    name = "sector_concentration"
    severity = "soft"

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        max_sector_pct = 0.30  # 默认

        holdings = getattr(portfolio, "holdings", [])
        if not holdings:
            return violations

        # 按行业分组计算占比
        total = sum(
            getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10
            for h in holdings
        )
        if total <= 0:
            return violations

        sector_values: dict[str, float] = {}
        for h in holdings:
            code = getattr(h, "cb_code", "")
            mv = getattr(h, "buy_price", 0) * getattr(h, "volume", 0) / 10
            industry = self._get_industry(market_data, code)
            sector_values[industry] = sector_values.get(industry, 0) + mv

        for industry, value in sector_values.items():
            pct = value / total
            if pct > max_sector_pct:
                violations.append(RiskViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    message=f"行业 '{industry}' 占比 {pct:.1%} 超过上限 {max_sector_pct:.0%}",
                    current_value=pct,
                    threshold=max_sector_pct,
                    suggested_action="reduce",
                ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        # 行业集中度违规时不自动调整，仅告警
        return signals

    def _get_industry(self, market_data: pd.DataFrame, code: str) -> str:
        if market_data.empty:
            return "未知"
        row = market_data[market_data["cb_code"] == code]
        if row.empty:
            return "未知"
        return str(row.iloc[0].get("industry", "未知"))
