"""组合模板

内置模板定义和模板管理。
"""

from __future__ import annotations

from quantified.portfolio_manager.models import PortfolioTemplate

BUILTIN_TEMPLATES: dict[str, PortfolioTemplate] = {
    "conservative": PortfolioTemplate(
        name="保守型",
        description="低风险、稳定收益，适合风险厌恶型投资者",
        config_overrides={
            "strategy.hold_count": 15,
            "strategy.scoring.credit.unknown": 8.0,
            "filters.min_credit_rating": "AA",
            "filters.max_price": 120,
            "risk.max_position_pct": 0.06,
            "risk.stop_loss_pct": -0.10,
            "risk.max_drawdown_pct": -0.06,
        },
        is_builtin=True,
    ),
    "balanced": PortfolioTemplate(
        name="均衡型",
        description="风险收益平衡，适合大多数投资者",
        config_overrides={
            "strategy.hold_count": 10,
            "filters.min_credit_rating": "AA-",
            "filters.max_price": 130,
            "risk.max_position_pct": 0.10,
            "risk.stop_loss_pct": -0.15,
            "risk.max_drawdown_pct": -0.10,
        },
        is_builtin=True,
    ),
    "aggressive": PortfolioTemplate(
        name="激进型",
        description="高风险高收益，适合风险偏好型投资者",
        config_overrides={
            "strategy.hold_count": 5,
            "strategy.scoring.credit.unknown": 3.0,
            "filters.min_credit_rating": "A+",
            "filters.max_price": 150,
            "risk.max_position_pct": 0.20,
            "risk.stop_loss_pct": -0.25,
            "risk.max_drawdown_pct": -0.15,
        },
        is_builtin=True,
    ),
}


def get_template(name: str) -> PortfolioTemplate | None:
    """获取模板"""
    return BUILTIN_TEMPLATES.get(name)


def list_templates() -> list[PortfolioTemplate]:
    """列出所有内置模板"""
    return list(BUILTIN_TEMPLATES.values())


def apply_template(
    config_data: dict[str, object],
    template: PortfolioTemplate,
) -> dict[str, object]:
    """将模板覆盖应用到配置数据

    Args:
        config_data: 原始配置字典
        template: 组合模板

    Returns:
        应用模板覆盖后的新配置字典
    """
    import copy

    result = copy.deepcopy(config_data)
    for key, value in template.config_overrides.items():
        _set_nested(result, key, value)
    return result


def _set_nested(data: dict, key: str, value: object) -> None:
    """设置嵌套字典值

    支持点分路径，如 "risk.max_position_pct"
    """
    parts = key.split(".")
    current = data
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    current[parts[-1]] = value
