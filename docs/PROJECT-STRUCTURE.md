# Project Structure

This document describes the complete directory structure of the Rubik Analytics project.

## Root Directory Structure

```
rubik-analytics/
├── backend/              # FastAPI backend application
├── frontend/             # Next.js frontend application
├── server/               # Deployment and development scripts
├── docs/                 # Project documentation
├── data/                 # Runtime data (databases, logs)
└── .gitignore           # Git ignore rules
```

## Backend Structure

```
backend/
├── app/                  # Main application package
│   ├── __init__.py
│   ├── main.py          # FastAPI application entry point
│   │
│   ├── api/             # API route handlers
│   │   ├── __init__.py
│   │   └── v1/          # API version 1
│   │       ├── __init__.py
│   │       ├── auth.py          # Authentication endpoints
│   │       ├── users.py         # User management endpoints
│   │       ├── admin.py         # Admin operations endpoints
│   │       ├── connections.py   # Database connection management
│   │       └── symbols.py       # Symbols management endpoints
│   │
│   ├── core/            # Core functionality
│   │   ├── config.py           # Application configuration
│   │   ├── security.py         # JWT and password hashing
│   │   ├── permissions.py      # Authorization and role checks
│   │   ├── audit.py            # Audit logging
│   │   └── database/           # Database abstraction layer
│   │       ├── __init__.py
│   │       ├── base.py          # Base database client interface
│   │       ├── connection_manager.py  # Connection management
│   │       ├── router.py        # Database routing
│   │       ├── sqlite_client.py # SQLite implementation
│   │       ├── duckdb_client.py # DuckDB implementation
│   │       ├── duckdb_sqlalchemy_client.py  # DuckDB SQLAlchemy
│   │       ├── postgres_client.py # PostgreSQL implementation
│   │       └── api_client.py    # API-based client (future)
│   │
│   ├── models/          # SQLAlchemy database models
│   │   ├── __init__.py
│   │   ├── user.py              # User model
│   │   ├── access_request.py   # Access request model
│   │   ├── feature_request.py  # Feature request model
│   │   ├── feedback.py         # Feedback model
│   │   ├── session.py          # Session model
│   │   ├── symbol.py           # Symbol and SymbolUploadLog models
│   │   ├── script.py           # TransformationScript model
│   │   ├── scheduler.py        # ScheduledIngestion and IngestionSource models
│   │   └── connection.py       # Connection model
│   │
│   ├── schemas/         # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── auth.py             # Auth-related schemas
│   │   ├── user.py             # User-related schemas
│   │   ├── admin.py            # Admin-related schemas
│   │   ├── symbol.py           # Symbol-related schemas
│   │   └── connection.py       # Connection-related schemas
│   │
│   └── services/       # Business logic services
│       ├── __init__.py
│       └── ai_service.py       # AI/LLM integration (future)
│
├── scripts/             # Utility scripts
│   ├── init/                   # Initialization scripts
│   │   ├── init_auth_database.py      # Initialize auth database and tables
│   │   └── init_symbols_database.py   # Initialize symbols DuckDB database
│   ├── migrations/             # Schema migration scripts
│   │   ├── migrate_core_schema.py     # Core user schema migration
│   │   ├── migrate_accounts_schema.py # Accounts schema migration
│   │   └── migrate_symbols_schema.py  # Symbols schema migration
│   └── maintenance/            # Maintenance scripts
│       └── run_system_maintenance.py  # System maintenance utilities
│
├── venv/               # Python virtual environment (gitignored)
├── requirements.txt    # Python dependencies
└── .env               # Environment variables (gitignored)
```

### Key Backend Files

#### `app/main.py`
- FastAPI application initialization
- CORS middleware configuration
- Database connection startup
- Super user auto-recovery
- Route registration

#### `app/core/config.py`
- Application settings
- Database paths (`DATA_DIR` points to root `data/` folder)
- JWT configuration
- CORS origins

#### `app/core/security.py`
- JWT token creation/validation
- Password hashing/verification
- System token generation

#### `app/core/permissions.py`
- User authentication dependency
- Role-based authorization
- Super admin bypass logic

## Frontend Structure

```
frontend/
├── app/                # Next.js App Router
│   ├── layout.tsx      # Root layout
│   ├── page.tsx        # Home page
│   ├── globals.css     # Global styles
│   │
│   ├── login/         # Public routes
│   │   └── page.tsx
│   │
│   ├── forgot-password/
│   │   └── page.tsx
│   │
│   └── (main)/        # Authenticated routes (route group)
│       ├── layout.tsx # Main layout with sidebar
│       ├── dashboard/
│       │   └── page.tsx
│       ├── analytics/
│       │   └── page.tsx
│       ├── admin/     # Admin-only routes
│       │   ├── accounts/
│       │   │   └── page.tsx
│       │   ├── requests/
│       │   │   └── page.tsx
│       │   ├── connections/
│       │   │   └── page.tsx
│       │   └── symbols/
│       │       └── page.tsx
│       └── settings/
│           └── page.tsx
│
├── components/        # React components
│   ├── providers/
│   │   └── AuthProvider.tsx    # Auth context provider
│   │
│   ├── ui/            # Reusable UI components
│   │   ├── Button.tsx
│   │   ├── Input.tsx
│   │   ├── Card.tsx
│   │   ├── Table.tsx
│   │   └── ErrorMessage.tsx
│   │
│   └── ...            # Other components
│
├── lib/               # Utilities
│   ├── api.ts        # API client (Axios)
│   ├── store.ts      # Zustand store
│   └── error-utils.ts # Error handling
│
├── types/             # TypeScript types
│   └── index.ts
│
├── public/            # Static assets
├── package.json       # Node.js dependencies
└── .env.local        # Environment variables (gitignored)
```

