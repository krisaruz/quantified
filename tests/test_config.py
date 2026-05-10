"""测试配置加载模块"""

import tempfile
from pathlib import Path

import yaml

from vertexquant.config import AppConfig, load_config, rating_ge


class TestLoadConfig:
    def test_default_config(self):
        config = AppConfig()
        assert config.strategy.hold_count == 10
        assert config.filters.exclude_st is True
        assert config.risk.stop_loss_pct == -0.15

    def test_load_from_yaml(self, tmp_path):
        data = {
            "strategy": {"hold_count": 5, "name": "custom"},
            "filters": {"max_price": 120},
        }
        p = tmp_path / "test.yaml"
        p.write_text(yaml.dump(data), encoding="utf-8")

        config = load_config(p)
        assert config.strategy.hold_count == 5
        assert config.strategy.name == "custom"
        assert config.filters.max_price == 120
        assert config.filters.exclude_st is True  # default preserved

    def test_missing_file_returns_defaults(self, tmp_path):
        config = load_config(tmp_path / "nonexistent.yaml")
        assert config.strategy.hold_count == 10


class TestRatingGe:
    def test_equal(self):
        assert rating_ge("AA-", "AA-") is True

    def test_higher(self):
        assert rating_ge("AAA", "AA-") is True
        assert rating_ge("AA+", "AA-") is True

    def test_lower(self):
        assert rating_ge("A+", "AA-") is False

    def test_none(self):
        assert rating_ge(None, "AA-") is False

    def test_unknown_rating(self):
        assert rating_ge("XYZ", "AA-") is False
