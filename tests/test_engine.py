"""核心规则引擎的单元测试。"""

from __future__ import annotations

import unittest

from allocation.config import Rules
from allocation.engine import allocate


def make_rules(**overrides) -> Rules:
    payload = {
        "name": "test",
        "safety_stock_ratio": 0.0,
        "min_fill_ratio": 0.5,
        "max_share_per_channel": 1.0,
        "priority_weights": {"A": 3, "B": 1},
    }
    payload.update(overrides)
    rules = Rules(**payload)
    rules.validate()
    return rules


class AllocationEngineTest(unittest.TestCase):
    def test_conservation_never_oversell(self) -> None:
        inventory = {"S1": 100.0}
        demand = [
            {"sku": "S1", "channel": "A", "demand": 80.0},
            {"sku": "S1", "channel": "B", "demand": 80.0},
        ]
        result = allocate(inventory, demand, make_rules())
        self.assertLessEqual(sum(line.allocated for line in result.lines), 100.0 + 1e-6)
        self.assertAlmostEqual(result.metrics["remaining_stock"], 0.0, places=6)

    def test_min_fill_ratio_protects_small_channel(self) -> None:
        inventory = {"S1": 100.0}
        demand = [
            {"sku": "S1", "channel": "A", "demand": 150.0},
            {"sku": "S1", "channel": "B", "demand": 50.0},
        ]
        rules = make_rules(min_fill_ratio=0.5, max_share_per_channel=1.0)
        result = allocate(inventory, demand, rules)
        fills = {line.channel: line.fill_rate for line in result.lines}
        self.assertGreaterEqual(fills["B"], 0.5 - 1e-6)

    def test_priority_channel_gets_more_when_scarce(self) -> None:
        inventory = {"S1": 60.0}
        demand = [
            {"sku": "S1", "channel": "A", "demand": 100.0},
            {"sku": "S1", "channel": "B", "demand": 100.0},
        ]
        rules = make_rules(min_fill_ratio=0.0, max_share_per_channel=1.0)
        result = allocate(inventory, demand, rules)
        fills = {line.channel: line.fill_rate for line in result.lines}
        self.assertGreater(fills["A"], fills["B"])

    def test_cap_is_respected(self) -> None:
        inventory = {"S1": 100.0}
        demand = [
            {"sku": "S1", "channel": "A", "demand": 200.0},
            {"sku": "S1", "channel": "B", "demand": 1.0},
        ]
        rules = make_rules(min_fill_ratio=0.0, max_share_per_channel=0.6)
        result = allocate(inventory, demand, rules)
        for line in result.lines:
            self.assertLessEqual(line.allocated, line.demand + 1e-6)
            self.assertLessEqual(line.allocated, 60.0 + 1e-6)

    def test_zero_inventory_returns_zero_allocation(self) -> None:
        inventory = {"S1": 0.0}
        demand = [{"sku": "S1", "channel": "A", "demand": 10.0}]
        result = allocate(inventory, demand, make_rules())
        self.assertEqual(result.lines[0].allocated, 0.0)
        self.assertEqual(result.metrics["overall_fill_rate"], 0.0)

    def test_invalid_rule_raises(self) -> None:
        with self.assertRaises(ValueError):
            make_rules(safety_stock_ratio=1.5).validate()


if __name__ == "__main__":
    unittest.main()
