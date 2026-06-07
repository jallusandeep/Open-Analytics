import gzip
import json
import time
from collections import deque
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data" / "upstox"
MASTER_INSTRUMENT_FILE = DATA_DIR / "upstox_instruments.json"
EXPIRED_INSTRUMENT_FILE = DATA_DIR / "upstox_expired_instruments.json"

UPSTOX_CURRENT_MASTER_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)

UPSTOX_CURRENT_HISTORICAL_V3_URL = "https://api.upstox.com/v3/historical-candle"
UPSTOX_CURRENT_INTRADAY_V3_URL = "https://api.upstox.com/v3/historical-candle/intraday"
UPSTOX_EXPIRED_HISTORICAL_URL = "https://api.upstox.com/v2/expired-instruments/historical-candle"

REQUEST_TIMEOUT_SECONDS = 180
UPSTOX_STANDARD_MAX_REQUESTS_PER_SECOND = 45
UPSTOX_STANDARD_MAX_REQUESTS_PER_MINUTE = 450
UPSTOX_STANDARD_MAX_REQUESTS_PER_30_MINUTES = 1800
UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS = 0.05
STALE_RUNNING_RUN_HOURS = 2
DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 4

CANCEL_SIGNAL_DIR = APP_ROOT / "runtime"
CANCEL_SIGNAL_FILE = CANCEL_SIGNAL_DIR / "upstox_data_collection.cancel"

DEFAULT_EXPIRED_UNDERLYING_KEYS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Fin Service",
    "NSE_INDEX|Nifty Midcap Select"
]
DEFAULT_EXPIRED_UNDERLYING_SEGMENT = "NSE_FO"
DEFAULT_EXPIRED_UNDERLYING_TYPES = ["INDEX", "EQUITY"]

EXPIRED_SOURCE_OPTION = "expired_option_contract"
EXPIRED_SOURCE_FUTURE = "expired_future_contract"

OHLCV_SYNC_TYPE = "upstox_ohlcv_daily"
OHLCV_CURRENT_SOURCE = "current"
OHLCV_EXPIRED_SOURCE = "expired"
OHLCV_HISTORICAL_MODE = "historical"
OHLCV_INTRADAY_MODE = "intraday"

OHLCV_ALLOWED_SOURCES = {OHLCV_CURRENT_SOURCE, OHLCV_EXPIRED_SOURCE}
OHLCV_ALLOWED_MODES = {OHLCV_HISTORICAL_MODE, OHLCV_INTRADAY_MODE}
OHLCV_DEFAULT_SOURCES = [OHLCV_CURRENT_SOURCE]
OHLCV_DEFAULT_MODES = [OHLCV_HISTORICAL_MODE]
OHLCV_DEFAULT_INTERVALS = ["day"]
OHLCV_DEFAULT_BATCH_SIZE = 25
OHLCV_DEFAULT_REQUEST_DELAY_MS = 500
OHLCV_DEFAULT_BATCH_DELAY_SECONDS = 2
OHLCV_DEFAULT_RETRY_COUNT = 3
OHLCV_CURRENT_HISTORY_START_DATE = date(2000, 1, 1)
OHLCV_INTRADAY_HISTORY_START_DATE = date(2022, 1, 1)
OHLCV_CURRENT_DAILY_MAX_DAYS = 3653
OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS = 31
OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS = 92
OHLCV_EXPIRED_MAX_DAYS = 3650

OHLCV_INTERVAL_OPTIONS = {
    "1minute": {"label": "1 minute", "unit": "minutes", "interval_value": 1, "expired_interval": "1minute"},
    "3minute": {"label": "3 minute", "unit": "minutes", "interval_value": 3, "expired_interval": "3minute"},
    "5minute": {"label": "5 minute", "unit": "minutes", "interval_value": 5, "expired_interval": "5minute"},
    "15minute": {"label": "15 minute", "unit": "minutes", "interval_value": 15, "expired_interval": "15minute"},
    "30minute": {"label": "30 minute", "unit": "minutes", "interval_value": 30, "expired_interval": "30minute"},
    "1hour": {"label": "1 hour", "unit": "hours", "interval_value": 1, "expired_interval": None},
    "day": {"label": "Day", "unit": "days", "interval_value": 1, "expired_interval": "day"},
    "week": {"label": "Week", "unit": "weeks", "interval_value": 1, "expired_interval": None},
    "month": {"label": "Month", "unit": "months", "interval_value": 1, "expired_interval": None}
}


class UpstoxRollingRateLimiter:
    def __init__(
        self,
        max_per_second: int = UPSTOX_STANDARD_MAX_REQUESTS_PER_SECOND,
        max_per_minute: int = UPSTOX_STANDARD_MAX_REQUESTS_PER_MINUTE,
        max_per_30_minutes: int = UPSTOX_STANDARD_MAX_REQUESTS_PER_30_MINUTES
    ):
        self.max_per_second = max(1, int(max_per_second))
        self.max_per_minute = max(1, int(max_per_minute))
        self.max_per_30_minutes = max(1, int(max_per_30_minutes))
        self.request_times = deque()

    def wait_for_slot(self):
        while True:
            now = time.monotonic()

            while self.request_times and now - self.request_times[0] >= 1800:
                self.request_times.popleft()

            requests_last_second = 0
            requests_last_minute = 0
            requests_last_30_minutes = len(self.request_times)

            for request_time in reversed(self.request_times):
                age = now - request_time

                if age <= 1:
                    requests_last_second += 1

                if age <= 60:
                    requests_last_minute += 1
                else:
                    break

            if (
                requests_last_second < self.max_per_second
                and requests_last_minute < self.max_per_minute
                and requests_last_30_minutes < self.max_per_30_minutes
            ):
                self.request_times.append(now)
                return

            sleep_seconds = UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS

            if requests_last_30_minutes >= self.max_per_30_minutes and self.request_times:
                sleep_seconds = max(
                    sleep_seconds,
                    1800 - (now - self.request_times[0]) + UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS
                )
            elif requests_last_minute >= self.max_per_minute:
                minute_window_start = None

                for request_time in self.request_times:
                    if now - request_time <= 60:
                        minute_window_start = request_time
                        break

                if minute_window_start is not None:
                    sleep_seconds = max(
                        sleep_seconds,
                        60 - (now - minute_window_start) + UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS
                    )
            elif requests_last_second >= self.max_per_second:
                second_window_start = None

                for request_time in self.request_times:
                    if now - request_time <= 1:
                        second_window_start = request_time
                        break

                if second_window_start is not None:
                    sleep_seconds = max(
                        sleep_seconds,
                        1 - (now - second_window_start) + UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS
                    )

            print(f"Upstox API rate limit guard sleeping {round(sleep_seconds, 2)} seconds.")
            time.sleep(sleep_seconds)


class SyncCancelled(Exception):
    pass


def is_upstox_expired_permission_error(error_text: str) -> bool:
    lowered_error = (error_text or "").lower()

    return (
        "udapi100067" in lowered_error
        or "udapi1149" in lowered_error
        or "read only token" in lowered_error
        or "upstox plus" in lowered_error
        or "not permitted" in lowered_error
        or "permission" in lowered_error
    )


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


def safe_strip(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def normalize_upstox_token(access_token: Any) -> str:
    token = safe_strip(access_token)

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return token


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


def get_saved_upstox_access_token(conn) -> str:
    row = conn.execute("""
        SELECT access_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstox connection is not configured. Save analytics token in Connections first."
        )

    connection_status = row[1] or "saved"

    if connection_status == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox connection is disconnected. Save analytics token in Connections first."
        )

    access_token = normalize_upstox_token(row[0])

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox analytics token is missing. Save analytics token in Connections first."
        )

    return access_token


def get_saved_upstox_analytical_token(conn) -> str:
    row = conn.execute("""
        SELECT analytical_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upstox connection is not configured. Save analytical token in Connections first."
        )

    connection_status = row[1] or "saved"

    if connection_status == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox connection is disconnected. Save analytical token in Connections first."
        )

    analytical_token = normalize_upstox_token(row[0])

    if not analytical_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox analytical token is missing. Save analytical token in Connections first."
        )

    return analytical_token


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


