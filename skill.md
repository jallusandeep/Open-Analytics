# Open Analytics Project Skill / Handoff

## Project

Open Analytics

Project path:

[C:\Projects\open-analytics](.)

## Codex Skills

Available skills for this workspace:

- `imagegen`: Generate or edit raster images for bitmap visual assets. Skill file: [SKILL.md](C:/Users/jallu/.codex/skills/.system/imagegen/SKILL.md).
- `openai-docs`: Use official OpenAI documentation for OpenAI product/API questions. Skill file: [SKILL.md](C:/Users/jallu/.codex/skills/.system/openai-docs/SKILL.md).
- `plugin-creator`: Create and scaffold Codex plugin directories and manifests. Skill file: [SKILL.md](C:/Users/jallu/.codex/skills/.system/plugin-creator/SKILL.md).
- `skill-creator`: Create or update Codex skills. Skill file: [SKILL.md](C:/Users/jallu/.codex/skills/.system/skill-creator/SKILL.md).
- `skill-installer`: Install Codex skills from curated lists or GitHub repo paths. Skill file: [SKILL.md](C:/Users/jallu/.codex/skills/.system/skill-installer/SKILL.md).
- `open-analytics`: Work on this Open Analytics repository. Skill file: [skill.md](skill.md).

## Current Status

- Backend: FastAPI app in [backend/app](backend/app).
- Frontend: React/Vite app in [frontend/src](frontend/src).
- Database: DuckDB file at [backend/app/db/open_analytics.duckdb](backend/app/db/open_analytics.duckdb).
- Version control: Git initialized on branch `main`.
- Current local branch is ahead of `origin/main` with recent UI refactor commits.
- Current app version in code: [backend/app/version.py](backend/app/version.py) -> `APP_VERSION = "1.0.2"`.

## Recent Important Changes

### User Accounts Visibility Fix

- `/api/v1/users/me` returns `{ status, user }`.
- [frontend/src/routes/ProtectedRoute.jsx](frontend/src/routes/ProtectedRoute.jsx) stores `response.data.user || response.data`.
- `MainLayout.jsx` and `AdminRoute.jsx` read `open_analytics_current_user`, with fallback to `open_analytics_user`.
- This fixed the missing User Accounts icon for `admin` and `super_admin` users.

### DuckDB Path Fix

- [backend/app/config.py](backend/app/config.py) loads `.env` from the backend folder.
- [backend/app/database.py](backend/app/database.py) resolves relative DB paths from [backend/](backend/).
- This prevents accidentally using `C:\Projects\open-analytics\app\db\open_analytics.duckdb`.
- The active app DB should resolve to `C:\Projects\open-analytics\backend\app\db\open_analytics.duckdb`.

### Connections Feature

- Admin users can open `/connections` from the left sidebar.
- [backend/app/api/v1/connection_routes.py](backend/app/api/v1/connection_routes.py) exposes admin-only connection APIs.
- [backend/app/services/connection_service.py](backend/app/services/connection_service.py) stores Upstox credentials in DuckDB and tests provider reachability.
- [backend/app/schemas/connection_schema.py](backend/app/schemas/connection_schema.py) owns request/response models for connection APIs.
- [frontend/src/pages/admin/Connections.jsx](frontend/src/pages/admin/Connections.jsx) owns the Connections admin screen.
- [frontend/src/api/connectionApi.js](frontend/src/api/connectionApi.js) isolates frontend connection API calls.
- The `external_connections` table is initialized from [backend/app/database.py](backend/app/database.py).

### Data Collection Feature

- Admin users can open the Data Collection screen from the left sidebar.
- [frontend/src/pages/admin/DataCollection.jsx](frontend/src/pages/admin/DataCollection.jsx) owns the collection monitor, preview tabs, run buttons, scheduler modal, and polling state.
- [frontend/src/api/dataCollectionApi.js](frontend/src/api/dataCollectionApi.js) isolates frontend data collection API calls.
- [backend/app/api/v1/data_collection_routes.py](backend/app/api/v1/data_collection_routes.py) exposes `/api/v1/data-collection/upstox/...` endpoints.
- [backend/app/services/data_collection_service.py](backend/app/services/data_collection_service.py) owns data collection runners, previews, summaries, run history, cancellation, and Upstox API calls.
- [backend/app/services/data_collection_scheduler_service.py](backend/app/services/data_collection_scheduler_service.py) owns schedule CRUD and the background scheduler loop.
- [backend/app/instrument_sync.py](backend/app/instrument_sync.py) is the standalone instrument sync script.
- There is no `backend/app/upstox/` package in the current structure. Do not import from `app.upstox`.
- Monitor job keys currently supported by backend runner and scheduler:

```txt
current_instruments
expired_instruments
equity_instruments
ohlcv_daily
equity_news
fundamentals
corporate_actions
fii_dii_activity
```

- Current, Expired, Equity, and OHLCV have real collection logic.
- Equity News, Fundamentals, Corporate Actions, and FII/DII have tracked backend runners and scheduler support, but no external provider download/source logic configured yet.

### User Accounts Component Refactor

- `UserAccounts.jsx` keeps the same visual look.
- Common form/control pieces stay in [frontend/src/components/common](frontend/src/components/common).
- Table-specific reusable pieces moved to [frontend/src/components/tables](frontend/src/components/tables).
- `UserAccounts.jsx` now imports:

```jsx
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
```

## Architecture

Open Analytics uses a simple layered architecture:

```txt
Frontend pages
  -> frontend API clients
  -> FastAPI route modules
  -> service modules
  -> DuckDB database helpers
  -> DuckDB tables
```

Frontend rules:

- Pages own workflow state and page-specific rendering.
- [frontend/src/components/common](frontend/src/components/common) owns small reusable controls.
- [frontend/src/components/layout](frontend/src/components/layout) owns application shell/navigation.
- [frontend/src/components/tables](frontend/src/components/tables) owns table/grid/filter UI.
- [frontend/src/api](frontend/src/api) modules isolate Axios calls.
- Route guards decide login/admin access.

Backend rules:

- [backend/app/api/v1](backend/app/api/v1) route files define HTTP endpoints.
- [backend/app/services](backend/app/services) files hold business logic.
- [backend/app/schemas](backend/app/schemas) files hold Pydantic request/response models.
- [backend/app/database.py](backend/app/database.py) owns DuckDB connection and schema initialization.
- [backend/app/dependencies.py](backend/app/dependencies.py) owns current-user and role guard dependencies.
- [backend/app/audit.py](backend/app/audit.py) owns history, sync log, and audit log helpers.

## Root Folder Structure

```txt
open-analytics/
  .gitignore
  README.md
  skill.md
  backend/
  docs/
  frontend/
  scripts/
```

Descriptions:

- `.gitignore`: excludes virtualenvs, `node_modules`, build output, logs, `.env`, and DuckDB files.
- [README.md](README.md): basic run instructions, URLs, admin login, and version notes.
- [skill.md](skill.md): project handoff and architecture guide for future work.
- [backend/](backend/): FastAPI backend, DuckDB setup, services, API routes, and scripts.
- [frontend/](frontend/): React/Vite frontend, reusable components, pages, routes, and API clients.
- [docs/](docs/): architecture, API, database, and UI notes.
- [scripts/](scripts/): helper batch scripts for install/start/backup workflows.

## Backend Structure

```txt
backend/
  requirements.txt
  run_backend.bat
  app/
    main.py
    instrument_sync.py
    config.py
    database.py
    dependencies.py
    security.py
    audit.py
    version.py
    api/v1/
    db/
    ml/
    schemas/
    services/
    utils/
```

### Backend Core Files

- [backend/requirements.txt](backend/requirements.txt): Python dependencies.
- [backend/run_backend.bat](backend/run_backend.bat): creates/uses backend venv, installs requirements, starts Uvicorn.
- [backend/app/main.py](backend/app/main.py): FastAPI app creation, CORS, startup database initialization, router registration.
- [backend/app/instrument_sync.py](backend/app/instrument_sync.py): standalone instrument sync CLI/script.
- [backend/app/config.py](backend/app/config.py): environment/settings loader; loads backend `.env`.
- [backend/app/database.py](backend/app/database.py): DuckDB path resolution, connection helper, schema/table creation, default admin setup.
- [backend/app/dependencies.py](backend/app/dependencies.py): JWT current-user dependency plus admin/super-admin guards.
- [backend/app/security.py](backend/app/security.py): password hashing, password verification, JWT creation.
- [backend/app/audit.py](backend/app/audit.py): writes user history, sync log, and audit log rows.
- [backend/app/version.py](backend/app/version.py): app and schema version constants.

### Backend API Routes

```txt
backend/app/api/v1/
  admin_routes.py
  auth_routes.py
  connection_routes.py
  data_collection_routes.py
  dashboard_routes.py
  prediction_routes.py
  stock_routes.py
  user_routes.py
```

