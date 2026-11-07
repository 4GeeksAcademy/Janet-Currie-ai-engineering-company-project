-- HealthCore dead-letter tasks (DEV-55).
-- SQLModel create_all also creates this table. Run in the SQL Editor if needed.
-- Does not store tokens, payloads, patient data, or raw tracebacks.

CREATE TABLE IF NOT EXISTS dead_letter_tasks (
    id SERIAL PRIMARY KEY,
    task_id TEXT NOT NULL UNIQUE,
    task_name TEXT NOT NULL,
    attempt_number INTEGER NOT NULL,
    error_message TEXT NOT NULL,
    failed_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS dead_letter_tasks_task_id_key
    ON dead_letter_tasks (task_id);