def download_upstox_master_gz_file_once() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    gz_file = MASTER_INSTRUMENT_FILE.with_suffix(".json.gz")
    temp_gz_file = gz_file.with_suffix(".gz.download")

    request = urllib.request.Request(
        UPSTOX_CURRENT_MASTER_URL,
        headers={
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    print("Downloading Upstox current instruments compressed master file.")
    print("No token required for current instruments.")
    print(f"URL  : {UPSTOX_CURRENT_MASTER_URL}")
    print(f"Save : {gz_file}")

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            with open(temp_gz_file, "wb") as output_file:
                while True:
                    chunk = response.read(DOWNLOAD_CHUNK_SIZE)

                    if not chunk:
                        break

                    output_file.write(chunk)

        temp_gz_file.replace(gz_file)

        print(f"Download completed: {gz_file}")

        return gz_file

    except Exception:
        try:
            if temp_gz_file.exists():
                temp_gz_file.unlink()
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
            print(f"Deleted temporary Upstox data file: {resolved_file}")
    except Exception as error:
        print(f"Unable to delete temporary Upstox data file: {error}")


def import_current_instruments_from_local_file(conn, sync_id: str, local_file: Path) -> int:
    check_sync_cancelled(conn, sync_id)

    duckdb_path = normalize_duckdb_file_path(local_file)

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
    """, [duckdb_path])

    print(f"DuckDB insert time: {round(time.time() - insert_started_at, 2)} seconds")

    total_rows = conn.execute("""
        SELECT COUNT(*)
        FROM upstox_instruments
        WHERE source_type = 'bod_complete';
    """).fetchone()[0]

    print(f"Current instruments inserted directly into DB: {total_rows}")

    return int(total_rows or 0)


def import_upstox_client():
    try:
        import upstox_client
        return upstox_client
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Upstox Python SDK is not installed. "
                "Run: pip install -r backend/requirements.txt"
            )
        )


def create_expired_instrument_api(access_token: str):
    upstox_client = import_upstox_client()

    configuration = upstox_client.Configuration()
    configuration.access_token = normalize_upstox_token(access_token)

    return upstox_client.ExpiredInstrumentApi(
        upstox_client.ApiClient(configuration)
    )


def model_to_dict(value: Any):
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, list):
        return [model_to_dict(item) for item in value]

    if isinstance(value, tuple):
        return [model_to_dict(item) for item in value]

    if isinstance(value, dict):
        return {
            str(key): model_to_dict(item)
            for key, item in value.items()
            if not str(key).startswith("_")
        }

    if hasattr(value, "to_dict"):
        try:
            return model_to_dict(value.to_dict())
        except Exception:
            pass

    if hasattr(value, "__dict__"):
        return {
            str(key): model_to_dict(item)
            for key, item in value.__dict__.items()
            if not str(key).startswith("_")
        }

    return str(value)


def extract_api_data(response: Any):
    payload = model_to_dict(response)

    if isinstance(payload, dict):
        data = payload.get("data")

        if data is not None:
            return data

        if "expiries" in payload:
            return payload.get("expiries")

        if "expiry_dates" in payload:
            return payload.get("expiry_dates")

    return payload


def normalize_expiry_value(value: Any) -> Optional[str]:
    if value is None:
        return None

    clean_value = str(value).strip()

    if not clean_value:
        return None

    return clean_value[:10]


def first_available(data: dict, keys: List[str], default=None):
    for key in keys:
        value = data.get(key)

        if value is not None:
            return value

    return default


def normalize_expired_contract_record(
    record: dict,
    source_type: str,
    underlying_key: str,
    expiry_date: str
) -> dict:
    plain_record = model_to_dict(record)

    if not isinstance(plain_record, dict):
        plain_record = {
            "value": plain_record
        }

    expiry = first_available(
        plain_record,
        ["expiry", "expiry_date", "expiration_date"],
        expiry_date
    )

    instrument_type = first_available(
        plain_record,
        ["instrument_type", "type"],
        "OPT" if source_type == EXPIRED_SOURCE_OPTION else "FUT"
    )

    return {
        "instrument_key": first_available(plain_record, ["instrument_key", "instrumentKey"]),
        "segment": first_available(plain_record, ["segment"]),
        "name": first_available(plain_record, ["name"]),
        "exchange": first_available(plain_record, ["exchange"]),
        "instrument_type": instrument_type,
        "trading_symbol": first_available(
            plain_record,
            ["trading_symbol", "tradingSymbol", "symbol"]
        ),
        "exchange_token": first_available(
            plain_record,
            ["exchange_token", "exchangeToken"]
        ),
        "expiry": normalize_expiry_value(expiry),
        "strike_price": first_available(
            plain_record,
            ["strike_price", "strikePrice", "strike"]
        ),
        "lot_size": first_available(
            plain_record,
            ["lot_size", "lotSize"]
        ),
        "minimum_lot": first_available(
            plain_record,
            ["minimum_lot", "minimumLot"]
        ),
        "freeze_quantity": first_available(
            plain_record,
            ["freeze_quantity", "freezeQuantity"]
        ),
        "tick_size": first_available(
            plain_record,
            ["tick_size", "tickSize"]
        ),
        "weekly": first_available(plain_record, ["weekly"]),
        "underlying_key": first_available(
            plain_record,
            ["underlying_key", "underlyingKey"],
            underlying_key
        ),
        "underlying_symbol": first_available(
            plain_record,
            ["underlying_symbol", "underlyingSymbol"]
        ),
        "underlying_type": first_available(
            plain_record,
            ["underlying_type", "underlyingType"]
        ),
        "source_type": source_type,
        "raw_json": json.dumps(plain_record, ensure_ascii=False, default=str)
    }


def normalize_expiry_list(response: Any) -> List[str]:
    data = extract_api_data(response)

    values = []

    if isinstance(data, list):
        values = data
    elif isinstance(data, dict):
        for key in ("expiries", "expiry_dates", "expiryDates", "data"):
            if isinstance(data.get(key), list):
                values = data.get(key)
                break

    normalized = []

    for item in values:
        if isinstance(item, dict):
            expiry = first_available(
                item,
                ["expiry", "expiry_date", "expiryDate", "date"]
            )
        else:
            expiry = item

        expiry_value = normalize_expiry_value(expiry)

        if expiry_value:
            normalized.append(expiry_value)

    return sorted(set(normalized))


def normalize_contract_list(
    response: Any,
    source_type: str,
    underlying_key: str,
    expiry_date: str
) -> List[dict]:
    data = extract_api_data(response)

    if isinstance(data, dict):
        possible_rows = None

        for key in ("contracts", "instruments", "data"):
            if isinstance(data.get(key), list):
                possible_rows = data.get(key)
                break

        if possible_rows is None:
            possible_rows = [data]

        data = possible_rows

    if not isinstance(data, list):
        return []

    rows = []

    for item in data:
        normalized = normalize_expired_contract_record(
            record=item,
            source_type=source_type,
            underlying_key=underlying_key,
            expiry_date=expiry_date
        )

        if normalized.get("instrument_key"):
            rows.append(normalized)

    return rows


def unique_preserve_order(values: List[str]) -> List[str]:
    seen = set()
    unique_values = []

    for value in values:
        clean_value = safe_strip(value)

        if clean_value and clean_value not in seen:
            seen.add(clean_value)
            unique_values.append(clean_value)

    return unique_values


def get_configured_expired_underlying_keys(
    conn,
    segment: str = DEFAULT_EXPIRED_UNDERLYING_SEGMENT,
    underlying_types: Optional[List[str]] = None
) -> List[str]:
    clean_segment = safe_strip(segment) or DEFAULT_EXPIRED_UNDERLYING_SEGMENT
    clean_underlying_types = unique_preserve_order(
        underlying_types or DEFAULT_EXPIRED_UNDERLYING_TYPES
    )

    if not clean_underlying_types:
        clean_underlying_types = DEFAULT_EXPIRED_UNDERLYING_TYPES.copy()

    type_placeholders = ", ".join(["?"] * len(clean_underlying_types))

    try:
        rows = conn.execute(f"""
            SELECT
                underlying_key,
                MIN(COALESCE(underlying_symbol, '')) AS symbol,
                MIN(COALESCE(underlying_type, '')) AS type,
                COUNT(1) AS contract_count
            FROM upstox_instruments
            WHERE segment = ?
              AND underlying_key IS NOT NULL
              AND TRIM(underlying_key) <> ''
              AND UPPER(COALESCE(underlying_type, '')) IN ({type_placeholders})
            GROUP BY underlying_key
            ORDER BY
                CASE
                    WHEN MIN(UPPER(COALESCE(underlying_type, ''))) = 'INDEX' THEN 0
                    ELSE 1
                END,
                MIN(COALESCE(underlying_symbol, '')),
                underlying_key;
        """, [clean_segment] + clean_underlying_types).fetchall()
    except Exception as error:
        print(f"Unable to discover expired underlying keys: {error}")
        rows = []

    discovered_keys = [row[0] for row in rows if row and safe_strip(row[0])]

    if discovered_keys:
        print(
            "Discovered expired underlying keys from current instruments: "
            f"{len(discovered_keys)}"
        )
        return unique_preserve_order(discovered_keys)

    print("Using fallback expired index underlying keys.")
    return DEFAULT_EXPIRED_UNDERLYING_KEYS.copy()


def normalize_sync_expired_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    raw_underlying_keys = payload.get("underlying_keys")

    if isinstance(raw_underlying_keys, str):
        underlying_keys = [
            value.strip()
            for value in raw_underlying_keys.split(",")
            if value.strip()
        ]
    elif isinstance(raw_underlying_keys, list):
        underlying_keys = [
            str(value).strip()
            for value in raw_underlying_keys
            if str(value).strip()
        ]
    else:
        underlying_keys = []

    raw_underlying_types = payload.get("underlying_types")

    if isinstance(raw_underlying_types, str):
        underlying_types = [
            value.strip().upper()
            for value in raw_underlying_types.split(",")
            if value.strip()
        ]
    elif isinstance(raw_underlying_types, list):
        underlying_types = [
            str(value).strip().upper()
            for value in raw_underlying_types
            if str(value).strip()
        ]
    else:
        underlying_types = DEFAULT_EXPIRED_UNDERLYING_TYPES.copy()

    underlying_types = unique_preserve_order(underlying_types)
    underlying_segment = safe_strip(
        payload.get("underlying_segment")
    ) or DEFAULT_EXPIRED_UNDERLYING_SEGMENT

    include_options = bool(payload.get("include_options", True))
    include_futures = bool(payload.get("include_futures", True))

    try:
        max_expiries = payload.get("max_expiries_per_underlying")

        if max_expiries in (None, "", 0, "0"):
            max_expiries = None
        else:
            max_expiries = max(1, int(max_expiries))
    except Exception:
        max_expiries = None

    try:
        request_pause_seconds = float(payload.get("request_pause_seconds", 0.15))
    except Exception:
        request_pause_seconds = 0.05

    if request_pause_seconds < 0:
        request_pause_seconds = 0

    force_refresh = bool(payload.get("force_refresh", False))

    return {
        "underlying_keys": underlying_keys,
        "underlying_segment": underlying_segment,
        "underlying_types": underlying_types,
        "include_options": include_options,
        "include_futures": include_futures,
        "max_expiries_per_underlying": max_expiries,
        "request_pause_seconds": request_pause_seconds,
        "force_refresh": force_refresh
    }


def write_expired_records_to_local_json(records: List[dict]) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    temp_file = EXPIRED_INSTRUMENT_FILE.with_suffix(".json.download")

    with open(temp_file, "w", encoding="utf-8") as output_file:
        json.dump(records, output_file, ensure_ascii=False, default=str)

    temp_file.replace(EXPIRED_INSTRUMENT_FILE)

    return EXPIRED_INSTRUMENT_FILE


def ensure_expired_contract_sync_status_table(conn):
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


def ensure_expired_underlying_sync_status_table(conn):
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


def has_expired_underlying_been_fully_checked(
    conn,
    underlying_key: str,
    include_options: bool,
    include_futures: bool,
    max_expiries: Optional[int] = None,
    force_refresh: bool = False
) -> bool:
    if force_refresh or max_expiries:
        return False

    ensure_expired_underlying_sync_status_table(conn)

    row = conn.execute("""
        SELECT status
        FROM upstox_expired_underlying_sync_status
        WHERE underlying_key = ?
          AND status = 'success'
          AND (? = FALSE OR include_options = TRUE)
          AND (? = FALSE OR include_futures = TRUE)
        LIMIT 1;
    """, [underlying_key, include_options, include_futures]).fetchone()

    return bool(row)


def record_expired_underlying_status(
    conn,
    underlying_key: str,
    status_value: str,
    expiry_count: int = 0,
    record_count: int = 0,
    include_options: bool = True,
    include_futures: bool = True,
    error_message: Optional[str] = None
):
    ensure_expired_underlying_sync_status_table(conn)

    conn.execute("""
        DELETE FROM upstox_expired_underlying_sync_status
        WHERE underlying_key = ?
          AND include_options = ?
          AND include_futures = ?;
    """, [underlying_key, include_options, include_futures])

    conn.execute("""
        INSERT INTO upstox_expired_underlying_sync_status (
            underlying_key,
            status,
            expiry_count,
            record_count,
            include_options,
            include_futures,
            last_error,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        underlying_key,
        status_value,
        int(expiry_count or 0),
        int(record_count or 0),
        bool(include_options),
        bool(include_futures),
        error_message
    ])


def has_expired_contract_group_been_checked(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str,
    force_refresh: bool = False
) -> bool:
    if force_refresh:
        return False

    existing_records = conn.execute("""
        SELECT COUNT(1)
        FROM upstox_expired_instruments
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type]).fetchone()[0]

    if existing_records:
        return True

    ensure_expired_contract_sync_status_table(conn)

    status_row = conn.execute("""
        SELECT status
        FROM upstox_expired_contract_sync_status
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?
          AND status = 'success'
        LIMIT 1;
    """, [underlying_key, expiry_date, source_type]).fetchone()

    return bool(status_row)


def record_expired_contract_group_status(
    conn,
    underlying_key: str,
    expiry_date: str,
    source_type: str,
    status_value: str,
    record_count: int = 0,
    error_message: Optional[str] = None
):
    ensure_expired_contract_sync_status_table(conn)

    conn.execute("""
        DELETE FROM upstox_expired_contract_sync_status
        WHERE underlying_key = ?
          AND expiry = TRY_CAST(? AS DATE)
          AND source_type = ?;
    """, [underlying_key, expiry_date, source_type])

    conn.execute("""
        INSERT INTO upstox_expired_contract_sync_status (
            underlying_key,
            expiry,
            source_type,
            status,
            record_count,
            last_error,
            synced_at
        )
        VALUES (?, TRY_CAST(? AS DATE), ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        underlying_key,
        expiry_date,
        source_type,
        status_value,
        int(record_count or 0),
        error_message
    ])


def download_expired_instruments_with_sdk(
    conn,
    sync_id: str,
    access_token: str,
    config: Optional[dict] = None
) -> dict:
    config = normalize_sync_expired_config(config)

    expired_api = create_expired_instrument_api(access_token)
    rate_limiter = UpstoxRollingRateLimiter()

    underlying_keys = config["underlying_keys"]

    if not underlying_keys:
        underlying_keys = get_configured_expired_underlying_keys(
            conn,
            segment=config["underlying_segment"],
            underlying_types=config["underlying_types"]
        )

    include_options = config["include_options"]
    include_futures = config["include_futures"]
    max_expiries = config["max_expiries_per_underlying"]
    request_pause_seconds = config["request_pause_seconds"]
    force_refresh = config["force_refresh"]

    if not include_options and not include_futures:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one expired instrument type: options or futures."
        )

    records = []
    failed_items = []
    group_statuses = []
    skipped_groups = 0
    underlying_statuses = []
    skipped_underlyings = 0
    persisted_records = 0
    was_cancelled = False

    def persist_completed_expired_batch():
        nonlocal records
        nonlocal group_statuses
        nonlocal underlying_statuses
        nonlocal persisted_records

        if not records and not group_statuses and not underlying_statuses:
            return

        try:
            conn.execute("BEGIN TRANSACTION")
            saved_records = import_expired_instruments_records(
                conn=conn,
                sync_id=sync_id,
                records=records,
                group_statuses=group_statuses,
                underlying_statuses=underlying_statuses
            )
            conn.execute("COMMIT")
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        persisted_records += saved_records
        records = []
        group_statuses = []
        underlying_statuses = []

    print("Downloading Upstox expired instruments using Python SDK.")
    print(f"Underlying keys: {len(underlying_keys)}")

    try:
        for underlying_index, underlying_key in enumerate(underlying_keys, start=1):
            check_sync_cancelled(conn, sync_id)

            if has_expired_underlying_been_fully_checked(
                conn,
                underlying_key=underlying_key,
                include_options=include_options,
                include_futures=include_futures,
                max_expiries=max_expiries,
                force_refresh=force_refresh
            ):
                skipped_underlyings += 1
                print(
                    "Skipping expired instruments for "
                    f"{underlying_key}: full underlying already checked."
                )
                continue

            print(
                "Fetching expired expiries "
                f"{underlying_index}/{len(underlying_keys)}: {underlying_key}"
            )

            try:
                rate_limiter.wait_for_slot()
                expiries_response = expired_api.get_expiries(underlying_key)
                expiries = normalize_expiry_list(expiries_response)
            except Exception as error:
                error_text = str(error)

                if is_upstox_expired_permission_error(error_text):
                    failed_items.append({
                        "underlying_key": underlying_key,
                        "expiry": None,
                        "type": "expiries",
                        "error": (
                            "Expired Instruments API access is not permitted "
                            f"for this underlying: {error_text}"
                        )
                    })
                    print(
                        "Skipping expired instruments for "
                        f"{underlying_key}: permission denied by Upstox."
                    )
                    continue

                if "401" in error_text or "UDAPI100050" in error_text or "Invalid token" in error_text:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Upstox token is invalid or expired. "
                            "Please save a fresh analytics token in Connections, "
                            "restart the backend, then run Expired Instruments again."
                        )
                    )

                failed_items.append({
                    "underlying_key": underlying_key,
                    "expiry": None,
                    "type": "expiries",
                    "error": error_text
                })
                print(f"Unable to fetch expiries for {underlying_key}: {error}")
                continue

            if max_expiries:
                expiries = expiries[:max_expiries]

            print(f"Expired expiries found for {underlying_key}: {len(expiries)}")
            underlying_failed = False
            underlying_record_count = 0

            for expiry_index, expiry_date in enumerate(expiries, start=1):
                check_sync_cancelled(conn, sync_id)

                if include_options:
                    if has_expired_contract_group_been_checked(
                        conn,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date,
                        source_type=EXPIRED_SOURCE_OPTION,
                        force_refresh=force_refresh
                    ):
                        skipped_groups += 1
                        print(
                            f"Options {underlying_key} {expiry_date}: "
                            "already available, skipping API call."
                        )
                    else:
                        try:
                            rate_limiter.wait_for_slot()
                            options_response = expired_api.get_expired_option_contracts(
                                underlying_key,
                                expiry_date
                            )

                            option_rows = normalize_contract_list(
                                response=options_response,
                                source_type=EXPIRED_SOURCE_OPTION,
                                underlying_key=underlying_key,
                                expiry_date=expiry_date
                            )

                            records.extend(option_rows)
                            underlying_record_count += len(option_rows)
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_OPTION,
                                "status": "success",
                                "record_count": len(option_rows),
                                "error": None
                            })

                            print(
                                f"Options {underlying_key} {expiry_date} "
                                f"({expiry_index}/{len(expiries)}): {len(option_rows)}"
                            )

                        except Exception as error:
                            error_text = str(error)
                            underlying_failed = True
                            failed_items.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "type": "options",
                                "error": error_text
                            })
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_OPTION,
                                "status": "failed",
                                "record_count": 0,
                                "error": error_text
                            })
                            print(
                                f"Unable to fetch expired option contracts for "
                                f"{underlying_key} {expiry_date}: {error}"
                            )

                    if request_pause_seconds:
                        time.sleep(request_pause_seconds)

                check_sync_cancelled(conn, sync_id)

                if include_futures:
                    if has_expired_contract_group_been_checked(
                        conn,
                        underlying_key=underlying_key,
                        expiry_date=expiry_date,
                        source_type=EXPIRED_SOURCE_FUTURE,
                        force_refresh=force_refresh
                    ):
                        skipped_groups += 1
                        print(
                            f"Futures {underlying_key} {expiry_date}: "
                            "already available, skipping API call."
                        )
                    else:
                        try:
                            rate_limiter.wait_for_slot()
                            futures_response = expired_api.get_expired_future_contracts(
                                underlying_key,
                                expiry_date
                            )

                            future_rows = normalize_contract_list(
                                response=futures_response,
                                source_type=EXPIRED_SOURCE_FUTURE,
                                underlying_key=underlying_key,
                                expiry_date=expiry_date
                            )

                            records.extend(future_rows)
                            underlying_record_count += len(future_rows)
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_FUTURE,
                                "status": "success",
                                "record_count": len(future_rows),
                                "error": None
                            })

                            print(
                                f"Futures {underlying_key} {expiry_date} "
                                f"({expiry_index}/{len(expiries)}): {len(future_rows)}"
                            )

                        except Exception as error:
                            error_text = str(error)
                            underlying_failed = True
                            failed_items.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "type": "futures",
                                "error": error_text
                            })
                            group_statuses.append({
                                "underlying_key": underlying_key,
                                "expiry": expiry_date,
                                "source_type": EXPIRED_SOURCE_FUTURE,
                                "status": "failed",
                                "record_count": 0,
                                "error": error_text
                            })
                            print(
                                f"Unable to fetch expired future contracts for "
                                f"{underlying_key} {expiry_date}: {error}"
                            )

                    if request_pause_seconds:
                        time.sleep(request_pause_seconds)

            if not max_expiries:
                underlying_statuses.append({
                    "underlying_key": underlying_key,
                    "status": "failed" if underlying_failed else "success",
                    "expiry_count": len(expiries),
                    "record_count": underlying_record_count,
                    "include_options": include_options,
                    "include_futures": include_futures,
                    "error": "One or more contract groups failed." if underlying_failed else None
                })

            persist_completed_expired_batch()
    except SyncCancelled:
        was_cancelled = True
        print("Expired instrument download cancelled; saving completed downloaded records.")

    if failed_items:
        failed_file = DATA_DIR / "upstox_expired_instruments_failed_items.json"

        with open(failed_file, "w", encoding="utf-8") as output_file:
            json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

        print(f"Expired instruments failed items saved: {failed_file}")

    unique_records = {}

    for record in records:
        instrument_key = record.get("instrument_key")
        source_type = record.get("source_type")
        expiry = record.get("expiry")
        unique_key = f"{source_type}|{expiry}|{instrument_key}"

        if instrument_key:
            unique_records[unique_key] = record

    final_records = list(unique_records.values())

    print(f"Expired instruments downloaded: {len(final_records)}")
    print(f"Expired contract API groups skipped as already available: {skipped_groups}")
    print(f"Expired underlyings skipped as fully checked: {skipped_underlyings}")

    if not final_records and failed_items:
        first_failure = failed_items[0]
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "No expired instruments were downloaded. First failure: "
                f"{first_failure.get('underlying_key')} "
                f"{first_failure.get('type')}: {first_failure.get('error')}"
            )
        )

    return {
        "records": final_records,
        "group_statuses": group_statuses,
        "underlying_statuses": underlying_statuses,
        "persisted_records": persisted_records,
        "skipped_groups": skipped_groups,
        "skipped_underlyings": skipped_underlyings,
        "cancelled": was_cancelled
    }