## Server Scripts Structure

```
server/
├── windows/           # Windows batch scripts
│   ├── start-all.bat         # Start backend and frontend
│   ├── stop-all.bat          # Stop all services
│   ├── restart-all.bat       # Restart all services
│   ├── backend-setup.bat     # Backend environment setup
│   ├── frontend-setup.bat    # Frontend environment setup
│   ├── fix-super-user.bat    # Fix super user access
│   └── diagnose-users.bat    # Diagnose user accounts
│
└── docker/            # Docker deployment files
    ├── docker-compose.yml
    ├── backend.Dockerfile
    └── frontend.Dockerfile
```

## Data Structure

```
data/
├── auth/              # Authentication database
│   └── sqlite/
│       └── auth.db    # SQLite database file
│
├── analytics/         # Analytics databases
│   └── duckdb/
│       ├── ohlcv.duckdb
│       ├── indicators.duckdb
│       └── symbols.duckdb
│
├── connections/       # Connection configurations
│
├── logs/              # Application logs
│
└── backups/           # Database backups
```

**Important**: All runtime data must be stored in the root `data/` folder. The `backend/data/` folder (if it exists) is a duplicate and should be removed when database files are not locked.

## Documentation Structure

```
docs/
├── README.md              # Main documentation entry point
├── ARCHITECTURE.md        # System architecture
├── PROJECT-STRUCTURE.md   # This file
├── QUICK-START.md         # Setup and getting started
├── TROUBLESHOOTING.md     # Common issues and solutions
└── examples/              # Example files
    └── sample_symbols.csv
```

## Folder Rules

### Strict Enforcement

1. **Backend Files**: All Python files must be in `backend/` (either `app/` or `scripts/`)
2. **Frontend Files**: All frontend code must be in `frontend/`
3. **Data Files**: All runtime data must be in root `data/` folder only
4. **Documentation**: All `.md` files must be in `docs/` folder only
5. **Server Scripts**: All server/deployment scripts must be in `server/`

### File Organization Principles

- **One model per table**: Each database table has its own model file
- **One router per domain**: API routes grouped by functional domain
- **One schema per model**: Pydantic schemas mirror SQLAlchemy models
- **No circular imports**: Clean dependency flow
- **Consolidated scripts**: Utility scripts organized by purpose (init, migrations, maintenance)

## Key Conventions

### Python (Backend)

- **Models**: SQLAlchemy models in `app/models/`
- **Schemas**: Pydantic schemas in `app/schemas/`
- **API Routes**: FastAPI routers in `app/api/v1/`
- **Core Logic**: Configuration, security, permissions in `app/core/`
- **Scripts**: Utility scripts in `scripts/` organized by type

### TypeScript (Frontend)

- **Pages**: Next.js pages in `app/` using App Router
- **Components**: React components in `components/`
- **Utilities**: Helper functions in `lib/`
- **Types**: TypeScript types in `types/`

### Database

- **SQLite**: Authentication and user data (`data/auth/sqlite/`)
- **DuckDB**: Analytics and symbols data (`data/analytics/duckdb/`)
- **PostgreSQL**: Future production support

## Symbols CSV Format

When uploading symbols via CSV, use the following format:

### Required Columns

| Column Name | Alternative Names | Description | Example |
|------------|------------------|-------------|---------|
| `exchange` | `exch` | Stock exchange code | `NSE`, `BSE` |
| `trading_symbol` | `tradingsymbol`, `contract` | Full trading symbol | `RELIANCE-EQ`, `NIFTY23DECFUT` |

### Optional Columns

| Column Name | Description | Example |
|------------|-------------|---------|
| `name` | Full name of the symbol | `Reliance Industries` |
| `instrument_type` | Type of instrument | `EQ`, `FUT`, `OPT`, `INDEX` |
| `segment` | Market segment | `EQ`, `F&O` |
| `exchange_token` | Exchange-specific token ID | `12345` |
| `isin` | ISIN code | `INE002A01018` |
| `expiry_date` | Expiry date (YYYY-MM-DD) | `2023-12-28` |
| `strike_price` | Strike price for options | `19500` |
| `lot_size` | Lot size | `1`, `15`, `50` |

### Format Guidelines

1. **Header Row**: First row must contain column names
2. **Case Insensitive**: Column names are case-insensitive and spaces are normalized
3. **Date Format**: Use `YYYY-MM-DD` format for dates
4. **Numeric Values**: Use decimal numbers for prices and sizes

Sample file available at `docs/examples/sample_symbols.csv`.

## Related Documentation

- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture details
- [QUICK-START.md](./QUICK-START.md) - Getting started guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues
