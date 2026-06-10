import uuid
import time
import threading
import duckdb
from pathlib import Path
from passlib.context import CryptContext

from app.config import settings
from app.version import APP_VERSION, SCHEMA_VERSION


APP_ROOT = Path(__file__).resolve().parent
BACKEND_ROOT = APP_ROOT.parent
DB_PATH = Path(settings.DUCKDB_PATH)

if not DB_PATH.is_absolute():
    # Supports both:
    #   DUCKDB_PATH=app/db/open_analytics.duckdb
    #   DUCKDB_PATH=db/open_analytics.duckdb
    # and resolves both to the real backend/app database area.
    if DB_PATH.parts and DB_PATH.parts[0] == "app":
        DB_PATH = BACKEND_ROOT / DB_PATH
    else:
        DB_PATH = APP_ROOT / DB_PATH

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_CONNECT_RETRY_ATTEMPTS = 60
DB_CONNECT_RETRY_DELAY_SECONDS = 0.5
DB_CONNECT_LOCK = threading.Lock()


def is_transient_duckdb_lock_error(error: Exception) -> bool:
    message = str(error).lower()

    return (
        (
            "cannot open file" in message
            and (
                "being used by another process" in message
                or "file is already open" in message
            )
        )
        or (
            "unique file handle conflict" in message
            and "already attached" in message
        )
        or (
            "failed to delete file" in message
            and ".wal" in message
            and "access is denied" in message
        )
    )


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(DB_CONNECT_RETRY_ATTEMPTS):
        try:
            with DB_CONNECT_LOCK:
                return duckdb.connect(str(DB_PATH))
        except (duckdb.IOException, duckdb.BinderException) as error:
            is_last_attempt = attempt == DB_CONNECT_RETRY_ATTEMPTS - 1

            if is_last_attempt or not is_transient_duckdb_lock_error(error):
                raise

            time.sleep(DB_CONNECT_RETRY_DELAY_SECONDS)


def get_read_only_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(DB_CONNECT_RETRY_ATTEMPTS):
        try:
            with DB_CONNECT_LOCK:
                return duckdb.connect(str(DB_PATH), read_only=True)
        except (duckdb.IOException, duckdb.BinderException) as error:
            is_last_attempt = attempt == DB_CONNECT_RETRY_ATTEMPTS - 1

            if is_last_attempt or not is_transient_duckdb_lock_error(error):
                raise

            time.sleep(DB_CONNECT_RETRY_DELAY_SECONDS)


DB_SCHEMA_STATS = {
    "already_exists": 0,
    "skipped": 0
}


def reset_db_schema_stats():
    DB_SCHEMA_STATS["already_exists"] = 0
    DB_SCHEMA_STATS["skipped"] = 0


def is_expected_schema_skip(error: Exception) -> bool:
    message = str(error).lower()

    return (
        "already exists" in message
        or "duplicate column" in message
        or (
            "column with name" in message
            and "already exists" in message
        )
        or (
            "index with name" in message
            and "already exists" in message
        )
    )


def safe_execute(conn, query: str):
    try:
        conn.execute(query)
    except Exception as e:
        if is_expected_schema_skip(e):
            DB_SCHEMA_STATS["already_exists"] += 1
        else:
            DB_SCHEMA_STATS["skipped"] += 1

        try:
            conn.rollback()
        except Exception:
            pass


