"""组合管理器"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from quantified.portfolio_manager.models import (
    PortfolioSnapshot,
    PortfolioSummary,
    PortfolioTemplate,
)
from quantified.portfolio_manager.snapshot import SnapshotManager
from quantified.portfolio_manager.templates import BUILTIN_TEMPLATES, get_template


class PortfolioManager:
    """多组合管理器"""

    def __init__(self, data_dir: Path = Path("data/portfolios")) -> None:
        self._data_dir = data_dir
        self._data_dir.mkdir(parents=True, exist_ok=True)

    def create(
        self,
        name: str,
        template: str = "balanced",
        initial_capital: float = 100000,
    ) -> PortfolioSummary:
        """从模板创建组合"""
        portfolio_dir = self._data_dir / name
        if portfolio_dir.exists():
            raise ValueError(f"组合 '{name}' 已存在")

        portfolio_dir.mkdir(parents=True)
        (portfolio_dir / "snapshots").mkdir()

        now = datetime.now().isoformat()
        meta = {
            "name": name,
            "template": template,
            "created_at": now,
            "last_updated": now,
            "initial_capital": initial_capital,
        }
        (portfolio_dir / "meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 初始化空持仓
        portfolio_data = {
            "cash": initial_capital,
            "holdings": [],
            "high_water_mark": initial_capital,
            "trade_history": [],
        }
        (portfolio_dir / "portfolio.json").write_text(
            json.dumps(portfolio_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        return PortfolioSummary(
            name=name,
            template=template,
            created_at=now,
            last_updated=now,
            holding_count=0,
            cash=initial_capital,
            total_assets=initial_capital,
            total_pnl_pct=0.0,
        )

    def load(self, name: str) -> dict:
        """加载组合数据"""
        portfolio_dir = self._data_dir / name
        if not portfolio_dir.exists():
            raise FileNotFoundError(f"组合 '{name}' 不存在")

        portfolio_path = portfolio_dir / "portfolio.json"
        return json.loads(portfolio_path.read_text(encoding="utf-8"))

    def save(self, name: str, data: dict) -> None:
        """保存组合数据"""
        portfolio_dir = self._data_dir / name
        if not portfolio_dir.exists():
            raise FileNotFoundError(f"组合 '{name}' 不存在")

        portfolio_path = portfolio_dir / "portfolio.json"
        portfolio_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 更新 last_updated
        meta_path = portfolio_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["last_updated"] = datetime.now().isoformat()
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def list_portfolios(self) -> list[PortfolioSummary]:
        """列出所有组合"""
        summaries: list[PortfolioSummary] = []

        for portfolio_dir in sorted(self._data_dir.iterdir()):
            if not portfolio_dir.is_dir():
                continue

            meta_path = portfolio_dir / "meta.json"
            portfolio_path = portfolio_dir / "portfolio.json"

            if not meta_path.exists() or not portfolio_path.exists():
                continue

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            portfolio = json.loads(portfolio_path.read_text(encoding="utf-8"))

            total_assets = portfolio.get("cash", 0) + sum(
                h.get("market_value", 0) for h in portfolio.get("holdings", [])
            )
            initial = meta.get("initial_capital", 100000)
            pnl_pct = (total_assets / initial - 1) if initial > 0 else 0

            summaries.append(PortfolioSummary(
                name=meta["name"],
                template=meta.get("template", "balanced"),
                created_at=meta.get("created_at", ""),
                last_updated=meta.get("last_updated", ""),
                holding_count=len(portfolio.get("holdings", [])),
                cash=portfolio.get("cash", 0),
                total_assets=total_assets,
                total_pnl_pct=pnl_pct,
            ))

        return summaries

    def delete(self, name: str) -> None:
        """删除组合"""
        import shutil

        portfolio_dir = self._data_dir / name
        if not portfolio_dir.exists():
            raise FileNotFoundError(f"组合 '{name}' 不存在")
        shutil.rmtree(portfolio_dir)

    def rename(self, old_name: str, new_name: str) -> None:
        """重命名组合"""
        old_dir = self._data_dir / old_name
        new_dir = self._data_dir / new_name

        if not old_dir.exists():
            raise FileNotFoundError(f"组合 '{old_name}' 不存在")
        if new_dir.exists():
            raise ValueError(f"组合 '{new_name}' 已存在")

        old_dir.rename(new_dir)

        # 更新 meta.json
        meta_path = new_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["name"] = new_name
            meta["last_updated"] = datetime.now().isoformat()
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def duplicate(self, source: str, target: str) -> None:
        """复制组合"""
        import shutil

        source_dir = self._data_dir / source
        target_dir = self._data_dir / target

        if not source_dir.exists():
            raise FileNotFoundError(f"源组合 '{source}' 不存在")
        if target_dir.exists():
            raise ValueError(f"目标组合 '{target}' 已存在")

        shutil.copytree(source_dir, target_dir)

        # 更新 meta.json
        meta_path = target_dir / "meta.json"
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["name"] = target
            meta["created_at"] = datetime.now().isoformat()
            meta["last_updated"] = datetime.now().isoformat()
            meta_path.write_text(
                json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    def get_snapshot_manager(self, name: str) -> SnapshotManager:
        """获取组合的快照管理器"""
        return SnapshotManager(self._data_dir / name / "snapshots")
