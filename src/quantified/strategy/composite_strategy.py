"""多策略组合器：加权融合多个子策略的信号"""

from __future__ import annotations

import logging
from collections import defaultdict

from quantified.strategy.protocol import Signal, StrategyContext
from quantified.strategy.registry import StrategyRegistry

logger = logging.getLogger(__name__)


@StrategyRegistry.register("composite")
class CompositeStrategy:
    """多策略组合器

    支持两种融合模式：
    - weighted_average: 加权平均得分
    - voting: 多数投票（超过半数策略同意才生成信号）
    """

    name = "composite"
    version = "1.0.0"
    description = "多策略组合器：加权融合多个子策略信号"

    def __init__(
        self,
        strategies: list[dict],
        method: str = "weighted_average",
        hold_count: int = 10,
        max_position_pct: float = 0.10,
    ) -> None:
        self.method = method
        self.hold_count = hold_count
        self.max_position_pct = max_position_pct
        self._sub_strategies: list[tuple[any, float]] = []

        for s in strategies:
            name = s["name"]
            weight = s.get("weight", 1.0)
            params = s.get("params", {})
            try:
                strategy = StrategyRegistry.get(name, **params)
                self._sub_strategies.append((strategy, weight))
            except KeyError:
                logger.warning("子策略 '%s' 未注册，跳过", name)

    def generate_signals(self, context: StrategyContext) -> list[Signal]:
        if not self._sub_strategies:
            return []

        # 收集所有子策略信号
        all_signals: dict[str, list[tuple[Signal, float]]] = defaultdict(list)

        for strategy, weight in self._sub_strategies:
            try:
                signals = strategy.generate_signals(context)
                for sig in signals:
                    all_signals[sig.cb_code].append((sig, weight))
            except Exception as e:
                logger.warning("子策略 '%s' 执行失败: %s", strategy.name, e)

        if not all_signals:
            return []

        # 融合信号
        if self.method == "voting":
            return self._merge_voting(all_signals, context)
        return self._merge_weighted(all_signals)

    def _merge_weighted(
        self, all_signals: dict[str, list[tuple[Signal, float]]]
    ) -> list[Signal]:
        """加权平均融合"""
        merged: list[Signal] = []

        for code, pairs in all_signals.items():
            # 统计各方向的加权得分
            direction_scores: dict[str, list[tuple[float, float]]] = defaultdict(list)
            for sig, weight in pairs:
                direction_scores[sig.direction].append((sig.score, weight))

            # 选择权重最高的方向
            best_direction = "hold"
            best_weighted_score = 0.0
            for direction, score_weight_pairs in direction_scores.items():
                total_weight = sum(w for _, w in score_weight_pairs)
                weighted_score = sum(s * w for s, w in score_weight_pairs) / total_weight if total_weight > 0 else 0
                if direction == "buy" and total_weight > best_weighted_score:
                    best_direction = "buy"
                    best_weighted_score = weighted_score
                elif direction == "sell" and any(s <= 0 for s, _ in score_weight_pairs):
                    best_direction = "sell"
                    best_weighted_score = 0

            # 合并原因
            reasons = [f"{p[0].reason}({w:.0%})" for p, w in zip(pairs, [w for _, w in pairs])]
            combined_reason = " | ".join(reasons[:3])

            # 计算平均分数和权重
            all_weights = [w for _, w in pairs]
            all_scores = [s.score for s, _ in pairs]
            avg_weight = sum(all_weights) / len(all_weights)
            avg_score = sum(s * w for s, w in zip(all_scores, all_weights)) / sum(all_weights)

            merged.append(Signal(
                cb_code=code,
                direction=best_direction,
                weight=avg_weight if best_direction == "buy" else 0.0,
                score=avg_score,
                reason=f"组合策略({len(pairs)}个子策略): {combined_reason}",
                metadata={"sub_signals": len(pairs)},
            ))

        # 按分数排序
        merged.sort(key=lambda s: s.score, reverse=True)
        return merged

    def _merge_voting(
        self,
        all_signals: dict[str, list[tuple[Signal, float]]],
        context: StrategyContext,
    ) -> list[Signal]:
        """投票融合：超过半数策略同意才生成信号"""
        total_strategies = len(self._sub_strategies)
        threshold = total_strategies / 2

        merged: list[Signal] = []

        for code, pairs in all_signals.items():
            buy_votes = sum(w for s, w in pairs if s.direction == "buy")
            sell_votes = sum(w for s, w in pairs if s.direction == "sell")

            if buy_votes > threshold:
                avg_score = sum(s.score * w for s, w in pairs if s.direction == "buy") / buy_votes
                merged.append(Signal(
                    cb_code=code, direction="buy",
                    weight=self.max_position_pct,
                    score=avg_score,
                    reason=f"投票通过({buy_votes:.1f}/{total_strategies}票)",
                ))
            elif sell_votes > threshold:
                merged.append(Signal(
                    cb_code=code, direction="sell",
                    weight=0.0, score=0.0,
                    reason=f"投票卖出({sell_votes:.1f}/{total_strategies}票)",
                ))

        merged.sort(key=lambda s: s.score, reverse=True)
        return merged

    def get_parameters(self) -> dict:
        return {
            "method": self.method,
            "hold_count": self.hold_count,
            "max_position_pct": self.max_position_pct,
            "strategies": [
                {"name": s.name, "weight": w, "params": s.get_parameters()}
                for s, w in self._sub_strategies
            ],
        }

    def set_parameters(self, params: dict) -> None:
        if "method" in params:
            self.method = params["method"]
        if "hold_count" in params:
            self.hold_count = int(params["hold_count"])
        if "max_position_pct" in params:
            self.max_position_pct = float(params["max_position_pct"])
