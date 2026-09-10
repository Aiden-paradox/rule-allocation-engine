"""命令行入口：python -m allocation.cli --scenario both --out outputs"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .config import Rules
from .data_loader import load_channel_demand, load_inventory, load_sales_history
from .engine import allocate
from .report import build_report, write_allocation_csv, write_forecast_csv


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="规则驱动的分货决策引擎")
    parser.add_argument("--data", default="data", help="数据目录（默认 data）")
    parser.add_argument("--config", default="config", help="规则目录（默认 config）")
    parser.add_argument("--scenario", choices=["baseline", "growth", "both"], default="both", help="运行哪套规则")
    parser.add_argument("--forecast", action="store_true", help="同时运行需求预测并输出 MAPE")
    parser.add_argument("--out", default="outputs", help="输出目录（默认 outputs）")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = parse_args(argv)
    data_dir = Path(args.data)
    config_dir = Path(args.config)
    out_dir = Path(args.out)

    inventory = load_inventory(data_dir / "inventory.csv")
    demand = load_channel_demand(data_dir / "channel_demand.csv")

    scenario_files = {
        "baseline": config_dir / "rules_baseline.json",
        "growth": config_dir / "rules_growth.json",
    }
    names = list(scenario_files) if args.scenario == "both" else [args.scenario]

    results = []
    for name in names:
        rules = Rules.from_json(scenario_files[name])
        result = allocate(inventory, demand, rules)
        results.append(result)
        write_allocation_csv(result, out_dir / f"allocation_{name}.csv")
        print(f"[OK] 规则 {name}: 整体满足率 {result.metrics['overall_fill_rate']:.1%}, "
              f"最低渠道满足率 {result.metrics['min_channel_fill_rate']:.1%}, "
              f"缺口 {result.metrics['unmet_demand']}")

    forecast_mape = None
    if args.forecast:
        history = load_sales_history(data_dir / "sales_history.csv")
        forecast_mape = write_forecast_csv(history, out_dir / "forecast.csv")
        print(f"[OK] 需求预测已输出，回测 MAPE = {forecast_mape:.2%}")

    build_report(results, forecast_mape, out_dir / "report.md")
    print(f"[OK] 报告已生成: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
