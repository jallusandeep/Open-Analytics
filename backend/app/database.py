import time
import threading
import duckdb
from pathlib import Path
from passlib.context import CryptContext

from app.config import settings


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


from app.db.schema_identity import ensure_identity_schema
from app.db.schema_instruments import ensure_instrument_schema
from app.db.schema_ai import ensure_ai_schema
from app.services.security_reference import ensure_reference_schema, migrate_legacy_reference
from app.db.schema_legacy_data import ensure_legacy_data_schema
from app.db.schema_fundamentals import ensure_fundamentals_schema
from app.db.schema_ipo_scraper import ensure_ipo_scraper_schema
from app.engines.universe import ensure_universe_engine_schema
from app.engines.data_quality import ensure_data_quality_schema
from app.engines.corporate_actions import ensure_corporate_action_schema


def init_database():
    conn = get_connection()
    reset_db_schema_stats()

    try:
        print("[DB] Schema check started.")
        ensure_identity_schema(conn, safe_execute, pwd_context)
        ensure_instrument_schema(conn, safe_execute)
        ensure_ai_schema(conn)
        ensure_legacy_data_schema(conn, safe_execute)
        ensure_fundamentals_schema(conn, safe_execute, migrate_fii_dii_activity_table)
        reference_exists = conn.execute("SELECT count(*) FROM information_schema.tables WHERE table_name='security_reference'").fetchone()[0]
        ensure_reference_schema(conn)
        ensure_universe_engine_schema(conn)
        ensure_data_quality_schema(conn)
        ensure_corporate_action_schema(conn)
        if not reference_exists:
            migrate_legacy_reference(conn)
        conn.commit()
        print(
            "[DB] Schema ready. "
            f"Existing items skipped: {DB_SCHEMA_STATS['already_exists']}, "
            f"other skipped: {DB_SCHEMA_STATS['skipped']}."
        )
        print(f"[DB] Database path: {DB_PATH}")


        ensure_ipo_scraper_schema(conn, safe_execute)

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        print(f"[DB] Schema failed: {e}")
        raise e

    finally:
        conn.close()