def migrate_fii_dii_activity_table(conn):
    try:
        columns = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'fii_dii_activity';
        """).fetchall()
    except Exception:
        return

    column_names = {row[0] for row in columns}

    if not column_names or "data_type" not in column_names:
        return

    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fii_dii_activity_v2 (
                date DATE NOT NULL,
                category VARCHAR NOT NULL,
                data_type VARCHAR NOT NULL DEFAULT 'NSE_EQ|CASH',
                buy_value DOUBLE,
                sell_value DOUBLE,
                net_value DOUBLE,
                buy_contracts BIGINT DEFAULT 0,
                sell_contracts BIGINT DEFAULT 0,
                oi_contracts BIGINT DEFAULT 0,
                oi_amount DOUBLE DEFAULT 0,
                raw_json JSON,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, category, data_type)
            );
        """)

        conn.execute("""
            INSERT OR REPLACE INTO fii_dii_activity_v2 (
                date,
                category,
                data_type,
                buy_value,
                sell_value,
                net_value,
                buy_contracts,
                sell_contracts,
                oi_contracts,
                oi_amount,
                raw_json,
                ingested_at
            )
            SELECT
                date,
                category,
                COALESCE(data_type, 'NSE_EQ|CASH'),
                buy_value,
                sell_value,
                net_value,
                COALESCE(buy_contracts, 0),
                COALESCE(sell_contracts, 0),
                COALESCE(oi_contracts, 0),
                COALESCE(oi_amount, 0),
                raw_json,
                COALESCE(ingested_at, CURRENT_TIMESTAMP)
            FROM fii_dii_activity;
        """)

        conn.execute("DROP TABLE fii_dii_activity;")
        conn.execute("ALTER TABLE fii_dii_activity_v2 RENAME TO fii_dii_activity;")
        conn.commit()
    except Exception as e:
        print("Skipped FII/DII activity table migration.")
        print(f"Reason: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def init_database():
    conn = get_connection()
    reset_db_schema_stats()

    try:
        print("[DB] Schema check started.")
        # -----------------------------
        # App metadata / version table
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        conn.execute("""
            INSERT OR REPLACE INTO app_metadata (key, value, updated_at)
            VALUES
            ('app_version', ?, CURRENT_TIMESTAMP),
            ('schema_version', ?, CURRENT_TIMESTAMP);
        """, [APP_VERSION, str(SCHEMA_VERSION)])

        # -----------------------------
        # Users table
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id VARCHAR PRIMARY KEY,
                login_id VARCHAR,
                full_name VARCHAR NOT NULL,
                email VARCHAR UNIQUE NOT NULL,
                mobile_number VARCHAR,
                password_hash VARCHAR NOT NULL,
                role VARCHAR DEFAULT 'user',
                access_restrictions JSON,
                is_active BOOLEAN DEFAULT TRUE,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE users ADD COLUMN login_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN mobile_number VARCHAR;")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN access_restrictions JSON;")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE users ADD COLUMN updated_by VARCHAR;")

        conn.execute("""
            UPDATE users
            SET login_id = split_part(email, '@', 1)
            WHERE login_id IS NULL;
        """)

        conn.execute("""
            UPDATE users
            SET record_status = 'S'
            WHERE record_status IS NULL;
        """)

        conn.execute("""
            UPDATE users
            SET version_no = 1
            WHERE version_no IS NULL;
        """)

        # -----------------------------
        # Default super admin user
        # -----------------------------
        super_admin_email = "jallusandeep0902@gmail.com"
        super_admin_password = "1234"
        super_admin_mobile_number = "8686504620"

        existing_super_admin = conn.execute("""
            SELECT user_id
            FROM users
            WHERE email = ?;
        """, [super_admin_email]).fetchone()

        if not existing_super_admin:
            super_admin_user_id = str(uuid.uuid4())
            super_admin_password_hash = pwd_context.hash(super_admin_password)

            conn.execute("""
                INSERT INTO users (
                    user_id,
                    login_id,
                    full_name,
                    email,
                    mobile_number,
                    password_hash,
                    role,
                    access_restrictions,
                    is_active,
                    record_status,
                    version_no,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                super_admin_user_id,
                "jallusandeep0902",
                "Sandeep Jallu",
                super_admin_email,
                super_admin_mobile_number,
                super_admin_password_hash,
                "super_admin",
                None,
                True,
                "S",
                1,
                "system",
                "system"
            ])

            pass
        else:
            conn.execute("""
                UPDATE users
                SET
                    login_id = CASE
                        WHEN login_id IS NULL OR login_id = '' THEN 'jallusandeep0902'
                        ELSE login_id
                    END,
                    full_name = CASE
                        WHEN full_name IS NULL OR TRIM(full_name) = '' THEN 'Sandeep Jallu'
                        ELSE full_name
                    END,
                    mobile_number = CASE
                        WHEN mobile_number IS NULL OR TRIM(mobile_number) = '' THEN ?
                        ELSE mobile_number
                    END,
                    role = 'super_admin',
                    is_active = TRUE,
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system'
                WHERE email = ?;
            """, [super_admin_mobile_number, super_admin_email])

            pass

        # -----------------------------
        # Users history table
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users_history (
                history_id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                login_id VARCHAR,
                full_name VARCHAR,
                email VARCHAR,
                mobile_number VARCHAR,
                role VARCHAR,
                access_restrictions JSON,
                is_active BOOLEAN,
                record_status VARCHAR DEFAULT 'H',
                action_type VARCHAR,
                version_no INTEGER,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changed_by VARCHAR
            );
        """)

        # -----------------------------
        # User sessions
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                session_id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                access_token VARCHAR NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                logged_out_at TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE user_sessions ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE user_sessions ADD COLUMN last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE user_sessions ADD COLUMN logged_out_at TIMESTAMP;")

        conn.execute("""
            UPDATE user_sessions
            SET is_active = TRUE
            WHERE is_active IS NULL;
        """)

        conn.execute("""
            UPDATE user_sessions
            SET last_seen_at = COALESCE(last_seen_at, created_at, CURRENT_TIMESTAMP)
            WHERE last_seen_at IS NULL;
        """)

        # -----------------------------
        # Password reset tokens
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS password_reset_tokens (
                reset_id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                reset_token VARCHAR NOT NULL,
                is_used BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
        """)

        # -----------------------------
        # Audit logs
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id VARCHAR PRIMARY KEY,
                user_id VARCHAR,
                action VARCHAR NOT NULL,
                table_name VARCHAR,
                record_id VARCHAR,
                old_value JSON,
                new_value JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # -----------------------------
        # External connections
        # Global admin-level provider credentials.
        # Telegram bot token is stored here globally.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS external_connections (
                connection_id VARCHAR PRIMARY KEY,
                provider VARCHAR UNIQUE NOT NULL,
                api_key VARCHAR,
                api_secret VARCHAR,
                redirect_url VARCHAR,
                analytical_token VARCHAR,
                analytical_token_updated_at TIMESTAMP,
                access_token VARCHAR,
                refresh_token VARCHAR,
                token_type VARCHAR,
                access_token_expires_at TIMESTAMP,
                token_updated_at TIMESTAMP,
                connection_status VARCHAR DEFAULT 'saved',
                last_tested_at TIMESTAMP,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN api_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN api_secret VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN redirect_url VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN analytical_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN analytical_token_updated_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN access_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN refresh_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN token_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN access_token_expires_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN token_updated_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN connection_status VARCHAR DEFAULT 'saved';")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN last_tested_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN updated_by VARCHAR;")

        conn.execute("""
            UPDATE external_connections
            SET analytical_token_updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)
            WHERE analytical_token IS NOT NULL
              AND TRIM(analytical_token) <> ''
              AND analytical_token_updated_at IS NULL;
        """)

        # -----------------------------
        # User Telegram connections
        # User-level Telegram chat links.
        # Admin configures the bot globally in external_connections.
        # Each user connects their own Telegram account from Settings.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS user_telegram_connections (
                telegram_connection_id VARCHAR PRIMARY KEY,
                user_id VARCHAR UNIQUE NOT NULL,
                telegram_chat_id VARCHAR,
                telegram_username VARCHAR,
                telegram_first_name VARCHAR,
                telegram_last_name VARCHAR,
                link_token VARCHAR UNIQUE NOT NULL,
                connection_status VARCHAR DEFAULT 'pending',
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN telegram_chat_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN telegram_username VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN telegram_first_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN telegram_last_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN link_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN connection_status VARCHAR DEFAULT 'pending';")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE user_telegram_connections ADD COLUMN updated_by VARCHAR;")

        conn.execute("""
            UPDATE user_telegram_connections
            SET record_status = 'S'
            WHERE record_status IS NULL;
        """)

        conn.execute("""
            UPDATE user_telegram_connections
            SET connection_status = CASE
                WHEN telegram_chat_id IS NOT NULL AND telegram_chat_id <> '' THEN 'connected'
                ELSE 'pending'
            END
            WHERE connection_status IS NULL;
        """)

        conn.execute("""
            UPDATE user_telegram_connections
            SET version_no = 1
            WHERE version_no IS NULL;
        """)

        # -----------------------------
        # Upstox instruments
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_instruments (
                instrument_key VARCHAR,
                source_type VARCHAR,
                segment VARCHAR,
                name VARCHAR,
                exchange VARCHAR,
                isin VARCHAR,
                instrument_type VARCHAR,
                trading_symbol VARCHAR,
                short_name VARCHAR,
                exchange_token VARCHAR,
                expiry DATE,
                strike_price DOUBLE,
                lot_size BIGINT,
                minimum_lot BIGINT,
                freeze_quantity DOUBLE,
                tick_size DOUBLE,
                weekly BOOLEAN,
                underlying_key VARCHAR,
                underlying_symbol VARCHAR,
                underlying_type VARCHAR,
                security_type VARCHAR,
                raw_json JSON,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN source_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN segment VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN exchange VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN instrument_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN short_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN exchange_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN expiry DATE;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN strike_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN lot_size BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN minimum_lot BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN freeze_quantity DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN tick_size DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN weekly BOOLEAN;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN underlying_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN security_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_instruments ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Upstox expired instruments
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_expired_instruments (
                instrument_key VARCHAR,
                segment VARCHAR,
                name VARCHAR,
                exchange VARCHAR,
                instrument_type VARCHAR,
                trading_symbol VARCHAR,
                exchange_token VARCHAR,
                expiry DATE,
                strike_price DOUBLE,
                lot_size BIGINT,
                minimum_lot BIGINT,
                freeze_quantity DOUBLE,
                tick_size DOUBLE,
                weekly BOOLEAN,
                underlying_key VARCHAR,
                underlying_symbol VARCHAR,
                underlying_type VARCHAR,
                source_type VARCHAR,
                raw_json JSON,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN segment VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN exchange VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN instrument_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN exchange_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN expiry DATE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN strike_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN lot_size BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN minimum_lot BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN freeze_quantity DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN tick_size DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN weekly BOOLEAN;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN underlying_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN source_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_expired_instruments ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_expired_contract_sync_status (
                underlying_key VARCHAR,
                expiry DATE,
                source_type VARCHAR,
                status VARCHAR DEFAULT 'success',
                record_count BIGINT DEFAULT 0,
                last_error VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN underlying_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN expiry DATE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN source_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN last_error VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_contract_sync_status ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_expired_underlying_sync_status (
                underlying_key VARCHAR,
                status VARCHAR DEFAULT 'success',
                expiry_count BIGINT DEFAULT 0,
                record_count BIGINT DEFAULT 0,
                include_options BOOLEAN DEFAULT TRUE,
                include_futures BOOLEAN DEFAULT TRUE,
                last_error VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN underlying_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN expiry_count BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN include_options BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN include_futures BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN last_error VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_expired_underlying_sync_status ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Upstox equity instruments
        # Daily NSE_EQ equity collection table.
        # instrument_key is the Upstox API key used for all future API calls.
        # downloaded_at is refreshed only when the daily equity dump runs.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_equity_instruments (
                instrument_key VARCHAR PRIMARY KEY,
                trading_symbol VARCHAR,
                name VARCHAR,
                isin VARCHAR,
                exchange VARCHAR DEFAULT 'NSE',
                segment VARCHAR DEFAULT 'NSE_EQ',
                exchange_token VARCHAR,
                tick_size DOUBLE,
                lot_size BIGINT,
                freeze_quantity DOUBLE,
                short_name VARCHAR,
                security_type VARCHAR,
                downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN exchange VARCHAR DEFAULT 'NSE';")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN segment VARCHAR DEFAULT 'NSE_EQ';")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN exchange_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN tick_size DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN lot_size BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN freeze_quantity DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN short_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN security_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_equity_instruments ADD COLUMN downloaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Upstox sync runs
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_sync_runs (
                sync_id VARCHAR PRIMARY KEY,
                sync_type VARCHAR NOT NULL,
                status VARCHAR DEFAULT 'running',
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                finished_at TIMESTAMP,
                duration_seconds BIGINT,
                message VARCHAR,
                total_records BIGINT DEFAULT 0,
                trigger_source VARCHAR DEFAULT 'manual',
                triggered_by_id VARCHAR,
                triggered_by_name VARCHAR,
                triggered_by_role VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN sync_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN status VARCHAR DEFAULT 'running';")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN finished_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN duration_seconds BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN message VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN total_records BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN trigger_source VARCHAR DEFAULT 'manual';")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN triggered_by_role VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN request_options JSON;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_sources JSON;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_candle_modes JSON;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN selected_intervals JSON;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN from_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN to_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN skip_existing BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN respect_api_limits BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN retry_failed BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN instrument_limit BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN single_instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN batch_size BIGINT DEFAULT 25;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN request_delay_ms BIGINT DEFAULT 500;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN batch_delay_seconds BIGINT DEFAULT 2;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN api_calls_attempted BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN api_calls_skipped BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN candles_inserted BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN candles_skipped BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN failed_instruments BIGINT DEFAULT 0;")

        conn.execute("""
            UPDATE upstox_sync_runs
            SET trigger_source = 'manual'
            WHERE trigger_source IS NULL OR TRIM(trigger_source) = '';
        """)

        conn.execute("""
            UPDATE upstox_sync_runs
            SET
                status = 'failed',
                finished_at = CURRENT_TIMESTAMP,
                duration_seconds = date_diff('second', started_at, CURRENT_TIMESTAMP),
                message = 'Sync run was interrupted before completion.'
            WHERE status IN ('running', 'cancel_requested');
        """)

        # -----------------------------
        # Upstox market holidays / calendar
        # Stores Upstox market holiday calendar for past and future dates.
        # Used by OHLCV sync to avoid unnecessary calls on non-trading days.
        # Upstox API:
        #   GET /v2/market/holidays
        #   GET /v2/market/holidays/{date}
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_market_holidays (
                holiday_date DATE PRIMARY KEY,
                description VARCHAR,
                holiday_type VARCHAR,
                closed_exchanges JSON,
                open_exchanges JSON,
                is_trading_day BOOLEAN DEFAULT FALSE,
                source_provider VARCHAR DEFAULT 'upstox',
                raw_json JSON,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN description VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN holiday_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN closed_exchanges JSON;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN open_exchanges JSON;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN is_trading_day BOOLEAN DEFAULT FALSE;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN source_provider VARCHAR DEFAULT 'upstox';")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_market_holidays ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            UPDATE upstox_market_holidays
            SET source_provider = 'upstox'
            WHERE source_provider IS NULL OR TRIM(source_provider) = '';
        """)

        conn.execute("""
            UPDATE upstox_market_holidays
            SET is_trading_day = FALSE
            WHERE is_trading_day IS NULL;
        """)

        # -----------------------------
        # Upstox data collection schedules
        # Multiple IST schedules for current, expired, and equity instruments.
        # schedule_time is stored in 24-hour HH:MM format.
        # schedule_label is used for 12-hour display like 09:30 AM.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_data_collection_schedules (
                schedule_id VARCHAR PRIMARY KEY,
                job_type VARCHAR NOT NULL,
                schedule_time VARCHAR NOT NULL,
                schedule_label VARCHAR,
                time_format VARCHAR DEFAULT '24',
                timezone VARCHAR DEFAULT 'Asia/Kolkata',
                is_active BOOLEAN DEFAULT TRUE,
                last_run_date VARCHAR,
                last_run_at TIMESTAMP,
                next_run_at TIMESTAMP,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN job_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN schedule_time VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN schedule_label VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN time_format VARCHAR DEFAULT '24';")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN timezone VARCHAR DEFAULT 'Asia/Kolkata';")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN last_run_date VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN last_run_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN next_run_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_data_collection_schedules ADD COLUMN updated_by VARCHAR;")

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET timezone = 'Asia/Kolkata'
            WHERE timezone IS NULL OR TRIM(timezone) = '';
        """)

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET time_format = '24'
            WHERE time_format IS NULL OR TRIM(time_format) = '';
        """)

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET record_status = 'S'
            WHERE record_status IS NULL;
        """)

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET version_no = 1
            WHERE version_no IS NULL;
        """)

        # -----------------------------
        # Upstox OHLCV saved collection settings
        # Stores saved checkbox/options config for OHLCV Options, Run Saved Options, and Scheduler.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_ohlcv_collection_settings (
                setting_id VARCHAR PRIMARY KEY,
                setting_name VARCHAR UNIQUE NOT NULL DEFAULT 'default',
                request_options JSON,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by VARCHAR
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN setting_name VARCHAR DEFAULT 'default';")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN request_options JSON;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN is_active BOOLEAN DEFAULT TRUE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_settings ADD COLUMN updated_by VARCHAR;")

        conn.execute("""
            UPDATE upstox_ohlcv_collection_settings
            SET is_active = TRUE
            WHERE is_active IS NULL;
        """)

        # -----------------------------
        # Upstox OHLCV collection status
        # Tracks completed OHLCV API chunks so skip-existing can avoid repeat calls,
        # including empty successful holiday/non-trading ranges.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_ohlcv_collection_status (
                provider VARCHAR DEFAULT 'upstox',
                instrument_source VARCHAR NOT NULL,
                candle_mode VARCHAR NOT NULL,
                instrument_key VARCHAR NOT NULL,
                unit VARCHAR NOT NULL,
                interval_value BIGINT NOT NULL,
                from_date DATE NOT NULL,
                to_date DATE NOT NULL,
                status VARCHAR DEFAULT 'success',
                candle_count BIGINT DEFAULT 0,
                last_error VARCHAR,
                source_sync_id VARCHAR,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN instrument_source VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN candle_mode VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN interval_value BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN from_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN to_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN status VARCHAR DEFAULT 'success';")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN candle_count BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN last_error VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_collection_status ADD COLUMN checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            UPDATE upstox_ohlcv_collection_status
            SET provider = 'upstox'
            WHERE provider IS NULL OR TRIM(provider) = '';
        """)

        # -----------------------------
        # Stocks
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                stock_id VARCHAR PRIMARY KEY,
                symbol VARCHAR UNIQUE NOT NULL,
                company_name VARCHAR,
                exchange VARCHAR,
                sector VARCHAR,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE stocks ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE stocks ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE stocks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Stock prices
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_prices (
                price_id VARCHAR PRIMARY KEY,
                stock_id VARCHAR NOT NULL,
                trade_date DATE NOT NULL,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                volume BIGINT,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE stock_prices ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Prediction requests
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_requests (
                request_id VARCHAR PRIMARY KEY,
                user_id VARCHAR NOT NULL,
                symbol VARCHAR NOT NULL,
                model_name VARCHAR,
                request_status VARCHAR DEFAULT 'pending',
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE prediction_requests ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Prediction results
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS prediction_results (
                result_id VARCHAR PRIMARY KEY,
                request_id VARCHAR NOT NULL,
                predicted_price DOUBLE,
                confidence_score DOUBLE,
                prediction_for_date DATE,
                record_status VARCHAR DEFAULT 'S',
                version_no INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE prediction_results ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Sync log table
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_log (
                sync_id VARCHAR PRIMARY KEY,
                table_name VARCHAR NOT NULL,
                record_id VARCHAR NOT NULL,
                action_type VARCHAR NOT NULL,
                version_no INTEGER,
                changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                changed_by VARCHAR,
                device_id VARCHAR
            );
        """)

        # -----------------------------
        # OHLCV Candles
        # Stores Upstox candle data for current/equity and expired instruments.
        # Supports historical/intraday, multiple intervals, skip-existing checks, and duplicate-safe inserts.
        # Upstox candle fields: timestamp, open, high, low, close, volume, open_interest.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_ohlcv_candles (
                provider VARCHAR DEFAULT 'upstox',
                instrument_source VARCHAR NOT NULL,
                candle_mode VARCHAR NOT NULL,
                instrument_key VARCHAR NOT NULL,
                trading_symbol VARCHAR,
                name VARCHAR,
                exchange VARCHAR,
                segment VARCHAR,
                isin VARCHAR,
                expiry DATE,
                instrument_type VARCHAR,
                unit VARCHAR NOT NULL,
                interval_value INTEGER NOT NULL,
                interval_label VARCHAR NOT NULL,
                candle_timestamp TIMESTAMP NOT NULL,
                candle_date DATE,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                volume BIGINT,
                open_interest BIGINT DEFAULT 0,
                source_sync_id VARCHAR,
                raw_json JSON,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (
                    provider,
                    instrument_source,
                    candle_mode,
                    instrument_key,
                    unit,
                    interval_value,
                    candle_timestamp
                )
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_source VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_mode VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN exchange VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN segment VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN expiry DATE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN instrument_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN interval_value INTEGER;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN interval_label VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_timestamp TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN candle_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN open_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN high_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN low_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN close_price DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN volume BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN open_interest BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_ohlcv_candles ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # OHLCV Daily compatibility table
        # Kept for existing code/screens that still read ohlcv_daily.
        # New OHLCV logic writes to upstox_ohlcv_candles and can also mirror daily candles here.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv_daily (
                instrument_key VARCHAR NOT NULL,
                trading_symbol VARCHAR NOT NULL,
                date DATE NOT NULL,
                open DOUBLE NOT NULL,
                high DOUBLE NOT NULL,
                low DOUBLE NOT NULL,
                close DOUBLE NOT NULL,
                volume BIGINT NOT NULL,
                oi BIGINT DEFAULT 0,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (instrument_key, date)
            );
        """)

        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN date DATE;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN open DOUBLE;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN high DOUBLE;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN low DOUBLE;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN close DOUBLE;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN volume BIGINT;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN oi BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE ohlcv_daily ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Equity news
        # Stock-level news articles.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS equity_news (
                news_id VARCHAR PRIMARY KEY,
                instrument_key VARCHAR NOT NULL,
                trading_symbol VARCHAR NOT NULL,
                title VARCHAR,
                summary TEXT,
                source VARCHAR,
                url VARCHAR,
                published_at TIMESTAMP,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN title VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN summary TEXT;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN source VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN url VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN thumbnail VARCHAR;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN published_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE equity_news ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Upstox company fundamentals
        # Complete Upstox Company Fundamentals API storage.
        # Stores every endpoint response as raw_json so no field is lost.
        # Preview/search columns are duplicated separately for fast UI tables.
        #
        # endpoint values:
        #   company_profile
        #   balance_sheet
        #   income_statement
        #   cash_flow
        #   share_holdings
        #   key_ratios
        #   corporate_actions
        #   competitors
        #
        # statement_type/time_period/include_full_statement are used for:
        #   balance_sheet, income_statement, cash_flow
        # Other endpoints keep these as NULL/false.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_company_fundamentals (
                fundamental_id VARCHAR PRIMARY KEY,
                provider VARCHAR DEFAULT 'upstox',
                isin VARCHAR NOT NULL,
                instrument_key VARCHAR,
                trading_symbol VARCHAR,
                company_name VARCHAR,
                exchange VARCHAR,
                segment VARCHAR,
                endpoint VARCHAR NOT NULL,
                endpoint_label VARCHAR,
                statement_type VARCHAR,
                time_period VARCHAR,
                include_full_statement BOOLEAN DEFAULT FALSE,
                api_status VARCHAR,
                data_status VARCHAR DEFAULT 'success',
                period_label VARCHAR,
                report_date DATE,
                sector VARCHAR,
                company_profile TEXT,
                market_cap_inr_value DOUBLE,
                market_cap_inr_unit VARCHAR,
                market_cap_inr_formatted VARCHAR,
                market_cap_usd_value DOUBLE,
                market_cap_usd_unit VARCHAR,
                market_cap_usd_formatted VARCHAR,
                total_asset DOUBLE,
                total_liability DOUBLE,
                revenue DOUBLE,
                operating_profit DOUBLE,
                net_profit DOUBLE,
                net_profit_growth DOUBLE,
                operating_cash_flow DOUBLE,
                operating_cash_flow_pct_change DOUBLE,
                investing_cash_flow DOUBLE,
                investing_cash_flow_pct_change DOUBLE,
                financing_cash_flow DOUBLE,
                financing_cash_flow_pct_change DOUBLE,
                promoters_holding DOUBLE,
                fii_holding DOUBLE,
                dii_holding DOUBLE,
                public_holding DOUBLE,
                other_holding DOUBLE,
                pe_ratio_company DOUBLE,
                pe_ratio_sector DOUBLE,
                pb_ratio_company DOUBLE,
                pb_ratio_sector DOUBLE,
                roa_company DOUBLE,
                roa_sector DOUBLE,
                roe_company DOUBLE,
                roe_sector DOUBLE,
                roce_company DOUBLE,
                roce_sector DOUBLE,
                ev_ebitda_company DOUBLE,
                ev_ebitda_sector DOUBLE,
                action_type VARCHAR,
                announcement_date DATE,
                ex_date DATE,
                record_date DATE,
                action_amount DOUBLE,
                action_ratio VARCHAR,
                additional_info TEXT,
                competitor_instrument_key VARCHAR,
                competitor_isin VARCHAR,
                competitor_company_profile TEXT,
                competitor_sector VARCHAR,
                competitor_market_cap_inr_value DOUBLE,
                competitor_market_cap_inr_unit VARCHAR,
                competitor_market_cap_inr_formatted VARCHAR,
                competitor_market_cap_usd_value DOUBLE,
                competitor_market_cap_usd_unit VARCHAR,
                competitor_market_cap_usd_formatted VARCHAR,
                summary_json JSON,
                history_json JSON,
                full_statement_json JSON,
                raw_json JSON,
                raw_data_json JSON,
                source_sync_id VARCHAR,
                source_provider_version VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN company_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN exchange VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN segment VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN endpoint VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN endpoint_label VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN statement_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN time_period VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN include_full_statement BOOLEAN DEFAULT FALSE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN api_status VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN data_status VARCHAR DEFAULT 'success';")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN period_label VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN report_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN sector VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN company_profile TEXT;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_inr_formatted VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN market_cap_usd_formatted VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN total_asset DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN total_liability DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN revenue DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_profit DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN net_profit DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN net_profit_growth DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_cash_flow DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN operating_cash_flow_pct_change DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN investing_cash_flow DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN investing_cash_flow_pct_change DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN financing_cash_flow DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN financing_cash_flow_pct_change DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN promoters_holding DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN fii_holding DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN dii_holding DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN public_holding DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN other_holding DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pe_ratio_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pe_ratio_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pb_ratio_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN pb_ratio_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roa_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roa_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roe_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roe_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roce_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN roce_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ev_ebitda_company DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ev_ebitda_sector DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN announcement_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN ex_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN record_date DATE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_amount DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN action_ratio VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN additional_info TEXT;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_company_profile TEXT;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_sector VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_inr_formatted VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_unit VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN competitor_market_cap_usd_formatted VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN summary_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN history_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN full_statement_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN raw_data_json JSON;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN source_provider_version VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            UPDATE upstox_company_fundamentals
            SET provider = 'upstox'
            WHERE provider IS NULL OR TRIM(provider) = '';
        """)

        conn.execute("""
            UPDATE upstox_company_fundamentals
            SET include_full_statement = FALSE
            WHERE include_full_statement IS NULL;
        """)

        conn.execute("""
            UPDATE upstox_company_fundamentals
            SET data_status = 'success'
            WHERE data_status IS NULL OR TRIM(data_status) = '';
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_isin_endpoint
            ON upstox_company_fundamentals (isin, endpoint);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_endpoint_synced
            ON upstox_company_fundamentals (endpoint, synced_at);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_symbol
            ON upstox_company_fundamentals (trading_symbol);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_sync
            ON upstox_company_fundamentals (source_sync_id);
        """)

        # -----------------------------
        # Upstox company fundamentals collection status
        # Tracks checked API request groups, including empty success responses.
        # This lets the sync skip API calls that were already completed.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_company_fundamentals_sync_status (
                provider VARCHAR DEFAULT 'upstox',
                isin VARCHAR NOT NULL,
                instrument_key VARCHAR,
                trading_symbol VARCHAR,
                endpoint VARCHAR NOT NULL,
                statement_type VARCHAR,
                time_period VARCHAR,
                include_full_statement BOOLEAN DEFAULT FALSE,
                status VARCHAR DEFAULT 'success',
                record_count BIGINT DEFAULT 0,
                last_error VARCHAR,
                source_sync_id VARCHAR,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN provider VARCHAR DEFAULT 'upstox';")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN instrument_key VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN endpoint VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN statement_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN time_period VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN include_full_statement BOOLEAN DEFAULT FALSE;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN status VARCHAR DEFAULT 'success';")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN record_count BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN last_error VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_company_fundamentals_sync_status ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            UPDATE upstox_company_fundamentals_sync_status
            SET provider = 'upstox'
            WHERE provider IS NULL OR TRIM(provider) = '';
        """)

        conn.execute("""
            UPDATE upstox_company_fundamentals_sync_status
            SET include_full_statement = FALSE
            WHERE include_full_statement IS NULL;
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_isin_endpoint
            ON upstox_company_fundamentals_sync_status (isin, endpoint, status);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_sync
            ON upstox_company_fundamentals_sync_status (source_sync_id);
        """)

        # -----------------------------
        # Fundamentals
        # Company financial data.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fundamentals (
                instrument_key VARCHAR NOT NULL,
                isin VARCHAR NOT NULL,
                trading_symbol VARCHAR NOT NULL,
                report_date DATE NOT NULL,
                period_type VARCHAR NOT NULL,
                revenue DOUBLE,
                net_profit DOUBLE,
                eps DOUBLE,
                pe_ratio DOUBLE,
                debt_to_equity DOUBLE,
                roe DOUBLE,
                cash_from_operations DOUBLE,
                promoter_holding_pct DOUBLE,
                fii_holding_pct DOUBLE,
                dii_holding_pct DOUBLE,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (instrument_key, report_date, period_type)
            );
        """)

        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN report_date DATE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN period_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN revenue DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN net_profit DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN eps DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN pe_ratio DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN debt_to_equity DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN roe DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN cash_from_operations DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN promoter_holding_pct DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN fii_holding_pct DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN dii_holding_pct DOUBLE;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE fundamentals ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # Corporate actions
        # Dividends, splits, bonuses, and similar company actions.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS corporate_actions (
                instrument_key VARCHAR NOT NULL,
                isin VARCHAR NOT NULL,
                trading_symbol VARCHAR NOT NULL,
                action_type VARCHAR NOT NULL,
                ex_date DATE NOT NULL,
                record_date DATE,
                amount DOUBLE,
                remarks VARCHAR,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (instrument_key, action_type, ex_date)
            );
        """)

        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN isin VARCHAR;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN trading_symbol VARCHAR;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN action_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ex_date DATE;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN record_date DATE;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN amount DOUBLE;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ratio VARCHAR;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN remarks VARCHAR;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE corporate_actions ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        # -----------------------------
        # FII / DII activity
        # Market-level institutional flow data.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS fii_dii_activity (
                date DATE NOT NULL,
                category VARCHAR NOT NULL,
                data_type VARCHAR NOT NULL DEFAULT 'NSE_EQ|CASH',
                buy_value DOUBLE,
                sell_value DOUBLE,
                net_value DOUBLE,
                ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (date, category, data_type)
            );
        """)

        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN category VARCHAR;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN data_type VARCHAR DEFAULT 'NSE_EQ|CASH';")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN buy_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN sell_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN net_value DOUBLE;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN buy_contracts BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN sell_contracts BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN oi_contracts BIGINT DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN oi_amount DOUBLE DEFAULT 0;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE fii_dii_activity ADD COLUMN ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        migrate_fii_dii_activity_table(conn)

        conn.commit()
        print(
            "[DB] Schema ready. "
            f"Existing items skipped: {DB_SCHEMA_STATS['already_exists']}, "
            f"other skipped: {DB_SCHEMA_STATS['skipped']}."
        )
        print(f"[DB] Database path: {DB_PATH}")


        # -----------------------------
        # IPO Watch GMP scraper
        # Stores IPO grey market premium scraper data from IPO Watch.
        # Source:
        #   https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/
        # Only required UI columns are stored separately.
        # -----------------------------
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ipo_gmp_scraper (
                ipo_name VARCHAR PRIMARY KEY,
                ipo_gmp VARCHAR,
                price_band VARCHAR,
                ipo_date VARCHAR,
                ipo_type VARCHAR,
                ipo_status VARCHAR,
                last_updated VARCHAR,
                source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
                raw_json JSON,
                source_sync_id VARCHAR,
                data_hash VARCHAR,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_gmp VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN price_band VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_date VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_status VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN last_updated VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN data_hash VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS ipo_gmp_scraper_snapshots (
                snapshot_id VARCHAR PRIMARY KEY,
                source_sync_id VARCHAR NOT NULL,
                ipo_name VARCHAR NOT NULL,
                ipo_gmp VARCHAR,
                price_band VARCHAR,
                ipo_date VARCHAR,
                ipo_type VARCHAR,
                ipo_status VARCHAR,
                last_updated VARCHAR,
                source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
                raw_json JSON,
                data_hash VARCHAR,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN snapshot_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_sync_id VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_name VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_gmp VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN price_band VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_date VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_status VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN last_updated VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN raw_json JSON;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN data_hash VARCHAR;")
        safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_status
            ON ipo_gmp_scraper (ipo_status);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_updated
            ON ipo_gmp_scraper (updated_at);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_ipo_name
            ON ipo_gmp_scraper_snapshots (ipo_name);
        """)

        safe_execute(conn, """
            CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_sync
            ON ipo_gmp_scraper_snapshots (source_sync_id);
        """)

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        print(f"[DB] Schema failed: {e}")
        raise e

    finally:
        conn.close()
