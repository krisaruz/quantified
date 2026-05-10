"""Flask Web 应用 —— 量化转债套利系统前端"""

from __future__ import annotations

import datetime
import logging
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request

from quantified.config import load_config
from quantified.db import init_db
from quantified.models.base import get_session_factory
from quantified.portfolio import Holding, append_trade_history, load_portfolio, load_trade_history, save_portfolio
from quantified.recommender import Recommender
from quantified.universe import build_filtered_ranked, build_universe

logger = logging.getLogger(__name__)


def _validate_date_param(name: str = "date") -> str | None:
    """校验请求中的日期参数格式，返回错误 JSON 响应或 None（合法）。"""
    val = request.args.get(name)
    if val is None:
        return None
    try:
        datetime.date.fromisoformat(val)
    except ValueError:
        return None  # will be caught below
    return None


def _parse_date_or_400(name: str = "date", default: str | None = None):
    """解析日期参数，格式无效时返回 (None, 400-response)。"""
    val = request.args.get(name, default)
    if val is None:
        return default, None
    try:
        datetime.date.fromisoformat(val)
        return val, None
    except ValueError:
        return None, (jsonify({"status": "error", "message": "日期格式无效，请使用 YYYY-MM-DD 格式"}), 400)

TEMPLATE_DIR = Path(__file__).parent / "templates"
app = Flask(__name__, template_folder=str(TEMPLATE_DIR))

_engine = None
_session_factory = None


def _get_session():
    global _engine, _session_factory
    if _engine is None:
        _engine = init_db()
        _session_factory = get_session_factory(_engine)
    return _session_factory()


