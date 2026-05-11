"""CLI 命令行工具入口

提供 sync / recommend / status / filter-check 四个子命令。
"""

from __future__ import annotations

import datetime
import logging
import subprocess
import sys
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


@click.group()
def main():
    """量化转债套利系统 - 可转债双低轮动策略"""
    pass


@main.command()
@click.option("--full", is_flag=True, help="全量重新同步")
@click.option("--skip-stock-history", is_flag=True, help="跳过正股历史日线")
def sync(full: bool, skip_stock_history: bool):
    """同步最新行情数据"""
    script = Path(__file__).resolve().parents[1] / "scripts" / "sync_data.py"
    if not script.exists():
        click.echo(f"错误: 同步脚本不存在 ({script})")
        return

    cmd = [sys.executable, str(script)]
    if full:
        cmd.append("--full")
    if skip_stock_history:
        cmd.append("--skip-stock-history")

    click.echo("正在同步数据...")
    result = subprocess.run(cmd, cwd=str(script.parent.parent))
    if result.returncode == 0:
        click.echo("同步完成")
    else:
        click.echo(f"同步失败 (exit code {result.returncode})")


@main.command()
def recommend():
    """查看今日调仓建议"""
    from vertexquant.config import load_config
    from vertexquant.db import init_db
    from vertexquant.models.base import get_session_factory
    from vertexquant.portfolio import load_portfolio
    from vertexquant.recommender import Recommender, format_recommendation
    from vertexquant.universe import build_filtered_ranked

    config = load_config()
    engine = init_db()
    session_factory = get_session_factory(engine)

    today = datetime.date.today().isoformat()

    with session_factory() as session:
        _, filtered, _ = build_filtered_ranked(session, today, config)

    if filtered.empty:
        click.echo("无数据，请先运行 vertexquant sync")
        return

    portfolio = load_portfolio()
    recommender = Recommender(config)
    rec = recommender.generate(filtered, portfolio, today)

    click.echo(format_recommendation(rec, config))


@main.command()
def status():
    """查看当前持仓和收益"""
    from vertexquant.config import load_config
    from vertexquant.db import init_db
    from vertexquant.models.base import get_session_factory
    from vertexquant.portfolio import load_portfolio
    from vertexquant.universe import build_universe

    config = load_config()
    engine = init_db()
    session_factory = get_session_factory(engine)
    today = datetime.date.today().isoformat()

    portfolio = load_portfolio()

    with session_factory() as session:
        universe = build_universe(session, today)

    click.echo(f"\n{'='*40}")
    click.echo("  当前持仓状态")
    click.echo(f"{'='*40}\n")

    total_market = 0.0
    if not portfolio.holdings:
        click.echo("  暂无持仓\n")
    else:
        for h in portfolio.holdings:
            row = universe[universe["cb_code"] == h.cb_code] if not universe.empty else None
            current = float(row.iloc[0]["cb_close"]) if row is not None and not row.empty else h.buy_price
            pnl_pct = (current - h.buy_price) / h.buy_price if h.buy_price > 0 else 0
            mkt = current * h.volume / 10
            total_market += mkt
            sign = "+" if pnl_pct >= 0 else ""
            click.echo(f"  {h.cb_name} ({h.cb_code})")
            click.echo(f"    {h.volume}张 | 买入{h.buy_price:.1f} → 现价{current:.1f} | {sign}{pnl_pct:.1%}")

    total = portfolio.cash + total_market
    initial = config.capital.initial
    total_pnl = (total - initial) / initial if initial > 0 else 0
    click.echo(f"\n  可用资金: {portfolio.cash:,.0f} 元")
    click.echo(f"  持仓市值: {total_market:,.0f} 元")
    click.echo(f"  总资产:   {total:,.0f} 元 ({total_pnl:+.2%})\n")


@main.command("filter-check")
def filter_check():
    """查看过滤器执行详情"""
    from vertexquant.config import load_config
    from vertexquant.db import init_db
    from vertexquant.models.base import get_session_factory
    from vertexquant.universe import build_filtered_ranked

    config = load_config()
    engine = init_db()
    session_factory = get_session_factory(engine)

    today = datetime.date.today().isoformat()

    with session_factory() as session:
        universe, filtered, audit = build_filtered_ranked(session, today, config)

    if universe.empty:
        click.echo("无数据，请先运行 vertexquant sync")
        return

    click.echo(f"\n{'='*50}")
    click.echo("  过滤器执行详情")
    click.echo(f"{'='*50}\n")

    for step in audit:
        removed = step.before_count - step.after_count
        click.echo(f"  [{step.name}]  {step.before_count} → {step.after_count}  (-{removed})")
        if step.removed:
            click.echo(f"    排除: {', '.join(step.removed[:5])}{'...' if len(step.removed) > 5 else ''}")

    click.echo(f"\n  最终合格: {len(filtered)} 只转债\n")


@main.command()
@click.option("--start", required=True, help="起始日期 (YYYY-MM-DD)")
@click.option("--end", default=None, help="截止日期，默认今天")
@click.option("--skip-conv-price", is_flag=True, help="跳过转股价历史")
@click.option("--only-bonds", is_flag=True, help="只回填转债日线")
@click.option("--only-stocks", is_flag=True, help="只回填正股日线")
def backfill(start: str, end: str | None, skip_conv_price: bool, only_bonds: bool, only_stocks: bool):
    """回填历史数据（回测前需要先运行）"""
    script = Path(__file__).resolve().parents[1] / "scripts" / "backfill_history.py"
    if not script.exists():
        click.echo(f"错误: 回填脚本不存在 ({script})")
        return

    cmd = [sys.executable, str(script), "--start", start]
    if end:
        cmd.extend(["--end", end])
    if skip_conv_price:
        cmd.append("--skip-conv-price")
    if only_bonds:
        cmd.append("--only-bonds")
    if only_stocks:
        cmd.append("--only-stocks")

    click.echo(f"正在回填历史数据 [{start} ~ {end or '今天'}]...")
    result = subprocess.run(cmd, cwd=str(script.parent.parent))
    if result.returncode == 0:
        click.echo("回填完成")
    else:
        click.echo(f"回填失败 (exit code {result.returncode})")


@main.command()
@click.option("--start", required=True, help="回测起始日期 (YYYY-MM-DD)")
@click.option("--end", default=None, help="回测截止日期，默认今天")
def backtest(start: str, end: str | None):
    """运行策略回测"""
    from vertexquant.backtest.engine import BacktestEngine
    from vertexquant.backtest.stats import compute_stats
    from vertexquant.config import load_config
    from vertexquant.db import init_db
    from vertexquant.models.base import get_session_factory

    end = end or datetime.date.today().isoformat()
    config = load_config()
    engine = init_db()
    session_factory = get_session_factory(engine)

    click.echo(f"正在运行回测 [{start} ~ {end}]...")
    with session_factory() as session:
        bt = BacktestEngine(config, session)
        result = bt.run(start, end)

    stats = compute_stats(result)
    click.echo(stats.format_report())


@main.command()
@click.option("--port", default=5000, help="端口号")
def web(port: int):
    """启动 Web 界面"""
    from vertexquant.web.app import run_server
    click.echo(f"启动 Web 界面: http://127.0.0.1:{port}")
    run_server(port=port, debug=True)


if __name__ == "__main__":
    main()