- [admin_routes.py](backend/app/api/v1/admin_routes.py): admin-only user account endpoints.
- [auth_routes.py](backend/app/api/v1/auth_routes.py): register and login endpoints.
- [connection_routes.py](backend/app/api/v1/connection_routes.py): admin-only external provider connection endpoints.
- [data_collection_routes.py](backend/app/api/v1/data_collection_routes.py): admin-only data collection preview, sync, run history, cancellation, and scheduler endpoints.
- [dashboard_routes.py](backend/app/api/v1/dashboard_routes.py): placeholder for dashboard APIs.
- [prediction_routes.py](backend/app/api/v1/prediction_routes.py): placeholder for prediction APIs.
- [stock_routes.py](backend/app/api/v1/stock_routes.py): placeholder for stock APIs.
- [user_routes.py](backend/app/api/v1/user_routes.py): user profile, user CRUD, user history, sync log, and audit log endpoints.

Current important endpoints:

```txt
GET    /
GET    /health
POST   /api/v1/auth/register
POST   /api/v1/auth/login
GET    /api/v1/users/me
GET    /api/v1/admin/users
POST   /api/v1/admin/users
DELETE /api/v1/admin/users/{user_id}
GET    /api/v1/connections
POST   /api/v1/connections/upstox
POST   /api/v1/connections/upstox/test
DELETE /api/v1/connections/upstox
GET    /api/v1/data-collection/upstox/summary
GET    /api/v1/data-collection/upstox/runs
GET    /api/v1/data-collection/upstox/instruments
GET    /api/v1/data-collection/upstox/expired-instruments
GET    /api/v1/data-collection/upstox/equity-instruments
GET    /api/v1/data-collection/upstox/ohlcv-daily
GET    /api/v1/data-collection/upstox/equity-news
GET    /api/v1/data-collection/upstox/fundamentals
GET    /api/v1/data-collection/upstox/corporate-actions
GET    /api/v1/data-collection/upstox/fii-dii-activity
POST   /api/v1/data-collection/upstox/sync-current
POST   /api/v1/data-collection/upstox/sync-all
POST   /api/v1/data-collection/upstox/sync-expired-default
POST   /api/v1/data-collection/upstox/sync-equity
POST   /api/v1/data-collection/upstox/sync-ohlcv-daily
POST   /api/v1/data-collection/upstox/sync-equity-news
POST   /api/v1/data-collection/upstox/sync-fundamentals
POST   /api/v1/data-collection/upstox/sync-corporate-actions
POST   /api/v1/data-collection/upstox/sync-fii-dii-activity
GET    /api/v1/data-collection/upstox/schedules
POST   /api/v1/data-collection/upstox/schedules
```

### Backend Services

```txt
backend/app/services/
  admin_service.py
  audit_service.py
  auth_service.py
  connection_service.py
  data_collection_service.py
  data_collection_scheduler_service.py
  prediction_service.py
  stock_service.py
  user_service.py
```

- [admin_service.py](backend/app/services/admin_service.py): lists, creates, and deactivates users for admin screens.
- [auth_service.py](backend/app/services/auth_service.py): register/login logic and JWT issuance.
- [connection_service.py](backend/app/services/connection_service.py): stores, tests, lists, and disconnects external provider connections.
- [data_collection_service.py](backend/app/services/data_collection_service.py): data collection runners, preview queries, summary, run history, cancellation, and Upstox API helpers.
- [data_collection_scheduler_service.py](backend/app/services/data_collection_scheduler_service.py): data collection schedule CRUD and background scheduled execution.
- [audit_service.py](backend/app/services/audit_service.py): reserved for audit-specific service logic.
- [prediction_service.py](backend/app/services/prediction_service.py): reserved for prediction business logic.
- [stock_service.py](backend/app/services/stock_service.py): reserved for stock business logic.
- [user_service.py](backend/app/services/user_service.py): reserved for user-specific service logic.

### Backend Schemas

```txt
backend/app/schemas/
  admin_schema.py
  auth_schema.py
  connection_schema.py
  prediction_schema.py
  stock_schema.py
  user_schema.py
```

- [admin_schema.py](backend/app/schemas/admin_schema.py): admin user create/list response models.
- [auth_schema.py](backend/app/schemas/auth_schema.py): register/login/current auth response models.
- [connection_schema.py](backend/app/schemas/connection_schema.py): Upstox connection request and connection response models.
- [prediction_schema.py](backend/app/schemas/prediction_schema.py): placeholder for prediction request/response models.
- [stock_schema.py](backend/app/schemas/stock_schema.py): placeholder for stock request/response models.
- [user_schema.py](backend/app/schemas/user_schema.py): current-user response model.