def import_expired_instruments_records(
    conn,
    sync_id: str,
    records: List[dict],
    group_statuses: Optional[List[dict]] = None,
    underlying_statuses: Optional[List[dict]] = None,
    allow_cancelled_import: bool = False
) -> int:
    if not allow_cancelled_import:
        check_sync_cancelled(conn, sync_id)

    insert_started_at = time.time()
    unique_records = {}

    for record in records:
        instrument_key = safe_strip(record.get("instrument_key"))
        source_type = safe_strip(record.get("source_type"))
        expiry = normalize_expiry_value(record.get("expiry"))

        if not instrument_key or source_type not in (EXPIRED_SOURCE_OPTION, EXPIRED_SOURCE_FUTURE):
            continue

        if not expiry:
            continue

        unique_records[f"{source_type}|{expiry}|{instrument_key}"] = {
            **record,
            "instrument_key": instrument_key,
            "source_type": source_type,
            "expiry": expiry
        }

    deduped_records = list(unique_records.values())
    groups_to_replace = unique_preserve_order([
        f"{record.get('underlying_key')}|{record.get('expiry')}|{record.get('source_type')}"
        for record in deduped_records
    ])

    print(f"Expired rows valid for direct insert after Python de-dupe: {len(deduped_records)}")

    for group_key in groups_to_replace:
        underlying_key, expiry_date, source_type = group_key.rsplit("|", 2)

        conn.execute("""
            DELETE FROM upstox_expired_instruments
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?;
        """, [underlying_key, expiry_date, source_type])

    if not allow_cancelled_import:
        check_sync_cancelled(conn, sync_id)

    if deduped_records:
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
            SELECT
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                TRY_CAST(? AS DATE),
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                TRY_CAST(? AS JSON),
                CURRENT_TIMESTAMP;
        """, [
            (
                record.get("instrument_key"),
                record.get("segment"),
                record.get("name"),
                record.get("exchange"),
                record.get("instrument_type"),
                record.get("trading_symbol"),
                record.get("exchange_token"),
                record.get("expiry"),
                record.get("strike_price"),
                record.get("lot_size"),
                record.get("minimum_lot"),
                record.get("freeze_quantity"),
                record.get("tick_size"),
                record.get("weekly"),
                record.get("underlying_key"),
                record.get("underlying_symbol"),
                record.get("underlying_type"),
                record.get("source_type"),
                record.get("raw_json")
            )
            for record in deduped_records
        ])

    for group_status in group_statuses or []:
        record_expired_contract_group_status(
            conn,
            underlying_key=group_status.get("underlying_key"),
            expiry_date=group_status.get("expiry"),
            source_type=group_status.get("source_type"),
            status_value=group_status.get("status") or "failed",
            record_count=group_status.get("record_count") or 0,
            error_message=group_status.get("error")
        )

    for underlying_status in underlying_statuses or []:
        record_expired_underlying_status(
            conn,
            underlying_key=underlying_status.get("underlying_key"),
            status_value=underlying_status.get("status") or "failed",
            expiry_count=underlying_status.get("expiry_count") or 0,
            record_count=underlying_status.get("record_count") or 0,
            include_options=bool(underlying_status.get("include_options", True)),
            include_futures=bool(underlying_status.get("include_futures", True)),
            error_message=underlying_status.get("error")
        )

    print(f"DuckDB expired direct insert time: {round(time.time() - insert_started_at, 2)} seconds")

    return len(deduped_records)


def import_expired_instruments_from_local_file(conn, sync_id: str, local_file: Path) -> int:
    check_sync_cancelled(conn, sync_id)

    duckdb_path = normalize_duckdb_file_path(local_file)

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired")

    read_started_at = time.time()

    print("Reading expired instrument JSON directly with DuckDB...")

    conn.execute(
        """
        CREATE TEMP TABLE temp_upstox_expired AS
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
                instrument_type: 'VARCHAR',
                trading_symbol: 'VARCHAR',
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
                source_type: 'VARCHAR',
                raw_json: 'VARCHAR'
            }
        );
        """,
        [duckdb_path]
    )

    print(f"DuckDB expired JSON read time: {round(time.time() - read_started_at, 2)} seconds")

    check_sync_cancelled(conn, sync_id)

    total_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_expired;
    """).fetchone()[0]

    print(f"Expired rows loaded into temp table: {total_rows}")

    insert_started_at = time.time()

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired_valid")

    conn.execute("""
        CREATE TEMP TABLE temp_upstox_expired_valid AS
        SELECT *
        FROM (
            SELECT
                instrument_key,
                segment,
                name,
                exchange,
                instrument_type,
                trading_symbol,
                exchange_token,
                TRY_CAST(expiry AS DATE) AS expiry_date,
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
                TRY_CAST(raw_json AS JSON) AS raw_json,
                ROW_NUMBER() OVER (
                    PARTITION BY source_type, TRY_CAST(expiry AS DATE), instrument_key
                    ORDER BY trading_symbol
                ) AS duplicate_rank
            FROM temp_upstox_expired
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              AND source_type IN (?, ?)
              AND TRY_CAST(expiry AS DATE) IS NOT NULL
        )
        WHERE duplicate_rank = 1;
    """, [EXPIRED_SOURCE_OPTION, EXPIRED_SOURCE_FUTURE])

    valid_rows = conn.execute("""
        SELECT COUNT(*)
        FROM temp_upstox_expired_valid;
    """).fetchone()[0]

    print(f"Expired rows valid for insert after de-dupe: {valid_rows}")

    conn.execute("""
        DELETE FROM upstox_expired_instruments
        WHERE EXISTS (
            SELECT 1
            FROM (
                SELECT DISTINCT
                    source_type,
                    underlying_key,
                    expiry_date
                FROM temp_upstox_expired_valid
            ) AS downloaded_groups
            WHERE downloaded_groups.source_type = upstox_expired_instruments.source_type
              AND COALESCE(downloaded_groups.underlying_key, '') = COALESCE(upstox_expired_instruments.underlying_key, '')
              AND downloaded_groups.expiry_date = upstox_expired_instruments.expiry
        );
    """)

    check_sync_cancelled(conn, sync_id)

    conn.execute("""
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
        SELECT
            instrument_key,
            segment,
            name,
            exchange,
            instrument_type,
            trading_symbol,
            exchange_token,
            expiry_date AS expiry,
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
            CURRENT_TIMESTAMP AS synced_at
        FROM temp_upstox_expired_valid;
    """)

    print(f"DuckDB expired insert time: {round(time.time() - insert_started_at, 2)} seconds")

    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired_valid")
    conn.execute("DROP TABLE IF EXISTS temp_upstox_expired")

    return int(valid_rows or 0)


