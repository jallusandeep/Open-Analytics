import uuid
import time
import duckdb
from pathlib import Path
from passlib.context import CryptContext
import os

from app.config import settings
from app.version import APP_VERSION, SCHEMA_VERSION


BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(settings.DUCKDB_PATH)

if not DB_PATH.is_absolute():
    DB_PATH = BACKEND_ROOT / DB_PATH

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

DB_CONNECT_RETRY_ATTEMPTS = 10
DB_CONNECT_RETRY_DELAY_SECONDS = 0.2


def is_transient_duckdb_lock_error(error: Exception) -> bool:
    message = str(error).lower()

    return (
        "cannot open file" in message
        and (
            "being used by another process" in message
            or "file is already open" in message
        )
    )


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    for attempt in range(DB_CONNECT_RETRY_ATTEMPTS):
        try:
            return duckdb.connect(str(DB_PATH))
        except duckdb.IOException as error:
            is_last_attempt = attempt == DB_CONNECT_RETRY_ATTEMPTS - 1

            if is_last_attempt or not is_transient_duckdb_lock_error(error):
                raise

            time.sleep(DB_CONNECT_RETRY_DELAY_SECONDS)


def safe_execute(conn, query: str):
    try:
        conn.execute(query)
    except Exception as e:
        print(f"Skipped SQL: {query}")
        print(f"Reason: {e}")
        try:
            conn.rollback()
        except Exception:
            pass


def init_database():
    conn = get_connection()

    try:
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
        # Default admin user
        # -----------------------------
        admin_email = os.getenv("ADMIN_EMAIL")
        admin_password = os.getenv("ADMIN_PASSWORD")

        existing_admin = conn.execute("""
            SELECT user_id
            FROM users
            WHERE email = ?;
        """, [admin_email]).fetchone()

        if not existing_admin:
            admin_user_id = str(uuid.uuid4())
            admin_password_hash = pwd_context.hash(admin_password)

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
                admin_user_id,
                "admin",
                "Admin User",
                admin_email,
                None,
                admin_password_hash,
                "admin",
                None,
                True,
                "S",
                1,
                "system",
                "system"
            ])

            print("Default admin user created.")
        else:
            conn.execute("""
                UPDATE users
                SET
                    login_id = 'admin',
                    full_name = CASE 
                        WHEN full_name IS NULL OR full_name = '' THEN 'Admin User'
                        ELSE full_name
                    END,
                    role = 'admin',
                    is_active = TRUE,
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system'
                WHERE email = ?;
            """, [admin_email])

            print("Default admin user verified.")

        # -----------------------------
        # Default super admin user
        # -----------------------------
        super_admin_email = "jallusandeep0902@gmail.com"
        super_admin_password = "1234"

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
                "Super Admin",
                super_admin_email,
                None,
                super_admin_password_hash,
                "super_admin",
                None,
                True,
                "S",
                1,
                "system",
                "system"
            ])

            print("Default super admin user created.")
        else:
            conn.execute("""
                UPDATE users
                SET
                    login_id = 'jallusandeep0902',
                    full_name = CASE
                        WHEN full_name IS NULL OR full_name = '' THEN 'Super Admin'
                        ELSE full_name
                    END,
                    role = 'super_admin',
                    is_active = TRUE,
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system'
                WHERE email = ?;
            """, [super_admin_email])

            print("Default super admin user verified.")

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
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP
            );
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
                access_token VARCHAR,
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
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN access_token VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN connection_status VARCHAR DEFAULT 'saved';")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN last_tested_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN record_status VARCHAR DEFAULT 'S';")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN version_no INTEGER DEFAULT 1;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN created_by VARCHAR;")
        safe_execute(conn, "ALTER TABLE external_connections ADD COLUMN updated_by VARCHAR;")

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
                total_records BIGINT DEFAULT 0
            );
        """)

        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN sync_type VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN status VARCHAR DEFAULT 'running';")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN finished_at TIMESTAMP;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN duration_seconds BIGINT;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN message VARCHAR;")
        safe_execute(conn, "ALTER TABLE upstox_sync_runs ADD COLUMN total_records BIGINT DEFAULT 0;")

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

        conn.commit()
        print("Database initialized successfully.")

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        print("Database initialization failed.")
        print(e)
        raise e

    finally:
        conn.close()
