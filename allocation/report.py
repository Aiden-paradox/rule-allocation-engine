"""结果导出与 Markdown 报告生成。"""

from __future__ import annotations

import csv
from pathlib import Path

from .engine import AllocationResult
from .forecast import forecast_by_series


def write_allocation_csv(result: AllocationResult, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sku", "channel", "demand", "allocated", "unmet", "fill_rate", "priority"])
        for line in result.lines:
            writer.writerow(
                [
                    line.sku,
                    line.channel,
                    round(line.demand, 2),
                    round(line.allocated, 2),
                    round(line.unmet, 2),
                    round(line.fill_rate, 4),
                    line.priority,
                ]
            )


def write_forecast_csv(history: list[dict[str, object]], path: str | Path) -> float:
    forecasts, mape = forecast_by_series(history)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sku", "channel", "forecast"])
        for row in forecasts:
            writer.writerow([row["sku"], row["channel"], row["forecast"]])
    return mape


def build_report(results: list[AllocationResult], forecast_mape: float | None, path: str | Path) -> None:
    lines: list[str] = ["# 分货决策对比报告", ""]
    lines.append("本报告由 `python -m allocation.cli --scenario both --out outputs` 自动生成。")
    lines.append("")
    if forecast_mape is not None:
        lines.append(f"需求预测回测 MAPE：**{forecast_mape:.2%}**（加权移动平均，仅用于演示预测链路）。")
        lines.append("")

    lines.append("## 一、整体指标对比")
    lines.append("")
    lines.append("| 指标 | " + " | ".join(result.rules_name for result in results) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in results) + " |")
    metric_names = [
        ("整体满足率", "overall_fill_rate", "percent"),
        ("最低渠道满足率", "min_channel_fill_rate", "percent"),
        ("平均渠道满足率", "avg_channel_fill_rate", "percent"),
        ("渠道满足率基尼系数", "channel_fill_gini", "number"),
        ("未满足需求", "unmet_demand", "number"),
        ("剩余库存（含安全库存）", "remaining_stock", "number"),
    ]
    for label, key, kind in metric_names:
        values = []
        for result in results:
            value = result.metrics[key]
            values.append(f"{value:.1%}" if kind == "percent" else f"{value}")
        lines.append(f"| {label} | " + " | ".join(values) + " |")
    lines.append("")

    lines.append("## 二、分渠道满足率")
    lines.append("")
    channels = sorted({line.channel for result in results for line in result.lines})
    lines.append("| 渠道 | " + " | ".join(result.rules_name for result in results) + " |")
    lines.append("| --- | " + " | ".join("---" for _ in results) + " |")
    for channel in channels:
        values = []
        for result in results:
            rate = result.metrics["by_channel"].get(channel, {}).get("fill_rate", 0.0)
            values.append(f"{rate:.1%}")
        lines.append(f"| {channel} | " + " | ".join(values) + " |")
    lines.append("")

    lines.append("## 三、逐 SKU 分货明细")
    for result in results:
        lines.append("")
        lines.append(f"### 规则：{result.rules_name}")
        lines.append("")
        lines.append("| SKU | 渠道 | 需求 | 已分配 | 缺口 | 满足率 |")
        lines.append("| --- | --- | --- | --- | --- | --- |")
        for line in result.lines:
            lines.append(
                f"| {line.sku} | {line.channel} | {line.demand:.0f} | {line.allocated:.0f} | "
                f"{line.unmet:.0f} | {line.fill_rate:.1%} |"
            )
    lines.append("")
    lines.append("## 四、结论与下一步")
    lines.append("")
    lines.append("- 两套规则的差异说明：规则一变，满足率与公平性指标都会变化，因此规则必须显性化并可回溯。")
    lines.append("- 下一步可接入真实 ERP/BI 数据、引入缺货成本与库存周转目标、用运筹优化替代启发式分配。")

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
