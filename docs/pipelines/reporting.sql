-- Apply in Supabase SQL editor. Read-only for telemetry_events.
-- Reporting schema is the destination for the monthly clinic supply pipeline.

create schema if not exists reporting;

create table if not exists reporting.monthly_clinic_supply_performance (
  id uuid primary key default gen_random_uuid(),
  clinic_id text not null,
  country text not null,
  month_start date not null,
  total_supply_cost numeric not null default 0,
  supply_consumption_count integer not null default 0,
  critical_stockout_count integer not null default 0,
  expiry_risk_count integer not null default 0,
  currency text not null,
  computed_at timestamptz not null default now(),
  unique (clinic_id, month_start)
);

create table if not exists reporting.pipeline_runs (
  run_id uuid primary key default gen_random_uuid(),
  started_at timestamptz not null,
  finished_at timestamptz,
  status text not null,
  records_processed integer not null default 0,
  error text,
  window_start timestamptz not null,
  window_end timestamptz not null,
  events_extracted integer not null default 0,
  events_quarantined integer not null default 0
);

create index if not exists pipeline_runs_started_at_idx
  on reporting.pipeline_runs (started_at desc);

alter table reporting.monthly_clinic_supply_performance enable row level security;
alter table reporting.pipeline_runs enable row level security;
