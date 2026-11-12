# HealthCore tool door

## Purpose

Give the support agent one locked way to read a saved incident, and give other callers a read of clinic stock. The door does not create incidents or change stock.

## Final Behavior

`mcps/healthcore-company-tools` serves Streamable HTTP at `http://127.0.0.1:8001/mcp`. Callers present the staff access token from `POST /auth/login`. `get_incident_status` needs `incidents:read`. `query_inventory` needs `inventory:read`. A create, update, delete, receive, or use request returns `INVENTORY_READ_ONLY`. A password-reset token cannot open the door.

The agent incident step calls `get_incident_status`. The staff token is a request context value and an Authorization header. It is not stored in the graph checkpoint. Policy routing is unchanged.

## Architecture and Data Flow

The API signs the staff token with the shared `SECRET_KEY` and HS256. The token carries issuer `https://healthcore-api`, audience `healthcore-company-tools`, and scope `incidents:read inventory:read`. mcpauth 0.1.1 checks that token through `bearer_auth_middleware(verify_staff_token, audience=...)`. The custom function checks the signature and expiry. The middleware checks issuer and audience.

The door reads incidents through `app.store.get_incident` and stock through `list_supplies`, `get_supply`, and `to_public`. It keeps no tables of its own.

## Important Files

- `mcps/healthcore-company-tools/`
- `services/api/app/auth/security.py`
- `services/api/app/agent/incidents.py`
- `services/api/app/routers/agent.py`

## Interfaces and Contracts

Tools: `get_incident_status(incident_id)` and `query_inventory(action, product_id)`. Incident output fields are `incident_id`, `date`, `clinic_id`, `country`, `category`, and `status`. Product fields are `id`, `name`, `sku`, `category`, `unit`, `country`, and `current_stock`.

Environment names: `SECRET_KEY`, `HEALTHCORE_TOKEN_ISSUER`, `HEALTHCORE_TOKEN_AUDIENCE`, `MCP_URL`, `MCP_PORT`.

## Decisions and Constraints

FastMCP 4.1.6, mcpauth 0.1.1, and langchain-mcp-adapters 0.3.2 are the locked libraries. The built-in mcpauth JWT mode cannot check this HS256 token. Cryptography stays at 44.0.3 on this Mac. The issuer is a URL because the middleware requires one. Incident rows live in API process memory, so a separately started door does not see an upload made in another process.

## Validation

Door tests, agent graph tests, agent tool tests, the knowledge-helper tests, the API suite, typecheck, and `docker compose config` were run. Playground, live model answers, the real match score, and Recall@3 were not run.

## Maintenance Notes

Do not add a write tool. Do not put the staff token in graph state. Do not add a second login site. The upload route remains the source that fills the incident store.
