import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"
UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_V3_BASE_URL = "https://api.upstox.com/v3"

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data" / "upstox"
MASTER_INSTRUMENT_FILE = DATA_DIR / "upstox_instruments.json"

UPSTOX_CURRENT_MASTER_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)

DEFAULT_UNDERLYING_KEYS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Fin Service",
    "NSE_INDEX|Nifty Midcap Select",
    "BSE_INDEX|SENSEX",
    "BSE_INDEX|BANKEX"
]

REQUEST_TIMEOUT_SECONDS = 180
API_SLEEP_SECONDS = 0.45
OHLCV_API_SLEEP_SECONDS = 0.35
OHLCV_API_RETRY_ATTEMPTS = 4
OHLCV_API_RETRY_BASE_SLEEP_SECONDS = 0.75
STALE_RUNNING_RUN_HOURS = 2
DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 4

CANCEL_SIGNAL_DIR = APP_ROOT / "runtime"
CANCEL_SIGNAL_FILE = CANCEL_SIGNAL_DIR / "upstox_data_collection.cancel"


class SyncCancelled(Exception):
    pass


def normalize_upstox_token(access_token: str) -> str:
    token = access_token.strip() if access_token else ""

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return token


def write_cancel_signal():
    CANCEL_SIGNAL_DIR.mkdir(parents=True, exist_ok=True)
    CANCEL_SIGNAL_FILE.write_text(
        datetime.now().isoformat(),
        encoding="utf-8"
    )


def clear_cancel_signal():
    try:
        if CANCEL_SIGNAL_FILE.exists():
            CANCEL_SIGNAL_FILE.unlink()
    except Exception:
        pass


def has_cancel_signal() -> bool:
    return CANCEL_SIGNAL_FILE.exists()


def duration_seconds(started_at: datetime) -> int:
    return max(0, int((datetime.now() - started_at).total_seconds()))


def normalize_duckdb_file_path(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def normalize_expiry(value: Any) -> Optional[str]:
    if value in (None, "", 0):
        return None

    if isinstance(value, str):
        value = value.strip()

        if not value:
            return None

        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            return value

        try:
            number_value = int(value)
            return datetime.fromtimestamp(
                number_value / 1000,
                tz=timezone.utc
            ).date().isoformat()
        except Exception:
            return None

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                value / 1000,
                tz=timezone.utc
            ).date().isoformat()
        except Exception:
            return None

    return None


def safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    try:
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None

    try:
        return int(float(value))
    except Exception:
        return None


def safe_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None

    if isinstance(value, str):
        clean_value = value.strip().lower()

        if clean_value in ("true", "1", "yes", "y"):
            return True

        if clean_value in ("false", "0", "no", "n"):
            return False

    return bool(value)


def get_upstox_access_token(conn) -> str:
    row = conn.execute("""
        SELECT
            access_token,
            connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
          AND access_token IS NOT NULL
          AND TRIM(access_token) <> ''
        ORDER BY updated_at DESC
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row or not row[0]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Upstox connection token is not saved. "
                "Please save Upstox connection in Connections first."
            )
        )

    return normalize_upstox_token(row[0])


def get_upstox_connection_status(conn) -> str:
    row = conn.execute("""
        SELECT connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        return "not_connected"

    return row[0] or "saved"


def mark_stale_sync_runs(conn):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            status = 'failed',
            finished_at = CURRENT_TIMESTAMP,
            duration_seconds = date_diff('second', started_at, CURRENT_TIMESTAMP),
            message = 'Sync run was interrupted before completion.'
        WHERE status IN ('running', 'cancel_requested')
          AND started_at < CURRENT_TIMESTAMP - (? * INTERVAL '1 hour');
    """, [STALE_RUNNING_RUN_HOURS])

    conn.commit()


def ensure_no_active_sync_run(conn):
    mark_stale_sync_runs(conn)

    row = conn.execute("""
        SELECT sync_type, status
        FROM upstox_sync_runs
        WHERE status IN ('running', 'cancel_requested')
        ORDER BY started_at DESC
        LIMIT 1;
    """).fetchone()

    if row:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Another data collection job is already active: {row[0]} ({row[1]})."
        )


def get_sync_trigger_metadata(current_user: Optional[dict]) -> Dict[str, str]:
    user = current_user or {}
    user_id = (
        user.get("user_id")
        or user.get("login_id")
        or user.get("email")
        or "system"
    )
    role = user.get("role") or ""
    is_system = user_id == "system" or role == "system"

    return {
        "trigger_source": "system" if is_system else "manual",
        "triggered_by_id": user_id,
        "triggered_by_name": "System" if is_system else (
            user.get("full_name")
            or user.get("login_id")
            or user.get("email")
            or "Manual"
        ),
        "triggered_by_role": "system" if is_system else role
    }


def create_sync_run(
    conn,
    sync_type: str,
    status_text: str,
    message: str = "",
    current_user: Optional[dict] = None
) -> str:
    sync_id = str(uuid.uuid4())
    trigger_metadata = get_sync_trigger_metadata(current_user)

    conn.execute("""
        INSERT INTO upstox_sync_runs (
            sync_id,
            sync_type,
            status,
            started_at,
            finished_at,
            duration_seconds,
            message,
            total_records,
            trigger_source,
            triggered_by_id,
            triggered_by_name,
            triggered_by_role
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL, NULL, ?, 0, ?, ?, ?, ?);
    """, [
        sync_id,
        sync_type,
        status_text,
        message,
        trigger_metadata["trigger_source"],
        trigger_metadata["triggered_by_id"],
        trigger_metadata["triggered_by_name"],
        trigger_metadata["triggered_by_role"]
    ])

    conn.commit()
    return sync_id


def finish_sync_run(
    conn,
    sync_id: str,
    status_text: str,
    message: str,
    total_records: int,
    started_at: datetime
):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            status = ?,
            finished_at = CURRENT_TIMESTAMP,
            duration_seconds = ?,
            message = ?,
            total_records = ?
        WHERE sync_id = ?;
    """, [
        status_text,
        duration_seconds(started_at),
        message,
        total_records,
        sync_id
    ])

    conn.commit()


def check_sync_cancelled(conn, sync_id: str):
    if has_cancel_signal():
        raise SyncCancelled()

    row = conn.execute("""
        SELECT status
        FROM upstox_sync_runs
        WHERE sync_id = ?;
    """, [sync_id]).fetchone()

    if row and row[0] in ("cancel_requested", "cancelled"):
        raise SyncCancelled()


def request_cancel_active_sync_runs_service():
    write_cancel_signal()

    conn = get_connection()

    try:
        try:
            rows = conn.execute("""
                SELECT sync_id, sync_type
                FROM upstox_sync_runs
                WHERE status IN ('running', 'cancel_requested')
                ORDER BY started_at DESC;
            """).fetchall()
        except Exception:
            return {
                "status": "success",
                "message": "Cancel signal created. Running dump will stop at the next safe checkpoint.",
                "cancelled_jobs": []
            }

        if not rows:
            return {
                "status": "idle",
                "message": "Cancel signal created, but no running data collection job was found.",
                "cancelled_jobs": []
            }

        try:
            conn.execute("""
                UPDATE upstox_sync_runs
                SET
                    message = 'Cancel requested by user.',
                    status = 'cancel_requested'
                WHERE status IN ('running', 'cancel_requested');
            """)
            conn.commit()
        except Exception:
            return {
                "status": "success",
                "message": "Cancel signal created. Status update is pending because database is busy.",
                "cancelled_jobs": [
                    {
                        "sync_id": row[0],
                        "sync_type": row[1]
                    }
                    for row in rows
                ]
            }

        return {
            "status": "success",
            "message": "Cancel requested. Running dump will stop at the next safe checkpoint.",
            "cancelled_jobs": [
                {
                    "sync_id": row[0],
                    "sync_type": row[1]
                }
                for row in rows
            ]
        }

    finally:
        conn.close()


def print_current_file_sanity_check(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        total = len(data) if isinstance(data, list) else 0
        print(f"Total active instruments found in file: {total}")

        if total > 0:
            sample = data[0]
            trading_symbol = sample.get("trading_symbol", "--")
            instrument_key = sample.get("instrument_key", "--")
            print(f"Sample Instrument: {trading_symbol} ({instrument_key})")

    except Exception as error:
        print(f"Current file sanity check skipped: {error}")


def download_upstox_master_file_once(force_download: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if (
        MASTER_INSTRUMENT_FILE.exists()
        and MASTER_INSTRUMENT_FILE.stat().st_size > 0
        and not force_download
    ):
        print(f"Using existing local Upstox master file: {MASTER_INSTRUMENT_FILE}")
        return MASTER_INSTRUMENT_FILE

    temp_gz_file = MASTER_INSTRUMENT_FILE.with_suffix(".json.gz.download")
    temp_json_file = MASTER_INSTRUMENT_FILE.with_suffix(".json.download")

    request = urllib.request.Request(
        UPSTOX_CURRENT_MASTER_URL,
        headers={
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    print("Downloading Upstox current instruments master file.")
    print("No token required for current instruments.")
    print(f"URL  : {UPSTOX_CURRENT_MASTER_URL}")
    print(f"Save : {MASTER_INSTRUMENT_FILE}")

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            with open(temp_gz_file, "wb") as output_file:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)

                    if not chunk:
                        break

                    output_file.write(chunk)

        with gzip.open(temp_gz_file, "rb") as gzip_file:
            with open(temp_json_file, "wb") as output_file:
                while True:
                    chunk = gzip_file.read(DOWNLOAD_CHUNK_SIZE)

                    if not chunk:
                        break

                    output_file.write(chunk)

        temp_json_file.replace(MASTER_INSTRUMENT_FILE)

        try:
            temp_gz_file.unlink()
        except Exception:
            pass

        print(f"Download completed: {MASTER_INSTRUMENT_FILE}")
        print_current_file_sanity_check(MASTER_INSTRUMENT_FILE)

        return MASTER_INSTRUMENT_FILE

    except Exception:
        try:
            if temp_gz_file.exists():
                temp_gz_file.unlink()

            if temp_json_file.exists():
                temp_json_file.unlink()
        except Exception:
            pass

        raise


def delete_downloaded_master_file(file_path: Optional[Path]):
    if not file_path:
        return

    try:
        resolved_file = file_path.resolve()
        resolved_data_dir = DATA_DIR.resolve()

        if resolved_data_dir not in resolved_file.parents:
            return

        if resolved_file.exists():
            resolved_file.unlink()
            print(f"Deleted temporary Upstox master file: {resolved_file}")
    except Exception as error:
        print(f"Unable to delete temporary Upstox master file: {error}")


def import_current_instruments_from_local_file(conn, sync_id: str, local_file: Path) -> int:
    check_sync_cancelled(conn, sync_id)

    duckdb_path = normalize_duckdb_file_path(local_file)

    conn.execute("DROP TABLE IF EXISTS temp_upstox_current")

    read_started_at = time.time()

    print("Reading required columns directly with DuckDB...")

    conn.execute(
        """
        CREATE TEMP TABLE temp_upstox_current AS
        SELECT *
        FROM read_json(
            ?,
            format = 'array',
            maximum_object_size = 16777216,
            columns = {
                instrument_key: 'VARCHAR',
                segment: 'VARCHAR',
                name: 'VARCHAR',
                exchange: 'VARCHAR',
                isin: 'VARCHAR',
                instrument_type: 'VARCHAR',
                trading_symbol: 'VARCHAR',
                short_name: 'VARCHAR',
                exchange_token: 'VARCHAR',
                expiry: 'VARCHAR',
                strike_price: 'DOUBLE',
                lot_size: 'BIGINT',
                minimum_lot: 'BIGINT',
                freeze_quantity: 'DOUBLE',
                tick_size: 'DOUBLE',
                weekly: 'BOOLEAN',
                underlying_key: 'VARCHAR',
                underlying_symbol: 'VARCHAR',
                underlying_type: 'VARCHAR',
                security_type: 'VARCHAR'
            }
        );
        """,
        [duckdb_path]
    )

    print(f"DuckDB JSON read time: {round(time.time() - read_started_at, 2)} seconds")

    check_sync_cancelled(conn, sync_id)

    total_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_current;
    """).fetchone()[0]

    print(f"Rows loaded into temp table: {total_rows}")

    insert_started_at = time.time()

    conn.execute("""
        DELETE FROM upstox_instruments
        WHERE source_type = 'bod_complete';
    """)

    check_sync_cancelled(conn, sync_id)

    conn.execute("""
        INSERT INTO upstox_instruments (
            instrument_key,
            source_type,
            segment,
            name,
            exchange,
            isin,
            instrument_type,
            trading_symbol,
            short_name,
            exchange_token,
            expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            security_type,
            raw_json,
            synced_at
        )
        SELECT
            instrument_key,
            'bod_complete' AS source_type,
            segment,
            name,
            exchange,
            isin,
            instrument_type,
            trading_symbol,
            short_name,
            exchange_token,
            CASE
                WHEN expiry IS NULL THEN NULL
                WHEN TRY_CAST(expiry AS BIGINT) IS NOT NULL
                    THEN CAST(epoch_ms(TRY_CAST(expiry AS BIGINT)) AS DATE)
                ELSE TRY_CAST(expiry AS DATE)
            END AS expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            security_type,
            NULL AS raw_json,
            CURRENT_TIMESTAMP AS synced_at
        FROM temp_upstox_current;
    """)

    print(f"DuckDB insert time: {round(time.time() - insert_started_at, 2)} seconds")

    conn.execute("DROP TABLE IF EXISTS temp_upstox_current")

    return int(total_rows or 0)


def import_equity_instruments_from_local_file(conn, sync_id: str, local_file: Path) -> int:
    check_sync_cancelled(conn, sync_id)

    duckdb_path = normalize_duckdb_file_path(local_file)

    conn.execute("DROP TABLE IF EXISTS temp_upstox_equity")

    print("Reading NSE_EQ equity instruments directly with DuckDB...")

    conn.execute(
        """
        CREATE TEMP TABLE temp_upstox_equity AS
        SELECT *
        FROM read_json(
            ?,
            format = 'array',
            maximum_object_size = 16777216,
            columns = {
                instrument_key: 'VARCHAR',
                segment: 'VARCHAR',
                name: 'VARCHAR',
                exchange: 'VARCHAR',
                isin: 'VARCHAR',
                instrument_type: 'VARCHAR',
                trading_symbol: 'VARCHAR',
                short_name: 'VARCHAR',
                exchange_token: 'VARCHAR',
                lot_size: 'BIGINT',
                freeze_quantity: 'DOUBLE',
                tick_size: 'DOUBLE',
                security_type: 'VARCHAR'
            }
        )
        WHERE segment = 'NSE_EQ'
          AND exchange = 'NSE'
          AND instrument_key IS NOT NULL
          AND TRIM(instrument_key) <> '';
        """,
        [duckdb_path]
    )

    check_sync_cancelled(conn, sync_id)

    total_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_equity;
    """).fetchone()[0]

    conn.execute("""
        DELETE FROM upstox_equity_instruments;
    """)

    check_sync_cancelled(conn, sync_id)

    conn.execute("""
        INSERT INTO upstox_equity_instruments (
            instrument_key,
            trading_symbol,
            name,
            isin,
            exchange,
            segment,
            exchange_token,
            tick_size,
            lot_size,
            freeze_quantity,
            short_name,
            security_type,
            downloaded_at
        )
        SELECT
            instrument_key,
            trading_symbol,
            name,
            isin,
            COALESCE(exchange, 'NSE') AS exchange,
            COALESCE(segment, 'NSE_EQ') AS segment,
            exchange_token,
            tick_size,
            lot_size,
            freeze_quantity,
            short_name,
            security_type,
            CURRENT_TIMESTAMP AS downloaded_at
        FROM temp_upstox_equity;
    """)

    conn.execute("DROP TABLE IF EXISTS temp_upstox_equity")

    return int(total_rows or 0)


def equity_instruments_collected_today(conn) -> bool:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM upstox_equity_instruments
        WHERE CAST(downloaded_at AS DATE) = CURRENT_DATE;
    """).fetchone()

    return bool(row and row[0] > 0)


def get_equity_instruments_count(conn) -> int:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM upstox_equity_instruments;
    """).fetchone()

    return int(row[0] or 0) if row else 0


def get_ohlcv_daily_count(conn) -> int:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM ohlcv_daily;
    """).fetchone()

    return int(row[0] or 0) if row else 0


def ohlcv_daily_collected_for_date(conn, target_date: str) -> bool:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM ohlcv_daily
        WHERE date = ?;
    """, [target_date]).fetchone()

    row_count = int(row[0] or 0) if row else 0

    if row_count <= 0:
        return False

    success_row = conn.execute("""
        SELECT 1
        FROM upstox_sync_runs
        WHERE sync_type = 'upstox_ohlcv_daily'
          AND status = 'success'
          AND message LIKE ?
        ORDER BY started_at DESC
        LIMIT 1;
    """, [f"%{target_date}%"]).fetchone()

    return bool(success_row)


def get_equity_ohlcv_instruments(conn) -> List[Dict[str, str]]:
    rows = conn.execute("""
        SELECT
            instrument_key,
            trading_symbol
        FROM upstox_equity_instruments
        WHERE instrument_key IS NOT NULL
          AND TRIM(instrument_key) <> ''
          AND trading_symbol IS NOT NULL
          AND TRIM(trading_symbol) <> ''
        ORDER BY trading_symbol;
    """).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1]
        }
        for row in rows
    ]


def get_equity_data_collection_instruments(conn) -> List[Dict[str, str]]:
    rows = conn.execute("""
        SELECT
            instrument_key,
            trading_symbol,
            isin
        FROM upstox_equity_instruments
        WHERE instrument_key IS NOT NULL
          AND TRIM(instrument_key) <> ''
          AND trading_symbol IS NOT NULL
          AND TRIM(trading_symbol) <> ''
          AND isin IS NOT NULL
          AND TRIM(isin) <> ''
        ORDER BY trading_symbol;
    """).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "isin": row[2]
        }
        for row in rows
    ]


def get_sync_type_label(value: str) -> str:
    labels = {
        "current": "Current Instruments",
        "expired": "Expired Instruments",
        "equity": "Equity",
        "ohlcv_daily": "Equity OHLCV",
        "equity_news": "Equity News",
        "fundamentals": "Fundamentals",
        "corporate_actions": "Corporate Actions",
        "fii_dii_activity": "FII/DII Activity"
    }

    return labels.get(value, value or "Data collection")


