-- Apply in Supabase SQL editor or via migration.
-- Telemetry rows are append-only; do not add UPDATE/DELETE policies for the API role.

create table if not exists public.telemetry_events (
  id uuid primary key default gen_random_uuid(),
  timestamp timestamptz not null,
  service text not null,
  event_type text not null,
  level text not null default 'info',
  value numeric,
  message text,
  tags jsonb not null default '{}'::jsonb
);

create index if not exists telemetry_events_timestamp_idx on public.telemetry_events (timestamp);
create index if not exists telemetry_events_event_type_idx on public.telemetry_events (event_type);
create index if not exists telemetry_events_tags_gin_idx on public.telemetry_events using gin (tags);

alter table public.telemetry_events enable row level security;
