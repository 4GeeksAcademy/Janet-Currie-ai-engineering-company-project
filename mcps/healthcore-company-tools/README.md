# HealthCore tool door

This door lets a signed-in staff member read one saved incident or read clinic stock. It does not create incidents, change a status, or change stock.

The sign-in is the staff login that already exists at `POST /auth/login`. This door does not add a second login site. A password-reset token cannot open the door.

## Setup

From the repository root:

```bash
uv sync --directory mcps/healthcore-company-tools
```

Copy `.env.example` to `.env` and keep the same `SECRET_KEY` the API uses. Do not put a real token in this file.

| Name | Meaning |
| --- | --- |
| `SECRET_KEY` | Shared secret that signs the staff token |
| `HEALTHCORE_TOKEN_ISSUER` | `https://healthcore-api` |
| `HEALTHCORE_TOKEN_AUDIENCE` | `healthcore-company-tools` |
| `MCP_URL` | `http://127.0.0.1:8001` |
| `MCP_PORT` | `8001` |

Start the door:

```bash
uv --directory mcps/healthcore-company-tools run healthcore-company-tools
```

The installed FastMCP 4.1.6 serves Streamable HTTP at `/mcp`. The local address is `http://127.0.0.1:8001/mcp`.

Streamable HTTP is the transport a remote MCP Playground can connect to. A local stdio process would not be reachable from that Playground.

## Tools

`get_incident_status` reads one id like `HC-000006` from the latest uploaded CSV. It needs the scope `incidents:read`. The answer uses `incident_id`, `date`, `clinic_id`, `country`, `category`, and `status`. It does not return a patient id or a description.

`query_inventory` lists products or reads one product by its numeric id. It needs the scope `inventory:read`. Each product has `id`, `name`, `sku`, `category`, `unit`, `country`, and `current_stock`.

There is no tool that creates an incident or changes stock. If a caller asks to create, update, delete, receive, or use stock, the answer is `INVENTORY_READ_ONLY`.

## Error codes

`AUTH_REQUIRED`, `INVALID_TOKEN`, `TOKEN_EXPIRED`, `INSUFFICIENT_SCOPE`, `INVENTORY_READ_ONLY`, `VALIDATION_ERROR`, `INCIDENT_NOT_FOUND`, `INVENTORY_NOT_FOUND`, `UPSTREAM_UNAVAILABLE`, `UPSTREAM_TIMEOUT`, and `INTERNAL_ERROR`.

A missing, broken, expired, or wrong-audience token cannot list tools or call them.

## Tests

```bash
uv --directory mcps/healthcore-company-tools run pytest
```

## MCP Playground

Forward port `8001` from a Codespace, then connect the Playground to the public `https://...` address with the path `/mcp`. Use a staff access token from `POST /auth/login` as the bearer token. Do not use `localhost` in the Playground, because that address points at the Playground machine.

Playground was not run from this laptop.

The incident rows live in the API process memory. A door process started on its own does not see an upload made in a different API process. Stock reads use the inventory database when that database is available to the door process.
