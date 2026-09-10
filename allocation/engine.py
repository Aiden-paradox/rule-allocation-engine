"""分货规则引擎：把业务规则翻译成可执行、可验证的分配逻辑。"""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import Rules
from .metrics import summarize

EPS = 1e-9


@dataclass
class AllocationLine:
    sku: str
    channel: str
    demand: float
    priority: float
    allocated: float = 0.0

    @property
    def unmet(self) -> float:
        return max(0.0, self.demand - self.allocated)

    @property
    def fill_rate(self) -> float:
        return self.allocated / self.demand if self.demand > EPS else 1.0


@dataclass
class AllocationResult:
    rules_name: str
    lines: list[AllocationLine] = field(default_factory=list)
    total_inventory: float = 0.0
    reserved_stock: float = 0.0
    metrics: dict[str, object] = field(default_factory=dict)


def allocate(inventory: dict[str, float], demand_rows: list[dict[str, object]], rules: Rules) -> AllocationResult:
    """按规则分配库存，返回逐渠道结果与整体指标。"""
    rules.validate()
    result = AllocationResult(rules_name=rules.name)
    skus = sorted({str(row["sku"]) for row in demand_rows})

    for sku in skus:
        available = float(inventory.get(sku, 0.0))
        result.total_inventory += available
        sku_rows = [row for row in demand_rows if str(row["sku"]) == sku]
        lines = [
            AllocationLine(
                sku=sku,
                channel=str(row["channel"]),
                demand=float(row["demand"]),
                priority=rules.priority_weight(str(row["channel"])),
            )
            for row in sku_rows
        ]
        reserved = _allocate_sku(available, lines, rules)
        result.reserved_stock += reserved
        result.lines.extend(lines)

    result.metrics = summarize(result.lines, result.total_inventory, result.reserved_stock)
    return result


def _allocate_sku(available: float, lines: list[AllocationLine], rules: Rules) -> float:
    """在单个 SKU 内执行两轮分配，返回该 SKU 预留的安全库存。"""
    if available <= EPS or not lines:
        return max(0.0, available)

    reserved = available * rules.safety_stock_ratio
    pool = available - reserved
    cap = available * rules.max_share_per_channel
    order = sorted(lines, key=lambda line: (-line.priority, -line.demand, line.channel))

    # 第一轮：按最低保障比例发放，避免小渠道被饿死。
    for line in order:
        floor = line.demand * rules.min_fill_ratio
        room = min(pool, cap - line.allocated)
        give = min(floor - line.allocated, room)
        if give > EPS:
            line.allocated += give
            pool -= give

    # 第二轮：剩余库存按“优先级权重 × 未满足需求”加权分配，并受上限约束。
    for _ in range(200):
        candidates = [
            line
            for line in order
            if line.unmet > EPS and (cap - line.allocated) > EPS
        ]
        if pool <= EPS or not candidates:
            break

        weights = {line.channel: max(0.0, line.priority) * line.unmet for line in candidates}
        total_weight = sum(weights.values())
        if total_weight <= EPS:
            break

        pool_before = pool
        progressed = False
        for line in candidates:
            share = pool_before * weights[line.channel] / total_weight
            give = min(share, line.unmet, cap - line.allocated, pool)
            if give > EPS:
                line.allocated += give
                pool -= give
                progressed = True
        if not progressed:
            break

    return reserved