### Backend Database And Scripts

```txt
backend/app/db/
  check_users.py
  init_db.py
  make_super_admin.py
  seed_data.py
  open_analytics.duckdb
```

- [check_users.py](backend/app/db/check_users.py): prints current users from the real DuckDB file.
- [init_db.py](backend/app/db/init_db.py): placeholder/manual database init script.
- [make_super_admin.py](backend/app/db/make_super_admin.py): promotes a selected user to `super_admin`.
- [seed_data.py](backend/app/db/seed_data.py): placeholder for seed data.
- [open_analytics.duckdb](backend/app/db/open_analytics.duckdb): local database file; ignored by Git.

### Backend ML And Utils

```txt
backend/app/ml/
  data_loader.py
  feature_engineering.py
  predict_model.py
  train_model.py
```

- [data_loader.py](backend/app/ml/data_loader.py): future data loading for ML.
- [feature_engineering.py](backend/app/ml/feature_engineering.py): future feature preparation.
- [predict_model.py](backend/app/ml/predict_model.py): future prediction runtime.
- [train_model.py](backend/app/ml/train_model.py): future model training.

```txt
backend/app/utils/
  logger.py
  password_utils.py
  response_utils.py
  token_utils.py
```

- Utility files are placeholders for reusable backend helpers.

## Frontend Structure

```txt
frontend/
  package.json
  package-lock.json
  run_frontend.bat
  tailwind.config.js
  vite.config.js
  src/
    main.jsx
    App.jsx
    index.css
    App.css
    api/
    assets/
    components/
    pages/
    routes/
    store/
    styles/
    utils/
```

### Frontend App Entry

- [frontend/package.json](frontend/package.json): npm scripts and frontend dependencies.
- [frontend/run_frontend.bat](frontend/run_frontend.bat): installs npm packages if needed and starts Vite.
- [frontend/tailwind.config.js](frontend/tailwind.config.js): Tailwind theme configuration.
- [frontend/vite.config.js](frontend/vite.config.js): Vite configuration.
- [frontend/src/main.jsx](frontend/src/main.jsx): React app mount point.
- [frontend/src/App.jsx](frontend/src/App.jsx): top-level route definitions.
- [frontend/src/index.css](frontend/src/index.css): Tailwind imports and base app styles.
- [frontend/src/App.css](frontend/src/App.css): app-specific CSS.

### Frontend API Clients

```txt
frontend/src/api/
  adminApi.js
  authApi.js
  axiosClient.js
  connectionApi.js
  dataCollectionApi.js
  predictionApi.js
  stockApi.js
```

- [axiosClient.js](frontend/src/api/axiosClient.js): Axios instance, base URL, auth token injection, 401/403 cleanup.
- [authApi.js](frontend/src/api/authApi.js): login, register, and current-user API calls.
- [adminApi.js](frontend/src/api/adminApi.js): admin user list/create/delete API calls.
- [connectionApi.js](frontend/src/api/connectionApi.js): list, save, test, and disconnect provider connection API calls.
- [dataCollectionApi.js](frontend/src/api/dataCollectionApi.js): data collection preview, sync, run history, cancellation, and schedule API calls.
- [predictionApi.js](frontend/src/api/predictionApi.js): placeholder for prediction API calls.
- [stockApi.js](frontend/src/api/stockApi.js): placeholder for stock API calls.

### Frontend Components

```txt
frontend/src/components/
  charts/
  common/
  layout/
  tables/
```

#### Charts

```txt
frontend/src/components/charts/
  PredictionChart.jsx
  StockChart.jsx
```

- Chart files are placeholders for future prediction/stock chart components.

#### Common Components

```txt
frontend/src/components/common/
  IconButton.jsx
  Input.jsx
  Loader.jsx
  Modal.jsx
  SearchBox.jsx
  Select.jsx
  Spinner.jsx
  ThemeToggle.jsx
  Tooltip.jsx
```

