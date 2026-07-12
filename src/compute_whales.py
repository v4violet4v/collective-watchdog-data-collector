from __future__ import annotations

import math
from collections import defaultdict
from statistics import median
from typing import Any

from normalize import masked_wallet, to_float


def _percentile_rank(sorted_values: list[float], value: float) -> float:
    if not sorted_values:
        return 0.0
    count = sum(1 for item in sorted_values if item <= value)
    return 100.0 * count / len(sorted_values)


def _robust_z(log_values: list[float], value: float) -> float:
    if len(log_values) < 3:
        return 0.0
    med = median(log_values)
    deviations = [abs(item - med) for item in log_values]
    mad = median(deviations)
    if mad == 0:
        return 0.0
    return 0.6745 * (math.log(max(value, 0.0) + 1) - med) / mad


def detect_whales(
    trades_by_market: dict[str, list[dict[str, Any]]],
    *,
    min_usd: float,
    min_history: int,
) -> dict[str, list[dict[str, Any]]]:
    alerts_by_market: dict[str, list[dict[str, Any]]] = {}

    for public_slug, trades in trades_by_market.items():
        by_asset: dict[str, list[float]] = defaultdict(list)
        for trade in trades:
            asset = str(trade.get("asset") or trade.get("outcome") or "unknown")
            notional = to_float(trade.get("price")) * to_float(trade.get("size"))
            by_asset[asset].append(notional)

        sorted_by_asset = {asset: sorted(values) for asset, values in by_asset.items()}
        log_by_asset = {asset: [math.log(max(value, 0.0) + 1) for value in values] for asset, values in by_asset.items()}

        alerts: list[dict[str, Any]] = []
        for trade in trades:
            asset = str(trade.get("asset") or trade.get("outcome") or "unknown")
            notional = to_float(trade.get("price")) * to_float(trade.get("size"))
            history_count = len(sorted_by_asset.get(asset, []))
            if notional < min_usd or history_count < min_history:
                continue

            percentile = _percentile_rank(sorted_by_asset[asset], notional)
            z_score = _robust_z(log_by_asset[asset], notional)
            if percentile < 95 and z_score < 3:
                continue

            if percentile >= 99.5 or z_score >= 7:
                severity = "Extreme"
            elif percentile >= 99 or z_score >= 5:
                severity = "Large"
            else:
                severity = "Watch"

            trader_name = trade.get("name") or trade.get("pseudonym")
            alerts.append(
                {
                    "time": trade.get("timestamp"),
                    "outcome": trade.get("outcome"),
                    "side": trade.get("side"),
                    "price": to_float(trade.get("price")),
                    "size": to_float(trade.get("size")),
                    "notional_usd": round(notional, 2),
                    "percentile_rank": round(percentile, 1),
                    "robust_z": round(z_score, 2),
                    "severity": severity,
                    "trader": masked_wallet(trade.get("proxyWallet"), trader_name),
                    "transaction_hash": trade.get("transactionHash"),
                }
            )

        alerts_by_market[public_slug] = sorted(
            alerts,
            key=lambda row: (to_float(row.get("time")), row["notional_usd"]),
            reverse=True,
        )

    return alerts_by_market
