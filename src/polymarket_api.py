from __future__ import annotations

import time
import os
from typing import Any

import requests
import urllib3


GAMMA_EVENTS_URL = "https://gamma-api.polymarket.com/events"
GAMMA_TAGS_URL = "https://gamma-api.polymarket.com/tags"
CLOB_BOOK_URL = "https://clob.polymarket.com/book"
CLOB_PRICE_HISTORY_URL = "https://clob.polymarket.com/prices-history"
DATA_TRADES_URL = "https://data-api.polymarket.com/trades"

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "collective-watchdog-data-collector/0.1",
}

SSL_VERIFY = os.getenv("COLLECTOR_SSL_VERIFY", "true").lower() not in {"0", "false", "no"}
if not SSL_VERIFY:
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def _order_candidates(order: str) -> list[str]:
    candidates = [order]
    if order == "volume_24hr":
        candidates.insert(0, "volume24hr")
    elif order == "volume24hr":
        candidates.append("volume_24hr")
    if order in {"volume_24hr", "volume24hr"}:
        candidates.append("volume")
    return list(dict.fromkeys(candidates))


def request_json(url: str, params: dict[str, Any] | None = None, timeout: int = 30) -> Any:
    response = requests.get(url, params=params, headers=HEADERS, timeout=timeout, verify=SSL_VERIFY)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        body = response.text[:1000].replace("\n", " ")
        raise RuntimeError(f"HTTP {response.status_code} from {url} with params={params}: {body}") from exc
    return response.json()


def fetch_events(
    *,
    max_events: int,
    page_size: int,
    active: bool | None = None,
    closed: bool | None = None,
    order: str = "volume24hr",
    ascending: bool = False,
) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    offset = 0

    while len(events) < max_events:
        limit = min(page_size, max_events - len(events))
        base_params: dict[str, Any] = {
            "limit": limit,
            "offset": offset,
            "ascending": str(ascending).lower(),
        }
        if active is not None:
            base_params["active"] = str(active).lower()
        if closed is not None:
            base_params["closed"] = str(closed).lower()

        last_error: Exception | None = None
        for order_value in _order_candidates(order):
            params = {**base_params, "order": order_value}
            try:
                payload = request_json(GAMMA_EVENTS_URL, params=params)
                break
            except RuntimeError as exc:
                last_error = exc
                if "HTTP 422" not in str(exc):
                    raise
        else:
            raise last_error or RuntimeError("Gamma events request failed")

        batch = payload if isinstance(payload, list) else payload.get("data", [])
        if not batch:
            break

        events.extend(batch)
        offset += len(batch)
        if len(batch) < limit:
            break
        time.sleep(0.05)

    return events


def fetch_tags(limit: int = 500) -> list[dict[str, Any]]:
    payload = request_json(GAMMA_TAGS_URL, params={"limit": limit})
    return payload if isinstance(payload, list) else payload.get("data", [])


def fetch_book(token_id: str) -> dict[str, Any]:
    return request_json(CLOB_BOOK_URL, params={"token_id": token_id}, timeout=20)


def fetch_price_history(token_id: str, interval: str = "1w", fidelity: int = 60) -> list[dict[str, Any]]:
    payload = request_json(
        CLOB_PRICE_HISTORY_URL,
        params={"market": token_id, "interval": interval, "fidelity": fidelity},
        timeout=20,
    )
    if isinstance(payload, dict):
        return payload.get("history", []) or payload.get("data", [])
    return payload if isinstance(payload, list) else []


def fetch_trades(condition_id: str, limit: int = 500) -> list[dict[str, Any]]:
    payload = request_json(
        DATA_TRADES_URL,
        params={"market": condition_id, "limit": limit, "offset": 0, "takerOnly": "true"},
        timeout=30,
    )
    return payload if isinstance(payload, list) else payload.get("data", [])
