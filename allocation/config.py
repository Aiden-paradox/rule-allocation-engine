"""规则定义、加载与校验。

业务同学只需要修改 config/*.json，不需要改代码。
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Rules:
    """一套分货规则。"""

    name: str
    safety_stock_ratio: float
    min_fill_ratio: float
    max_share_per_channel: float
    priority_weights: dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_json(cls, path: str | Path) -> "Rules":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        rules = cls(
            name=str(raw.get("name", "unnamed")),
            safety_stock_ratio=float(raw.get("safety_stock_ratio", 0.0)),
            min_fill_ratio=float(raw.get("min_fill_ratio", 0.0)),
            max_share_per_channel=float(raw.get("max_share_per_channel", 1.0)),
            priority_weights={str(k): float(v) for k, v in raw.get("priority_weights", {}).items()},
        )
        rules.validate()
        return rules

    def priority_weight(self, channel: str) -> float:
        return float(self.priority_weights.get(channel, 1.0))

    def validate(self) -> None:
        if not 0.0 <= self.safety_stock_ratio < 1.0:
            raise ValueError(f"安全库存比例必须位于 [0, 1)：{self.safety_stock_ratio}")
        if not 0.0 <= self.min_fill_ratio <= 1.0:
            raise ValueError(f"最低保障比例必须位于 [0, 1]：{self.min_fill_ratio}")
        if not 0.0 < self.max_share_per_channel <= 1.0:
            raise ValueError(f"单渠道占比上限必须位于 (0, 1]：{self.max_share_per_channel}")
        if self.min_fill_ratio > self.max_share_per_channel:
            raise ValueError("最低保障比例不应大于单渠道占比上限")
        for channel, weight in self.priority_weights.items():
            if weight < 0:
                raise ValueError(f"渠道权重不能为负：{channel}={weight}")