def parse_upstox_error(error_body: str):
    try:
        payload = json.loads(error_body)
    except Exception:
        return {
            "raw": error_body,
            "error_code": None,
            "message": error_body or "Upstox API request failed."
        }

    errors = payload.get("errors")

    if isinstance(errors, list) and errors:
        first_error = errors[0] or {}

        return {
            "raw": payload,
            "error_code": (
                first_error.get("errorCode")
                or first_error.get("error_code")
                or first_error.get("code")
            ),
            "message": first_error.get("message") or str(payload)
        }

    return {
        "raw": payload,
        "error_code": (
            payload.get("errorCode")
            or payload.get("error_code")
            or payload.get("code")
        ),
        "message": payload.get("message") or str(payload)
    }


def raise_clean_upstox_error(upstox_status_code: int, error_body: str):
    parsed_error = parse_upstox_error(error_body)
    error_code = parsed_error.get("error_code")
    message = parsed_error.get("message") or ""

    if upstox_status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Saved Upstox token is invalid, expired, or not authenticated. "
                "Please save a fresh Upstox OAuth connection in Connections."
            )
        )

    if error_code == "UDAPI100067" or "read only token" in message.lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Saved Upstox token is valid, but Expired Instruments API is not permitted "
                "with this token. Please use an OAuth token from an Upstox Plus/API enabled app."
            )
        )

    if not message:
        message = f"Upstox API request failed with status {upstox_status_code}."

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Upstox API error: {message}"
    )


def upstox_api_get(access_token: str, path: str, params: Optional[Dict[str, str]] = None):
    token = normalize_upstox_token(access_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Saved Upstox token is empty. "
                "Please save a fresh Upstox OAuth connection in Connections."
            )
        )

    query_string = ""

    if params:
        query_string = "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{UPSTOX_BASE_URL}{path}{query_string}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise_clean_upstox_error(
            upstox_status_code=error.code,
            error_body=error_body
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox API."
        )


def upstox_v3_api_get(
    access_token: str,
    path: str,
    params: Optional[Dict[str, str]] = None
):
    token = normalize_upstox_token(access_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Saved Upstox token is empty. "
                "Please save a fresh Upstox OAuth connection in Connections."
            )
        )

    query_string = ""

    if params:
        query_string = "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{UPSTOX_V3_BASE_URL}{path}{query_string}",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise_clean_upstox_error(
            upstox_status_code=error.code,
            error_body=error_body
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox API."
        )


def upstox_expired_api_get(
    access_token: str,
    path: str,
    underlying_key: str,
    expiry_date: Optional[str] = None
):
    primary_params = {
        "underlying_key": underlying_key
    }
    fallback_params = {
        "instrument_key": underlying_key
    }

    if expiry_date:
        primary_params["expiry_date"] = expiry_date
        fallback_params["expiry_date"] = expiry_date

    try:
        return upstox_api_get(
            access_token=access_token,
            path=path,
            params=primary_params
        )
    except HTTPException as error:
        detail = str(error.detail).lower()
        should_retry_with_instrument_key = (
            error.status_code == status.HTTP_400_BAD_REQUEST
            and "instrument_key" in detail
        )

        if not should_retry_with_instrument_key:
            raise

        print(
            "Upstox expired instruments request requires instrument_key. "
            "Retrying with instrument_key."
        )

        return upstox_api_get(
            access_token=access_token,
            path=path,
            params=fallback_params
        )


def get_expiries(access_token: str, underlying_key: str) -> List[str]:
    response = upstox_expired_api_get(
        access_token=access_token,
        path="/expired-instruments/expiries",
        underlying_key=underlying_key
    )

    data = response.get("data") if isinstance(response, dict) else []

    if not isinstance(data, list):
        return []

    return data


def get_expired_option_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str
) -> List[Dict[str, Any]]:
    response = upstox_expired_api_get(
        access_token=access_token,
        path="/expired-instruments/option/contract",
        underlying_key=underlying_key,
        expiry_date=expiry_date
    )

    data = response.get("data") if isinstance(response, dict) else []

    if not isinstance(data, list):
        return []

    return data


def get_expired_future_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str
) -> List[Dict[str, Any]]:
    response = upstox_expired_api_get(
        access_token=access_token,
        path="/expired-instruments/future/contract",
        underlying_key=underlying_key,
        expiry_date=expiry_date
    )

    data = response.get("data") if isinstance(response, dict) else []

    if not isinstance(data, list):
        return []

    return data


def get_upstox_daily_candles(
    access_token: str,
    instrument_key: str,
    from_date: str,
    to_date: str
) -> List[List[Any]]:
    encoded_key = urllib.parse.quote(instrument_key, safe="")
    path = f"/historical-candle/{encoded_key}/days/1/{to_date}/{from_date}"

    response = None

    for attempt in range(1, OHLCV_API_RETRY_ATTEMPTS + 1):
        try:
            response = upstox_v3_api_get(
                access_token=access_token,
                path=path
            )
            break
        except HTTPException as error:
            is_transient_error = error.status_code == status.HTTP_502_BAD_GATEWAY
            is_last_attempt = attempt >= OHLCV_API_RETRY_ATTEMPTS

            if not is_transient_error or is_last_attempt:
                raise

            sleep_seconds = OHLCV_API_RETRY_BASE_SLEEP_SECONDS * attempt
            print(
                "OHLCV candle fetch retry: "
                f"{instrument_key} attempt {attempt + 1}/{OHLCV_API_RETRY_ATTEMPTS} "
                f"after transient Upstox error: {error.detail}"
            )
            time.sleep(sleep_seconds)

    data = response.get("data") if isinstance(response, dict) else {}
    candles = data.get("candles") if isinstance(data, dict) else []

    if not isinstance(candles, list):
        return []

    return candles


