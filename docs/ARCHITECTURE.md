# System Architecture

## Overview

Rubik Analytics follows a **modern three-tier architecture** with clear separation between presentation, business logic, and data layers. The system is designed for scalability, maintainability, and security.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Next.js 14 Frontend (React + TypeScript)             │   │
│  │  - Pages (App Router)                                │   │
│  │  - Components (UI, Business Logic)                   │   │
│  │  - State Management (Zustand)                         │   │
│  │  - API Client (Axios)                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                    HTTP/REST API
                            │
┌─────────────────────────────────────────────────────────────┐
│                    API LAYER                                │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  FastAPI Backend                                      │   │
│  │  - Authentication (JWT)                               │   │
│  │  - Authorization (Role-Based)                          │   │
│  │  - Business Logic                                     │   │
│  │  - Request Validation (Pydantic)                      │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                            │
                    Database Abstraction
                            │
┌─────────────────────────────────────────────────────────────┐
│                    DATA LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   SQLite     │  │    DuckDB    │  │  PostgreSQL  │     │
│  │  (Auth/Users)│  │  (Analytics) │  │   (Future)    │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
│  Connection Manager + Database Router                        │
└─────────────────────────────────────────────────────────────┘
```

## Component Architecture

### Frontend Architecture

#### Next.js App Router Structure
- **Route Groups**: `(main)` for authenticated routes
- **Layout System**: Nested layouts for consistent UI
- **Server/Client Components**: Optimal rendering strategy
- **API Routes**: Not used (external FastAPI backend)

#### State Management
- **Zustand Store**: Global application state
- **React Context**: AuthProvider for authentication state
- **Local State**: Component-level state with React hooks
- **Server State**: Managed via Axios interceptors

#### Component Hierarchy
```
App Layout
├── AuthProvider (Context)
├── Main Layout
│   ├── Sidebar (Navigation)
│   ├── TopSubNav (Breadcrumbs)
│   └── Page Content
│       ├── Dashboard
│       ├── Analytics
│       ├── Admin Panel
│       └── Settings
```

#### Theme System
- **Dark/Light Themes**: User preference stored in database
- **Theme Persistence**: Stored in user profile (`theme_preference` field)
- **Tailwind Dark Mode**: Uses CSS variables and `dark:` classes
- **Default Theme**: Dark theme

### Backend Architecture

#### FastAPI Application Structure
```
app/
├── main.py              # Application entry point
├── api/v1/              # API version 1 routes
│   ├── auth.py          # Authentication endpoints
│   ├── users.py         # User management
│   ├── admin.py         # Admin operations
│   ├── connections.py   # Database connections
│   └── symbols.py       # Symbols management
├── core/                # Core functionality
│   ├── config.py        # Configuration
│   ├── security.py      # JWT & password hashing
│   ├── permissions.py   # Authorization
│   ├── audit.py         # Audit logging
│   └── database/        # Database abstraction
├── models/              # SQLAlchemy models
├── schemas/             # Pydantic schemas
└── services/            # Business logic services
```

#### Request Flow
1. **Client Request** → Axios interceptor adds JWT token
2. **FastAPI Middleware** → CORS, request validation
3. **Route Handler** → Dependency injection (auth, DB)
4. **Permission Check** → Role-based authorization
5. **Business Logic** → Service layer processing
6. **Database Access** → Connection manager routes query
7. **Response** → Pydantic schema validation
8. **Client** → Response handling with error management

## Authentication & Security

### Authentication System

Rubik Analytics uses **JWT (JSON Web Tokens)** for stateless authentication with multi-identifier login support.

#### Authentication Flow
```
1. User submits credentials (identifier + password)
   ↓
2. Backend validates identifier (username/email/mobile/user_id)
   ↓
3. Password verified against bcrypt hash
   ↓
4. User status checked (is_active, role)
   ↓
5. JWT token generated with user claims
   ↓
6. Token returned to client
   ↓
7. Client stores token in HTTP-only cookie
   ↓
