"""组合快照管理"""

from __future__ import annotations

import json
from pathlib import Path

from quantified.portfolio_manager.models import PortfolioSnapshot


class SnapshotManager:
    """快照管理器（文件系统实现）"""

    def __init__(self, snapshots_dir: Path) -> None:
        self._dir = snapshots_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, snapshot: PortfolioSnapshot) -> None:
        """保存快照"""
        path = self._dir / f"{snapshot.date}.json"
        data = {
            "date": snapshot.date,
            "portfolio_name": snapshot.portfolio_name,
            "cash": snapshot.cash,
            "holdings": [
                {
                    "cb_code": h.cb_code,
                    "cb_name": h.cb_name,
                    "volume": h.volume,
                    "avg_cost": h.avg_cost,
                    "current_price": h.current_price,
                    "market_value": h.market_value,
                    "pnl": h.pnl,
                    "pnl_pct": h.pnl_pct,
                    "weight": h.weight,
                }
                for h in snapshot.holdings
            ],
            "total_assets": snapshot.total_assets,
            "total_pnl_pct": snapshot.total_pnl_pct,
            "high_water_mark": snapshot.high_water_mark,
        }
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, date: str) -> PortfolioSnapshot | None:
        """加载快照"""
        path = self._dir / f"{date}.json"
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        from quantified.portfolio_manager.models import HoldingSnapshot

        holdings = [
            HoldingSnapshot(**h) for h in data["holdings"]
        ]
        return PortfolioSnapshot(
            date=data["date"],
            portfolio_name=data["portfolio_name"],
            cash=data["cash"],
            holdings=holdings,
            total_assets=data["total_assets"],
            total_pnl_pct=data["total_pnl_pct"],
            high_water_mark=data["high_water_mark"],
        )

    def list_dates(self) -> list[str]:
        """列出所有快照日期"""
        dates = []
        for p in self._dir.glob("*.json"):
            dates.append(p.stem)
        return sorted(dates)

    def get_history(
        self, start: str, end: str
    ) -> list[PortfolioSnapshot]:
        """获取时间范围内的快照历史"""
        snapshots: list[PortfolioSnapshot] = []
        for date_str in self.list_dates():
            if start <= date_str <= end:
                snap = self.load(date_str)
                if snap:
                    snapshots.append(snap)
        return snapshots

    def delete(self, date: str) -> bool:
        """删除快照"""
        path = self._dir / f"{date}.json"
        if path.exists():
            path.unlink()
            return True
        return False
