# Open Analytics engineering guide

This file records the current repository layout and the rules for extending it. Read the code before changing a feature; this guide is a map, not a substitute for the implementation.

## Architecture

```text
React page -> frontend/src/api -> FastAPI route -> backend service -> DuckDB
```

- Route modules handle HTTP input, authentication dependencies, and response shaping. Keep provider calls, SQL, and business rules in services.
- Services own collection workflows and domain rules. Keep provider-specific parsing near the provider integration and keep database access explicit.
- Schemas define request and response contracts. Add validation at the API boundary.
- Frontend API modules own URL and Axios details. Pages own feature workflow state; reusable controls live in `components/`.
- Never make a new page or service depend on another page's internal state or a different feature's private helper.

## Folder map

```text
open-analytics/
  backend/
    .env.example                  local configuration template
    app/
      api/v1/                    versioned FastAPI routes
      services/
        connections/             Upstox and Telegram connection logic
        data_collection/         collectors, normalization, previews, summaries
        *_service.py             auth, admin, queue, and scheduler services
      schemas/                   Pydantic API contracts
      db/                        schema modules, database tools, local DuckDB file
      data/upstox/               generated provider downloads
      telegram_alerts_msg/       notification templates and sender
      config.py                  settings loaded from environment
      database.py                DuckDB connection and ordered schema setup
      main.py                    app creation, middleware, lifecycle, routes
      dependencies.py            auth and role dependencies
      instrument_sync.py         standalone instrument sync entry point
  frontend/
    public/                       static files served by Vite
    src/
      api/                        HTTP clients grouped by feature
      components/                 shared controls, tables, and layout
      pages/admin/dataCollection/ data collection UI, helpers, cell renderers
      pages/                     other screens grouped by feature
      routes/                    access guards
      App.jsx                    application routes
      index.css                  global and Tailwind styles
      main.jsx                   React entry point
  scripts/                       local startup helpers
  server/docker/                 container and deployment configuration
  docs/                          documentation
  Research/                      research design notes; do not reorganize casually
  README.md                      setup and navigation
```

## Placement rules

1. Put a new backend endpoint in the appropriate `api/v1/*_routes.py` file. Put its implementation in the matching service package and its request/response models in `schemas/`.
2. Put a new data collection provider or dataset in `services/data_collection/`. Keep fetching, normalization, persistence, and preview logic in focused modules. Avoid adding another all-purpose service file.
3. Put a new frontend screen under `pages/<feature>/` and its HTTP calls under `api/`. Extract page-specific components and pure data transforms into that feature folder before the page becomes difficult to navigate.
4. Put UI primitives used by multiple features in `components/common/` or `components/tables/`. A component used by one feature stays with that feature.
5. Add a focused test for date rules, financial calculations, normalization, migrations, and other behavior where a wrong result may look plausible. Keep tests next to the backend or frontend test suite when one is established.
6. Keep runtime files out of source control: virtual environments, `node_modules`, build output, logs, downloaded provider data, DuckDB files, and local `.env` files. Copy `backend/.env.example` to `backend/.env` for local configuration. Never put tokens or passwords in notebooks, examples, or committed files.
7. Update `README.md` and this guide when introducing or moving a top-level feature folder. Do not move or delete user research notes, databases, or deployment backups as routine cleanup.

## Current refactoring boundaries

- `backend/app/database.py` owns the connection and calls the ordered schema modules in `backend/app/db/`. Put new table setup in a focused schema module, preserving initialization order. For data-changing migrations, use an explicit version and test upgrades against both new and existing databases.
- `backend/app/services/data_collection/__init__.py` still re-exports and injects symbols across split modules. New code should import the function's owning module directly. Remove the compatibility behavior incrementally only after callers and cross-module dependencies have been made explicit and tested.
- `frontend/src/pages/admin/dataCollection/DataCollectionPage.jsx` still owns considerable workflow state. Stateless table cell rendering now lives in `tableCellRenderers.jsx`; new tabs should be separate feature components, with pure transforms in helpers and network calls in `src/api/dataCollectionApi.js`.
- Equity news, IPO calendar, and IPO GMP now live in `news_ipo_service.py`, `ipo_calendar_service.py`, and `ipo_gmp_service.py`. Shared table setup and Upstox HTTP helpers still live in the news module; move them to a focused shared module when changing them, with import and collection checks.

## Checks

```text
cd frontend && npm run build
cd backend && python -c "from app.main import app; print(len(app.routes))"
git diff --check
```

Run targeted tests for the code changed. The repository currently has no comprehensive automated test suite, so a passing build and import check do not prove collection or database behavior.