def safe_table_count(conn, table_name: str) -> int:
    if not table_name:
        return 0

    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0] or 0)
    except Exception as error:
        print(f"Data collection count unavailable for {table_name}: {error}")
        return 0


def safe_fetchone(conn, query: str, params: Optional[List[Any]] = None):
    try:
        return conn.execute(query, params or []).fetchone()
    except Exception as error:
        print(f"Data collection query unavailable: {error}")
        return None


def safe_fetchall(conn, query: str, params: Optional[List[Any]] = None):
    try:
        return conn.execute(query, params or []).fetchall()
    except Exception as error:
        print(f"Data collection query unavailable: {error}")
        return []


def safe_mark_stale_sync_runs(conn):
    try:
        mark_stale_sync_runs(conn)
    except Exception as error:
        print(f"Data collection stale run cleanup skipped: {error}")


def safe_last_success_run(conn, sync_type: str):
    try:
        return conn.execute("""
            SELECT finished_at, duration_seconds
            FROM upstox_sync_runs
            WHERE sync_type = ?
              AND status = 'success'
            ORDER BY finished_at DESC
            LIMIT 1;
        """, [sync_type]).fetchone()
    except Exception:
        return None


def table_name_for_sync_type(sync_type: Optional[str]) -> Optional[str]:
    return {
        "upstox_current_instruments": "upstox_instruments",
        "upstox_expired_instruments": "upstox_expired_instruments",
        "upstox_equity_instruments": "upstox_equity_instruments",
        "upstox_ohlcv_daily": "upstox_ohlcv_candles"
    }.get(sync_type or "")


def safe_active_job_started_count(conn, sync_type: Optional[str], started_at) -> Optional[int]:
    table_name = table_name_for_sync_type(sync_type)

    if not table_name or not started_at:
        return None

    timestamp_column = "ingested_at" if table_name == "upstox_ohlcv_candles" else "synced_at"

    try:
        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE {timestamp_column} < ?;
        """, [started_at]).fetchone()
        return int(row[0] or 0)
    except Exception:
        return None


def get_data_collection_summary_service():
    conn = get_connection()

    try:
        safe_mark_stale_sync_runs(conn)
        connection_status = get_upstox_connection_status(conn)

        current_count = safe_table_count(conn, "upstox_instruments")
        expired_count = safe_table_count(conn, "upstox_expired_instruments")
        equity_count = safe_table_count(conn, "upstox_equity_instruments")
        ohlcv_daily_count = safe_table_count(conn, "upstox_ohlcv_candles")
        equity_news_count = safe_table_count(conn, "equity_news")
        fundamentals_count = safe_table_count(conn, "fundamentals")
        corporate_actions_count = safe_table_count(conn, "corporate_actions")
        fii_dii_count = safe_table_count(conn, "fii_dii_activity")

        total_runs_row = safe_fetchone(conn, """
            SELECT COUNT(*)
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            );
        """)
        total_runs = int(total_runs_row[0] or 0) if total_runs_row else 0

        last_run = safe_fetchone(conn, """
            SELECT
                sync_type,
                status,
                started_at,
                finished_at,
                duration_seconds,
                total_records
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            )
            ORDER BY started_at DESC
            LIMIT 1;
        """)

        current_run = safe_last_success_run(conn, "upstox_current_instruments")
        expired_run = safe_last_success_run(conn, "upstox_expired_instruments")
        equity_run = safe_last_success_run(conn, "upstox_equity_instruments")
        ohlcv_run = safe_last_success_run(conn, "upstox_ohlcv_daily")

        active_run = safe_fetchone(conn, """
            SELECT sync_type, status, started_at
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC
            LIMIT 1;
        """)

        active_job = active_run[0] if active_run else None
        active_job_started_at = active_run[2] if active_run and active_run[2] else None
        active_job_table = table_name_for_sync_type(active_job)
        active_job_current_records = (
            safe_table_count(conn, active_job_table)
            if active_job_table else None
        )
        active_job_records_at_start = safe_active_job_started_count(
            conn,
            active_job,
            active_job_started_at
        )

        return {
            "connection_status": connection_status,
            "total_current_instruments": current_count,
            "total_expired_instruments": expired_count,
            "total_equity_instruments": equity_count,
            "total_ohlcv_daily": ohlcv_daily_count,
            "total_equity_news": equity_news_count,
            "total_fundamentals": fundamentals_count,
            "total_corporate_actions": corporate_actions_count,
            "total_fii_dii_activity": fii_dii_count,
            "total_sync_runs": total_runs,
            "last_sync_at": str(last_run[3]) if last_run and last_run[3] else None,
            "last_duration_seconds": last_run[4] if last_run else None,
            "current_last_sync_at": str(current_run[0]) if current_run and current_run[0] else None,
            "current_duration_seconds": current_run[1] if current_run else None,
            "expired_last_sync_at": str(expired_run[0]) if expired_run and expired_run[0] else None,
            "expired_duration_seconds": expired_run[1] if expired_run else None,
            "equity_last_sync_at": str(equity_run[0]) if equity_run and equity_run[0] else None,
            "equity_duration_seconds": equity_run[1] if equity_run else None,
            "ohlcv_daily_last_sync_at": str(ohlcv_run[0]) if ohlcv_run and ohlcv_run[0] else None,
            "ohlcv_daily_duration_seconds": ohlcv_run[1] if ohlcv_run else None,
            "active_job": active_job,
            "active_job_status": active_run[1] if active_run else None,
            "active_job_started_at": str(active_job_started_at) if active_job_started_at else None,
            "active_job_current_records": active_job_current_records,
            "active_job_records_at_start": active_job_records_at_start,
            "active_job_records_added": (
                active_job_current_records - active_job_records_at_start
                if active_job_current_records is not None
                and active_job_records_at_start is not None
                else None
            )
        }

    finally:
        conn.close()


def get_data_collection_runs_service():
    conn = get_connection()

    try:
        rows = safe_fetchall(conn, """
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
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            )
            ORDER BY started_at DESC
            LIMIT 25;
        """)

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

        local_file = download_upstox_master_gz_file_once()

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

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Current instrument dump failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump current instruments: {error}"
        )

    finally:
        delete_downloaded_master_file(local_file)
        conn.close()


def sync_upstox_expired_instruments_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    expired_download = {
        "records": [],
        "group_statuses": [],
        "skipped_groups": 0
    }
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        access_token = get_saved_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_expired_instruments",
            "running",
            "Expired instrument SDK download started.",
            current_user=current_user
        )

        expired_download = download_expired_instruments_with_sdk(
            conn=conn,
            sync_id=sync_id,
            access_token=access_token,
            config=config
        )

        was_cancelled = bool(expired_download.get("cancelled"))

        if not was_cancelled:
            check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")

        total_records = int(expired_download.get("persisted_records") or 0)

        total_records += import_expired_instruments_records(
            conn=conn,
            sync_id=sync_id,
            records=expired_download.get("records", []),
            group_statuses=expired_download.get("group_statuses", []),
            underlying_statuses=expired_download.get("underlying_statuses", []),
            allow_cancelled_import=was_cancelled
        )

        conn.execute("COMMIT")

        if was_cancelled:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Expired instrument SDK download cancelled. Completed records were saved.",
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "cancelled",
                "message": "Expired instrument SDK download cancelled. Completed records were saved.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at)
            }

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Expired instruments downloaded through Upstox SDK and imported successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Expired instruments downloaded through Upstox SDK and imported successfully.",
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
                "Expired instrument SDK download cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Expired instrument SDK download cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        error_message = error.detail

        if isinstance(error_message, dict):
            error_message = error_message.get("message") or str(error_message)

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Expired instrument SDK download failed: {error_message}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "failed",
            "message": str(error_message),
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Expired instrument SDK download failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump expired instruments through Upstox SDK: {error}"
        )

    finally:
        conn.close()



def parse_iso_date(value: Any, field_name: str, default_value: Optional[date] = None) -> date:
    if value in (None, ""):
        if default_value is not None:
            return default_value

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} is required."
        )

    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field_name} must be a valid date in YYYY-MM-DD format."
        )


def normalize_string_list(value: Any, default_values: List[str]) -> List[str]:
    if value in (None, ""):
        return default_values.copy()

    if isinstance(value, str):
        values = [item.strip() for item in value.split(",")]
    elif isinstance(value, list):
        values = [str(item).strip() for item in value]
    else:
        values = []

    return unique_preserve_order([value for value in values if value]) or default_values.copy()


def normalize_bool(value: Any, default_value: bool = False) -> bool:
    if value is None:
        return default_value

    if isinstance(value, bool):
        return value

    if isinstance(value, (int, float)):
        return bool(value)

    clean_value = str(value).strip().lower()

    if clean_value in ("1", "true", "yes", "y", "on"):
        return True

    if clean_value in ("0", "false", "no", "n", "off"):
        return False

    return default_value


def normalize_positive_int(value: Any, default_value: int, minimum: int = 1, maximum: Optional[int] = None) -> int:
    try:
        number = int(value)
    except Exception:
        number = default_value

    number = max(minimum, number)

    if maximum is not None:
        number = min(maximum, number)

    return number


def normalize_optional_positive_int(value: Any, minimum: int = 1, maximum: Optional[int] = None) -> Optional[int]:
    if value in (None, "", 0, "0", "all"):
        return None

    try:
        number = int(value)
    except Exception:
        return None

    number = max(minimum, number)

    if maximum is not None:
        number = min(maximum, number)

    return number


def normalize_ohlcv_interval_key(value: Any) -> str:
    clean_value = str(value or "").strip().lower().replace(" ", "")

    aliases = {
        "1m": "1minute",
        "1min": "1minute",
        "1minute": "1minute",
        "3m": "3minute",
        "3min": "3minute",
        "3minute": "3minute",
        "5m": "5minute",
        "5min": "5minute",
        "5minute": "5minute",
        "15m": "15minute",
        "15min": "15minute",
        "15minute": "15minute",
        "30m": "30minute",
        "30min": "30minute",
        "30minute": "30minute",
        "1h": "1hour",
        "1hour": "1hour",
        "hour": "1hour",
        "day": "day",
        "daily": "day",
        "1day": "day",
        "week": "week",
        "weekly": "week",
        "1week": "week",
        "month": "month",
        "monthly": "month",
        "1month": "month"
    }

    return aliases.get(clean_value, clean_value)


def normalize_ohlcv_config(payload: Optional[dict]) -> dict:
    payload = payload or {}
    today = datetime.now().date()

    selected_sources = normalize_string_list(
        payload.get("sources") or payload.get("selected_sources"),
        OHLCV_DEFAULT_SOURCES
    )
    selected_sources = [value for value in selected_sources if value in OHLCV_ALLOWED_SOURCES]

    selected_modes = normalize_string_list(
        payload.get("candle_modes") or payload.get("selected_candle_modes"),
        OHLCV_DEFAULT_MODES
    )
    selected_modes = [value for value in selected_modes if value in OHLCV_ALLOWED_MODES]

    raw_intervals = normalize_string_list(
        payload.get("intervals") or payload.get("selected_intervals"),
        OHLCV_DEFAULT_INTERVALS
    )
    selected_intervals = []

    for interval in raw_intervals:
        interval_key = normalize_ohlcv_interval_key(interval)

        if interval_key in OHLCV_INTERVAL_OPTIONS:
            selected_intervals.append(interval_key)

    selected_intervals = unique_preserve_order(selected_intervals)

    if not selected_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV instrument source."
        )

    if not selected_modes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV candle mode."
        )

    if not selected_intervals:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one OHLCV interval."
        )

    raw_from_date = payload.get("from_date")
    raw_to_date = payload.get("to_date")

    from_date_was_provided = raw_from_date not in (None, "")
    to_date_was_provided = raw_to_date not in (None, "")

    use_current_day = normalize_bool(
        payload.get("use_current_day") if "use_current_day" in payload else payload.get("to_current_day"),
        not to_date_was_provided
    )
    auto_date_range = normalize_bool(
        payload.get("auto_date_range"),
        not from_date_was_provided
    )

    from_date = parse_iso_date(
        raw_from_date,
        "from_date",
        OHLCV_CURRENT_HISTORY_START_DATE
    )
    to_date = today if use_current_day else parse_iso_date(raw_to_date, "to_date", today)

    if to_date > today:
        to_date = today

    if to_date < from_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="to_date must be greater than or equal to from_date."
        )

    if OHLCV_INTRADAY_MODE in selected_modes:
        to_date = today if use_current_day else min(to_date, today)

    instrument_limit = normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000)
    single_instrument_key = safe_strip(payload.get("single_instrument_key"))

    batch_size = normalize_positive_int(
        payload.get("batch_size"),
        OHLCV_DEFAULT_BATCH_SIZE,
        1,
        500
    )
    request_delay_ms = normalize_positive_int(
        payload.get("request_delay_ms"),
        OHLCV_DEFAULT_REQUEST_DELAY_MS,
        0,
        60000
    )
    batch_delay_seconds = normalize_positive_int(
        payload.get("batch_delay_seconds"),
        OHLCV_DEFAULT_BATCH_DELAY_SECONDS,
        0,
        3600
    )
    retry_count = normalize_positive_int(
        payload.get("retry_count"),
        OHLCV_DEFAULT_RETRY_COUNT,
        1,
        10
    )

    return {
        "sources": selected_sources,
        "candle_modes": selected_modes,
        "intervals": selected_intervals,
        "from_date": from_date,
        "to_date": to_date,
        "from_date_was_provided": from_date_was_provided,
        "to_date_was_provided": to_date_was_provided,
        "use_current_day": use_current_day,
        "auto_date_range": auto_date_range,
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "respect_api_limits": normalize_bool(payload.get("respect_api_limits"), True),
        "retry_failed": normalize_bool(payload.get("retry_failed"), True),
        "instrument_limit": instrument_limit,
        "single_instrument_key": single_instrument_key,
        "batch_size": batch_size,
        "request_delay_ms": request_delay_ms,
        "batch_delay_seconds": batch_delay_seconds,
        "retry_count": retry_count
    }


def ohlcv_config_to_jsonable(config: dict) -> dict:
    return {
        **config,
        "from_date": config["from_date"].isoformat(),
        "to_date": config["to_date"].isoformat(),
        "from_date_was_provided": bool(config.get("from_date_was_provided")),
        "to_date_was_provided": bool(config.get("to_date_was_provided")),
        "use_current_day": bool(config.get("use_current_day")),
        "auto_date_range": bool(config.get("auto_date_range"))
    }

def get_default_ohlcv_options_payload() -> dict:
    today = datetime.now().date()

    return {
        "sources": OHLCV_DEFAULT_SOURCES.copy(),
        "candle_modes": OHLCV_DEFAULT_MODES.copy(),
        "intervals": OHLCV_DEFAULT_INTERVALS.copy(),
        "from_date": OHLCV_CURRENT_HISTORY_START_DATE.isoformat(),
        "to_date": today.isoformat(),
        "from_date_was_provided": False,
        "to_date_was_provided": False,
        "use_current_day": True,
        "auto_date_range": True,
        "skip_existing": True,
        "respect_api_limits": True,
        "retry_failed": True,
        "instrument_limit": None,
        "single_instrument_key": "",
        "batch_size": OHLCV_DEFAULT_BATCH_SIZE,
        "request_delay_ms": OHLCV_DEFAULT_REQUEST_DELAY_MS,
        "batch_delay_seconds": OHLCV_DEFAULT_BATCH_DELAY_SECONDS,
        "retry_count": OHLCV_DEFAULT_RETRY_COUNT
    }


def get_upstox_ohlcv_options_service():
    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT request_options, updated_at, updated_by
            FROM upstox_ohlcv_collection_settings
            WHERE setting_name = 'default'
              AND is_active = TRUE
            LIMIT 1;
        """).fetchone()

        if not row or not row[0]:
            return {
                "options": get_default_ohlcv_options_payload(),
                "updated_at": None,
                "updated_by": None
            }

        try:
            request_options = json.loads(row[0]) if isinstance(row[0], str) else row[0]
        except Exception:
            request_options = get_default_ohlcv_options_payload()

        return {
            "options": request_options or get_default_ohlcv_options_payload(),
            "updated_at": str(row[1]) if row[1] else None,
            "updated_by": row[2]
        }

    finally:
        conn.close()