def validate_ohlcv_date(value: str) -> str:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OHLCV target date must be in YYYY-MM-DD format."
        )

    return value


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def deterministic_id(*parts: Any) -> str:
    text = "|".join(str(part or "") for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def milliseconds_to_timestamp(value: Any) -> Optional[datetime]:
    timestamp = safe_int(value)

    if timestamp is None:
        return None

    try:
        return datetime.fromtimestamp(timestamp / 1000, tz=timezone.utc).replace(
            tzinfo=None
        )
    except Exception:
        return None


def parse_upstox_display_date(value: Any) -> Optional[str]:
    text = safe_text(value)

    if not text:
        return None

    for date_format in ("%d %b %Y", "%d %B %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, date_format).date().isoformat()
        except ValueError:
            continue

    return None


def parse_upstox_period_date(value: Any) -> Optional[str]:
    text = safe_text(value)

    if not text:
        return None

    for date_format in ("%b %Y", "%B %Y", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, date_format).date()
            return parsed.isoformat()
        except ValueError:
            continue

    return None


def parse_percent_number(value: Any) -> Optional[float]:
    text = safe_text(value)

    if not text:
        return safe_float(value)

    return safe_float(text.replace("%", "").replace(",", ""))


def get_metric_history_value(section: Dict[str, Any], period: str) -> Optional[float]:
    history = section.get("history") if isinstance(section, dict) else []

    if not isinstance(history, list):
        return None

    for item in history:
        if not isinstance(item, dict):
            continue

        if safe_text(item.get("period")) == period:
            return safe_float(item.get("value"))

    return None


def get_named_metric(metrics: List[Dict[str, Any]], name: str) -> Optional[float]:
    for item in metrics:
        if not isinstance(item, dict):
            continue

        if safe_text(item.get("name")).lower() == name.lower():
            return parse_percent_number(item.get("company_value"))

    return None


def get_category_section(sections: List[Dict[str, Any]], category: str):
    for section in sections:
        if not isinstance(section, dict):
            continue

        if safe_text(section.get("category")).lower() == category.lower():
            return section

    return None


def get_full_statement_section(sections: List[Dict[str, Any]], particular: str):
    for section in sections:
        if not isinstance(section, dict):
            continue

        if safe_text(section.get("particular")).lower() == particular.lower():
            return section

    return None


def update_sync_run_message(conn, sync_id: str, message: str):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET message = ?
        WHERE sync_id = ?;
    """, [message, sync_id])
    conn.commit()


def update_sync_run_progress(
    conn,
    sync_id: str,
    message: str,
    total_records: int
):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            message = ?,
            total_records = ?
        WHERE sync_id = ?;
    """, [message, total_records, sync_id])
    conn.commit()


def resolve_latest_available_ohlcv_date(
    access_token: str,
    instruments: List[Dict[str, str]],
    target_date: str
) -> str:
    target = datetime.strptime(target_date, "%Y-%m-%d").date()
    from_date = (target - timedelta(days=30)).isoformat()

    for instrument in instruments[:5]:
        instrument_key = instrument["instrument_key"]
        trading_symbol = instrument["trading_symbol"]

        try:
            candles = get_upstox_daily_candles(
                access_token=access_token,
                instrument_key=instrument_key,
                from_date=from_date,
                to_date=target_date
            )
        except HTTPException as error:
            print(
                "OHLCV latest-date probe skipped: "
                f"{trading_symbol} ({instrument_key}) - {error.detail}"
            )
            continue

        candle_dates = [
            candle_date
            for candle_date in [
                candle_timestamp_to_date(candle[0])
                if isinstance(candle, list) and candle
                else None
                for candle in candles
            ]
            if candle_date and candle_date <= target_date
        ]

        if candle_dates:
            return max(candle_dates)

    return target_date


def candle_timestamp_to_date(value: Any) -> Optional[str]:
    if not value:
        return None

    text = str(value).strip()

    if not text:
        return None

    if len(text) >= 10:
        return text[:10]

    return None


def map_ohlcv_candle(
    instrument_key: str,
    trading_symbol: str,
    candle: List[Any]
) -> Optional[List[Any]]:
    if not isinstance(candle, list) or len(candle) < 6:
        return None

    candle_date = candle_timestamp_to_date(candle[0])

    if not candle_date:
        return None

    open_price = safe_float(candle[1])
    high_price = safe_float(candle[2])
    low_price = safe_float(candle[3])
    close_price = safe_float(candle[4])
    volume = safe_int(candle[5])
    oi = safe_int(candle[6]) if len(candle) > 6 else 0

    if (
        open_price is None
        or high_price is None
        or low_price is None
        or close_price is None
        or volume is None
    ):
        return None

    return [
        instrument_key,
        trading_symbol,
        candle_date,
        open_price,
        high_price,
        low_price,
        close_price,
        volume,
        oi or 0
    ]


def insert_ohlcv_daily_rows(conn, rows: List[List[Any]]) -> int:
    if not rows:
        return 0

    for row in rows:
        conn.execute("""
            DELETE FROM ohlcv_daily
            WHERE instrument_key = ?
              AND date = ?;
        """, [row[0], row[2]])

    conn.executemany("""
        INSERT INTO ohlcv_daily (
            instrument_key,
            trading_symbol,
            date,
            open,
            high,
            low,
            close,
            volume,
            oi,
            ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, rows)

    return len(rows)


def map_expired_instrument(row: Dict[str, Any], source_type: str):
    return [
        safe_text(row.get("instrument_key")),
        safe_text(row.get("segment")),
        safe_text(row.get("name")),
        safe_text(row.get("exchange")),
        safe_text(row.get("instrument_type")),
        safe_text(row.get("trading_symbol")),
        safe_text(row.get("exchange_token")),
        normalize_expiry(row.get("expiry")),
        safe_float(row.get("strike_price")),
        safe_int(row.get("lot_size")),
        safe_int(row.get("minimum_lot")),
        safe_float(row.get("freeze_quantity")),
        safe_float(row.get("tick_size")),
        safe_bool(row.get("weekly")),
        safe_text(row.get("underlying_key")),
        safe_text(row.get("underlying_symbol")),
        safe_text(row.get("underlying_type")),
        source_type,
        json.dumps(row, ensure_ascii=False),
        datetime.now()
    ]


def is_valid_expired_row(row: Dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False

    instrument_key = safe_text(row.get("instrument_key"))
    trading_symbol = safe_text(row.get("trading_symbol"))
    expiry = normalize_expiry(row.get("expiry"))

    return bool(instrument_key or trading_symbol or expiry)


def insert_expired_instruments(
    conn,
    rows: List[Dict[str, Any]],
    source_type: str,
    sync_id: str
) -> int:
    if not rows:
        return 0

    check_sync_cancelled(conn, sync_id)

    valid_rows = [row for row in rows if is_valid_expired_row(row)]

    if not valid_rows:
        return 0

    mapped_rows = [map_expired_instrument(row, source_type) for row in valid_rows]

    check_sync_cancelled(conn, sync_id)

    conn.executemany("""
        INSERT INTO upstox_expired_instruments (
            instrument_key,
            segment,
            name,
            exchange,
            instrument_type,
            trading_symbol,
            exchange_token,
            expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            source_type,
            raw_json,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """, mapped_rows)

    check_sync_cancelled(conn, sync_id)

    return len(mapped_rows)


def expired_instruments_exist(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str
) -> bool:
    row = conn.execute("""
        SELECT COUNT(*)
        FROM upstox_expired_instruments
        WHERE underlying_key = ?
          AND expiry = ?
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type]).fetchone()

    return bool(row and row[0] > 0)


def clear_expired_instruments_for_source(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str
):
    conn.execute("""
        DELETE FROM upstox_expired_instruments
        WHERE underlying_key = ?
          AND expiry = ?
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type])


def get_data_collection_summary_service():
    conn = get_connection()

    try:
        mark_stale_sync_runs(conn)
        connection_status = get_upstox_connection_status(conn)

        current_count = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_instruments;
        """).fetchone()[0]

        expired_count = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_expired_instruments;
        """).fetchone()[0]

        equity_count = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_equity_instruments;
        """).fetchone()[0]

        ohlcv_daily_count = conn.execute("""
            SELECT COUNT(*)
            FROM ohlcv_daily;
        """).fetchone()[0]

        equity_news_count = conn.execute("""
            SELECT COUNT(*)
            FROM equity_news;
        """).fetchone()[0]

        fundamentals_count = conn.execute("""
            SELECT COUNT(*)
            FROM fundamentals;
        """).fetchone()[0]

        corporate_actions_count = conn.execute("""
            SELECT COUNT(*)
            FROM corporate_actions;
        """).fetchone()[0]

        fii_dii_activity_count = conn.execute("""
            SELECT COUNT(*)
            FROM fii_dii_activity;
        """).fetchone()[0]

        total_runs = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_sync_runs;
        """).fetchone()[0]

        last_run = conn.execute("""
            SELECT
                sync_type,
                status,
                started_at,
                finished_at,
                duration_seconds,
                total_records
            FROM upstox_sync_runs
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()

        current_run = conn.execute("""
            SELECT finished_at, duration_seconds
            FROM upstox_sync_runs
            WHERE sync_type = 'upstox_current_instruments'
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        expired_run = conn.execute("""
            SELECT finished_at, duration_seconds
            FROM upstox_sync_runs
            WHERE sync_type = 'upstox_expired_instruments'
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        equity_run = conn.execute("""
            SELECT finished_at, duration_seconds
            FROM upstox_sync_runs
            WHERE sync_type = 'upstox_equity_instruments'
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        ohlcv_daily_run = conn.execute("""
            SELECT finished_at, duration_seconds
            FROM upstox_sync_runs
            WHERE sync_type = 'upstox_ohlcv_daily'
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1;
        """).fetchone()

        active_run = conn.execute("""
            SELECT sync_type, status, started_at
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()

        return {
            "connection_status": connection_status,
            "total_current_instruments": current_count,
            "total_expired_instruments": expired_count,
            "total_equity_instruments": equity_count,
            "total_ohlcv_daily": ohlcv_daily_count,
            "total_equity_news": equity_news_count,
            "total_fundamentals": fundamentals_count,
            "total_corporate_actions": corporate_actions_count,
            "total_fii_dii_activity": fii_dii_activity_count,
            "total_sync_runs": total_runs,
            "last_sync_at": str(last_run[3]) if last_run and last_run[3] else None,
            "last_duration_seconds": last_run[4] if last_run else None,
            "current_last_sync_at": str(current_run[0]) if current_run and current_run[0] else None,
            "current_duration_seconds": current_run[1] if current_run else None,
            "expired_last_sync_at": str(expired_run[0]) if expired_run and expired_run[0] else None,
            "expired_duration_seconds": expired_run[1] if expired_run else None,
            "equity_last_sync_at": str(equity_run[0]) if equity_run and equity_run[0] else None,
            "equity_duration_seconds": equity_run[1] if equity_run else None,
            "ohlcv_daily_last_sync_at": str(ohlcv_daily_run[0]) if ohlcv_daily_run and ohlcv_daily_run[0] else None,
            "ohlcv_daily_duration_seconds": ohlcv_daily_run[1] if ohlcv_daily_run else None,
            "active_job": active_run[0] if active_run else None,
            "active_job_status": active_run[1] if active_run else None,
            "active_job_started_at": str(active_run[2]) if active_run and active_run[2] else None
        }

    finally:
        conn.close()


def get_data_collection_runs_service():
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                sync_id,
                sync_type,
                status,
                started_at,
                finished_at,
                duration_seconds,
                message,
                total_records,
                trigger_source,
                triggered_by_id,
                triggered_by_name,
                triggered_by_role
            FROM upstox_sync_runs
            ORDER BY started_at DESC
            LIMIT 25;
        """).fetchall()

        return [
            {
                "sync_id": row[0],
                "sync_type": row[1],
                "status": row[2],
                "started_at": str(row[3]) if row[3] else None,
                "finished_at": str(row[4]) if row[4] else None,
                "duration_seconds": row[5],
                "message": row[6],
                "total_records": row[7],
                "trigger_source": row[8] or "manual",
                "triggered_by_id": row[9],
                "triggered_by_name": row[10],
                "triggered_by_role": row[11]
            }
            for row in rows
        ]

    finally:
        conn.close()


def sync_upstox_current_instruments_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    local_file = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_current_instruments",
            "running",
            "Current instrument dump started.",
            current_user=current_user
        )

        local_file = download_upstox_master_file_once(force_download=True)

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")

        total_records = import_current_instruments_from_local_file(
            conn=conn,
            sync_id=sync_id,
            local_file=local_file
        )

        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Current instruments downloaded and imported successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Current instruments downloaded and imported successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Current instrument dump cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Current instrument dump cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Current instrument dump failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Current instrument dump failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump current instruments: {e}"
        )

    finally:
        delete_downloaded_master_file(local_file)
        conn.close()


def sync_upstox_equity_instruments_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    local_file = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_equity_instruments",
            "running",
            "Equity instrument daily dump started.",
            current_user=current_user
        )

        if equity_instruments_collected_today(conn):
            total_records = get_equity_instruments_count(conn)

            finish_sync_run(
                conn,
                sync_id,
                "success",
                "Equity instruments already collected today. Daily refresh skipped.",
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "success",
                "message": "Equity instruments already collected today. Daily refresh skipped.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
                "skipped": True
            }

        local_file = download_upstox_master_file_once(force_download=True)

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")

        total_records = import_equity_instruments_from_local_file(
            conn=conn,
            sync_id=sync_id,
            local_file=local_file
        )

        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "NSE equity instruments collected successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "NSE equity instruments collected successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "skipped": False
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Equity instrument dump cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Equity instrument dump cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Equity instrument dump failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Equity instrument dump failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump equity instruments: {e}"
        )

    finally:
        delete_downloaded_master_file(local_file)
        conn.close()


def sync_upstox_ohlcv_daily_service(
    current_user: dict,
    target_date: Optional[str] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    requested_target_date = bool(target_date)
    clean_target_date = validate_ohlcv_date(
        target_date or datetime.now().date().isoformat()
    )

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_ohlcv_daily",
            "running",
            "Equity OHLCV daily collection started.",
            current_user=current_user
        )

        instruments = get_equity_ohlcv_instruments(conn)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity instruments found. Please run Equity collection first."
            )

        if not requested_target_date:
            resolved_target_date = resolve_latest_available_ohlcv_date(
                access_token=access_token,
                instruments=instruments,
                target_date=clean_target_date
            )

            if resolved_target_date != clean_target_date:
                update_sync_run_message(
                    conn,
                    sync_id,
                    (
                        "Equity OHLCV daily collection started. "
                        f"Latest available Upstox date resolved to {resolved_target_date}."
                    )
                )
                clean_target_date = resolved_target_date

        if ohlcv_daily_collected_for_date(conn, clean_target_date):
            total_records = get_ohlcv_daily_count(conn)

            finish_sync_run(
                conn,
                sync_id,
                "success",
                f"OHLCV daily data already collected for {clean_target_date}. Daily refresh skipped.",
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "success",
                "message": f"OHLCV daily data already collected for {clean_target_date}. Daily refresh skipped.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
                "skipped": True,
                "target_date": clean_target_date
            }

        from_date = clean_target_date
        to_date = clean_target_date
        processed_instruments = 0
        total_instruments = len(instruments)

        for instrument in instruments:
            check_sync_cancelled(conn, sync_id)
            processed_instruments += 1

            instrument_key = instrument["instrument_key"]
            trading_symbol = instrument["trading_symbol"]

            try:
                candles = get_upstox_daily_candles(
                    access_token=access_token,
                    instrument_key=instrument_key,
                    from_date=from_date,
                    to_date=to_date
                )
            except HTTPException as error:
                print(
                    "OHLCV candle fetch skipped: "
                    f"{trading_symbol} ({instrument_key}) - {error.detail}"
                )
                continue

            mapped_rows = [
                mapped_row
                for mapped_row in [
                    map_ohlcv_candle(
                        instrument_key=instrument_key,
                        trading_symbol=trading_symbol,
                        candle=candle
                    )
                    for candle in candles
                ]
                if mapped_row
            ]

            if mapped_rows:
                total_records += insert_ohlcv_daily_rows(conn, mapped_rows)
                conn.commit()

            if processed_instruments == 1 or processed_instruments % 50 == 0:
                update_sync_run_progress(
                    conn,
                    sync_id,
                    (
                        f"Equity OHLCV daily collection running for {clean_target_date}. "
                        f"Processed {processed_instruments}/{total_instruments} instruments, "
                        f"downloaded {total_records} candles."
                    ),
                    total_records
                )

            time.sleep(OHLCV_API_SLEEP_SECONDS)

        if total_records <= 0:
            message = (
                "No Equity OHLCV candles were returned by Upstox "
                f"for {clean_target_date}."
            )

            finish_sync_run(
                conn,
                sync_id,
                "failed",
                message,
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "failed",
                "message": message,
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
                "skipped": False,
                "target_date": clean_target_date
            }

        finish_sync_run(
            conn,
            sync_id,
            "success",
            f"Equity OHLCV daily data collected for {clean_target_date}.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": f"Equity OHLCV daily data collected for {clean_target_date}.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "skipped": False,
            "target_date": clean_target_date
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Equity OHLCV daily collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Equity OHLCV daily collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "target_date": clean_target_date
        }

    except HTTPException as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                str(e.detail),
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Equity OHLCV daily collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to collect Equity OHLCV daily data: {e}"
        )

    finally:
        conn.close()


def sync_upstox_table_placeholder_service(
    current_user: dict,
    sync_type: str,
    label: str,
    table_name: str,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        sync_id = create_sync_run(
            conn,
            sync_type,
            "running",
            f"{label} collection started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_name};
        """).fetchone()
        total_records = int(row[0] or 0) if row else 0

        message = (
            f"{label} runner completed. External download source is not "
            "configured yet, so existing preview records were left unchanged."
        )

        finish_sync_run(
            conn,
            sync_id,
            "success",
            message,
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": message,
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "skipped": True
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                f"{label} collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": f"{label} collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"{label} collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run {label} collection: {e}"
        )

    finally:
        conn.close()


def get_upstox_news(
    access_token: str,
    instrument_keys: List[str],
    page_number: int = 1,
    page_size: int = 100
) -> Dict[str, Any]:
    return upstox_api_get(
        access_token,
        "/news",
        {
            "category": "instrument_keys",
            "instrument_keys": ",".join(instrument_keys),
            "page_number": str(page_number),
            "page_size": str(page_size)
        }
    )


def get_upstox_fundamental_data(
    access_token: str,
    isin: str,
    endpoint: str,
    params: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    return upstox_api_get(
        access_token,
        f"/fundamentals/{urllib.parse.quote(isin, safe='')}/{endpoint}",
        params or {}
    )


def get_upstox_market_activity(
    access_token: str,
    path: str,
    data_type: str = "NSE_EQ|CASH",
    interval: str = "1D"
) -> Dict[str, Any]:
    return upstox_api_get(
        access_token,
        path,
        {
            "data_type": data_type,
            "interval": interval
        }
    )


def insert_equity_news_rows(conn, rows: List[List[Any]]) -> int:
    if not rows:
        return 0

    for row in rows:
        conn.execute("""
            DELETE FROM equity_news
            WHERE news_id = ?;
        """, [row[0]])

    conn.executemany("""
        INSERT INTO equity_news (
            news_id,
            instrument_key,
            trading_symbol,
            title,
            summary,
            source,
            url,
            published_at,
            thumbnail,
            raw_json,
            ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, rows)

    return len(rows)


def map_equity_news_rows(
    instruments_by_key: Dict[str, Dict[str, str]],
    response: Dict[str, Any]
) -> List[List[Any]]:
    data = response.get("data") if isinstance(response, dict) else {}

    if not isinstance(data, dict):
        return []

    rows = []

    for instrument_key, articles in data.items():
        instrument = instruments_by_key.get(instrument_key, {})
        trading_symbol = instrument.get("trading_symbol") or instrument_key

        if not isinstance(articles, list):
            continue

        for article in articles:
            if not isinstance(article, dict):
                continue

            url = safe_text(article.get("article_link"))
            published_time = article.get("published_time")
            news_id = deterministic_id(instrument_key, url, published_time)

            rows.append([
                news_id,
                instrument_key,
                trading_symbol,
                safe_text(article.get("heading")),
                safe_text(article.get("summary")),
                "Upstox",
                url,
                milliseconds_to_timestamp(published_time),
                safe_text(article.get("thumbnail")),
                json_text(article)
            ])

    return rows


def insert_fundamentals_rows(conn, rows: List[List[Any]]) -> int:
    if not rows:
        return 0

    for row in rows:
        conn.execute("""
            DELETE FROM fundamentals
            WHERE instrument_key = ?
              AND report_date = ?
              AND period_type = ?;
        """, [row[0], row[3], row[4]])

    conn.executemany("""
        INSERT INTO fundamentals (
            instrument_key,
            isin,
            trading_symbol,
            report_date,
            period_type,
            revenue,
            net_profit,
            eps,
            pe_ratio,
            debt_to_equity,
            roe,
            cash_from_operations,
            promoter_holding_pct,
            fii_holding_pct,
            dii_holding_pct,
            raw_json,
            ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, rows)

    return len(rows)


def map_fundamentals_rows(
    instrument: Dict[str, str],
    income_response: Dict[str, Any],
    ratios_response: Dict[str, Any],
    holdings_response: Dict[str, Any]
) -> List[List[Any]]:
    income_data = income_response.get("data") if isinstance(income_response, dict) else {}
    ratios = ratios_response.get("data") if isinstance(ratios_response, dict) else []
    holdings = holdings_response.get("data") if isinstance(holdings_response, dict) else []

    if not isinstance(income_data, dict):
        return []

    income_statement = income_data.get("income_statement")
    full_statement = income_data.get("full_statement")

    if not isinstance(income_statement, list):
        income_statement = []

    if not isinstance(full_statement, list):
        full_statement = []

    if not isinstance(ratios, list):
        ratios = []

    if not isinstance(holdings, list):
        holdings = []

    revenue_section = get_category_section(income_statement, "revenue")
    net_profit_section = get_category_section(income_statement, "net_profit")
    eps_section = (
        get_full_statement_section(full_statement, "EPS - Basic")
        or get_full_statement_section(full_statement, "EPS - Diluted")
    )
    promoter_section = get_category_section(holdings, "promoters")
    fii_section = get_category_section(holdings, "fii")
    dii_section = (
        get_category_section(holdings, "dii")
        or get_category_section(holdings, "other_dii")
    )

    period_values = set()

    for section in [revenue_section, net_profit_section, eps_section]:
        history = section.get("history") if isinstance(section, dict) else []
        if isinstance(history, list):
            for item in history:
                if isinstance(item, dict) and safe_text(item.get("period")):
                    period_values.add(safe_text(item.get("period")))

    rows = []
    period_type = safe_text(income_data.get("time_period")) or "yearly"
    raw_payload = json_text({
        "income_statement": income_response,
        "key_ratios": ratios_response,
        "share_holdings": holdings_response
    })

    for period in sorted(period_values, reverse=True):
        report_date = parse_upstox_period_date(period)

        if not report_date:
            continue

        rows.append([
            instrument["instrument_key"],
            instrument["isin"],
            instrument["trading_symbol"],
            report_date,
            period_type,
            get_metric_history_value(revenue_section, period),
            get_metric_history_value(net_profit_section, period),
            get_metric_history_value(eps_section, period),
            get_named_metric(ratios, "P/E"),
            None,
            get_named_metric(ratios, "ROE"),
            None,
            get_metric_history_value(promoter_section, period),
            get_metric_history_value(fii_section, period),
            get_metric_history_value(dii_section, period),
            raw_payload
        ])

    return rows


def insert_corporate_action_rows(conn, rows: List[List[Any]]) -> int:
    if not rows:
        return 0

    for row in rows:
        conn.execute("""
            DELETE FROM corporate_actions
            WHERE instrument_key = ?
              AND action_type = ?
              AND ex_date = ?;
        """, [row[0], row[3], row[4]])

    conn.executemany("""
        INSERT INTO corporate_actions (
            instrument_key,
            isin,
            trading_symbol,
            action_type,
            ex_date,
            record_date,
            amount,
            ratio,
            remarks,
            raw_json,
            ingested_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, rows)

    return len(rows)


def map_corporate_action_rows(
    instrument: Dict[str, str],
    response: Dict[str, Any]
) -> List[List[Any]]:
    data = response.get("data") if isinstance(response, dict) else []

    if not isinstance(data, list):
        return []

    rows = []

    for action in data:
        if not isinstance(action, dict):
            continue

        details = action.get("event_details")
        details_map = {}

        if isinstance(details, list):
            for detail in details:
                if isinstance(detail, dict):
                    details_map[safe_text(detail.get("name"))] = safe_text(
                        detail.get("value")
                    )

        ex_date = (
            parse_upstox_display_date(details_map.get("Ex dividend date"))
            or parse_upstox_display_date(details_map.get("Ex date"))
            or parse_upstox_display_date(action.get("expiry_date"))
        )

        if not ex_date:
            continue

        remarks = (
            details_map.get("Details")
            or details_map.get("Dividend type")
            or json_text(details_map)
        )

        rows.append([
            instrument["instrument_key"],
            instrument["isin"],
            instrument["trading_symbol"],
            safe_text(action.get("name")) or "Corporate Action",
            ex_date,
            parse_upstox_display_date(details_map.get("Record date")),
            safe_float(action.get("amount")),
            safe_text(action.get("ratio")),
            remarks,
            json_text(action)
        ])

    return rows


def insert_fii_dii_activity_rows(conn, rows: List[List[Any]]) -> int:
    if not rows:
        return 0

    for row in rows:
        conn.execute("""
            DELETE FROM fii_dii_activity
            WHERE date = ?
              AND category = ?;
        """, [row[0], row[1]])

    conn.executemany("""
        INSERT INTO fii_dii_activity (
            date,
            category,
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
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, rows)

    return len(rows)


def map_market_activity_rows(
    category: str,
    response: Dict[str, Any],
    data_type: str = "NSE_EQ|CASH"
) -> List[List[Any]]:
    data = response.get("data") if isinstance(response, dict) else {}
    records = data.get(data_type) if isinstance(data, dict) else []

    if not isinstance(records, list):
        return []

    rows = []

    for record in records:
        if not isinstance(record, dict):
            continue

        activity_date = milliseconds_to_timestamp(record.get("time_stamp"))

        if not activity_date:
            continue

        buy_value = safe_float(record.get("buy_amount")) or 0
        sell_value = safe_float(record.get("sell_amount")) or 0

        rows.append([
            activity_date.date().isoformat(),
            category,
            buy_value,
            sell_value,
            buy_value - sell_value,
            safe_int(record.get("buy_contracts")) or 0,
            safe_int(record.get("sell_contracts")) or 0,
            safe_int(record.get("oi_contracts")) or 0,
            safe_float(record.get("oi_amount")) or 0,
            json_text({
                "data_type": data_type,
                "record": record
            })
        ])

    return rows


def sync_upstox_equity_news_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)
        instruments = get_equity_data_collection_instruments(conn)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity instruments found. Please run Equity collection first."
            )

        sync_id = create_sync_run(
            conn,
            "upstox_equity_news",
            "running",
            "Equity News collection started.",
            current_user=current_user
        )

        instruments_by_key = {
            instrument["instrument_key"]: instrument
            for instrument in instruments
        }

        for start_index in range(0, len(instruments), 30):
            check_sync_cancelled(conn, sync_id)
            batch = instruments[start_index:start_index + 30]
            instrument_keys = [item["instrument_key"] for item in batch]

            page_number = 1

            while True:
                check_sync_cancelled(conn, sync_id)
                response = get_upstox_news(
                    access_token=access_token,
                    instrument_keys=instrument_keys,
                    page_number=page_number,
                    page_size=100
                )
                rows = map_equity_news_rows(instruments_by_key, response)
                total_records += insert_equity_news_rows(conn, rows)
                conn.commit()

                metadata = response.get("metadata") if isinstance(response, dict) else {}
                page = metadata.get("page") if isinstance(metadata, dict) else {}
                total_pages = int(page.get("total_pages") or 0) if isinstance(page, dict) else 0

                if page_number >= max(1, total_pages):
                    break

                page_number += 1
                time.sleep(API_SLEEP_SECONDS)

            processed = min(start_index + 30, len(instruments))
            update_sync_run_progress(
                conn,
                sync_id,
                (
                    f"Equity News collection running. "
                    f"Processed {processed}/{len(instruments)} instruments, "
                    f"saved {total_records} articles."
                ),
                total_records
            )
            time.sleep(API_SLEEP_SECONDS)

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Equity News collected from Upstox successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Equity News collected from Upstox successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Equity News collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Equity News collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Equity News collection failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Equity News collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run Equity News collection: {e}"
        )

    finally:
        conn.close()


def sync_upstox_fundamentals_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)
        instruments = get_equity_data_collection_instruments(conn)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity instruments found. Please run Equity collection first."
            )

        sync_id = create_sync_run(
            conn,
            "upstox_fundamentals",
            "running",
            "Fundamentals collection started.",
            current_user=current_user
        )

        for index, instrument in enumerate(instruments, start=1):
            check_sync_cancelled(conn, sync_id)
            isin = instrument["isin"]

            try:
                income_response = get_upstox_fundamental_data(
                    access_token,
                    isin,
                    "income-statement",
                    {
                        "type": "consolidated",
                        "time_period": "yearly",
                        "fs": "true"
                    }
                )
                ratios_response = get_upstox_fundamental_data(
                    access_token,
                    isin,
                    "key-ratios"
                )
                holdings_response = get_upstox_fundamental_data(
                    access_token,
                    isin,
                    "share-holdings"
                )
            except HTTPException as error:
                print(
                    "Fundamentals fetch skipped: "
                    f"{instrument['trading_symbol']} ({isin}) - {error.detail}"
                )
                continue

            rows = map_fundamentals_rows(
                instrument=instrument,
                income_response=income_response,
                ratios_response=ratios_response,
                holdings_response=holdings_response
            )
            total_records += insert_fundamentals_rows(conn, rows)
            conn.commit()

            if index == 1 or index % 25 == 0:
                update_sync_run_progress(
                    conn,
                    sync_id,
                    (
                        f"Fundamentals collection running. "
                        f"Processed {index}/{len(instruments)} instruments, "
                        f"saved {total_records} rows."
                    ),
                    total_records
                )

            time.sleep(API_SLEEP_SECONDS)

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Fundamentals collected from Upstox successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Fundamentals collected from Upstox successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Fundamentals collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Fundamentals collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Fundamentals collection failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Fundamentals collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run Fundamentals collection: {e}"
        )

    finally:
        conn.close()


