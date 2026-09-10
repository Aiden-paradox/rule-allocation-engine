"""经营指标计算：让分货结果可量化、可对比。"""

from __future__ import annotations

from typing import Iterable

EPS = 1e-9


def _gini(values: list[float]) -> float:
    """基尼系数：0 表示完全平均，越大表示越不均衡。"""
    numbers = sorted(values)
    count = len(numbers)
    if count == 0:
        return 0.0
    total = sum(numbers)
    if total <= EPS:
        return 0.0
    cumulative = 0.0
    for index, value in enumerate(numbers, start=1):
        cumulative += (2 * index - count - 1) * value
    return cumulative / (count * total)


def summarize(lines: Iterable[object], total_inventory: float, reserved_stock: float) -> dict[str, object]:
    line_list = list(lines)
    total_demand = sum(line.demand for line in line_list)
    total_allocated = sum(line.allocated for line in line_list)
    unmet = sum(line.unmet for line in line_list)
    fill_rates = [line.fill_rate for line in line_list if line.demand > EPS]

    by_channel: dict[str, dict[str, float]] = {}
    for line in line_list:
        bucket = by_channel.setdefault(line.channel, {"demand": 0.0, "allocated": 0.0})
        bucket["demand"] += line.demand
        bucket["allocated"] += line.allocated
    for bucket in by_channel.values():
        demand = bucket["demand"]
        bucket["fill_rate"] = bucket["allocated"] / demand if demand > EPS else 1.0

    return {
        "total_demand": round(total_demand, 2),
        "total_allocated": round(total_allocated, 2),
        "total_inventory": round(total_inventory, 2),
        "reserved_stock": round(reserved_stock, 2),
        "remaining_stock": round(total_inventory - total_allocated, 2),
        "unmet_demand": round(unmet, 2),
        "overall_fill_rate": round(total_allocated / total_demand, 4) if total_demand > EPS else 1.0,
        "min_channel_fill_rate": round(min(fill_rates), 4) if fill_rates else 1.0,
        "avg_channel_fill_rate": round(sum(fill_rates) / len(fill_rates), 4) if fill_rates else 1.0,
        "channel_fill_gini": round(_gini(fill_rates), 4),
        "by_channel": {
            channel: {
                "demand": round(bucket["demand"], 2),
                "allocated": round(bucket["allocated"], 2),
                "fill_rate": round(bucket["fill_rate"], 4),
            }
            for channel, bucket in sorted(by_channel.items())
        },
    }
