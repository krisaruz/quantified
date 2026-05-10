"""风控引擎：多层风控规则链"""

from __future__ import annotations

import logging

import pandas as pd

from quantified.risk.protocol import IRiskRule, RiskViolation

logger = logging.getLogger(__name__)


class RiskEngine:
    """风控引擎：执行多层风控规则链

    用法：
        engine = RiskEngine()
        engine.add_rule(MaxPositionRule())
        engine.add_rule(StopLossRule())

        violations = engine.check(portfolio, signals, market_data, config)
        adjusted = engine.adjust(signals, violations)
    """

    def __init__(self) -> None:
        self.rules: list[IRiskRule] = []

    def add_rule(self, rule: IRiskRule) -> None:
        """添加风控规则"""
        self.rules.append(rule)
        logger.debug("添加风控规则: %s (%s)", rule.name, rule.severity)

    def check(
        self,
        portfolio: object,
        signals: list,
        market_data: pd.DataFrame,
        config: object,
    ) -> list[RiskViolation]:
        """执行所有风控规则检查"""
        violations: list[RiskViolation] = []
        for rule in self.rules:
            try:
                rule_violations = rule.check(portfolio, signals, market_data, config)
                violations.extend(rule_violations)
            except Exception as e:
                logger.warning("风控规则 '%s' 执行失败: %s", rule.name, e)
        return violations

    def adjust(
        self,
        signals: list,
        violations: list[RiskViolation],
    ) -> list:
        """根据违规调整信号"""
        adjusted = list(signals)
        for violation in violations:
            rule = self._find_rule(violation.rule_name)
            if rule:
                try:
                    adjusted = rule.adjust(adjusted, violation)
                except Exception as e:
                    logger.warning("规则 '%s' 调整信号失败: %s", rule.name, e)
        return adjusted

    def check_and_adjust(
        self,
        portfolio: object,
        signals: list,
        market_data: pd.DataFrame,
        config: object,
    ) -> tuple[list, list[RiskViolation]]:
        """检查并调整信号"""
        violations = self.check(portfolio, signals, market_data, config)
        adjusted = self.adjust(signals, violations)
        return adjusted, violations

    def _find_rule(self, name: str) -> IRiskRule | None:
        for rule in self.rules:
            if rule.name == name:
                return rule
        return None

    def list_rules(self) -> list[dict]:
        """列出所有规则"""
        return [{"name": r.name, "severity": r.severity} for r in self.rules]
