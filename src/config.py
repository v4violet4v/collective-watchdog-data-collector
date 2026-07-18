from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CollectorConfig:
    output_dir: Path
    max_events: int
    event_page_size: int
    price_history_interval: str
    price_history_fidelity: int
    price_history_days: int
    price_history_max_points: int
    trades_per_market: int
    top_markets_for_trades: int
    min_whale_usd: float
    min_whale_history: int
    r2_bucket: str | None
    r2_endpoint_url: str | None
    r2_access_key_id: str | None
    r2_secret_access_key: str | None
    require_r2_upload: bool


def load_config() -> CollectorConfig:
    return CollectorConfig(
        output_dir=Path(os.getenv("OUTPUT_DIR", "dist")),
        max_events=int(os.getenv("MAX_EVENTS", "300")),
        event_page_size=int(os.getenv("EVENT_PAGE_SIZE", "100")),
        price_history_interval=os.getenv("PRICE_HISTORY_INTERVAL", "1w"),
        price_history_fidelity=int(os.getenv("PRICE_HISTORY_FIDELITY", "1440")),
        price_history_days=int(os.getenv("PRICE_HISTORY_DAYS", "90")),
        price_history_max_points=int(os.getenv("PRICE_HISTORY_MAX_POINTS", "240")),
        trades_per_market=int(os.getenv("TRADES_PER_MARKET", "500")),
        top_markets_for_trades=int(os.getenv("TOP_MARKETS_FOR_TRADES", "50")),
        min_whale_usd=float(os.getenv("MIN_WHALE_USD", "10000")),
        min_whale_history=int(os.getenv("MIN_WHALE_HISTORY", "20")),
        r2_bucket=os.getenv("R2_BUCKET"),
        r2_endpoint_url=os.getenv("R2_ENDPOINT_URL"),
        r2_access_key_id=os.getenv("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=os.getenv("R2_SECRET_ACCESS_KEY"),
        require_r2_upload=os.getenv("REQUIRE_R2_UPLOAD", "false").lower() in {"1", "true", "yes"},
    )