def save_upstox_ohlcv_options_service(payload: dict, current_user: dict):
    normalized_config = normalize_ohlcv_config(payload)
    request_options = ohlcv_config_to_jsonable(normalized_config)
    trigger_metadata = get_sync_trigger_metadata(current_user)
    user_id = trigger_metadata["triggered_by_id"] or "system"

    conn = get_connection()

    try:
        existing = conn.execute("""
            SELECT setting_id
            FROM upstox_ohlcv_collection_settings
            WHERE setting_name = 'default'
            LIMIT 1;
        """).fetchone()

        if existing:
            conn.execute("""
                UPDATE upstox_ohlcv_collection_settings
                SET
                    request_options = TRY_CAST(? AS JSON),
                    is_active = TRUE,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE setting_name = 'default';
            """, [
                json.dumps(request_options, ensure_ascii=False, default=str),
                user_id
            ])
        else:
            conn.execute("""
                INSERT INTO upstox_ohlcv_collection_settings (
                    setting_id,
                    setting_name,
                    request_options,
                    is_active,
                    created_by,
                    updated_by
                )
                VALUES (?, 'default', TRY_CAST(? AS JSON), TRUE, ?, ?);
            """, [
                str(uuid.uuid4()),
                json.dumps(request_options, ensure_ascii=False, default=str),
                user_id,
                user_id
            ])

        conn.commit()

        return {
            "status": "success",
            "message": "OHLCV options saved successfully.",
            "data": {
                "options": request_options
            }
        }

    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    finally:
        conn.close()


def get_saved_ohlcv_options_for_run(conn) -> dict:
    row = conn.execute("""
        SELECT request_options
        FROM upstox_ohlcv_collection_settings
        WHERE setting_name = 'default'
          AND is_active = TRUE
        LIMIT 1;
    """).fetchone()

    if not row or not row[0]:
        return get_default_ohlcv_options_payload()

    try:
        return json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        return get_default_ohlcv_options_payload()