def _safe_json(obj):
    """递归处理 numpy 类型为 Python 原生类型"""
    if isinstance(obj, dict):
        return {k: _safe_json(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_safe_json(i) for i in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.bool_):
        return bool(obj)
    if isinstance(obj, float) and (np.isnan(obj) or np.isinf(obj)):
        return None
    if isinstance(obj, datetime.date):
        return obj.isoformat()
    return obj


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/universe")
def api_universe():
    """获取全市场转债截面数据（已过滤+计算双低）"""
    config = load_config()
    today, err = _parse_date_or_400("date", datetime.date.today().isoformat())
    if err:
        return err

    session = _get_session()
    try:
        universe, filtered, audit = build_filtered_ranked(session, today, config)
    finally:
        session.close()

    if universe.empty:
        return jsonify({"status": "no_data", "items": [], "filter_audit": []})

    items = filtered.to_dict(orient="records") if not filtered.empty else []
    audit_list = [asdict(s) for s in audit]

    return jsonify(_safe_json({
        "status": "ok",
        "version": _get_version(),
        "date": today,
        "total_before_filter": len(universe),
        "total_after_filter": len(filtered),
        "items": items,
        "filter_audit": audit_list,
    }))


@app.route("/api/recommendation")
def api_recommendation():
    """获取调仓建议"""
    config = load_config()
    today, err = _parse_date_or_400("date", datetime.date.today().isoformat())
    if err:
        return err

    session = _get_session()
    try:
        _, filtered, _ = build_filtered_ranked(session, today, config)
    finally:
        session.close()

    if filtered.empty:
        return jsonify({"status": "no_data", "actions": []})

    portfolio = load_portfolio()
    recommender = Recommender(config)
    rec = recommender.generate(filtered, portfolio, today)

    return jsonify(_safe_json({
        "status": "ok",
        "version": _get_version(),
        "date": rec.date,
        "is_rebalance_day": rec.is_rebalance_day,
        "drawdown_paused": rec.drawdown_paused,
        "target_count": rec.target_count,
        "current_count": rec.current_count,
        "cash": rec.cash,
        "total_value": rec.total_value,
        "total_pnl_pct": rec.total_pnl_pct,
        "summary": rec.summary,
        "actions": [asdict(a) for a in rec.actions],
    }))


@app.route("/api/portfolio")
def api_portfolio():
    """获取当前持仓，联查当前市价计算盈亏"""
    config = load_config()
    portfolio = load_portfolio()
    today, err = _parse_date_or_400("date", datetime.date.today().isoformat())
    if err:
        return err

    holdings_data = []
    total_market_value = 0.0

    session = _get_session()
    try:
        universe = build_universe(session, today)
    finally:
        session.close()

    for h in portfolio.holdings:
        row = universe[universe["cb_code"] == h.cb_code] if not universe.empty else pd.DataFrame()
        current_price = float(row.iloc[0]["cb_close"]) if not row.empty else h.buy_price
        cost = h.buy_price * h.volume / 10
        market_val = current_price * h.volume / 10
        pnl = market_val - cost
        pnl_pct = (current_price - h.buy_price) / h.buy_price if h.buy_price > 0 else 0
        fee = _calc_fee(cost, config) + _calc_fee(market_val, config)
        total_market_value += market_val
        holdings_data.append({
            "cb_code": h.cb_code,
            "cb_name": h.cb_name,
            "buy_date": h.buy_date,
            "buy_price": h.buy_price,
            "current_price": current_price,
            "volume": h.volume,
            "cost": round(cost, 2),
            "market_value": round(market_val, 2),
            "pnl": round(pnl - fee, 2),
            "pnl_pct": round(pnl_pct, 4),
            "fee": round(fee, 2),
        })

    total_assets = portfolio.cash + total_market_value
    initial = config.capital.initial
    total_pnl_pct = (total_assets - initial) / initial if initial > 0 else 0

    return jsonify(_safe_json({
        "status": "ok",
        "cash": portfolio.cash,
        "count": len(portfolio.holdings),
        "total_market_value": round(total_market_value, 2),
        "total_assets": round(total_assets, 2),
        "total_pnl_pct": round(total_pnl_pct, 4),
        "holdings": holdings_data,
    }))


@app.route("/api/portfolio/buy", methods=["POST"])
def api_buy():
    """买入操作"""
    data = request.json
    if not data or "cb_code" not in data or "buy_price" not in data or "volume" not in data:
        return jsonify({"status": "error", "message": "缺少必要参数"}), 400

    config = load_config()
    price = float(data["buy_price"])
    volume = int(data["volume"])
    if price <= 0 or volume <= 0:
        return jsonify({"status": "error", "message": "价格和数量必须大于0"}), 400

    portfolio = load_portfolio()
    cost = price * volume / 10
    fee = _calc_fee(cost, config)
    total_cost = cost + fee

    if total_cost > portfolio.cash:
        return jsonify({"status": "error", "message": f"资金不足（需要 {total_cost:.0f}，可用 {portfolio.cash:.0f}）"}), 400

    holding = Holding(
        cb_code=data["cb_code"],
        cb_name=data.get("cb_name", data["cb_code"]),
        buy_date=data.get("buy_date", datetime.date.today().isoformat()),
        buy_price=price,
        volume=volume,
    )
    portfolio.add(holding, total_cost)
    save_portfolio(portfolio)
    append_trade_history("buy", data["cb_code"], data.get("cb_name", data["cb_code"]), price, volume, fee)
    return jsonify({"status": "ok", "cash": portfolio.cash, "fee": round(fee, 2)})


@app.route("/api/portfolio/sell", methods=["POST"])
def api_sell():
    """卖出操作"""
    data = request.json
    if not data or "cb_code" not in data or "sell_price" not in data:
        return jsonify({"status": "error", "message": "缺少必要参数"}), 400

    config = load_config()
    portfolio = load_portfolio()
    h = portfolio.get_holding(data["cb_code"])
    if not h:
        return jsonify({"status": "error", "message": "未持有该转债"}), 404

    sell_price = float(data["sell_price"])
    proceeds = sell_price * h.volume / 10
    fee = _calc_fee(proceeds, config)
    net_proceeds = proceeds - fee

    portfolio.remove(data["cb_code"], net_proceeds)
    save_portfolio(portfolio)
    append_trade_history("sell", data["cb_code"], h.cb_name, sell_price, h.volume, fee)
    return jsonify({"status": "ok", "cash": portfolio.cash, "fee": round(fee, 2)})


@app.route("/api/portfolio/history")
def api_portfolio_history():
    """获取交易历史记录"""
    limit = request.args.get("limit", 50, type=int)
    records = load_trade_history(limit=min(limit, 200))
    return jsonify(_safe_json({"status": "ok", "records": records}))


@app.route("/api/config")
def api_config():
    """获取当前配置"""
    config = load_config()
    return jsonify(_safe_json({
        "status": "ok",
        "config": config.model_dump(),
    }))


@app.route("/api/stats")
def api_stats():
    """系统总览统计"""
    from quantified.db import get_meta
    from quantified.models.bond import BondBasic

    session = _get_session()
    try:
        total_bonds = session.query(BondBasic).count()
        last_sync = get_meta(session, "last_sync_bond_daily") or "从未同步"
    finally:
        session.close()

    portfolio = load_portfolio()
    return jsonify(_safe_json({
        "status": "ok",
        "version": _get_version(),
        "total_bonds": total_bonds,
        "last_sync": last_sync,
        "portfolio_count": len(portfolio.holdings),
        "portfolio_cash": portfolio.cash,
    }))


@app.route("/api/backtest")
def api_backtest():
    """运行回测并返回结果"""
    import threading

    from quantified.backtest.engine import BacktestEngine
    from quantified.backtest.stats import compute_stats

    start, err = _parse_date_or_400("start", "2024-01-01")
    if err:
        return err
    end, err = _parse_date_or_400("end", datetime.date.today().isoformat())
    if err:
        return err
    config = load_config()

    session = _get_session()
    bt_result = [None]
    bt_error = [None]

    def _run():
        try:
            bt = BacktestEngine(config, session)
            bt_result[0] = bt.run(start, end)
        except Exception as exc:
            bt_error[0] = exc

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout=120)
    session.close()

    if t.is_alive():
        return jsonify({"status": "error", "message": "回测超时，请缩短日期范围"}), 504
    if bt_error[0]:
        return jsonify({"status": "error", "message": str(bt_error[0])}), 500

    result = bt_result[0]

    stats = compute_stats(result)

    snapshots = [
        {"date": s.date, "net_value": round(s.net_value, 2),
         "cash": round(s.cash, 2), "position_count": s.position_count}
        for s in result.daily_snapshots
    ]

    trades = [
        {"date": t.date, "cb_code": t.cb_code, "cb_name": t.cb_name,
         "direction": t.direction, "price": round(t.price, 3),
         "volume": t.volume, "amount": round(t.amount, 2),
         "fee": round(t.fee, 2), "reason": t.reason}
        for t in result.trades
    ]

    return jsonify(_safe_json({
        "status": "ok",
        "start_date": result.start_date,
        "end_date": result.end_date,
        "initial_capital": result.initial_capital,
        "final_value": round(result.final_value, 2),
        "trading_days": result.trading_days,
        "stats": {
            "total_return": round(stats.total_return, 4),
            "annualized_return": round(stats.annualized_return, 4),
            "max_drawdown": round(stats.max_drawdown, 4),
            "max_drawdown_start": stats.max_drawdown_start,
            "max_drawdown_end": stats.max_drawdown_end,
            "sharpe_ratio": round(stats.sharpe_ratio, 2),
            "annualized_volatility": round(stats.annualized_volatility, 4),
            "total_trades": stats.total_trades,
            "buy_trades": stats.buy_trades,
            "sell_trades": stats.sell_trades,
            "win_rate": round(stats.win_rate, 4),
            "profit_loss_ratio": round(stats.profit_loss_ratio, 2) if stats.profit_loss_ratio != float("inf") else 999,
            "total_fees": round(stats.total_fees, 2),
            "avg_positions": round(stats.avg_positions, 1),
        },
        "snapshots": snapshots,
        "trades": trades,
    }))


@app.route("/health")
def health():
    """健康检查端点"""
    from quantified.db import get_meta

    try:
        session = _get_session()
        last_sync = get_meta(session, "last_sync_bond_daily")
        session.close()
        db_ok = True
    except Exception:
        last_sync = None
        db_ok = False

    stale = False
    if last_sync:
        last_dt = datetime.date.fromisoformat(last_sync)
        stale = (datetime.date.today() - last_dt).days > 3

    return jsonify({
        "status": "healthy" if db_ok and not stale else "degraded",
        "version": _get_version(),
        "database": "connected" if db_ok else "error",
        "last_sync": last_sync,
        "data_stale": stale,
    })


def _calc_fee(amount: float, config) -> float:
    """计算交易佣金"""
    fee = amount * config.fees.commission_rate
    return max(fee, config.fees.min_commission) if amount > 0 else 0


def _get_version() -> str:
    from quantified import __version__
    return __version__


def run_server(host: str = "127.0.0.1", port: int = 5000, debug: bool = False):
    app.run(host=host, port=port, debug=debug)


if __name__ == "__main__":
    run_server(debug=False)
