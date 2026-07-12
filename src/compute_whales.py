from __future__ import annotations

import math
from collections import defaultdict
from statistics import median
from typing import Any

from normalize import masked_wallet, to_float

WATCH_Z = 3.0
LARGE_Z = 4.0
EXTREME_Z = 5.0
WATCH_BREAKOUT_RATIO = 1.25
LARGE_BREAKOUT_RATIO = 1.5
EXTREME_BREAKOUT_RATIO = 2.0


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


def _asset_key(trade: dict[str, Any]) -> str:
    return str(trade.get("asset") or trade.get("outcome") or "unknown")


def _notional(trade: dict[str, Any]) -> float:
    return to_float(trade.get("price")) * to_float(trade.get("size"))


def detect_whales(
    trades_by_market: dict[str, list[dict[str, Any]]],
    *,
    min_usd: float,
    min_history: int,
) -> dict[str, list[dict[str, Any]]]:
    alerts_by_market: dict[str, list[dict[str, Any]]] = {}

    for public_slug, trades in trades_by_market.items():
        by_asset: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for trade in trades:
            by_asset[_asset_key(trade)].append(trade)

        alerts: list[dict[str, Any]] = []
        for asset_trades in by_asset.values():
            prior_values: list[float] = []
            chronological_trades = sorted(asset_trades, key=lambda row: to_float(row.get("timestamp")))

            for trade in chronological_trades:
                notional = _notional(trade)
                history_count = len(prior_values)
                if notional < min_usd or history_count < min_history:
                    prior_values.append(notional)
                    continue

                sorted_prior = sorted(prior_values)
                prior_max = max(prior_values, default=0.0)
                breakout_ratio = notional / prior_max if prior_max > 0 else 0.0
                percentile = _percentile_rank(sorted_prior, notional)
                z_score = _robust_z([math.log(max(value, 0.0) + 1) for value in prior_values], notional)

                is_breakout = breakout_ratio >= WATCH_BREAKOUT_RATIO or z_score >= WATCH_Z
                is_new_high = notional > prior_max
                if not is_new_high or not is_breakout:
                    prior_values.append(notional)
                    continue

                if breakout_ratio >= EXTREME_BREAKOUT_RATIO or z_score >= EXTREME_Z:
                    severity = "Extreme"
                elif breakout_ratio >= LARGE_BREAKOUT_RATIO or z_score >= LARGE_Z:
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
                        "prior_max_usd": round(prior_max, 2),
                        "breakout_ratio": round(breakout_ratio, 2),
                        "severity": severity,
                        "trader": masked_wallet(trade.get("proxyWallet"), trader_name),
                        "transaction_hash": trade.get("transactionHash"),
                    }
                )
                prior_values.append(notional)

        alerts_by_market[public_slug] = sorted(
            alerts,
            key=lambda row: (to_float(row.get("time")), row["notional_usd"]),
            reverse=True,
        )

    return alerts_by_market
