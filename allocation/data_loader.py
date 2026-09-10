"""数据读取与校验。"""

from __future__ import annotations

import csv
from pathlib import Path


def load_inventory(path: str | Path) -> dict[str, float]:
    inventory: dict[str, float] = {}
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sku = (row.get("sku") or "").strip()
            if not sku:
                raise ValueError("inventory.csv 存在空 sku")
            qty = float(row["available_qty"])
            if qty < 0:
                raise ValueError(f"库存不能为负：{sku}={qty}")
            inventory[sku] = qty
    return inventory


def load_channel_demand(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            sku = (row.get("sku") or "").strip()
            channel = (row.get("channel") or "").strip()
            demand = float(row["demand"])
            if not sku or not channel:
                raise ValueError("channel_demand.csv 存在空 sku 或 channel")
            if demand < 0:
                raise ValueError(f"需求不能为负：{sku}/{channel}={demand}")
            rows.append({"sku": sku, "channel": channel, "demand": demand})
    if not rows:
        raise ValueError("channel_demand.csv 没有有效数据")
    return rows


def load_sales_history(path: str | Path) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            rows.append(
                {
                    "week": (row.get("week") or "").strip(),
                    "sku": (row.get("sku") or "").strip(),
                    "channel": (row.get("channel") or "").strip(),
                    "sales": float(row["sales"]),
                }
            )
    return rows
