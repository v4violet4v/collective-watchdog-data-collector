from __future__ import annotations

import json
from pathlib import Path
from datetime import datetime, timedelta, timezone
from typing import Any

from compute_whales import detect_whales
from config import load_config
from export_r2 import upload_directory_to_r2
from normalize import normalize_events, summarize_book, to_float
from polymarket_api import fetch_book, fetch_events, fetch_price_history, fetch_tags, fetch_trades


def write_json(path: Path, data: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {path}")


def fetch_chart_history(token_id: str, config, start_ts: int | None, end_ts: int | None) -> list[dict]:
    attempts = []
    if start_ts is not None or end_ts is not None:
        attempts.append(("configured-range", start_ts, end_ts, config.price_history_interval))
    attempts.extend(
        [
            ("max-fallback", None, None, "max"),
            ("1m-fallback", None, None, "1m"),
            ("1w-fallback", None, None, "1w"),
        ],
    )

    last_history: list[dict] = []
    last_error: Exception | None = None
    for label, attempt_start, attempt_end, interval in attempts:
        try:
            history = fetch_price_history(
                token_id,
                interval=interval,
                fidelity=config.price_history_fidelity,
                start_ts=attempt_start,
                end_ts=attempt_end,
            )
            if len(history) >= 2:
                return history
            last_history = history
            print(f"Price history attempt {label} returned {len(history)} points for token {token_id}")
        except Exception as exc:
            last_error = exc
            print(f"Price history attempt {label} failed for token {token_id}: {exc}")

    if last_history:
        return last_history
    if last_error:
        raise last_error
    return []


def normalize_price_history(history: list[dict], max_points: int) -> list[dict]:
    points = []
    for row in history[-max_points:]:
        timestamp = row.get("t") or row.get("timestamp")
        price = row.get("p")
        if timestamp is None or price is None:
            continue
        points.append({"t": timestamp, "last_trade_price": to_float(price)})
    return points


def parse_market_end_ts(value: Any) -> int | None:
    if value is None or value == "":
        return None

    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp <= 0:
            return None
        if timestamp > 10_000_000_000:
            timestamp /= 1000
        return int(timestamp)

    text = str(value).strip()
    if not text:
        return None

    try:
        if len(text) == 10 and text[4] == "-" and text[7] == "-":
            end_dt = datetime.fromisoformat(text).replace(tzinfo=timezone.utc)
            end_dt = end_dt + timedelta(days=1) - timedelta(seconds=1)
        else:
            end_dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
            if end_dt.tzinfo is None:
                end_dt = end_dt.replace(tzinfo=timezone.utc)
            else:
                end_dt = end_dt.astimezone(timezone.utc)
    except ValueError:
        return None

    return int(end_dt.timestamp())


def trade_fetch_end_ts(market: dict[str, Any], now_ts: int) -> int | None:
    end_ts = parse_market_end_ts(market.get("end_date"))
    if end_ts is not None and end_ts < now_ts:
        return end_ts
    return None


def main() -> None:
    config = load_config()
    now = datetime.now(timezone.utc)
    generated_at = now.replace(microsecond=0).isoformat()
    now_ts = int(now.timestamp())
    price_history_end_ts: int | None = None
    price_history_start_ts: int | None = None
    if config.price_history_days > 0:
        price_history_end = now
        price_history_start = price_history_end - timedelta(days=config.price_history_days)
        price_history_end_ts = int(price_history_end.timestamp())
        price_history_start_ts = int(price_history_start.timestamp())

    print("Fetching active and closed Polymarket events...")
    active_events = fetch_events(max_events=config.max_events, page_size=config.event_page_size, active=True, closed=False)
    closed_events = fetch_events(max_events=max(50, config.max_events // 5), page_size=config.event_page_size, active=False, closed=True)
    tags = fetch_tags()

    public_events, flat_markets = normalize_events(active_events + closed_events, generated_at)
    flat_markets.sort(key=lambda row: (row["closed"], -row["volume_24h_m"], -row["volume_m"]))

    print("Fetching price history and latest books for markets...")
    for market in flat_markets[: config.max_events]:
        for outcome in market["outcomes"]:
            token_id = outcome.get("source_token_id")
            if not token_id:
                continue
            try:
                book = summarize_book(fetch_book(token_id))
                outcome.update(book)
                if book["midpoint"]:
                    outcome["probability"] = book["midpoint"]
            except Exception as exc:
                outcome["book_error"] = str(exc)

            try:
                history = fetch_chart_history(token_id, config, price_history_start_ts, price_history_end_ts)
                history_points = normalize_price_history(history, config.price_history_max_points)
                if len(history_points) >= 2 and len(history_points) > len(market["price_history"]):
                    market["price_history"] = history_points
            except Exception as exc:
                outcome["history_error"] = str(exc)

    top_markets = [market for market in flat_markets if market["active"] and not market["closed"]][: config.top_markets_for_trades]
    trades_by_market = {}
    print(f"Fetching trades for {len(top_markets)} high-priority markets...")
    for market in top_markets:
        try:
            end_ts = trade_fetch_end_ts(market, now_ts)
            if end_ts is not None:
                print(f"Capping trades for ended market {market['public_slug']} at end timestamp {end_ts}")
            trades_by_market[market["public_slug"]] = fetch_trades(
                market["source_condition_id"],
                config.trades_per_market,
                end_ts=end_ts,
            )
        except Exception as exc:
            print(f"Trade fetch failed for {market['public_slug']}: {exc}")
            trades_by_market[market["public_slug"]] = []

    alerts_by_market = detect_whales(
        trades_by_market,
        min_usd=config.min_whale_usd,
        min_history=config.min_whale_history,
    )

    for event in public_events:
        for market in event["markets"]:
            alerts = alerts_by_market.get(market["public_slug"], [])
            if not alerts:
                continue
            severity_rank = {"Watch": 1, "Large": 2, "Extreme": 3}
            top = max(alerts, key=lambda row: severity_rank.get(row["severity"], 0))
            market["whale"] = {
                "severity": top["severity"],
                "count_24h": len(alerts),
                "largest_notional": max(row["notional_usd"] for row in alerts),
            }

    dashboard = {
        "generated_at": generated_at,
        "source": "Polymarket public APIs",
        "purpose": "Information and research only. No betting, trading, wallet connection, or investment advice.",
        "events": public_events,
    }
    write_json(config.output_dir / "latest" / "dashboard.json", dashboard)
    write_json(config.output_dir / "latest" / "tags.json", {"generated_at": generated_at, "tags": tags})
    write_json(config.output_dir / "alerts" / "latest-big-trades.json", {"generated_at": generated_at, "alerts_by_market": alerts_by_market})

    for event in public_events:
        for market in event["markets"]:
            write_json(
                config.output_dir / "history" / "market" / market["public_slug"] / "detail.json",
                {
                    "generated_at": generated_at,
                    "event_title": event["event_title"],
                    "tags": event.get("tags", []),
                    "market": market,
                    "big_trades": alerts_by_market.get(market["public_slug"], []),
                },
            )

    upload_directory_to_r2(config)


if __name__ == "__main__":
    main()
