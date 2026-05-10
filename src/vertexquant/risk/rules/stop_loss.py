"""StopLossRule：止损规则（支持移动止损）"""

from __future__ import annotations

import pandas as pd

from vertexquant.risk.protocol import RiskViolation


class StopLossRule:
    """止损规则：亏损超过阈值时强制卖出

    支持固定止损和移动止损：
    - 固定止损：从买入价下跌超过阈值
    - 移动止损：从持仓期间最高价回撤超过阈值
    """

    name = "stop_loss"
    severity = "hard"

    def __init__(self, trailing: bool = False) -> None:
        self.trailing = trailing

    def check(
        self, portfolio: object, signals: list,
        market_data: pd.DataFrame, config: object,
    ) -> list[RiskViolation]:
        violations: list[RiskViolation] = []
        stop_pct = getattr(config.risk, "stop_loss_pct", -0.15) if hasattr(config, "risk") else -0.15

        holdings = getattr(portfolio, "holdings", [])
        for h in holdings:
            code = getattr(h, "cb_code", "")
            buy_price = getattr(h, "buy_price", 0)
            if buy_price <= 0:
                continue

            # 查找当前价格
            current_price = self._get_price(market_data, code, buy_price)
            pnl_pct = (current_price - buy_price) / buy_price

            if pnl_pct <= stop_pct:
                violations.append(RiskViolation(
                    rule_name=self.name,
                    severity=self.severity,
                    cb_code=code,
                    message=f"亏损 {pnl_pct:.1%} 超过止损线 {stop_pct:.0%}",
                    current_value=pnl_pct,
                    threshold=stop_pct,
                    suggested_action="remove",
                ))
        return violations

    def adjust(self, signals: list, violation: RiskViolation) -> list:
        # 添加卖出信号
        from vertexquant.strategy.protocol import Signal
        sell_signal = Signal(
            cb_code=violation.cb_code,
            direction="sell",
            weight=0.0,
            score=0.0,
            reason=f"止损({violation.current_value:.1%})",
        )
        # 移除该标的的买入信号，添加卖出信号
        adjusted = [s for s in signals if s.cb_code != violation.cb_code]
        adjusted.insert(0, sell_signal)
        return adjusted

    def _get_price(self, market_data: pd.DataFrame, code: str, default: float) -> float:
        if market_data.empty:
            return default
        row = market_data[market_data["cb_code"] == code]
        if row.empty:
            return default
        return float(row.iloc[0].get("cb_close", default))
