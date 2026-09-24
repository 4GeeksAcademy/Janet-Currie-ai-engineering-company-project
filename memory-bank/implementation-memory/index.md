# Implementation memory catalog

| Implementation | Description | File | Keywords |
|----------------|-------------|------|----------|
| Bullet-proof test coverage | AUTH-088 / API-042 / FE-019 pytest and Jest suites | [bullet-proof-test-coverage.md](bullet-proof-test-coverage.md) | pytest, Jest, auth, incidents, suppliers, toUserMessage |
| Inventory API | HCR-0188 SQLModel `/inventory` catalogue and movements | [inventory-api.md](inventory-api.md) | SQLModel, MedicalSupply, current_stock, seed-inventory |
| Inventory backoffice UI | Authenticated `uis/web` supplies, delivery, consumption, history | [inventory-backoffice-ui.md](inventory-backoffice-ui.md) | /backoffice/inventory, InsufficientStockError, stockStatus |
| Docker Compose dev stack | Two-service `docker compose up` for website, staff UI, FastAPI | [docker-compose-dev.md](docker-compose-dev.md) | infra-40, healthcore_dev, CORS_ORIGINS, NEXT_PUBLIC_API_BASE_URL |
| Web Vitals audit | Production Lighthouse loop on `uis/website` and `uis/web` | [web-vitals.md](web-vitals.md) | Lighthouse, hc_lang, LangToggle, useAsyncResource |
| Serialization audit | Explicit FastAPI `response_model` contracts; no email on public register | [serialization-audit.md](serialization-audit.md) | UserRegisteredResponse, HealthResponse, IncidentAnalysisResponse, response_model |
