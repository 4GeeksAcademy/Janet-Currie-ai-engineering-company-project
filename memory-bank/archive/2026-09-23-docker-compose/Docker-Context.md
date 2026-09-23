# Company Project Context: Docker Development Environment

## Purpose

This document is the implementation handoff for containerizing the existing AI Engineering company-project monorepo for local development. It defines the required Dockerfiles, Docker Compose topology, hot-reload behavior, configuration and secret boundaries, networking rules, validation expectations, and scope limits.

The implementation agent must apply this work to the existing company monorepo. Do not create a new repository, copy the applications into a separate project, or redesign the application architecture. Before planning or changing files, inspect the real checkout, its active `memory-bank/` files, package-manager lockfiles, frontend and backend start commands, environment-variable usage, authentication/inventory API URLs, database dependencies, and current `.gitignore` rules. Replace illustrative commands only where the repository proves that a different concrete command is required.


## Ticket and Business Context

The governing ticket is **`infra-40`**.

The company platform already contains:

- a public Next.js website under `/uis/website`;
- an internal Next.js backoffice under `/uis/backoffice`;
- a FastAPI application under `/services`;
- supporting scripts and environment-dependent integrations.

The applications run locally, but onboarding is unreliable because developers can have different Node and Python versions, globally installed dependencies, and undocumented configuration. The purpose of this project is to define the development environment as versioned code so every team member runs the same service topology with one root-level command.

The required developer experience is:

```bash
docker compose up
```

From the repository root, that command must start the full platform without developers manually installing application dependencies on the host or starting each application separately.

## Project Goal

Create a reproducible Docker Compose development environment with exactly two application services:

1. one **UI service** containing and running both Next.js applications;
2. one **backend service** running FastAPI through Uvicorn.

Both services must support development hot reloading, receive configuration through environment variables, expose their applications to the host on the correct ports, and communicate over an explicitly named Docker network. Container-to-container traffic must address the target by its Compose service name, never `localhost` or a hardcoded container IP.

## Required Repository Artifacts

The implementation is expected to add or update these responsibilities:

```text
repository-root/
├── .env                         # local values only; ignored by Git
├── .gitignore                   # must ignore the root .env
├── docker-compose.yml           # two-service development orchestration
├── uis/
│   ├── Dockerfile               # one image for website + backoffice
│   ├── .dockerignore
│   ├── start.sh                 # starts both Next.js dev servers
│   ├── website/
│   └── backoffice/
└── services/
    ├── Dockerfile               # FastAPI development image
    ├── .dockerignore
    └── ...
```

The exact existing files inside `uis/` and `services/` must be discovered before implementation. Do not overwrite working scripts or configuration without first determining whether they can be reused or minimally extended.

## Fixed Container Topology

### UI service

- Build context: `/uis`.
- Image base: an official Alpine-based Node image.
- One container must run both Next.js development applications.
- Public website listens on container/host port `3000`.
- Backoffice listens on container/host port `3001`.
- Dependencies for `/uis/website` and `/uis/backoffice` must be installed separately, using the package manager and lockfile each application actually uses.
- The Dockerfile's default `CMD` must invoke `/uis/start.sh` or its container-relative equivalent.
- Source code must be bind-mounted for hot reload.

### Backend service

- Build context: `/services`.
- Image base: an official Python image compatible with the project's declared Python version.
- Install `uv` in the image.
- Install backend dependencies from `requirements.txt` with:

  ```bash
  uv pip install -r requirements.txt
  ```

- Start the actual FastAPI application with Uvicorn and `--reload` enabled.
- Publish the backend's real listening port to the host; this is normally `8000`, but the implementation agent must verify the existing entry point and port rather than inventing them.
- Source code must be bind-mounted for hot reload.

### Docker Compose

- File location: repository-root `docker-compose.yml`.
- Define exactly the required UI and backend application services unless newer requirements explicitly add infrastructure services.
- Build the UI service from `/uis` and the backend service from `/services`.
- Publish UI ports `3000` and `3001` to the host.
- Publish the verified Uvicorn/FastAPI port to the host.
- Bind-mount each service's source tree so host changes are visible in its container.
- Attach both services to an explicitly declared and explicitly named Docker network.
- Load service configuration from the repository-root `.env` rather than hardcoding environment-specific values or secrets into the Dockerfile or Compose YAML.

