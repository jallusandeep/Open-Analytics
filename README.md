# Open Analytics

FastAPI + React analytics application with JWT authentication, DuckDB storage,
and admin user account management.

## Run

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

## URLs

```txt
Backend:      http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
Frontend:     http://localhost:5173
```

## Admin Login

```txt
Email: admin@openanalytics.com
Password: admin123
```

The User Accounts screen is available at:

```txt
/admin/users
```

It is visible only for users with `admin` or `super_admin` role.

## Version

Current app version: `1.0.1`

The `1.0.1` update fixes DuckDB path resolution so the backend always uses
`backend/app/db/open_analytics.duckdb`, even when commands are launched from the
project root.
