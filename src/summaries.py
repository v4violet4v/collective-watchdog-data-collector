"""Comparable daily snapshots; never mix CLOB midpoints with Gamma prices."""
import math
import os
from datetime import datetime


def enrich_snapshots(events, previous, generated_at):
    now = datetime.fromisoformat(generated_at.replace("Z", "+00:00")).timestamp()
    tolerance = max(0, int(os.getenv("CHANGE_MAX_GAP_HOURS", "6"))) * 3600
    retained = {}
    for event in events:
        for market in event["markets"]:
            for outcome in market["outcomes"]:
                key = outcome.get("source_token_id")
                if not key:
                    continue
                source = outcome.get("probability_source", "gamma_outcome_price")
                rows = [r for r in previous.get(key, []) if now - 4 * 86400 <= r.get("t", 0) < now]
                candidates = [r for r in rows if 0 <= now - 86400 - r["t"] <= tolerance and r.get("source") == source]
                price = outcome.get("probability")
                outcome["change_24h_pp"] = None
                outcome.pop("comparison_at", None)
                outcome.pop("comparison_probability", None)
                if isinstance(price, (int, float)) and math.isfinite(price) and 0 <= price <= 1:
                    if candidates:
                        base = max(candidates, key=lambda r: r["t"])
                        outcome.update(change_24h_pp=round(100 * (price - base["p"]), 4), comparison_at=base["t"], comparison_probability=base["p"])
                    rows.append({"t": now, "p": price, "source": source})
                outcome["as_of"] = generated_at
                retained[key] = rows[-100:]
    return retained


def lightweight_events(events):
    return [{**event, "markets": [
        {key: value for key, value in market.items() if key not in {
            "price_history", "volume_history", "source_condition_id", "description", "resolution_source"
        }} for market in event["markets"]
    ]} for event in events]