def update_ohlcv_sync_run_options(conn, sync_id: str, config: dict):
    jsonable_config = ohlcv_config_to_jsonable(config)

    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            request_options = TRY_CAST(? AS JSON),
            selected_sources = TRY_CAST(? AS JSON),
            selected_candle_modes = TRY_CAST(? AS JSON),
            selected_intervals = TRY_CAST(? AS JSON),
            from_date = TRY_CAST(? AS DATE),
            to_date = TRY_CAST(? AS DATE),
            skip_existing = ?,
            respect_api_limits = ?,
            retry_failed = ?,
            instrument_limit = ?,
            single_instrument_key = ?,
            batch_size = ?,
            request_delay_ms = ?,
            batch_delay_seconds = ?
        WHERE sync_id = ?;
    """, [
        json.dumps(jsonable_config, ensure_ascii=False, default=str),
        json.dumps(config["sources"], ensure_ascii=False),
        json.dumps(config["candle_modes"], ensure_ascii=False),
        json.dumps(config["intervals"], ensure_ascii=False),
        config["from_date"].isoformat(),
        config["to_date"].isoformat(),
        bool(config["skip_existing"]),
        bool(config["respect_api_limits"]),
        bool(config["retry_failed"]),
        config["instrument_limit"],
        config["single_instrument_key"],
        config["batch_size"],
        config["request_delay_ms"],
        config["batch_delay_seconds"],
        sync_id
    ])

    conn.commit()


def finish_ohlcv_sync_run_metrics(conn, sync_id: str, metrics: dict):
    conn.execute("""
        UPDATE upstox_sync_runs
        SET
            api_calls_attempted = ?,
            api_calls_skipped = ?,
            candles_inserted = ?,
            candles_skipped = ?,
            failed_instruments = ?
        WHERE sync_id = ?;
    """, [
        int(metrics.get("api_calls_attempted") or 0),
        int(metrics.get("api_calls_skipped") or 0),
        int(metrics.get("candles_inserted") or 0),
        int(metrics.get("candles_skipped") or 0),
        int(metrics.get("failed_instruments") or 0),
        sync_id
    ])

    conn.commit()


def get_ohlcv_interval_definition(interval_key: str) -> dict:
    interval = OHLCV_INTERVAL_OPTIONS.get(interval_key)

    if not interval:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported OHLCV interval: {interval_key}"
        )

    return interval


def get_ohlcv_chunk_days(unit: str, interval_value: int, source: str) -> Optional[int]:
    if source == OHLCV_EXPIRED_SOURCE:
        return OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS if unit == "minutes" else OHLCV_EXPIRED_MAX_DAYS

    if unit == "minutes" and interval_value <= 15:
        return OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS

    if unit == "minutes" and interval_value > 15:
        return OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS

    if unit == "hours":
        return OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS

    if unit == "days":
        return OHLCV_CURRENT_DAILY_MAX_DAYS

    return None


def split_ohlcv_date_range(from_date: date, to_date: date, unit: str, interval_value: int, source: str) -> List[dict]:
    max_days = get_ohlcv_chunk_days(unit, interval_value, source)

    if not max_days:
        return [{"from_date": from_date, "to_date": to_date}]

    chunks = []
    current_from = from_date

    while current_from <= to_date:
        current_to = min(to_date, current_from + timedelta(days=max_days - 1))
        chunks.append({"from_date": current_from, "to_date": current_to})
        current_from = current_to + timedelta(days=1)

    return chunks


def get_existing_ohlcv_dates_for_chunk(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date: date,
    to_date: date
) -> set:
    rows = conn.execute("""
        SELECT DISTINCT candle_date
        FROM upstox_ohlcv_candles
        WHERE provider = ?
          AND instrument_source = ?
          AND candle_mode = ?
          AND instrument_key = ?
          AND unit = ?
          AND interval_value = ?
          AND candle_date BETWEEN ? AND ?;
    """, [
        UPSTOX_PROVIDER,
        source,
        mode,
        instrument_key,
        unit,
        interval_value,
        from_date,
        to_date
    ]).fetchall()

    return {row[0] for row in rows if row and row[0]}


def all_dates_exist_for_chunk(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date: date,
    to_date: date
) -> bool:
    existing_dates = get_existing_ohlcv_dates_for_chunk(
        conn=conn,
        source=source,
        mode=mode,
        instrument_key=instrument_key,
        unit=unit,
        interval_value=interval_value,
        from_date=from_date,
        to_date=to_date
    )

    if not existing_dates:
        return False

    day_count = (to_date - from_date).days + 1

    return len(existing_dates) >= day_count

def get_ohlcv_available_start_date(source: str, mode: str, unit: str) -> date:
    if source == OHLCV_CURRENT_SOURCE and mode == OHLCV_HISTORICAL_MODE:
        if unit in ("minutes", "hours"):
            return OHLCV_INTRADAY_HISTORY_START_DATE

        return OHLCV_CURRENT_HISTORY_START_DATE

    if source == OHLCV_CURRENT_SOURCE and mode == OHLCV_INTRADAY_MODE:
        return OHLCV_INTRADAY_HISTORY_START_DATE

    return OHLCV_CURRENT_HISTORY_START_DATE



def build_ohlcv_saved_bounds_cache(
    conn,
    source: str,
    config: dict,
    instruments: List[dict]
) -> dict:
    instrument_keys = unique_preserve_order([
        safe_strip(instrument.get("instrument_key"))
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    ])

    if not instrument_keys:
        return {}

    interval_rows = []

    for mode in config["candle_modes"]:
        for interval_key in config["intervals"]:
            interval = OHLCV_INTERVAL_OPTIONS.get(interval_key)

            if not interval:
                continue

            interval_rows.append((
                mode,
                interval["unit"],
                int(interval["interval_value"])
            ))

    if not interval_rows:
        return {}

    try:
        conn.execute("DROP TABLE IF EXISTS temp_ohlcv_plan_instruments")
        conn.execute("DROP TABLE IF EXISTS temp_ohlcv_plan_intervals")

        conn.execute("""
            CREATE TEMP TABLE temp_ohlcv_plan_instruments (
                instrument_key VARCHAR
            );
        """)

        conn.execute("""
            CREATE TEMP TABLE temp_ohlcv_plan_intervals (
                candle_mode VARCHAR,
                unit VARCHAR,
                interval_value INTEGER
            );
        """)

        conn.executemany("""
            INSERT INTO temp_ohlcv_plan_instruments (instrument_key)
            VALUES (?);
        """, [(instrument_key,) for instrument_key in instrument_keys])

        conn.executemany("""
            INSERT INTO temp_ohlcv_plan_intervals (
                candle_mode,
                unit,
                interval_value
            )
            VALUES (?, ?, ?);
        """, interval_rows)

        rows = conn.execute("""
            SELECT
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value,
                MIN(candles.candle_date) AS min_date,
                MAX(candles.candle_date) AS max_date,
                COUNT(1) AS row_count
            FROM upstox_ohlcv_candles candles
            INNER JOIN temp_ohlcv_plan_instruments instruments
                ON instruments.instrument_key = candles.instrument_key
            INNER JOIN temp_ohlcv_plan_intervals intervals
                ON intervals.candle_mode = candles.candle_mode
               AND intervals.unit = candles.unit
               AND intervals.interval_value = candles.interval_value
            WHERE candles.provider = ?
              AND candles.instrument_source = ?
            GROUP BY
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value;
        """, [
            UPSTOX_PROVIDER,
            source
        ]).fetchall()

        cache = {}

        for row in rows:
            cache[(
                row[0],
                row[1],
                row[2],
                int(row[3] or 0)
            )] = {
                "min_date": row[4],
                "max_date": row[5],
                "count": int(row[6] or 0)
            }

        log_ohlcv_message(
            f"Loaded saved OHLCV bounds cache for source={source}: "
            f"{len(cache)} instrument/mode/interval groups."
        )

        return cache

    finally:
        try:
            conn.execute("DROP TABLE IF EXISTS temp_ohlcv_plan_intervals")
            conn.execute("DROP TABLE IF EXISTS temp_ohlcv_plan_instruments")
        except Exception:
            pass

def get_saved_ohlcv_date_bounds(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    saved_bounds_cache: Optional[dict] = None
) -> dict:
    cache_key = (
        mode,
        instrument_key,
        unit,
        int(interval_value or 0)
    )

    if saved_bounds_cache is not None:
        return saved_bounds_cache.get(cache_key, {
            "min_date": None,
            "max_date": None,
            "count": 0
        })

    row = conn.execute("""
        SELECT
            MIN(candle_date),
            MAX(candle_date),
            COUNT(1)
        FROM upstox_ohlcv_candles
        WHERE provider = ?
          AND instrument_source = ?
          AND candle_mode = ?
          AND instrument_key = ?
          AND unit = ?
          AND interval_value = ?;
    """, [
        UPSTOX_PROVIDER,
        source,
        mode,
        instrument_key,
        unit,
        interval_value
    ]).fetchone()

    if not row:
        return {
            "min_date": None,
            "max_date": None,
            "count": 0
        }

    return {
        "min_date": row[0],
        "max_date": row[1],
        "count": int(row[2] or 0)
    }


def should_skip_ohlcv_chunk_by_saved_bounds(
    conn,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    from_date: date,
    to_date: date
) -> bool:
    bounds = get_saved_ohlcv_date_bounds(
        conn=conn,
        source=source,
        mode=mode,
        instrument_key=instrument_key,
        unit=unit,
        interval_value=interval_value
    )

    min_date = bounds.get("min_date")
    max_date = bounds.get("max_date")

    if not min_date or not max_date:
        return False

    return min_date <= from_date and max_date >= to_date


def get_effective_ohlcv_date_range_for_instrument(
    conn,
    config: dict,
    source: str,
    mode: str,
    instrument_key: str,
    unit: str,
    interval_value: int,
    saved_bounds_cache: Optional[dict] = None
) -> Optional[dict]:
    available_start_date = get_ohlcv_available_start_date(
        source=source,
        mode=mode,
        unit=unit
    )
    effective_from_date = max(config["from_date"], available_start_date)
    effective_to_date = config["to_date"]

    if effective_to_date < effective_from_date:
        return None

    if (
        config.get("skip_existing")
        and config.get("auto_date_range")
        and not config.get("from_date_was_provided")
    ):
        bounds = get_saved_ohlcv_date_bounds(
            conn=conn,
            source=source,
            mode=mode,
            instrument_key=instrument_key,
            unit=unit,
            interval_value=interval_value,
            saved_bounds_cache=saved_bounds_cache
        )
        saved_max_date = bounds.get("max_date")

        if saved_max_date:
            effective_from_date = max(
                effective_from_date,
                saved_max_date + timedelta(days=1)
            )

            if effective_from_date > effective_to_date:
                return None

    return {
        "from_date": effective_from_date,
        "to_date": effective_to_date
    }



def fetch_ohlcv_instruments(conn, source: str, config: dict) -> List[dict]:
    params = []

    if source == OHLCV_CURRENT_SOURCE:
        where_sql = """
        WHERE instrument_key IS NOT NULL
          AND TRIM(instrument_key) <> ''
          AND source_type = 'bod_complete'
          AND (
              UPPER(COALESCE(segment, '')) IN ('NSE_EQ', 'BSE_EQ')
              OR UPPER(COALESCE(instrument_type, '')) IN ('EQ', 'EQUITY')
          )
        """

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                isin,
                NULL AS expiry,
                instrument_type
            FROM upstox_instruments
            {where_sql}
            ORDER BY trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    if source == OHLCV_EXPIRED_SOURCE:
        where_sql = "WHERE instrument_key IS NOT NULL AND TRIM(instrument_key) <> ''"

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                NULL AS isin,
                expiry,
                instrument_type
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY expiry DESC, trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    return []

    if source == OHLCV_EXPIRED_SOURCE:
        where_sql = "WHERE instrument_key IS NOT NULL AND TRIM(instrument_key) <> ''"

        if config["single_instrument_key"]:
            where_sql += " AND instrument_key = ?"
            params.append(config["single_instrument_key"])

        limit_sql = ""

        if config["instrument_limit"]:
            limit_sql = "LIMIT ?"
            params.append(config["instrument_limit"])

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                NULL AS isin,
                expiry,
                instrument_type
            FROM upstox_expired_instruments
            {where_sql}
            ORDER BY expiry DESC, trading_symbol, instrument_key
            {limit_sql};
        """, params).fetchall()

        return [
            {
                "instrument_key": row[0],
                "trading_symbol": row[1],
                "name": row[2],
                "exchange": row[3],
                "segment": row[4],
                "isin": row[5],
                "expiry": row[6],
                "instrument_type": row[7]
            }
            for row in rows
        ]

    return []


