from __future__ import annotations

import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_jsonish(value: Any) -> list[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, list) else [parsed]
        except json.JSONDecodeError:
            return [part.strip() for part in value.split(",") if part.strip()]
    return [value]


def to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None or value == "":
            return default
        number = float(value)
        if math.isnan(number) or math.isinf(number):
            return default
        return number
    except (TypeError, ValueError):
        return default


def to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in {"1", "true", "yes"}
    return bool(value)


def money_millions(value: Any) -> float:
    raw = to_float(value)
    millions = raw / 1_000_000
    if 0 < raw < 100_000:
        return round(millions, 3)
    return round(millions, 1)


def slugify(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:120] or fallback


def stable_hash(value: Any, length: int = 16) -> str:
    raw = str(value or "").encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:length]


def masked_wallet(value: Any, profile_name: Any = None) -> str:
    name = str(profile_name or "").strip()
    if name:
        return name[:40]

    wallet = str(value or "").strip()
    if len(wallet) >= 12:
        return f"Wallet {wallet[:6]}...{wallet[-4:]}"
    if wallet:
        return f"Wallet {stable_hash(wallet, 8)}"
    return "Unknown trader"


def normalize_events(events: list[dict[str, Any]], generated_at: str) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    public_events: dict[str, dict[str, Any]] = {}
    flat_markets: list[dict[str, Any]] = []

    for event in events:
        event_title = event.get("title") or "Untitled event"
        event_slug = event.get("slug") or slugify(event_title, stable_hash(event.get("id")))
        public_event = public_events.setdefault(
            event_slug,
            {
                "event_title": event_title,
                "event_slug": event_slug,
                "active": to_bool(event.get("active")),
                "closed": to_bool(event.get("closed")),
                "volume_m": money_millions(event.get("volume") or event.get("volumeNum")),
                "volume_24h_m": money_millions(event.get("volume24hr")),
                "liquidity_m": money_millions(event.get("liquidity") or event.get("liquidityNum")),
                "tags": [tag.get("label") or tag.get("name") for tag in event.get("tags", []) if isinstance(tag, dict)],
                "markets": [],
            },
        )

        for market in event.get("markets") or []:
            condition_id = market.get("conditionId")
            if not condition_id:
                continue

            question = market.get("question") or market.get("title") or "Untitled market"
            market_slug = market.get("slug") or slugify(question, stable_hash(condition_id))
            outcomes = parse_jsonish(market.get("outcomes") or market.get("shortOutcomes"))
            token_ids = [str(token) for token in parse_jsonish(market.get("clobTokenIds"))]
            outcome_prices = parse_jsonish(market.get("outcomePrices"))
            public_slug = f"{event_slug}-{market_slug}"[:160]

            market_row = {
                "generated_at": generated_at,
                "event_title": event_title,
                "event_slug": event_slug,
                "public_slug": public_slug,
                "question": question,
                "active": to_bool(market.get("active")),
                "closed": to_bool(market.get("closed")),
                "end_date": market.get("endDateIso") or market.get("endDate"),
                "volume_m": money_millions(market.get("volumeNum") or market.get("volume")),
                "volume_24h_m": money_millions(market.get("volume24hr") or market.get("volume24hrClob")),
                "liquidity_m": money_millions(market.get("liquidityNum") or market.get("liquidity")),
                "last_trade_price": to_float(market.get("lastTradePrice"), 0.0),
                "source_condition_id": condition_id,
                "outcomes": [
                    {
                        "name": outcomes[i] if i < len(outcomes) else f"Outcome {i + 1}",
                        "probability": to_float(outcome_prices[i], 0.0) if i < len(outcome_prices) else 0.0,
                        "source_token_id": token_ids[i] if i < len(token_ids) else "",
                    }
                    for i in range(max(len(outcomes), len(token_ids)))
                ],
                "price_history": [],
                "volume_history": [],
                "whale": {"severity": "None", "count_24h": 0, "largest_notional": 0.0},
            }
            public_event["markets"].append(market_row)
            flat_markets.append(market_row)

    return list(public_events.values()), flat_markets


def summarize_book(book: dict[str, Any]) -> dict[str, float]:
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    bid_prices = [to_float(row.get("price")) for row in bids if isinstance(row, dict)]
    ask_prices = [to_float(row.get("price")) for row in asks if isinstance(row, dict)]
    best_bid = max(bid_prices, default=0.0)
    best_ask = min([price for price in ask_prices if price > 0], default=0.0)
    midpoint = round((best_bid + best_ask) / 2, 4) if best_bid and best_ask else 0.0
    spread = round(best_ask - best_bid, 4) if best_bid and best_ask else 0.0
    return {"best_bid": best_bid, "best_ask": best_ask, "midpoint": midpoint, "spread": spread}