- [IconButton.jsx](frontend/src/components/common/IconButton.jsx): square icon button with tooltip and visual variants.
- [Input.jsx](frontend/src/components/common/Input.jsx): compact shared input style used by forms.
- [Select.jsx](frontend/src/components/common/Select.jsx): custom compact dropdown/select control.
- [Spinner.jsx](frontend/src/components/common/Spinner.jsx): shared loading spinner.
- [Tooltip.jsx](frontend/src/components/common/Tooltip.jsx): compact hover tooltip.
- [Loader.jsx](frontend/src/components/common/Loader.jsx): placeholder for page/section loader.
- [Modal.jsx](frontend/src/components/common/Modal.jsx): placeholder for modal dialog component.
- [SearchBox.jsx](frontend/src/components/common/SearchBox.jsx): shared toolbar/filter search control with compact focus styling.
- [ThemeToggle.jsx](frontend/src/components/common/ThemeToggle.jsx): placeholder for theme toggle.

#### Layout Components

```txt
frontend/src/components/layout/
  MainLayout.jsx
  Navbar.jsx
  PageHeader.jsx
  Sidebar.jsx
```

- [MainLayout.jsx](frontend/src/components/layout/MainLayout.jsx): current app shell, fixed left sidebar, navigation, logout.
- [Navbar.jsx](frontend/src/components/layout/Navbar.jsx): placeholder for top navigation.
- [PageHeader.jsx](frontend/src/components/layout/PageHeader.jsx): placeholder for reusable page header.
- [Sidebar.jsx](frontend/src/components/layout/Sidebar.jsx): placeholder for sidebar extraction if layout is split later.

#### Table Components

```txt
frontend/src/components/tables/
  DataTable.jsx
  DataTableHeaderFilter.jsx
  FilterSearchInput.jsx
  FilterSelect.jsx
  PredictionTable.jsx
  StockTable.jsx
  TableFilterDropdown.jsx
  TableToolbar.jsx
```

- [DataTable.jsx](frontend/src/components/tables/DataTable.jsx): reusable grid/table wrapper with loading, empty state, row rendering, action column, and header filters.
- [DataTableHeaderFilter.jsx](frontend/src/components/tables/DataTableHeaderFilter.jsx): header filter button plus portal-positioned filter dropdown.
- [TableFilterDropdown.jsx](frontend/src/components/tables/TableFilterDropdown.jsx): Excel-like filter dropdown with sort, text/color filter menu stubs, search, multi-select values, apply/cancel.
- [TableToolbar.jsx](frontend/src/components/tables/TableToolbar.jsx): search input, role/status filters, search button, clear filters, and right-side icon actions.
- [FilterSearchInput.jsx](frontend/src/components/tables/FilterSearchInput.jsx): compact toolbar search input with clear button.
- [FilterSelect.jsx](frontend/src/components/tables/FilterSelect.jsx): select wrapper with floating clear badge.
- [PredictionTable.jsx](frontend/src/components/tables/PredictionTable.jsx): placeholder for prediction table.
- [StockTable.jsx](frontend/src/components/tables/StockTable.jsx): placeholder for stock table.

### Frontend Pages

```txt
frontend/src/pages/
  admin/
  auth/
  dashboard/
  predictions/
  settings/
  stocks/
```

#### Admin Pages

```txt
frontend/src/pages/admin/
  AuditLogs.jsx
  Connections.jsx
  DataCollection.jsx
  UserAccounts.jsx
  UserManagement.jsx
```

- [UserAccounts.jsx](frontend/src/pages/admin/UserAccounts.jsx): admin user account screen; owns page state and uses reusable table/common components.
- [Connections.jsx](frontend/src/pages/admin/Connections.jsx): admin external connection screen for saving/testing Upstox credentials.
- [DataCollection.jsx](frontend/src/pages/admin/DataCollection.jsx): admin collection monitor, preview tabs, run buttons, schedule modal, and polling/timer UI.
- [AuditLogs.jsx](frontend/src/pages/admin/AuditLogs.jsx): placeholder for audit log screen.
- [UserManagement.jsx](frontend/src/pages/admin/UserManagement.jsx): placeholder for user management screen.

#### Auth Pages

```txt
frontend/src/pages/auth/
  ForgotPassword.jsx
  Login.jsx
  Register.jsx
  ResetPassword.jsx
```

- [Login.jsx](frontend/src/pages/auth/Login.jsx): current login screen; stores JWT token and login response.
- [ForgotPassword.jsx](frontend/src/pages/auth/ForgotPassword.jsx): placeholder.
- [Register.jsx](frontend/src/pages/auth/Register.jsx): placeholder.
- [ResetPassword.jsx](frontend/src/pages/auth/ResetPassword.jsx): placeholder.

#### Other Pages

