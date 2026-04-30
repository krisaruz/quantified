"""测试 CLI 模块"""

from click.testing import CliRunner

from quantified.cli import main


class TestCLIImports:
    """确保 CLI 模块可以正常导入和初始化"""

    def test_main_group_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "量化转债" in result.output

    def test_sync_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["sync", "--help"])
        assert result.exit_code == 0
        assert "同步" in result.output

    def test_recommend_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["recommend", "--help"])
        assert result.exit_code == 0

    def test_status_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0

    def test_filter_check_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["filter-check", "--help"])
        assert result.exit_code == 0

    def test_web_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["web", "--help"])
        assert result.exit_code == 0
        assert "端口" in result.output