def build_ohlcv_url(source: str, mode: str, instrument_key: str, interval: dict, from_date: date, to_date: date) -> str:
    encoded_instrument_key = urllib.parse.quote(instrument_key, safe="")

    if source == OHLCV_EXPIRED_SOURCE:
        expired_interval = interval.get("expired_interval")

        if not expired_interval:
            raise ValueError("Interval is not supported for expired OHLCV candles.")

        return (
            f"{UPSTOX_EXPIRED_HISTORICAL_URL}/"
            f"{encoded_instrument_key}/{expired_interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        )

    if mode == OHLCV_INTRADAY_MODE:
        return (
            f"{UPSTOX_CURRENT_INTRADAY_V3_URL}/"
            f"{encoded_instrument_key}/{interval['unit']}/{interval['interval_value']}"
        )

    return (
        f"{UPSTOX_CURRENT_HISTORICAL_V3_URL}/"
        f"{encoded_instrument_key}/{interval['unit']}/{interval['interval_value']}/"
        f"{to_date.isoformat()}/{from_date.isoformat()}"
    )


def upstox_http_get_json(url: str, token: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict:
    request = urllib.request.Request(
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {normalize_upstox_token(token)}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_text = response.read().decode("utf-8")
            return json.loads(response_text or "{}")
    except urllib.error.HTTPError as error:
        error_text = error.read().decode("utf-8", errors="replace")
        raise HTTPException(
            status_code=error.code,
            detail=error_text or str(error)
        )
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to call Upstox OHLCV API: {error}"
        )


def fetch_ohlcv_candles_with_retry(
    url: str,
    token: str,
    retry_count: int,
    retry_failed: bool,
    rate_limiter: UpstoxRollingRateLimiter
) -> dict:
    attempts = retry_count if retry_failed else 1
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot()
            return upstox_http_get_json(url=url, token=token)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = (
                error.status_code in (408, 429, 500, 502, 503, 504)
                or "timeout" in error_text
                or "rate" in error_text
            )

            if not retry_failed or not should_retry or attempt >= attempts:
                raise

            sleep_seconds = min(30, 2 * attempt)
            print(f"Upstox OHLCV retry {attempt}/{attempts} after {sleep_seconds}s: {error.detail}")
            time.sleep(sleep_seconds)

    if last_error:
        raise last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to call Upstox OHLCV API."
    )


def extract_ohlcv_candles(response: dict) -> List[list]:
    if not isinstance(response, dict):
        return []

    data = response.get("data")

    if isinstance(data, dict) and isinstance(data.get("candles"), list):
        return data.get("candles")

    if isinstance(response.get("candles"), list):
        return response.get("candles")

    return []


def parse_ohlcv_timestamp(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    clean_value = str(value).strip()

    try:
        parsed = datetime.fromisoformat(clean_value.replace("Z", "+00:00"))
        return parsed.replace(tzinfo=None)
    except Exception:
        pass

    try:
        return datetime.strptime(clean_value[:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        return None


def normalize_ohlcv_candle_record(
    candle: list,
    source: str,
    mode: str,
    interval: dict,
    instrument: dict,
    sync_id: str
) -> Optional[dict]:
    if not isinstance(candle, list) or len(candle) < 6:
        return None

    candle_timestamp = parse_ohlcv_timestamp(candle[0])

    if not candle_timestamp:
        return None

    return {
        "provider": UPSTOX_PROVIDER,
        "instrument_source": source,
        "candle_mode": mode,
        "instrument_key": instrument.get("instrument_key"),
        "trading_symbol": instrument.get("trading_symbol"),
        "name": instrument.get("name"),
        "exchange": instrument.get("exchange"),
        "segment": instrument.get("segment"),
        "isin": instrument.get("isin"),
        "expiry": normalize_expiry_value(instrument.get("expiry")),
        "instrument_type": instrument.get("instrument_type"),
        "unit": interval["unit"],
        "interval_value": interval["interval_value"],
        "interval_label": interval["label"],
        "candle_timestamp": candle_timestamp,
        "candle_date": candle_timestamp.date(),
        "open_price": candle[1] if len(candle) > 1 else None,
        "high_price": candle[2] if len(candle) > 2 else None,
        "low_price": candle[3] if len(candle) > 3 else None,
        "close_price": candle[4] if len(candle) > 4 else None,
        "volume": candle[5] if len(candle) > 5 else 0,
        "open_interest": candle[6] if len(candle) > 6 else 0,
        "source_sync_id": sync_id,
        "raw_json": json.dumps(candle, ensure_ascii=False, default=str)
    }


def insert_ohlcv_candles(conn, records: List[dict]) -> int:
    if not records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ohlcv_candles (
            provider,
            instrument_source,
            candle_mode,
            instrument_key,
            trading_symbol,
            name,
            exchange,
            segment,
            isin,
            expiry,
            instrument_type,
            unit,
            interval_value,
            interval_label,
            candle_timestamp,
            candle_date,
            open_price,
            high_price,
            low_price,
            close_price,
            volume,
            open_interest,
            source_sync_id,
            raw_json,
            ingested_at,
            updated_at
        )
        SELECT
            ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS DATE), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            TRY_CAST(? AS JSON), CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            record.get("provider"),
            record.get("instrument_source"),
            record.get("candle_mode"),
            record.get("instrument_key"),
            record.get("trading_symbol"),
            record.get("name"),
            record.get("exchange"),
            record.get("segment"),
            record.get("isin"),
            record.get("expiry"),
            record.get("instrument_type"),
            record.get("unit"),
            record.get("interval_value"),
            record.get("interval_label"),
            record.get("candle_timestamp"),
            record.get("candle_date"),
            record.get("open_price"),
            record.get("high_price"),
            record.get("low_price"),
            record.get("close_price"),
            record.get("volume"),
            record.get("open_interest"),
            record.get("source_sync_id"),
            record.get("raw_json")
        )
        for record in records
    ])

    return len(records)


def insert_ohlcv_daily_compatibility_rows(conn, records: List[dict]) -> int:
    daily_records = [
        record
        for record in records
        if record.get("instrument_source") == OHLCV_CURRENT_SOURCE
        and record.get("candle_mode") == OHLCV_HISTORICAL_MODE
        and record.get("unit") == "days"
        and int(record.get("interval_value") or 0) == 1
    ]

    if not daily_records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO ohlcv_daily (
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
    """, [
        (
            record.get("instrument_key"),
            record.get("trading_symbol") or "--",
            record.get("candle_date"),
            record.get("open_price"),
            record.get("high_price"),
            record.get("low_price"),
            record.get("close_price"),
            record.get("volume") or 0,
            record.get("open_interest") or 0
        )
        for record in daily_records
    ])

    return len(daily_records)



def log_ohlcv_message(message: str):
    print(f"[OHLCV] {message}", flush=True)


def count_ohlcv_records_for_sync(
    conn,
    sync_id: Optional[str],
    started_at: Optional[datetime] = None
) -> int:
    if not sync_id:
        return 0

    try:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_ohlcv_candles
            WHERE source_sync_id = ?;
        """, [sync_id]).fetchone()

        return int(row[0] or 0) if row else 0

    except Exception as error:
        log_ohlcv_message(f"Unable to count saved records for sync {sync_id}: {error}")
        return 0