```txt
frontend/src/pages/dashboard/Dashboard.jsx
frontend/src/pages/predictions/PredictionHome.jsx
frontend/src/pages/predictions/PredictionResult.jsx
frontend/src/pages/settings/ProfileSettings.jsx
frontend/src/pages/stocks/StockDetails.jsx
frontend/src/pages/stocks/StockList.jsx
```

- [Dashboard.jsx](frontend/src/pages/dashboard/Dashboard.jsx): current dashboard screen.
- Prediction, settings, and stock pages are placeholders for later workflows.

### Frontend Routes

```txt
frontend/src/routes/
  AdminRoute.jsx
  AppRoutes.jsx
  ProtectedRoute.jsx
```

- [ProtectedRoute.jsx](frontend/src/routes/ProtectedRoute.jsx): verifies token with `/users/me`, stores current user, redirects to login if invalid.
- [AdminRoute.jsx](frontend/src/routes/AdminRoute.jsx): allows only `admin` and `super_admin` users.
- [AppRoutes.jsx](frontend/src/routes/AppRoutes.jsx): placeholder for future route extraction.

### Frontend Store, Styles, Utils

```txt
frontend/src/store/
  authStore.js
  stockStore.js
  themeStore.js
```

- [Store files](frontend/src/store) are placeholders for app state if needed later.

```txt
frontend/src/styles/
  globals.css
  table.css
  theme.css
```

- [Style files](frontend/src/styles) are placeholders for extracted global/table/theme CSS.

```txt
frontend/src/utils/
  constants.js
  formatDate.js
  formatNumber.js
```

- [Utility files](frontend/src/utils) are placeholders for shared frontend constants and formatters.

## Admin Users

Current verified users in the real backend database:

```txt
admin@openanalytics.com       role=admin        active=True
superadmin@openanalytics.com  role=super_admin  active=True
sandeep@test.com              role=super_admin  active=False
sandeep2@test.com             role=user         active=False
```

Default admin login:

```txt
Email: admin@openanalytics.com
Password: admin123
```

The User Accounts menu appears only when the logged-in user role is:

```txt
admin
super_admin
```

Normal users are redirected away from `/admin/users`.

## UI Rules

- Keep the interface compact and professional.
- Use the existing dark theme.
- Keep visual look consistent when extracting reusable components.
- Use [frontend/src/components/common](frontend/src/components/common) for small shared controls.
- Use [frontend/src/components/tables](frontend/src/components/tables) for table, filter, and toolbar components.
- Use [frontend/src/components/layout](frontend/src/components/layout) for navigation and app shell.
- Sidebar stays fixed, minimized, and icon-only.
- App logo is only the `>` symbol using Lucide `ChevronRight`.
- Do not put the logo inside a pill, border, or box.
- Use `Spinner` for loading states.
- Use `Tooltip` for compact icon controls.

## Start Commands

Backend:

```bat
backend\run_backend.bat
```

Frontend:

```bat
frontend\run_frontend.bat
```

Full app:

```bat
scripts\start_all.bat
```

URLs:

```txt
Backend:      http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
Frontend:     http://localhost:5173
```

## Verification Commands

Compile backend:

```powershell
backend\venv\Scripts\python.exe -m py_compile backend\app\config.py backend\app\database.py backend\app\main.py backend\app\instrument_sync.py backend\app\services\admin_service.py backend\app\services\connection_service.py backend\app\services\data_collection_service.py backend\app\services\data_collection_scheduler_service.py backend\app\api\v1\admin_routes.py backend\app\api\v1\connection_routes.py backend\app\api\v1\data_collection_routes.py
```

Check users:

```powershell
backend\venv\Scripts\python.exe backend\app\db\check_users.py
```

Build frontend:

```powershell
cd frontend
npm run build
```

## Git Notes

Recent local commits:

```txt
1b602a0 Move reusable table components to tables folder
8a9cebb Extract user accounts UI to common components
8431088 user accounts table fixed
3fead09 Fix admin sidebar user accounts visibility
```

## Current Caveats / Next Work

- Do not use `backend/app/upstox`; the current project structure keeps data collection in [backend/app/services](backend/app/services).
- Add real external source/download logic for Equity News, Fundamentals, Corporate Actions, and FII/DII. Their runners and scheduler jobs already exist but currently leave preview data unchanged.
- Add Upstox OAuth/token refresh flow if live authenticated API calls need long-term refresh.
- Add admin user history screen from `users_history`.
- Add stronger frontend error display for 401/403 admin API failures.
- Add backend tests for admin user listing, DB path resolution, external connection save/list/disconnect, and data collection scheduler behavior.
