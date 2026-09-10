"""需求预测：加权移动平均 + MAPE 回测，展示“数据 → 预测 → 决策”链路。"""

from __future__ import annotations

from collections import defaultdict

DEFAULT_WEIGHTS = (0.5, 0.3, 0.2)


def _weighted_average(values: list[float], weights: tuple[float, ...]) -> float:
    window = values[-len(weights):]
    usable = weights[-len(window):]
    total = sum(usable)
    if total <= 0:
        return 0.0
    return sum(value * weight for value, weight in zip(window, usable)) / total


def forecast_by_series(history: list[dict[str, object]], weights: tuple[float, ...] = DEFAULT_WEIGHTS) -> tuple[list[dict[str, object]], float]:
    """按 (sku, channel) 分组预测下一期需求，并返回 MAPE 回测结果。"""
    groups: dict[tuple[str, str], list[tuple[str, float]]] = defaultdict(list)
    for row in history:
        groups[(str(row["sku"]), str(row["channel"]))].append((str(row["week"]), float(row["sales"])))

    forecasts: list[dict[str, object]] = []
    errors: list[float] = []
    for (sku, channel), series in sorted(groups.items()):
        series.sort(key=lambda item: item[0])
        values = [value for _, value in series]
        for index in range(0, len(values) - 1):
            if index + 1 < len(weights):
                # 历史数据不足以构成一个完整窗口，跳过回测。
                continue
            predicted = _weighted_average(values[: index + 1], weights)
            actual = values[index + 1]
            if actual > 0:
                errors.append(abs(predicted - actual) / actual)
        forecast_value = _weighted_average(values, weights)
        forecasts.append({"sku": sku, "channel": channel, "forecast": round(forecast_value, 2)})

    mape = sum(errors) / len(errors) if errors else 0.0
    return forecasts, mape