def sync_upstox_corporate_actions_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)
        instruments = get_equity_data_collection_instruments(conn)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No equity instruments found. Please run Equity collection first."
            )

        sync_id = create_sync_run(
            conn,
            "upstox_corporate_actions",
            "running",
            "Corporate Actions collection started.",
            current_user=current_user
        )

        for index, instrument in enumerate(instruments, start=1):
            check_sync_cancelled(conn, sync_id)

            try:
                response = get_upstox_fundamental_data(
                    access_token,
                    instrument["isin"],
                    "corporate-actions"
                )
            except HTTPException as error:
                print(
                    "Corporate Actions fetch skipped: "
                    f"{instrument['trading_symbol']} ({instrument['isin']}) - {error.detail}"
                )
                continue

            rows = map_corporate_action_rows(instrument, response)
            total_records += insert_corporate_action_rows(conn, rows)
            conn.commit()

            if index == 1 or index % 25 == 0:
                update_sync_run_progress(
                    conn,
                    sync_id,
                    (
                        f"Corporate Actions collection running. "
                        f"Processed {index}/{len(instruments)} instruments, "
                        f"saved {total_records} actions."
                    ),
                    total_records
                )

            time.sleep(API_SLEEP_SECONDS)

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Corporate Actions collected from Upstox successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Corporate Actions collected from Upstox successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Corporate Actions collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Corporate Actions collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Corporate Actions collection failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Corporate Actions collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run Corporate Actions collection: {e}"
        )

    finally:
        conn.close()