def filter_new_ohlcv_records(conn, records: List[dict]) -> List[dict]:
    if not records:
        return []

    try:
        conn.execute("DROP TABLE IF EXISTS temp_ohlcv_incoming_records")

        conn.execute("""
            CREATE TEMP TABLE temp_ohlcv_incoming_records (
                provider VARCHAR,
                instrument_source VARCHAR,
                candle_mode VARCHAR,
                instrument_key VARCHAR,
                trading_symbol VARCHAR,
                name VARCHAR,
                exchange VARCHAR,
                segment VARCHAR,
                isin VARCHAR,
                expiry VARCHAR,
                instrument_type VARCHAR,
                unit VARCHAR,
                interval_value INTEGER,
                interval_label VARCHAR,
                candle_timestamp TIMESTAMP,
                candle_date DATE,
                open_price DOUBLE,
                high_price DOUBLE,
                low_price DOUBLE,
                close_price DOUBLE,
                volume DOUBLE,
                open_interest DOUBLE,
                source_sync_id VARCHAR,
                raw_json VARCHAR
            );
        """)

        conn.executemany("""
            INSERT INTO temp_ohlcv_incoming_records (
                provider,
                instrument_source,
                candle_mode,
                instrument_key,
                trading_symbol,
                name,
                exchange,
                segment,
                isin,
                expiry,
                instrument_type,
                unit,
                interval_value,
                interval_label,
                candle_timestamp,
                candle_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                open_interest,
                source_sync_id,
                raw_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, [
            (
                record.get("provider"),
                record.get("instrument_source"),
                record.get("candle_mode"),
                record.get("instrument_key"),
                record.get("trading_symbol"),
                record.get("name"),
                record.get("exchange"),
                record.get("segment"),
                record.get("isin"),
                record.get("expiry"),
                record.get("instrument_type"),
                record.get("unit"),
                int(record.get("interval_value") or 0),
                record.get("interval_label"),
                record.get("candle_timestamp"),
                record.get("candle_date"),
                record.get("open_price"),
                record.get("high_price"),
                record.get("low_price"),
                record.get("close_price"),
                record.get("volume"),
                record.get("open_interest"),
                record.get("source_sync_id"),
                record.get("raw_json")
            )
            for record in records
        ])

        rows = conn.execute("""
            SELECT
                incoming.provider,
                incoming.instrument_source,
                incoming.candle_mode,
                incoming.instrument_key,
                incoming.trading_symbol,
                incoming.name,
                incoming.exchange,
                incoming.segment,
                incoming.isin,
                incoming.expiry,
                incoming.instrument_type,
                incoming.unit,
                incoming.interval_value,
                incoming.interval_label,
                incoming.candle_timestamp,
                incoming.candle_date,
                incoming.open_price,
                incoming.high_price,
                incoming.low_price,
                incoming.close_price,
                incoming.volume,
                incoming.open_interest,
                incoming.source_sync_id,
                incoming.raw_json
            FROM (
                SELECT
                    *,
                    ROW_NUMBER() OVER (
                        PARTITION BY
                            provider,
                            instrument_source,
                            candle_mode,
                            instrument_key,
                            unit,
                            interval_value,
                            candle_timestamp
                        ORDER BY candle_timestamp
                    ) AS duplicate_rank
                FROM temp_ohlcv_incoming_records
            ) incoming
            LEFT JOIN upstox_ohlcv_candles existing
                ON existing.provider = incoming.provider
               AND existing.instrument_source = incoming.instrument_source
               AND existing.candle_mode = incoming.candle_mode
               AND existing.instrument_key = incoming.instrument_key
               AND existing.unit = incoming.unit
               AND existing.interval_value = incoming.interval_value
               AND existing.candle_timestamp = incoming.candle_timestamp
            WHERE incoming.duplicate_rank = 1
              AND existing.instrument_key IS NULL;
        """).fetchall()

        return [
            {
                "provider": row[0],
                "instrument_source": row[1],
                "candle_mode": row[2],
                "instrument_key": row[3],
                "trading_symbol": row[4],
                "name": row[5],
                "exchange": row[6],
                "segment": row[7],
                "isin": row[8],
                "expiry": row[9],
                "instrument_type": row[10],
                "unit": row[11],
                "interval_value": row[12],
                "interval_label": row[13],
                "candle_timestamp": row[14],
                "candle_date": row[15],
                "open_price": row[16],
                "high_price": row[17],
                "low_price": row[18],
                "close_price": row[19],
                "volume": row[20],
                "open_interest": row[21],
                "source_sync_id": row[22],
                "raw_json": row[23]
            }
            for row in rows
        ]

    finally:
        try:
            conn.execute("DROP TABLE IF EXISTS temp_ohlcv_incoming_records")
        except Exception:
            pass

def persist_ohlcv_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    new_records = filter_new_ohlcv_records(conn, records)

    if not new_records:
        log_ohlcv_message(
            "OHLCV batch skipped because all returned candles already exist in DuckDB."
        )
        return 0

    try:
        conn.execute("BEGIN TRANSACTION")
        insert_ohlcv_candles(conn, new_records)
        insert_ohlcv_daily_compatibility_rows(conn, new_records)
        conn.execute("COMMIT")
        return len(new_records)
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise


def update_ohlcv_metrics_progress(conn, sync_id: str, metrics: dict):
    try:
        finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
    except Exception as error:
        print(f"Unable to update OHLCV progress metrics: {error}")


def sync_upstox_ohlcv_daily_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0
    metrics = {
        "api_calls_attempted": 0,
        "api_calls_skipped": 0,
        "candles_inserted": 0,
        "candles_skipped": 0,
        "failed_instruments": 0
    }
    failed_items = []

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        run_config = config or get_saved_ohlcv_options_for_run(conn)
        normalized_config = normalize_ohlcv_config(run_config)

        log_ohlcv_message(
            "Starting collection "
            f"sources={normalized_config['sources']} "
            f"modes={normalized_config['candle_modes']} "
            f"intervals={normalized_config['intervals']} "
            f"from={normalized_config['from_date']} "
            f"to={normalized_config['to_date']} "
            f"use_current_day={normalized_config['use_current_day']} "
            f"auto_date_range={normalized_config['auto_date_range']} "
            f"limit={normalized_config['instrument_limit'] or 'all'} "
            f"single={normalized_config['single_instrument_key'] or '--'}"
        )

        analytical_token = None
        access_token = None

        if OHLCV_CURRENT_SOURCE in normalized_config["sources"]:
            analytical_token = get_saved_upstox_analytical_token(conn)
            log_ohlcv_message("Analytical token loaded for current OHLCV.")

        if OHLCV_EXPIRED_SOURCE in normalized_config["sources"]:
            access_token = get_saved_upstox_access_token(conn)
            log_ohlcv_message("Access token loaded for expired OHLCV.")

        sync_id = create_sync_run(
            conn,
            OHLCV_SYNC_TYPE,
            "running",
            "OHLCV download started.",
            current_user=current_user
        )
        update_ohlcv_sync_run_options(conn, sync_id, normalized_config)

        log_ohlcv_message(f"Sync run created: {sync_id}")

        rate_limiter = UpstoxRollingRateLimiter()

        for source in normalized_config["sources"]:
            check_sync_cancelled(conn, sync_id)

            instruments = fetch_ohlcv_instruments(conn, source, normalized_config)

            if not instruments:
                log_ohlcv_message(f"No instruments found for source={source}.")
                continue

            token = analytical_token if source == OHLCV_CURRENT_SOURCE else access_token

            log_ohlcv_message(
                f"Source {source}: {len(instruments)} instruments loaded."
            )

            saved_bounds_cache = build_ohlcv_saved_bounds_cache(
                conn=conn,
                source=source,
                config=normalized_config,
                instruments=instruments
            )

            for instrument_index, instrument in enumerate(instruments, start=1):
                check_sync_cancelled(conn, sync_id)

                if instrument_index > 1 and normalized_config["batch_size"]:
                    if (instrument_index - 1) % normalized_config["batch_size"] == 0:
                        log_ohlcv_message(
                            "Batch pause "
                            f"after {instrument_index - 1} instruments "
                            f"for {normalized_config['batch_delay_seconds']}s."
                        )
                        time.sleep(normalized_config["batch_delay_seconds"])
                        check_sync_cancelled(conn, sync_id)

                instrument_key = safe_strip(instrument.get("instrument_key"))
                trading_symbol = safe_strip(instrument.get("trading_symbol")) or "--"

                if not instrument_key:
                    continue

                log_ohlcv_message(
                    f"Instrument {instrument_index}/{len(instruments)} "
                    f"{trading_symbol} ({instrument_key})"
                )

                for mode in normalized_config["candle_modes"]:
                    check_sync_cancelled(conn, sync_id)

                    if source == OHLCV_EXPIRED_SOURCE and mode == OHLCV_INTRADAY_MODE:
                        metrics["api_calls_skipped"] += 1
                        log_ohlcv_message(
                            f"Skipped {instrument_key}: expired intraday is not supported."
                        )
                        update_ohlcv_metrics_progress(conn, sync_id, metrics)
                        continue

                    for interval_key in normalized_config["intervals"]:
                        check_sync_cancelled(conn, sync_id)

                        interval = get_ohlcv_interval_definition(interval_key)

                        if source == OHLCV_EXPIRED_SOURCE and not interval.get("expired_interval"):
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: expired interval {interval_key} is not supported."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        if mode == OHLCV_INTRADAY_MODE and interval["unit"] in ("weeks", "months"):
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: intraday interval {interval_key} is not supported."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        effective_range = get_effective_ohlcv_date_range_for_instrument(
                            conn=conn,
                            config=normalized_config,
                            source=source,
                            mode=mode,
                            instrument_key=instrument_key,
                            unit=interval["unit"],
                            interval_value=interval["interval_value"],
                            saved_bounds_cache=saved_bounds_cache
                        )

                        if not effective_range:
                            metrics["api_calls_skipped"] += 1
                            log_ohlcv_message(
                                f"Skipped {instrument_key}: saved data already reaches "
                                f"{normalized_config['to_date']} for {source} {mode} {interval_key}."
                            )
                            update_ohlcv_metrics_progress(conn, sync_id, metrics)
                            continue

                        chunks = split_ohlcv_date_range(
                            from_date=effective_range["from_date"],
                            to_date=effective_range["to_date"],
                            unit=interval["unit"],
                            interval_value=interval["interval_value"],
                            source=source
                        )

                        if mode == OHLCV_INTRADAY_MODE:
                            chunks = [
                                {
                                    "from_date": effective_range["to_date"],
                                    "to_date": effective_range["to_date"]
                                }
                            ]

                        for chunk_index, chunk in enumerate(chunks, start=1):
                            check_sync_cancelled(conn, sync_id)

                            chunk_from = chunk["from_date"]
                            chunk_to = chunk["to_date"]

                            if normalized_config["skip_existing"] and should_skip_ohlcv_chunk_by_saved_bounds(
                                conn=conn,
                                source=source,
                                mode=mode,
                                instrument_key=instrument_key,
                                unit=interval["unit"],
                                interval_value=interval["interval_value"],
                                from_date=chunk_from,
                                to_date=chunk_to
                            ):
                                skipped_days = (chunk_to - chunk_from).days + 1
                                metrics["api_calls_skipped"] += 1
                                metrics["candles_skipped"] += skipped_days
                                log_ohlcv_message(
                                    f"Skipped API call {instrument_key} {source} {mode} "
                                    f"{interval_key} {chunk_from} to {chunk_to}: saved date range already covers it."
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue

                            url = build_ohlcv_url(
                                source=source,
                                mode=mode,
                                instrument_key=instrument_key,
                                interval=interval,
                                from_date=chunk_from,
                                to_date=chunk_to
                            )

                            try:
                                log_ohlcv_message(
                                    f"API {source} {mode} {interval_key} "
                                    f"chunk {chunk_index}/{len(chunks)} "
                                    f"{instrument_key} {chunk_from} to {chunk_to}"
                                )

                                response = fetch_ohlcv_candles_with_retry(
                                    url=url,
                                    token=token,
                                    retry_count=normalized_config["retry_count"],
                                    retry_failed=normalized_config["retry_failed"],
                                    rate_limiter=rate_limiter
                                )
                                metrics["api_calls_attempted"] += 1

                                candles = extract_ohlcv_candles(response)
                                records = []

                                for candle in candles:
                                    normalized_record = normalize_ohlcv_candle_record(
                                        candle=candle,
                                        source=source,
                                        mode=mode,
                                        interval=interval,
                                        instrument=instrument,
                                        sync_id=sync_id
                                    )

                                    if normalized_record:
                                        records.append(normalized_record)

                                inserted_records = persist_ohlcv_records(conn, records)

                                if inserted_records:
                                    total_records += inserted_records
                                    metrics["candles_inserted"] += inserted_records

                                log_ohlcv_message(
                                    f"Saved {inserted_records} OHLCV rows for "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}. "
                                    f"Total saved={total_records}."
                                )

                                update_ohlcv_metrics_progress(conn, sync_id, metrics)

                                if normalized_config["request_delay_ms"]:
                                    time.sleep(normalized_config["request_delay_ms"] / 1000)
                                    check_sync_cancelled(conn, sync_id)

                            except SyncCancelled:
                                raise
                            except HTTPException as error:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass

                                metrics["failed_instruments"] += 1
                                failed_items.append({
                                    "instrument_key": instrument_key,
                                    "source": source,
                                    "mode": mode,
                                    "interval": interval_key,
                                    "from_date": chunk_from.isoformat(),
                                    "to_date": chunk_to.isoformat(),
                                    "error": error.detail
                                })
                                log_ohlcv_message(
                                    "API failed "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}: {error.detail}"
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue
                            except Exception as error:
                                try:
                                    conn.rollback()
                                except Exception:
                                    pass

                                metrics["failed_instruments"] += 1
                                failed_items.append({
                                    "instrument_key": instrument_key,
                                    "source": source,
                                    "mode": mode,
                                    "interval": interval_key,
                                    "from_date": chunk_from.isoformat(),
                                    "to_date": chunk_to.isoformat(),
                                    "error": str(error)
                                })
                                log_ohlcv_message(
                                    "Save/API failed "
                                    f"{instrument_key} {source} {mode} {interval_key} "
                                    f"{chunk_from} to {chunk_to}: {error}"
                                )
                                update_ohlcv_metrics_progress(conn, sync_id, metrics)
                                continue

        total_records = count_ohlcv_records_for_sync(conn, sync_id) or total_records
        metrics["candles_inserted"] = max(
            int(metrics.get("candles_inserted") or 0),
            int(total_records or 0)
        )

        status_text = "success" if not failed_items else "partial_success"
        message = "OHLCV downloaded successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_ohlcv_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

            message = (
                "OHLCV downloaded with some failed instruments. "
                f"Failed items saved to {failed_file}."
            )

        finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
        finish_sync_run(
            conn,
            sync_id,
            status_text,
            message,
            total_records,
            started_at
        )

        log_ohlcv_message(
            f"Finished sync {sync_id}: status={status_text}, saved={total_records}, "
            f"api_calls={metrics['api_calls_attempted']}, skipped={metrics['api_calls_skipped']}, "
            f"failed={metrics['failed_instruments']}."
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": status_text,
            "message": message,
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "metrics": metrics,
            "failed_items": len(failed_items)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        saved_records = count_ohlcv_records_for_sync(conn, sync_id, started_at)
        total_records = max(total_records, saved_records)
        metrics["candles_inserted"] = max(
            int(metrics.get("candles_inserted") or 0),
            int(total_records or 0)
        )

        log_ohlcv_message(
            f"Cancellation received for sync {sync_id}. "
            f"Committed OHLCV rows preserved={total_records}."
        )

        if sync_id:
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "OHLCV download cancelled. Completed rows were saved.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "OHLCV download cancelled. Completed rows were saved.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "metrics": metrics
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            saved_records = count_ohlcv_records_for_sync(conn, sync_id)
            total_records = max(total_records, saved_records)
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"OHLCV download failed: {error.detail}",
                total_records,
                started_at
            )

        log_ohlcv_message(f"Failed sync {sync_id}: {error.detail}")

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            saved_records = count_ohlcv_records_for_sync(conn, sync_id)
            total_records = max(total_records, saved_records)
            finish_ohlcv_sync_run_metrics(conn, sync_id, metrics)
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"OHLCV download failed: {error}",
                total_records,
                started_at
            )

        log_ohlcv_message(f"Failed sync {sync_id}: {error}")

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to download OHLCV: {error}"
        )

    finally:
        conn.close()

def build_ohlcv_preview_filters(
    search: str,
    source: str,
    mode: str,
    interval: str,
    segment: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_source = source.strip() if source else "all"
    clean_mode = mode.strip() if mode else "all"
    clean_interval = interval.strip() if interval else "all"
    clean_segment = segment.strip() if segment else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(name, '')) LIKE ?
                OR LOWER(COALESCE(exchange, '')) LIKE ?
                OR LOWER(COALESCE(segment, '')) LIKE ?
                OR LOWER(COALESCE(instrument_type, '')) LIKE ?
                OR LOWER(COALESCE(instrument_source, '')) LIKE ?
                OR LOWER(COALESCE(candle_mode, '')) LIKE ?
                OR LOWER(COALESCE(interval_label, '')) LIKE ?
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
            search_value,
            search_value
        ])

    if clean_source != "all":
        where_clauses.append("instrument_source = ?")
        params.append(clean_source)

    if clean_mode != "all":
        where_clauses.append("candle_mode = ?")
        params.append(clean_mode)

    if clean_interval != "all":
        interval_key = normalize_ohlcv_interval_key(clean_interval)
        interval_definition = OHLCV_INTERVAL_OPTIONS.get(interval_key)

        if interval_definition:
            where_clauses.append("unit = ? AND interval_value = ?")
            params.extend([
                interval_definition["unit"],
                interval_definition["interval_value"]
            ])
        else:
            where_clauses.append("LOWER(COALESCE(interval_label, '')) = ?")
            params.append(clean_interval.lower())

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_ohlcv_preview(row):
    return {
        "instrument_key": row[0],
        "trading_symbol": row[1],
        "source": row[2],
        "mode": row[3],
        "unit": row[4],
        "interval_value": row[5],
        "interval_label": row[6],
        "timestamp": str(row[7]) if row[7] else None,
        "date": str(row[8]) if row[8] else None,
        "open": row[9],
        "high": row[10],
        "low": row[11],
        "close": row[12],
        "volume": row[13],
        "open_interest": row[14],
        "exchange": row[15],
        "segment": row[16],
        "instrument_type": row[17],
        "expiry": str(row[18]) if row[18] else None,
        "name": row[19],
        "isin": row[20],
        "ingested_at": str(row[21]) if row[21] else None,
        "updated_at": str(row[22]) if row[22] else None
    }


def get_upstox_ohlcv_preview_service(
    search: str = "",
    source: str = "all",
    mode: str = "all",
    interval: str = "all",
    segment: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_ohlcv_preview_filters(
            search=search,
            source=source,
            mode=mode,
            interval=interval,
            segment=segment
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_ohlcv_candles
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                instrument_source,
                candle_mode,
                unit,
                interval_value,
                interval_label,
                candle_timestamp,
                candle_date,
                open_price,
                high_price,
                low_price,
                close_price,
                volume,
                open_interest,
                exchange,
                segment,
                instrument_type,
                expiry,
                name,
                isin,
                ingested_at,
                updated_at
            FROM upstox_ohlcv_candles
            {where_sql}
            ORDER BY candle_timestamp DESC, ingested_at DESC, instrument_key
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_ohlcv_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()

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

    if page_size > 2000:
        return 2000

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
