"""EqualWeightSizer：等权重分配"""

from __future__ import annotations


class EqualWeightSizer:
    """等权重分配：每个标的分配相同权重"""

    name = "equal_weight"

    def calculate_weights(
        self,
        signals: list,
        total_capital: float,
        market_data: object,
    ) -> dict[str, float]:
        buy_signals = [s for s in signals if s.direction == "buy"]
        if not buy_signals:
            return {}

        weight = 1.0 / len(buy_signals)
        return {s.cb_code: weight for s in buy_signals}
