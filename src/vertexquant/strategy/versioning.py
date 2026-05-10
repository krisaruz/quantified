"""策略版本管理：参数快照 + 历史回测对比"""

from __future__ import annotations

import datetime
import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_VERSIONS_PATH = Path(__file__).resolve().parents[2] / "data" / "strategy_versions.jsonl"


@dataclass
class StrategyVersion:
    """策略版本快照"""

    strategy_name: str
    version: str
    parameters: dict
    created_at: str = field(default_factory=lambda: datetime.datetime.now().isoformat())
    description: str = ""
    backtest_result: dict | None = None


class VersionManager:
    """策略版本管理器"""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_VERSIONS_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_version(
        self,
        strategy_name: str,
        parameters: dict,
        version: str | None = None,
        description: str = "",
        backtest_result: dict | None = None,
    ) -> StrategyVersion:
        """保存策略参数快照"""
        if version is None:
            version = self._next_version(strategy_name)

        sv = StrategyVersion(
            strategy_name=strategy_name,
            version=version,
            parameters=parameters,
            description=description,
            backtest_result=backtest_result,
        )

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(sv), ensure_ascii=False) + "\n")

        logger.info("保存策略版本: %s v%s", strategy_name, version)
        return sv

    def list_versions(self, strategy_name: str | None = None) -> list[StrategyVersion]:
        """列出版本历史"""
        if not self.path.exists():
            return []

        versions: list[StrategyVersion] = []
        for line in self.path.read_text(encoding="utf-8").strip().splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                sv = StrategyVersion(**data)
                if strategy_name is None or sv.strategy_name == strategy_name:
                    versions.append(sv)
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning("解析版本记录失败: %s", e)

        return versions

    def get_latest(self, strategy_name: str) -> StrategyVersion | None:
        """获取最新版本"""
        versions = self.list_versions(strategy_name)
        return versions[-1] if versions else None

    def compare(
        self, strategy_name: str, version_a: str, version_b: str
    ) -> dict:
        """对比两个版本的参数差异"""
        versions = self.list_versions(strategy_name)
        va = next((v for v in versions if v.version == version_a), None)
        vb = next((v for v in versions if v.version == version_b), None)

        if not va or not vb:
            return {"error": "版本不存在"}

        diff: dict[str, dict] = {}
        all_keys = set(va.parameters.keys()) | set(vb.parameters.keys())

        for key in sorted(all_keys):
            val_a = va.parameters.get(key)
            val_b = vb.parameters.get(key)
            if val_a != val_b:
                diff[key] = {"from": val_a, "to": val_b}

        return {
            "strategy_name": strategy_name,
            "version_a": version_a,
            "version_b": version_b,
            "differences": diff,
            "backtest_a": va.backtest_result,
            "backtest_b": vb.backtest_result,
        }

    def _next_version(self, strategy_name: str) -> str:
        """生成下一个版本号"""
        versions = self.list_versions(strategy_name)
        if not versions:
            return "1.0.0"

        try:
            last = versions[-1].version
            parts = last.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except (ValueError, IndexError):
            return f"1.0.{len(versions)}"
