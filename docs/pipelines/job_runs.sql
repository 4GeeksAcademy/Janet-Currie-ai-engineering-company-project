-- Apply in Supabase SQL editor. Do not apply to production unless authorized.
-- Nightly orchestration (DEV-53). Distinct from reporting.pipeline_runs.

create schema if not exists reporting;

create table if not exists reporting.job_runs (
  id uuid primary key default gen_random_uuid(),
  job_name text not null,
  target_date date not null,
  status text not null,
  started_at timestamptz,
  finished_at timestamptz,
  error_message text,
  created_at timestamptz not null default now(),
  constraint job_runs_status_check
    check (status in ('pending', 'processing', 'completed', 'failed'))
);

create index if not exists job_runs_job_name_target_date_idx
  on reporting.job_runs (job_name, target_date);

-- Distributed lock: at most one processing row per job_name.
create unique index if not exists job_runs_processing_lock_uidx
  on reporting.job_runs (job_name)
  where status = 'processing';

-- One successful orchestration per job_name + target_date; failed rows stay retryable.
create unique index if not exists job_runs_completed_uidx
  on reporting.job_runs (job_name, target_date)
  where status = 'completed';

alter table reporting.job_runs enable row level security;

-- PostgREST still needs schema usage even with the service_role key:
--   grant usage on schema reporting to postgres, anon, authenticated, service_role;
--   grant all on all tables in schema reporting to postgres, service_role;
--   notify pgrst, 'reload schema';
