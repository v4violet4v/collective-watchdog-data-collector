create table if not exists collector_runs (
  id bigserial primary key,
  source text not null,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  status text not null default 'running',
  message text
);

create table if not exists events (
  id bigserial primary key,
  source text not null,
  source_event_id text,
  public_slug text not null unique,
  event_title text not null,
  tags jsonb not null default '[]'::jsonb,
  active boolean not null default false,
  closed boolean not null default false,
  start_date timestamptz,
  end_date timestamptz,
  last_seen_at timestamptz not null default now()
);

create table if not exists markets (
  id bigserial primary key,
  event_id bigint references events(id),
  source_market_id text,
  condition_id_hash text,
  public_slug text not null unique,
  question text not null,
  active boolean not null default false,
  closed boolean not null default false,
  end_date timestamptz,
  last_seen_at timestamptz not null default now()
);

create table if not exists market_options (
  id bigserial primary key,
  market_id bigint references markets(id),
  outcome_index integer not null,
  outcome_name text not null,
  token_id_hash text
);

create table if not exists market_snapshots (
  id bigserial primary key,
  market_id bigint references markets(id),
  snapshot_at timestamptz not null,
  volume numeric,
  volume_24h numeric,
  liquidity numeric,
  last_trade_price numeric,
  best_bid numeric,
  best_ask numeric,
  midpoint numeric,
  spread numeric
);

create table if not exists trades (
  id bigserial primary key,
  market_id bigint references markets(id),
  option_id bigint references market_options(id),
  source_trade_hash text,
  executed_at timestamptz,
  outcome text,
  side text,
  price numeric,
  size numeric,
  notional_usd numeric,
  wallet_hash text,
  trader_label text
);

create table if not exists whale_alerts (
  id bigserial primary key,
  trade_id bigint references trades(id),
  market_id bigint references markets(id),
  option_id bigint references market_options(id),
  alert_at timestamptz not null default now(),
  severity text not null,
  percentile_rank numeric,
  robust_z numeric,
  notional_usd numeric,
  reason text
);

