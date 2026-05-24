# Open Analytics Project Skill / Handoff

## Project

Open Analytics

Path:

```txt
C:\Projects\open-analytics
```

## Current Status

- FastAPI backend is in `backend/app`.
- React/Vite frontend is in `frontend/src`.
- DuckDB database is stored at `backend/app/db/open_analytics.duckdb`.
- Git version control has been initialized in the project root.
- `.gitignore` excludes virtualenvs, `node_modules`, build output, logs, `.env`, and DuckDB files.

## Latest Fix

Version: `1.0.2`

Admin sidebar visibility fix:

- `/api/v1/users/me` returns `{ status, user }`.
- `frontend/src/routes/ProtectedRoute.jsx` now stores `response.data.user || response.data`.
- `frontend/src/components/layout/MainLayout.jsx` and `frontend/src/routes/AdminRoute.jsx` fall back to `open_analytics_user` if `open_analytics_current_user` is missing.
- This fixes the missing User Accounts icon for `admin` and `super_admin` users.

Previous `1.0.1` fix:

Admin user accounts were not reliably appearing because the backend resolved `DUCKDB_PATH=app/db/open_analytics.duckdb` relative to the current working directory. If code was run from the project root, it opened or created:

```txt
C:\Projects\open-analytics\app\db\open_analytics.duckdb
```

instead of the real database:

```txt
C:\Projects\open-analytics\backend\app\db\open_analytics.duckdb
```

Fix applied:

- `backend/app/config.py` now loads `.env` from the backend folder.
- `backend/app/database.py` now resolves relative DuckDB paths from `backend/`.
- `backend/app/version.py` is now `APP_VERSION = "1.0.1"`.

## Admin Users

Current verified users in the real backend database:

```txt
admin@openanalytics.com   role=admin        active=True
sandeep@test.com          role=super_admin  active=True
sandeep2@test.com         role=user         active=True
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

## Backend

Stack:

```txt
FastAPI
DuckDB
JWT authentication
passlib bcrypt password hashing
python-jose
pydantic
pydantic-settings
uvicorn
```

Important files:

```txt
backend/app/main.py
backend/app/config.py
backend/app/database.py
backend/app/dependencies.py
backend/app/services/auth_service.py
backend/app/services/admin_service.py
backend/app/api/v1/auth_routes.py
backend/app/api/v1/user_routes.py
backend/app/api/v1/admin_routes.py
backend/app/schemas/admin_schema.py
backend/app/version.py
```

Admin APIs:

```txt
GET    /api/v1/admin/users
POST   /api/v1/admin/users
DELETE /api/v1/admin/users/{user_id}
```

General APIs:

```txt
GET  /
GET  /health
POST /api/v1/auth/register
POST /api/v1/auth/login
GET  /api/v1/users/me
GET  /api/v1/users/me/ping
```

## Frontend

Stack:

```txt
React
Vite
Tailwind CSS
Axios
React Router DOM
Lucide React icons
```

Important files:

```txt
frontend/src/App.jsx
frontend/src/api/axiosClient.js
frontend/src/api/adminApi.js
frontend/src/pages/auth/Login.jsx
frontend/src/pages/dashboard/Dashboard.jsx
frontend/src/pages/admin/UserAccounts.jsx
frontend/src/components/layout/MainLayout.jsx
frontend/src/routes/ProtectedRoute.jsx
frontend/src/routes/AdminRoute.jsx
```

Reusable common components currently present:

```txt
Button.jsx
Dropdown.jsx
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

## UI Rules

- Keep the interface compact and professional.
- Use the existing dark theme.
- Use reusable common components instead of duplicating styles.
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
start_all.bat
```

URLs:

```txt
Backend:      http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
Frontend:     http://localhost:5173
```

## Verification Commands

Compile backend files:

```powershell
backend\venv\Scripts\python.exe -m py_compile backend\app\config.py backend\app\database.py backend\app\services\admin_service.py backend\app\api\v1\admin_routes.py
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

## Next Work

- Add edit/update user account flow.
- Add admin user history screen from `users_history`.
- Add stronger frontend error display for 401/403 admin API failures.
- Add backend tests for admin user listing and DB path resolution.