8. Subsequent requests include token in Authorization header
```

#### Multi-Identifier Login
The system supports login with any of the following:
- **Username** (case-insensitive)
- **Email** (case-insensitive)
- **Mobile Number**
- **User ID** (UUID)

#### JWT Token Structure
- **sub**: Username (subject)
- **exp**: Expiration timestamp (8 hours default)
- **iat**: Issued at timestamp

#### Security Measures
- **Password Hashing**: bcrypt with salt (10 rounds)
- **Token Expiration**: 8 hours (configurable)
- **Idle Timeout**: 30 minutes (configurable)
- **CORS Configuration**: Restricted to allowed origins
- **Input Validation**: Pydantic schemas for all requests

### Critical Security Items

⚠️ **Must Change Before Production:**
1. **JWT Secret Keys** - Generate strong, random secrets
2. **Default Admin Password** - Change from `admin123` immediately
3. **CORS Configuration** - Restrict to production domain
4. **Enable HTTPS** - Required for production

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for security-related issues.

## Database Architecture

### Multi-Database Architecture

Rubik Analytics uses a **multi-database architecture** with dynamic connection management.

#### SQLite (Authentication Database)
- **Purpose**: User authentication, accounts, requests, feedback
- **Location**: `data/auth/sqlite/auth.db`
- **Use Cases**: User accounts, access requests, feature requests, feedback, sessions
- **Characteristics**: File-based, ACID compliant, embedded database

#### DuckDB (Analytics Database)
- **Purpose**: Analytical data, time-series data, large datasets
- **Location**: `data/analytics/duckdb/`
- **Databases**: `symbols.duckdb` for symbol data
- **Characteristics**: Columnar storage, optimized for analytics, fast aggregations, embedded

#### PostgreSQL (Future)
- **Purpose**: Production-grade relational database
- **Planned Use Cases**: Production deployments, high availability, replication

### Database Models

#### User Model
- **id**: Integer (Primary Key)
- **user_id**: String (UUID, Unique, Immutable)
- **username**: String (Unique, Required, Indexed)
- **name**: String (Optional)
- **email**: String (Unique, Optional, Indexed)
- **mobile**: String (Required, Indexed)
- **hashed_password**: String (Required)
- **role**: String (Default: "user") - user, admin, super_admin
- **is_active**: Boolean (Default: True)
- **theme_preference**: String (Default: "dark")
- **last_active_at**: DateTime (Optional) - For live status tracking
- **created_at**: DateTime
- **updated_at**: DateTime

#### AccessRequest Model
- **id**: Integer (Primary Key)
- **name**: String (Required)
- **email**: String (Optional)
- **mobile**: String (Required)
- **company**: String (Optional)
- **reason**: Text (Required)
- **requested_role**: String (Default: "user")
- **status**: String (Default: "pending") - pending, approved, rejected
- **created_at**: DateTime
- **updated_at**: DateTime
- **reviewed_by**: Integer (Foreign Key to User)
- **reviewed_at**: DateTime (Optional)

### Database Connection Management

- **ConnectionManager**: Manages database connections
- **DatabaseRouter**: Routes queries to appropriate database
- **DatabaseClient**: Interface for database operations
- **Connection Pooling**: Efficient connection reuse

## User Management System

### Core Principles

1. **Single Source of Truth**: Accounts table is the ONLY source of truth for active users
2. **User ID System**: Every user has a unique, immutable UUID
3. **No Public Signup**: All access must be requested via Access Request form

### User Request Flow

```
1. User submits Access Request (Contact Admin)
   ↓
2. Request stored with status "pending"
   ↓
3. Admin reviews request
   ↓
4a. APPROVE → Create User Account → User can login
4b. REJECT → No account created → Request marked rejected
```

### Account Lifecycle

```
1. Account Creation (via approval or manual creation)
   ↓
2. Account Activation (is_active = true)
   ↓
3. User Login & Usage (updates last_active_at)
   ↓
4. Account Updates (profile, password, theme)
   ↓
5. Account Deactivation (optional, admin only)
   ↓