## UI Dockerfile Requirements

Create `/uis/Dockerfile` with the following behavior:

- Use an official Node Alpine base image.
- Set a clear container working directory.
- Copy dependency manifests and lockfiles before source code where practical so dependency layers can be cached.
- Install the website's dependencies in the website directory.
- Install the backoffice's dependencies in the backoffice directory.
- Use reproducible, lockfile-respecting install commands supported by the actual repository.
- Copy the source and `start.sh` required at runtime.
- Ensure `start.sh` can be executed in the Linux container.
- Expose or document ports `3000` and `3001` consistently with Compose.
- Use `start.sh` as the default command.

This is a development image. Both Next.js applications must run in development mode so their hot-reload behavior remains available.

### Dependency and bind-mount interaction

A bind mount of the host `/uis` directory can hide dependencies installed into the same path during image build. The implementation plan must account for this explicitly. Use a repository-compatible approach such as container-managed dependency volumes or a mount layout that preserves image-installed dependencies while still bind-mounting source files. Do not require developers to populate host `node_modules` as a workaround; that would undermine reproducibility.

### `uis/start.sh`

The script must start both applications:

- website: Next.js development server on `0.0.0.0:3000`;
- backoffice: Next.js development server on `0.0.0.0:3001`.

Binding to `0.0.0.0` is essential because a process bound only to the container's loopback interface will not be reachable through a published host port.

The implementation agent must use each package's actual development command. The script must keep the container alive while both processes run, propagate termination cleanly when Compose stops, and avoid leaving one application silently unavailable if its process exits. It must use Linux-compatible line endings and be executable in the image. Do not introduce a heavyweight process manager unless the repository or a demonstrated reliability need justifies it.

## UI `.dockerignore` Requirements

Create `/uis/.dockerignore`. It must exclude at minimum:

```text
node_modules
.next
.env*
*.log
```

Patterns must cover these artifacts inside both child applications. Also exclude other generated, local, cache, coverage, editor, and version-control content when it is safe and relevant, but do not exclude manifests, lockfiles, `start.sh`, source code, or configuration required to build and run the applications.

The `.dockerignore` protects build context and image layers. It does not replace `.gitignore` or runtime environment configuration.

## Backend Dockerfile Requirements

Create `/services/Dockerfile` with the following behavior:

- Use an official Python base image compatible with the project.
- Configure predictable Python container behavior according to existing conventions, such as unbuffered logs and no bytecode where appropriate.
- Set the backend working directory.
- Install `uv` without depending on a developer's host installation.
- Copy `requirements.txt` before the full source where practical for layer caching.
- Install dependencies using `uv pip install -r requirements.txt` in the environment strategy chosen for the container.
- Copy the runtime source needed by FastAPI and any required local modules.
- Use the verified Uvicorn import path and listen on `0.0.0.0`.
- Enable `--reload` in the default development command.
- Keep environment-specific values outside the image.

If the repository uses a virtual environment, ensure its location is not hidden by the source bind mount. If it installs into the system environment inside the container, make that choice explicit and keep it isolated to the image. Do not modify the application's dependency declarations merely to force a guessed Docker pattern.

## Backend `.dockerignore` Requirements

Create `/services/.dockerignore`. It must exclude at minimum:

```text
__pycache__
*.pyc
.env*
tests/
*.log
```

Exclude other safe development artifacts such as local virtual environments, caches, coverage output, editor files, and version-control metadata where present. Do not exclude `requirements.txt`, application source, package metadata, migrations, templates, or runtime files required by the service.

The assignment specifically requires `tests/` to stay out of the backend image. Tests should continue to run through the repository's normal host/CI workflow unless a future requirement adds a dedicated test image or Compose profile.

## Docker Compose Requirements

The root `docker-compose.yml` must be a development orchestrator, not a production deployment manifest.

### UI service definition

The UI service must:

- build from `./uis` using `/uis/Dockerfile`;
- run the Dockerfile's `start.sh` command or an equivalent explicit Compose command that still starts both applications;
- publish website port `3000` and backoffice port `3001`;
- bind-mount the UI source needed for hot reload;
- preserve container-installed dependencies from bind-mount shadowing;
- receive all required public and server-side frontend environment values from root configuration;
- join the explicitly named project network.

### Backend service definition

The backend service must:

- build from `./services` using `/services/Dockerfile`;
- run Uvicorn with `--reload` using the real FastAPI import path;
- publish the verified backend port;
- bind-mount backend source for reload;
- receive database, JWT, email-provider, CORS, and other required backend variables from root configuration without hardcoding their values;
- join the same explicitly named project network.

### Named network

Declare a network in the top-level `networks` section and give it an explicit Docker name. Attach both services to it. Inside this network, use the backend service key as the DNS hostname for container-originated requests.

Do not depend on ephemeral container IP addresses. Do not use deprecated `links`. Compose provides service-name DNS on the shared network.

### Startup and readiness

Compose startup order is not the same as application readiness. If either application makes startup-time calls to the other, inspect whether existing retry behavior is sufficient. Add a narrowly scoped healthcheck/readiness dependency only if the real application requires it; do not expand the assignment into a general observability project.

## Networking Contract

The assignment requires service-to-service URLs to use Docker service names instead of `localhost`.

Inside a container, `localhost` means that same container:

- the UI container cannot reach FastAPI through `http://localhost:<backend-port>`;
- the backend container cannot reach either UI application through its own `localhost`;
- container-to-container requests must use a URL such as `http://<backend-service-name>:<backend-port>`.

The implementation agent must inventory every connection URL, including inventory/auth API configuration, CORS origins, callbacks, server-side fetches, and scripts.

### Browser-versus-container distinction

A browser running on the developer's host is **not** inside the Docker network and cannot normally resolve a Compose service name such as `backend`. Therefore:

- server-side requests originating in the UI container can use the backend service name;
- browser-side requests need a host-reachable published URL such as `http://localhost:<published-backend-port>`, or they must call a same-origin Next.js path that the UI server proxies/rewrites to the backend service name;
- a `NEXT_PUBLIC_*` value is embedded into browser code and must not blindly be set to a Docker-only hostname.

The implementation plan must inspect where each frontend request executes and choose a repository-compatible configuration. A same-origin proxy/rewriter is acceptable if needed, but it is not automatically required. The final system must satisfy both realities: internal traffic uses service-name DNS, and host-browser traffic remains reachable.

### CORS and allowed origins

If the browser calls the published FastAPI port directly, the backend must allow the actual development origins for the website and backoffice, normally the host URLs using ports `3000` and `3001`. Preserve the existing CORS configuration mechanism and inject values through the environment. Do not solve CORS by allowing every origin with credentials unless that is already a deliberate, safe development contract.

## Hot-Reload Requirements

Host edits must appear without rebuilding the image:

- website source changes must be reflected through the Next.js dev server on port `3000`;
- backoffice source changes must be reflected through the Next.js dev server on port `3001`;
- backend source changes must trigger Uvicorn reload.

Use bind mounts for source code. If filesystem events do not propagate reliably on the supported Docker Desktop host, add the narrow polling/watch configuration required by the frameworks and document it; do not enable expensive global polling without evidence that it is needed.

Dependency-manifest changes may legitimately require rebuilding the affected image. The no-rebuild acceptance criterion applies to normal source changes, not installation of new packages.

## Environment Configuration

Create a local repository-root `.env` before composing the services, as required by the assignment. The implementation agent must first inventory actual environment-variable names from both frontends and the backend rather than guessing or copying stale names.

The root configuration must cover, as applicable:

- host-browser and container-internal API origins;
- database/Supabase connection settings;
- JWT signing and expiration settings;
- frontend authentication configuration;
- inventory API configuration;
- email-provider configuration used by password reset;
- CORS/allowed origins;
- any existing required third-party integration variables.

### Secret rules

- Never hardcode real API keys, passwords, JWT secrets, database credentials, or tokens in either Dockerfile or `docker-compose.yml`.
- Never bake `.env` files into an image; both `.dockerignore` files must exclude `.env*`.
- The root `.env` must be ignored by Git.
- Do not print secrets in build output, container logs, healthchecks, example commands, or documentation.
- Public frontend variables are visible to browser users and must not contain secrets.
- If a secret is found in tracked files or Git history, treat it as compromised, report it, and rotate it through the relevant provider. Do not rewrite repository history or rotate credentials without explicit authorization.

### Reproducible onboarding and examples

The assignment requires `docker compose up` to work without additional application-setup steps once the required local `.env` is present. Preserve or create a safe committed example file only if that matches repository convention. An example must contain variable names and non-sensitive placeholders, never working secrets. Document any unavoidable one-time copy/configuration step clearly; do not falsely claim a clean clone can run without credentials when external services require them.

## Persistence and External Services

The source assignment defines only two application containers and does not request a database container. The backend may continue using its existing Supabase/PostgreSQL or other external services through environment configuration.

Inspect whether the project writes TinyDB data, uploaded files, generated files, or other durable development state inside `/services`. A broad source bind mount may preserve these accidentally, but the implementation plan must identify the real paths and ensure container recreation does not unexpectedly erase required local development data or commit runtime data. Do not add unrelated database, cache, or storage containers unless a newer requirement explicitly expands the topology.

## Required Initial Analysis

Before writing container files, the implementation agent must inspect and record:

- the actual monorepo tree and whether `/uis`, `/uis/website`, `/uis/backoffice`, and `/services` match the brief;
- Node and Python version declarations;
- package managers and lockfiles for both Next.js apps;
- the exact development command for each Next.js app and how to bind its host/port;
- the FastAPI application import path and current Uvicorn command;
- the backend listening port;
- how `uv` and `requirements.txt` are currently used;
- all required frontend and backend environment variables;
- which frontend calls run in the browser versus the Next.js server;
- every use of `localhost`, `127.0.0.1`, hardcoded IPs, or fixed API origins in application/configuration files;
- authentication, inventory, password-reset, database, CORS, and callback URLs;
- data files or directories that must survive container restarts;
- current `.gitignore` behavior and whether any `.env` file is already tracked;
- existing Docker, Compose, devcontainer, or startup files that must be preserved or reconciled;
- current test, lint, type-check, and build commands so containerization does not hide regressions.

Create a repository-grounded implementation plan naming the concrete files, commands, ports, mounts, environment mappings, service names, network name, dependency-volume strategy, and validation steps before modifying the project.

## Validation Plan

Treat containerization and validation as one task. The implementation is not complete when files merely parse; it must run the actual applications.

### Static and configuration validation

At minimum:

- validate the resolved Compose model with `docker compose config`;
- inspect the resolved configuration to ensure required variables are present without printing secret values into reports;
- confirm both Dockerfiles build from their intended contexts;
- confirm both `.dockerignore` files exist and required build inputs remain available;
- confirm root `.env` is ignored and not tracked;
- search Dockerfiles, Compose, and versioned environment examples for hardcoded real secrets;
- search inter-service configuration for `localhost`, loopback addresses, and hardcoded container IPs, classifying browser-facing host URLs separately from container-internal URLs.

### Build and startup validation

From the repository root:

```bash
docker compose up --build
```

Then verify:

- Compose starts exactly the expected UI and backend services without fatal errors;
- the UI container keeps both Next.js processes running;
- `docker compose ps` shows the expected services and published ports;
- the website is reachable from the host on port `3000`;
- the backoffice is reachable from the host on port `3001`;
- FastAPI and its documentation/health route, where present, are reachable on the published backend port;
- the frontends can complete real authenticated/API flows against the containerized backend;
- container logs contain no secrets and no repeating connection failures.

### Network validation

Verify from the relevant container that:

- the backend service name resolves through Docker DNS;
- the UI container can reach the backend by service name and container port;
- no container-to-container request depends on the host's `localhost`;
- browser-originated requests use a host-reachable or proxied route;
- CORS allows the two real development origins without introducing an unsafe wildcard-with-credentials configuration.

### Hot-reload validation

With Compose still running:

1. Make a harmless, reversible source edit in the website and verify the running page updates without image rebuild.
2. Make a harmless, reversible source edit in the backoffice and verify it updates without image rebuild.
3. Make a harmless, reversible backend source edit and verify Uvicorn reloads and continues serving requests.
4. Restore the temporary validation edits without disturbing user work.

Do not claim hot reload works merely because bind mounts appear in the Compose file; observe the behavior.

### Regression validation

Run the project's applicable existing tests, type checks, lint checks, and builds outside or inside the appropriate environment according to repository convention. Containerization must not change application behavior or bypass a valid existing check.

Record exact commands and observed results in the active memory bank. If Docker is unavailable, an external service is unreachable, or credentials are missing, state the precise limitation and perform the strongest available static validation. Clearly distinguish verified behavior from unverified behavior.

## Evaluator-Critical Checks

The implementation will be explicitly evaluated for the following:

1. Running `docker compose up` at the repository root starts the full platform without errors or separate manual application-start commands.
2. Normal host source changes appear in both Next.js applications and FastAPI without rebuilding images.
3. One UI container runs the website on port `3000` and the backoffice on port `3001`.
4. The FastAPI backend runs in its own container with Uvicorn `--reload`.
5. Both services share an explicitly named Docker network.
6. Container-to-container communication uses Compose service-name DNS rather than `localhost` or hardcoded IP addresses.
7. No real secrets, API keys, or passwords are hardcoded in a Dockerfile or `docker-compose.yml`.
8. The root `.env` is ignored and does not appear in Git history.
9. `/uis/.dockerignore` and `/services/.dockerignore` exist and contain at least the assignment's required exclusions.

These are mandatory requirements, not suggestions.

## Acceptance Criteria

The containerization project is complete only when all of the following are true:

- A developer with Docker Compose v2 and a correctly configured ignored root `.env` can start the platform from the repository root with `docker compose up`.
- The root Compose file defines the required UI and backend application services and an explicitly named shared network.
- `/uis/Dockerfile` uses an official Node Alpine image, installs both applications' dependencies separately, and starts both through `start.sh`.
- The website is reachable on host port `3000` and the backoffice on host port `3001`.
- `/services/Dockerfile` uses an official compatible Python image, installs `uv`, installs `requirements.txt` with `uv pip install -r requirements.txt`, and runs the correct Uvicorn target with `--reload`.
- The backend is reachable through its published host port.
- Source bind mounts provide observed hot reload for the website, backoffice, and backend without masking required container dependencies.
- The UI container can reach the backend over Docker DNS using the backend service name.
- Browser-side API calls remain reachable from the host or use a working same-origin proxy; no Docker-only hostname is incorrectly exposed to the browser.
- All inter-service URLs have been reviewed and no container uses `localhost` to reach another container.
- Required environment variables are injected from configuration rather than hardcoded.
- Real secrets are absent from versioned container files, build contexts, logs, and public frontend variables.
- Root `.env` is ignored and untracked.
- Both required `.dockerignore` files exist with all minimum patterns.
- Container startup, ports, live API communication, hot reload, and applicable application regression checks have been observed and recorded.
- Existing application behavior outside container-specific configuration remains unchanged.

## Scope Boundaries

In scope:

- one development Dockerfile and `.dockerignore` for `/uis`;
- a UI startup script for both Next.js applications;
- one development Dockerfile and `.dockerignore` for `/services`;
- a repository-root two-service `docker-compose.yml`;
- a named development network;
- source bind mounts and dependency-preserving mount behavior;
- root environment mapping and `.gitignore` verification;
- the smallest application/configuration changes necessary to replace invalid container-internal `localhost` URLs;
- documentation and focused validation necessary for reproducible local use.

Out of scope unless a newer requirement explicitly adds it:

- Kubernetes, Helm, Swarm, Terraform, or cloud deployment;
- production Dockerfiles, production Compose profiles, reverse proxies, TLS, domains, or certificates;
- CI/CD pipelines or container registries;
- adding PostgreSQL, Supabase, Redis, mail, or other infrastructure containers;
- separating the two Next.js applications into multiple containers;
- application feature development or unrelated refactoring;
- authentication, inventory, or database redesign;
- broad observability, logging, backup, or scaling work;
- Git commits, pushes, branches, pull requests, or history rewriting without explicit user authorization.

## Handoff Expectations

The implementation agent should begin by inspecting the real monorepo and producing a concrete plan. During implementation, keep the active project memory bank current with material findings, decisions, progress, validation output, blockers, and next steps.

Before finalizing:

1. Reconcile every required artifact and minimum ignore pattern against this document.
2. Verify both applications run simultaneously in the single UI container.
3. Verify all three development servers are host-accessible and hot reload has been observed.
4. Audit every inter-service URL and explicitly distinguish container-internal from host-browser traffic.
5. Confirm the root `.env` is ignored, untracked, excluded from image contexts, and not echoed in validation evidence.
6. Run the Compose, network, live-flow, and regression checks with actual command output.
7. Record remaining environment-specific limitations rather than claiming unverified portability.
8. Update durable implementation memory only after the containerization work has genuinely been finalized.
