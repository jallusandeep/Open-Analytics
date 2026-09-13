# Open Analytics

FastAPI + React analytics application with JWT authentication, DuckDB storage,
Upstox connections, and admin data collection.

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
scripts\start_all.bat
```

## URLs

```txt
Backend:      http://127.0.0.1:8000
Swagger Docs: http://127.0.0.1:8000/docs
Frontend:     http://localhost:5173
```

## Project structure

```text
open-analytics/
├── backend/
│   ├── app/
│   │   ├── api/v1/                 # FastAPI routes
│   │   ├── services/
│   │   │   ├── connections/        # Upstox connection and token logic
│   │   │   └── data_collection/    # Collection, preview, and sync logic
│   │   ├── db/                     # Database helpers and local DuckDB file
│   │   ├── schemas/                # Request and response models
│   │   ├── telegram_alerts_msg/    # Telegram notification helpers
│   │   ├── config.py               # Backend settings
│   │   ├── database.py             # DuckDB schema and connection
│   │   └── main.py                 # FastAPI app and router registration
│   ├── requirements.txt
│   └── run_backend.bat
├── frontend/
│   ├── public/                     # Static browser assets
│   ├── src/
│   │   ├── api/                    # HTTP client and API calls
│   │   ├── components/             # Shared UI components
│   │   ├── pages/                  # Dashboard, admin, auth, settings
│   │   ├── routes/                 # Route access guards
│   │   ├── App.jsx                 # Application routes
│   │   └── main.jsx                # React entry point
│   ├── package.json
│   └── run_frontend.bat
├── docs/                          # Architecture and deployment notes
├── Research/                      # Notes for future research work
├── scripts/                       # Local startup script
├── server/docker/                 # Container and compose files
└── README.md
```

Local environments (`venv/`, `node_modules/`), generated files (`dist/`, logs),
and the DuckDB database are not source files and are excluded from this tree.
