"""RiskParitySizer：风险平价分配"""

from __future__ import annotations

import math


class RiskParitySizer:
    """风险平价：各标的对组合风险贡献相等

    简化实现：基于等波动率假设的反方差加权。
    """

    name = "risk_parity"

    def __init__(self, default_vol: float = 0.02) -> None:
        self.default_vol = default_vol

    def calculate_weights(
        self,
        signals: list,
        total_capital: float,
        market_data: object,
    ) -> dict[str, float]:
        buy_signals = [s for s in signals if s.direction == "buy"]
        if not buy_signals:
            return {}

        # 获取各标的波动率
        vols = {}
        for sig in buy_signals:
            vol = self._get_volatility(market_data, sig.cb_code)
            vols[sig.cb_code] = vol if vol and vol > 0 else self.default_vol

        # 反方差加权
        inv_vols = {code: 1.0 / (v ** 2) for code, v in vols.items()}
        total_inv = sum(inv_vols.values())

        if total_inv <= 0:
            weight = 1.0 / len(buy_signals)
            return {s.cb_code: weight for s in buy_signals}

        return {code: iv / total_inv for code, iv in inv_vols.items()}

    def _get_volatility(self, market_data: object, code: str) -> float | None:
        if market_data is None or not hasattr(market_data, "empty"):
            return None
        if market_data.empty:
            return None
        row = market_data[market_data["cb_code"] == code]
        if row.empty:
            return None
        return float(row.iloc[0].get("volatility_20d", self.default_vol))
