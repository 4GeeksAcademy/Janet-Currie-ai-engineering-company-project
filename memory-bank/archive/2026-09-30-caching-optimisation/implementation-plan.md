# Implementation plan — Caching optimisation

Improve HealthCore staff-app and API performance with evidence-based lazy loading, one real `useMemo`, and TTL caching of at least two FastAPI reads—after profiling with realistic data—then record everything in `CACHING_REPORT.md`.

Phases: map every route → config-controlled request timing → idempotent larger seed → median cold/warm baselines → invalidation matrix → in-process TTL cache → two staff `next/dynamic` splits → focused tests → report and full validation.

Stay on `Caching-Optimisation`. Do not add Redis, a CDN, service workers, or HTTP cache headers unless measurements force it. Do not recount website `AppointmentModal`. Do not cache auth, profiles, health, or incident CSV. Caching must keep existing Pydantic `response_model` shapes.

Out of scope: new backend, repeating homepage `next/dynamic` LCP experiment, git publish unless asked, production data, rewriting unrelated UI.