def sync_upstox_fii_dii_activity_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_fii_dii_activity",
            "running",
            "FII/DII Activity collection started.",
            current_user=current_user
        )

        fii_response = get_upstox_market_activity(
            access_token,
            "/market/fii",
            "NSE_EQ|CASH",
            "1D"
        )
        check_sync_cancelled(conn, sync_id)
        dii_response = get_upstox_market_activity(
            access_token,
            "/market/dii",
            "NSE_EQ|CASH",
            "1D"
        )

        rows = (
            map_market_activity_rows("FII", fii_response, "NSE_EQ|CASH")
            + map_market_activity_rows("DII", dii_response, "NSE_EQ|CASH")
        )
        total_records = insert_fii_dii_activity_rows(conn, rows)
        conn.commit()

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "FII/DII Activity collected from Upstox successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "FII/DII Activity collected from Upstox successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "FII/DII Activity collection cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "FII/DII Activity collection cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "FII/DII Activity collection failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"FII/DII Activity collection failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run FII/DII Activity collection: {e}"
        )

    finally:
        conn.close()


def sync_upstox_expired_instruments_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        access_token = get_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_expired_instruments",
            "running",
            "Expired instrument dump started.",
            current_user=current_user
        )

        for underlying_key in DEFAULT_UNDERLYING_KEYS:
            check_sync_cancelled(conn, sync_id)

            expiries = get_expiries(access_token, underlying_key)

            check_sync_cancelled(conn, sync_id)

            for expiry_date in expiries:
                check_sync_cancelled(conn, sync_id)

                if not expired_instruments_exist(
                    conn=conn,
                    underlying_key=underlying_key,
                    expiry_date=expiry_date,
                    source_type="expired_option"
                ):
                    option_rows = get_expired_option_contracts(
                        access_token=access_token,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date
                    )

                    clear_expired_instruments_for_source(
                        conn=conn,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date,
                        source_type="expired_option"
                    )

                    total_records += insert_expired_instruments(
                        conn=conn,
                        rows=option_rows,
                        source_type="expired_option",
                        sync_id=sync_id
                    )

                    conn.commit()
                    time.sleep(API_SLEEP_SECONDS)

                check_sync_cancelled(conn, sync_id)

                if not expired_instruments_exist(
                    conn=conn,
                    underlying_key=underlying_key,
                    expiry_date=expiry_date,
                    source_type="expired_future"
                ):
                    future_rows = get_expired_future_contracts(
                        access_token=access_token,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date
                    )

                    clear_expired_instruments_for_source(
                        conn=conn,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date,
                        source_type="expired_future"
                    )

                    total_records += insert_expired_instruments(
                        conn=conn,
                        rows=future_rows,
                        source_type="expired_future",
                        sync_id=sync_id
                    )

                    conn.commit()
                    time.sleep(API_SLEEP_SECONDS)

                check_sync_cancelled(conn, sync_id)

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Expired instruments dumped successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Expired instruments dumped successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Expired instrument dump cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Expired instrument dump cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                str(e.detail),
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Expired instrument dump failed: {e}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump expired instruments: {e}"
        )

    finally:
        conn.close()


def sync_upstox_all_instruments_service(current_user: dict):
    started_at = datetime.now()
    total_records = 0
    jobs = {}

    job_steps = [
        (
            "current",
            sync_upstox_current_instruments_service,
            {"clear_cancel_at_start": True}
        ),
        (
            "expired",
            sync_upstox_expired_instruments_service,
            {"clear_cancel_at_start": False}
        ),
        (
            "equity",
            sync_upstox_equity_instruments_service,
            {"clear_cancel_at_start": False}
        ),
        (
            "ohlcv_daily",
            sync_upstox_ohlcv_daily_service,
            {"target_date": None, "clear_cancel_at_start": False}
        ),
        (
            "equity_news",
            sync_upstox_equity_news_service,
            {"clear_cancel_at_start": False}
        ),
        (
            "fundamentals",
            sync_upstox_fundamentals_service,
            {"clear_cancel_at_start": False}
        ),
        (
            "corporate_actions",
            sync_upstox_corporate_actions_service,
            {"clear_cancel_at_start": False}
        ),
        (
            "fii_dii_activity",
            sync_upstox_fii_dii_activity_service,
            {"clear_cancel_at_start": False}
        )
    ]

    try:
        for job_key, job_function, kwargs in job_steps:
            try:
                result = job_function(current_user, **kwargs)
            except HTTPException as error:
                result = {
                    "status": "failed",
                    "message": str(error.detail),
                    "total_records": 0,
                    "duration_seconds": 0
                }
            except Exception as error:
                result = {
                    "status": "failed",
                    "message": str(error),
                    "total_records": 0,
                    "duration_seconds": 0
                }

            jobs[job_key] = result
            total_records += int(result.get("total_records") or 0)

            if result.get("status") == "cancelled":
                return {
                    "status": "cancelled",
                    "message": f"{get_sync_type_label(job_key)} collection cancelled.",
                    "total_records": total_records,
                    "duration_seconds": duration_seconds(started_at),
                    "jobs": jobs
                }

    finally:
        clear_cancel_signal()

    failed_jobs = [
        job_key
        for job_key, result in jobs.items()
        if result.get("status") == "failed"
    ]

    return {
        "status": "partial_success" if failed_jobs else "success",
        "message": (
            "All configured data collection runners completed with some failures."
            if failed_jobs
            else "All configured data collection runners completed."
        ),
        "total_records": total_records,
        "duration_seconds": duration_seconds(started_at),
        "jobs": jobs
    }


def normalize_page(value: int) -> int:
    try:
        page = int(value)
    except Exception:
        return 1

    return max(page, 1)


def normalize_page_size(value: int) -> int:
    try:
        page_size = int(value)
    except Exception:
        return 50

    if page_size < 10:
        return 10

    if page_size > 200:
        return 200

    return page_size


def build_preview_filters(
    search: str,
    source_type: str,
    segment: str,
    instrument_type: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_source_type = source_type.strip() if source_type else "all"
    clean_segment = segment.strip() if segment else "all"
    clean_instrument_type = instrument_type.strip() if instrument_type else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(name, '')) LIKE ?
                OR LOWER(COALESCE(segment, '')) LIKE ?
                OR LOWER(COALESCE(exchange, '')) LIKE ?
                OR LOWER(COALESCE(instrument_type, '')) LIKE ?
                OR LOWER(COALESCE(underlying_symbol, '')) LIKE ?
                OR LOWER(COALESCE(underlying_key, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_source_type != "all":
        where_clauses.append("source_type = ?")
        params.append(clean_source_type)

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    if clean_instrument_type != "all":
        where_clauses.append("instrument_type = ?")
        params.append(clean_instrument_type)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def build_equity_preview_filters(search: str, security_type: str):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_security_type = security_type.strip() if security_type else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(name, '')) LIKE ?
                OR LOWER(COALESCE(isin, '')) LIKE ?
                OR LOWER(COALESCE(exchange, '')) LIKE ?
                OR LOWER(COALESCE(segment, '')) LIKE ?
                OR LOWER(COALESCE(short_name, '')) LIKE ?
                OR LOWER(COALESCE(security_type, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_security_type != "all":
        where_clauses.append("security_type = ?")
        params.append(clean_security_type)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def build_ohlcv_daily_preview_filters(search: str, from_date: str, to_date: str):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_from_date = from_date.strip() if from_date else ""
    clean_to_date = to_date.strip() if to_date else ""

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([search_value, search_value])

    if clean_from_date:
        where_clauses.append("date >= ?")
        params.append(clean_from_date)

    if clean_to_date:
        where_clauses.append("date <= ?")
        params.append(clean_to_date)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_instrument_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "name": row[2],
        "segment": row[3],
        "exchange": row[4],
        "instrument_type": row[5],
        "expiry": str(row[6]) if row[6] else None,
        "strike_price": row[7],
        "lot_size": row[8],
        "source_type": row[9],
        "underlying_key": row[10],
        "underlying_symbol": row[11],
        "synced_at": str(row[12]) if row[12] else None
    }


def row_to_equity_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "name": row[2],
        "isin": row[3],
        "exchange": row[4],
        "segment": row[5],
        "exchange_token": row[6],
        "tick_size": row[7],
        "lot_size": row[8],
        "freeze_quantity": row[9],
        "short_name": row[10],
        "security_type": row[11],
        "downloaded_at": str(row[12]) if row[12] else None
    }


def row_to_ohlcv_daily_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "date": str(row[2]) if row[2] else None,
        "open": row[3],
        "high": row[4],
        "low": row[5],
        "close": row[6],
        "volume": row[7],
        "oi": row[8],
        "ingested_at": str(row[9]) if row[9] else None
    }