6. Account Reactivation (admin only)
```

### Live Status Tracking

- **Online**: `last_active_at` within last 5 minutes
- **Offline**: `last_active_at` older than 5 minutes, or null
- Updated on: Login, API calls, ping endpoint

## Authorization & Permissions

### Role-Based Access Control (RBAC)

Three primary roles with hierarchical permissions:

#### Super Admin (`super_admin`)
- **Capabilities**: Full system access
- **Protections**: Cannot be deactivated, cannot have role changed, auto-reactivated if deactivated
- **Bypasses**: All `is_active` checks
- **Use Cases**: Initial system setup, emergency access, system administration

#### Admin (`admin`)
- **Capabilities**: User and system management, can approve/reject requests, can create/manage accounts
- **Limitations**: Cannot modify Super Admin
- **Use Cases**: User management, system configuration

#### User (`user`)
- **Capabilities**: Standard access, can submit access requests, can update own profile
- **Limitations**: Limited permissions, cannot access admin endpoints
- **Use Cases**: Standard application usage

### Permission Enforcement

- **API Level**: All rules enforced at API level via dependency injection
- **Permission Checks**: Via `require_roles()`, `get_admin_user()`, `get_super_admin()` decorators
- **Super Admin Bypass**: Logic in place to bypass restrictions for super_admin
- **Role Validation**: On every request

## Design Patterns

### Dependency Injection
FastAPI's dependency injection system is used extensively:
- `get_current_user()` - Authenticates and returns current user
- `get_db()` - Provides database session
- `require_roles()` - Enforces role-based access

### Repository Pattern
Database access is abstracted through ConnectionManager and DatabaseRouter.

### Strategy Pattern
Different database types implement the same `DatabaseClient` interface, allowing dynamic switching.

## API Design

### Base URL
```
http://localhost:8000/api/v1
```

### Authentication
Most endpoints require JWT token in Authorization header:
```
Authorization: Bearer <token>
```

### Response Format
- **Success**: `{"data": {...}}`
- **Error**: `{"detail": "Error message"}`

### Key Endpoints

#### Authentication
- `POST /api/v1/auth/login` - Login with identifier and password
- `POST /api/v1/auth/logout` - Logout current user
- `POST /api/v1/auth/refresh` - Refresh access token

#### User Management
- `GET /api/v1/users/me` - Get current user
- `PUT /api/v1/users/me` - Update profile
- `POST /api/v1/users/me/ping` - Update activity status

#### Admin Operations
- `GET /api/v1/admin/users` - List all users
- `POST /api/v1/admin/users` - Create user account
- `PUT /api/v1/admin/users/{id}` - Update user
- `GET /api/v1/admin/requests` - List access requests
- `POST /api/v1/admin/requests/{id}/approve` - Approve request
- `POST /api/v1/admin/requests/{id}/reject` - Reject request

See http://localhost:8000/docs for complete API documentation.

## Technology Choices

### Why FastAPI?
- **Performance**: One of the fastest Python frameworks
- **Type Safety**: Pydantic validation
- **Async Support**: Native async/await
- **Auto Documentation**: OpenAPI/Swagger generation

### Why Next.js 14?
- **App Router**: Modern routing system
- **Server Components**: Optimal performance
- **TypeScript**: Type safety
- **React 18**: Latest React features

### Why SQLAlchemy?
- **ORM Benefits**: Type-safe queries
- **Database Agnostic**: Easy database switching
- **Connection Pooling**: Built-in support

### Why DuckDB?
- **Analytics Focus**: Optimized for analytical queries
- **Embedded**: No separate server needed
- **Performance**: Fast columnar operations

## Scalability Considerations

### Horizontal Scaling
- **Stateless Backend**: JWT allows load balancing
- **Database Connections**: Connection pooling via SQLAlchemy

### Vertical Scaling
- **Async Operations**: FastAPI async/await
- **Connection Pooling**: Efficient database connection reuse

### Database Scaling
- **Analytics Separation**: DuckDB for analytics, SQLite for auth
- **Connection Routing**: Dynamic connection switching

## Related Documentation

- [PROJECT-STRUCTURE.md](./PROJECT-STRUCTURE.md) - Detailed file organization
- [QUICK-START.md](./QUICK-START.md) - Setup and getting started
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions

