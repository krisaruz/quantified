"""数据质量校验

提供可转债/股票数据的质量检查框架。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class QualityCheck:
    """单项质量检查结果"""

    name: str
    passed: bool
    message: str
    affected_rows: int
    severity: str  # "error" | "warning"
    details: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class QualityReport:
    """数据质量报告"""

    entity: str
    check_date: str
    total_rows: int
    checks: list[QualityCheck]

    @property
    def overall_score(self) -> float:
        if not self.checks:
            return 1.0
        passed = sum(1 for c in self.checks if c.passed)
        return passed / len(self.checks)

    @property
    def is_acceptable(self) -> bool:
        return self.overall_score >= 0.8

    @property
    def errors(self) -> list[QualityCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "error"]

    @property
    def warnings(self) -> list[QualityCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "warning"]


class DataQualityChecker:
    """数据质量校验器"""

    def check_bond_daily(
        self,
        df: pd.DataFrame,
        check_date: str,
    ) -> QualityReport:
        """校验转债日线数据质量"""
        checks: list[QualityCheck] = []

        checks.append(self._check_price_range(df))
        checks.append(self._check_ohlc_consistency(df))
        checks.append(self._check_volume_non_negative(df))
        checks.append(self._check_sudden_jump(df))
        checks.append(self._check_zero_volume(df))

        return QualityReport(
            entity="bond_daily",
            check_date=check_date,
            total_rows=len(df),
            checks=checks,
        )

    def check_stock_daily(
        self,
        df: pd.DataFrame,
        check_date: str,
    ) -> QualityReport:
        """校验股票日线数据质量"""
        checks: list[QualityCheck] = []

        checks.append(self._check_price_range(df))
        checks.append(self._check_ohlc_consistency(df))
        checks.append(self._check_volume_non_negative(df))
        checks.append(self._check_sudden_jump(df))

        return QualityReport(
            entity="stock_daily",
            check_date=check_date,
            total_rows=len(df),
            checks=checks,
        )

    def _check_price_range(
        self,
        df: pd.DataFrame,
        low: float = 50.0,
        high: float = 500.0,
    ) -> QualityCheck:
        """价格范围检查"""
        if "close" not in df.columns:
            return QualityCheck(
                name="price_range",
                passed=True,
                message="无 close 列，跳过",
                affected_rows=0,
                severity="warning",
            )

        mask = (df["close"] < low) | (df["close"] > high)
        affected = df[mask]

        return QualityCheck(
            name="price_range",
            passed=len(affected) == 0,
            message=f"{len(affected)} 行价格超出 [{low}, {high}] 范围",
            affected_rows=len(affected),
            severity="warning",
            details=affected[["close"]].to_dict("records") if len(affected) > 0 else [],
        )

    def _check_ohlc_consistency(self, df: pd.DataFrame) -> QualityCheck:
        """OHLC 一致性检查: high >= max(open, close), low <= min(open, close)"""
        required = {"open", "high", "low", "close"}
        if not required.issubset(df.columns):
            return QualityCheck(
                name="ohlc_consistency",
                passed=True,
                message="缺少 OHLC 列，跳过",
                affected_rows=0,
                severity="error",
            )

        cond_high = df["high"] >= df[["open", "close"]].max(axis=1)
        cond_low = df["low"] <= df[["open", "close"]].min(axis=1)
        violations = df[~(cond_high & cond_low)]

        return QualityCheck(
            name="ohlc_consistency",
            passed=len(violations) == 0,
            message=f"{len(violations)} 行 OHLC 不一致",
            affected_rows=len(violations),
            severity="error",
        )

    def _check_volume_non_negative(self, df: pd.DataFrame) -> QualityCheck:
        """成交量非负检查"""
        if "volume" not in df.columns:
            return QualityCheck(
                name="volume_non_negative",
                passed=True,
                message="无 volume 列，跳过",
                affected_rows=0,
                severity="error",
            )

        violations = df[df["volume"] < 0]
        return QualityCheck(
            name="volume_non_negative",
            passed=len(violations) == 0,
            message=f"{len(violations)} 行成交量为负",
            affected_rows=len(violations),
            severity="error",
        )

    def _check_sudden_jump(
        self,
        df: pd.DataFrame,
        threshold: float = 0.30,
    ) -> QualityCheck:
        """相邻日涨跌幅突变检查"""
        if "close" not in df.columns or len(df) < 2:
            return QualityCheck(
                name="sudden_jump",
                passed=True,
                message="数据不足或无 close 列，跳过",
                affected_rows=0,
                severity="warning",
            )

        pct_change = df["close"].pct_change().abs()
        violations = df[pct_change > threshold]

        return QualityCheck(
            name="sudden_jump",
            passed=len(violations) == 0,
            message=f"{len(violations)} 行涨跌幅超过 {threshold:.0%}",
            affected_rows=len(violations),
            severity="warning",
        )

    def _check_zero_volume(
        self,
        df: pd.DataFrame,
        consecutive: int = 3,
    ) -> QualityCheck:
        """连续零成交量检查"""
        if "volume" not in df.columns:
            return QualityCheck(
                name="zero_volume",
                passed=True,
                message="无 volume 列，跳过",
                affected_rows=0,
                severity="warning",
            )

        is_zero = (df["volume"] == 0).astype(int)
        rolling_sum = is_zero.rolling(window=consecutive, min_periods=consecutive).sum()
        consecutive_zeros = (rolling_sum >= consecutive).sum()

        return QualityCheck(
            name="zero_volume",
            passed=consecutive_zeros == 0,
            message=f"存在 {consecutive_zeros} 处连续 {consecutive} 日零成交量",
            affected_rows=int(consecutive_zeros),
            severity="warning",
        )