def get_upstox_instruments_preview_service(
    search: str = "",
    source_type: str = "all",
    segment: str = "all",
    instrument_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_preview_filters(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_instruments
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                segment,
                exchange,
                instrument_type,
                expiry,
                strike_price,
                lot_size,
                source_type,
                underlying_key,
                underlying_symbol,
                synced_at
            FROM upstox_instruments
            {where_sql}
            ORDER BY synced_at DESC, segment, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_instrument_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_upstox_expired_instruments_preview_service(
    search: str = "",
    source_type: str = "all",
    segment: str = "all",
    instrument_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_preview_filters(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_expired_instruments
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                segment,
                exchange,
                instrument_type,
                expiry,
                strike_price,
                lot_size,
                source_type,
                underlying_key,
                underlying_symbol,
                synced_at
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY synced_at DESC, expiry DESC, segment, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_instrument_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_upstox_equity_instruments_preview_service(
    search: str = "",
    security_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_equity_preview_filters(
            search=search,
            security_type=security_type
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_equity_instruments
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                exchange_token,
                tick_size,
                lot_size,
                freeze_quantity,
                short_name,
                security_type,
                downloaded_at
            FROM upstox_equity_instruments
            {where_sql}
            ORDER BY downloaded_at DESC, trading_symbol, name
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_equity_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_ohlcv_daily_preview_service(
    search: str = "",
    from_date: str = "",
    to_date: str = "",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_ohlcv_daily_preview_filters(
            search=search,
            from_date=from_date,
            to_date=to_date
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM ohlcv_daily
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                date,
                open,
                high,
                low,
                close,
                volume,
                oi,
                ingested_at
            FROM ohlcv_daily
            {where_sql}
            ORDER BY date DESC, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_ohlcv_daily_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def build_equity_news_preview_filters(
    search: str,
    from_date: str,
    to_date: str,
    source: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_from_date = from_date.strip() if from_date else ""
    clean_to_date = to_date.strip() if to_date else ""
    clean_source = source.strip() if source else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(title, '')) LIKE ?
                OR LOWER(COALESCE(summary, '')) LIKE ?
                OR LOWER(COALESCE(source, '')) LIKE ?
                OR LOWER(COALESCE(url, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_source != "all":
        where_clauses.append("source = ?")
        params.append(clean_source)

    if clean_from_date:
        where_clauses.append("CAST(published_at AS DATE) >= ?")
        params.append(clean_from_date)

    if clean_to_date:
        where_clauses.append("CAST(published_at AS DATE) <= ?")
        params.append(clean_to_date)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def build_fundamentals_preview_filters(
    search: str,
    period_type: str,
    from_date: str,
    to_date: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_period_type = period_type.strip() if period_type else "all"
    clean_from_date = from_date.strip() if from_date else ""
    clean_to_date = to_date.strip() if to_date else ""

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(isin, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(period_type, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_period_type != "all":
        where_clauses.append("period_type = ?")
        params.append(clean_period_type)

    if clean_from_date:
        where_clauses.append("report_date >= ?")
        params.append(clean_from_date)

    if clean_to_date:
        where_clauses.append("report_date <= ?")
        params.append(clean_to_date)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def build_corporate_actions_preview_filters(
    search: str,
    action_type: str,
    from_date: str,
    to_date: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_action_type = action_type.strip() if action_type else "all"
    clean_from_date = from_date.strip() if from_date else ""
    clean_to_date = to_date.strip() if to_date else ""

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(isin, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(action_type, '')) LIKE ?
                OR LOWER(COALESCE(remarks, '')) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if clean_action_type != "all":
        where_clauses.append("action_type = ?")
        params.append(clean_action_type)

    if clean_from_date:
        where_clauses.append("ex_date >= ?")
        params.append(clean_from_date)

    if clean_to_date:
        where_clauses.append("ex_date <= ?")
        params.append(clean_to_date)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def build_fii_dii_activity_preview_filters(
    category: str,
    from_date: str,
    to_date: str
):
    where_clauses = []
    params = []

    clean_category = category.strip() if category else "all"
    clean_from_date = from_date.strip() if from_date else ""
    clean_to_date = to_date.strip() if to_date else ""

    if clean_category != "all":
        where_clauses.append("category = ?")
        params.append(clean_category)

    if clean_from_date:
        where_clauses.append("date >= ?")
        params.append(clean_from_date)

    if clean_to_date:
        where_clauses.append("date <= ?")
        params.append(clean_to_date)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_equity_news_preview(row):
    return {
        "news_id": row[0],
        "instrument_key": row[1],
        "trading_symbol": row[2],
        "title": row[3],
        "summary": row[4],
        "source": row[5],
        "url": row[6],
        "published_at": str(row[7]) if row[7] else None,
        "ingested_at": str(row[8]) if row[8] else None
    }


def row_to_fundamentals_preview(row):
    return {
        "instrument_key": row[0],
        "isin": row[1],
        "trading_symbol": row[2],
        "report_date": str(row[3]) if row[3] else None,
        "period_type": row[4],
        "revenue": row[5],
        "net_profit": row[6],
        "eps": row[7],
        "pe_ratio": row[8],
        "debt_to_equity": row[9],
        "roe": row[10],
        "cash_from_operations": row[11],
        "promoter_holding_pct": row[12],
        "fii_holding_pct": row[13],
        "dii_holding_pct": row[14],
        "ingested_at": str(row[15]) if row[15] else None
    }


def row_to_corporate_actions_preview(row):
    return {
        "instrument_key": row[0],
        "isin": row[1],
        "trading_symbol": row[2],
        "action_type": row[3],
        "ex_date": str(row[4]) if row[4] else None,
        "record_date": str(row[5]) if row[5] else None,
        "amount": row[6],
        "remarks": row[7],
        "ingested_at": str(row[8]) if row[8] else None
    }


def row_to_fii_dii_activity_preview(row):
    return {
        "date": str(row[0]) if row[0] else None,
        "category": row[1],
        "buy_value": row[2],
        "sell_value": row[3],
        "net_value": row[4],
        "ingested_at": str(row[5]) if row[5] else None
    }


def get_equity_news_preview_service(
    search: str = "",
    from_date: str = "",
    to_date: str = "",
    source: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_equity_news_preview_filters(
            search=search,
            from_date=from_date,
            to_date=to_date,
            source=source
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM equity_news
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                news_id,
                instrument_key,
                trading_symbol,
                title,
                summary,
                source,
                url,
                published_at,
                ingested_at
            FROM equity_news
            {where_sql}
            ORDER BY published_at DESC, ingested_at DESC, trading_symbol
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_equity_news_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_fundamentals_preview_service(
    search: str = "",
    period_type: str = "all",
    from_date: str = "",
    to_date: str = "",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_fundamentals_preview_filters(
            search=search,
            period_type=period_type,
            from_date=from_date,
            to_date=to_date
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM fundamentals
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                isin,
                trading_symbol,
                report_date,
                period_type,
                revenue,
                net_profit,
                eps,
                pe_ratio,
                debt_to_equity,
                roe,
                cash_from_operations,
                promoter_holding_pct,
                fii_holding_pct,
                dii_holding_pct,
                ingested_at
            FROM fundamentals
            {where_sql}
            ORDER BY report_date DESC, trading_symbol, period_type
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_fundamentals_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_corporate_actions_preview_service(
    search: str = "",
    action_type: str = "all",
    from_date: str = "",
    to_date: str = "",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_corporate_actions_preview_filters(
            search=search,
            action_type=action_type,
            from_date=from_date,
            to_date=to_date
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM corporate_actions
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                isin,
                trading_symbol,
                action_type,
                ex_date,
                record_date,
                amount,
                remarks,
                ingested_at
            FROM corporate_actions
            {where_sql}
            ORDER BY ex_date DESC, trading_symbol, action_type
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_corporate_actions_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()


def get_fii_dii_activity_preview_service(
    category: str = "all",
    from_date: str = "",
    to_date: str = "",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_fii_dii_activity_preview_filters(
            category=category,
            from_date=from_date,
            to_date=to_date
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM fii_dii_activity
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                date,
                category,
                buy_value,
                sell_value,
                net_value,
                ingested_at
            FROM fii_dii_activity
            {where_sql}
            ORDER BY date DESC, category
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_fii_dii_activity_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()

