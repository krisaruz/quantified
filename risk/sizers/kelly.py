"""KellySizer：凯利公式仓位管理"""

from __future__ import annotations


class KellySizer:
    """凯利公式：基于胜率和赔率的最优仓位

    f* = (p * b - q) / b
    其中 p = 胜率, b = 赔率, q = 1 - p

    实际使用半凯利以降低风险。
    """

    name = "kelly"

    def __init__(
        self,
        default_win_rate: float = 0.55,
        default_odds: float = 1.5,
        fraction: float = 0.5,
    ) -> None:
        self.default_win_rate = default_win_rate
        self.default_odds = default_odds
        self.fraction = fraction  # 半凯利 = 0.5

    def calculate_weights(
        self,
        signals: list,
        total_capital: float,
        market_data: object,
    ) -> dict[str, float]:
        buy_signals = [s for s in signals if s.direction == "buy"]
        if not buy_signals:
            return {}

        weights = {}
        for sig in buy_signals:
            win_rate = self._estimate_win_rate(sig)
            odds = self._estimate_odds(sig)

            # 凯利公式
            q = 1 - win_rate
            kelly = (win_rate * odds - q) / odds if odds > 0 else 0
            kelly = max(0, kelly) * self.fraction  # 半凯利

            weights[sig.cb_code] = kelly

        # 归一化到总仓位不超过 1
        total = sum(weights.values())
        if total > 1:
            weights = {code: w / total for code, w in weights.items()}

        return weights

    def _estimate_win_rate(self, signal: object) -> float:
        # 基于信号元数据估计胜率
        meta = getattr(signal, "metadata", {})
        return meta.get("win_rate", self.default_win_rate)

    def _estimate_odds(self, signal: object) -> float:
        # 基于信号元数据估计赔率
        meta = getattr(signal, "metadata", {})
        return meta.get("odds", self.default_odds)
