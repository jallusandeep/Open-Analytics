import gzip
import json
import logging
import time
import uuid
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.repositories.base_repository import db_connection
from app.repositories.data_collection_repository import DataCollectionRepository

logger = logging.getLogger(__name__)
data_collection_repo = DataCollectionRepository()


UPSTOX_PROVIDER = "upstox"

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data" / "upstox"
MASTER_INSTRUMENT_FILE = DATA_DIR / "upstox_instruments.json"
EXPIRED_INSTRUMENT_FILE = DATA_DIR / "upstox_expired_instruments.json"

UPSTOX_CURRENT_MASTER_URL = (
    "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz"
)

REQUEST_TIMEOUT_SECONDS = 180
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
    return data_collection_repo.get_upstox_connection_status(conn)


def get_saved_upstox_access_token(conn) -> str:
    row = data_collection_repo.get_saved_upstox_access_token_row(conn)

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


def mark_stale_sync_runs(conn):
    data_collection_repo.mark_stale_sync_runs(conn)


def ensure_no_active_sync_run(conn):
    mark_stale_sync_runs(conn)

    row = data_collection_repo.get_active_sync_run(conn)

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

    logger.info(
        "Creating sync run: sync_id=%s type=%s status=%s",
        sync_id,
        sync_type,
        status_text,
    )

    data_collection_repo.create_sync_run(
        conn,
        sync_id=sync_id,
        sync_type=sync_type,
        status_text=status_text,
        message=message,
        trigger_metadata=trigger_metadata,
    )
    return sync_id


def finish_sync_run(
    conn,
    sync_id: str,
    status_text: str,
    message: str,
    total_records: int,
    started_at: datetime
):
    logger.info(
        "Finishing sync run: sync_id=%s status=%s records=%s",
        sync_id,
        status_text,
        total_records,
    )

    data_collection_repo.finish_sync_run(
        conn,
        sync_id=sync_id,
        status_text=status_text,
        message=message,
        total_records=total_records,
        duration_seconds=duration_seconds(started_at),
    )


def check_sync_cancelled(conn, sync_id: str):
    if has_cancel_signal():
        raise SyncCancelled()

    row = data_collection_repo.get_sync_run_status(conn, sync_id)

    if row and row[0] in ("cancel_requested", "cancelled"):
        raise SyncCancelled()


def request_cancel_active_sync_runs_service():
    logger.info("Requesting cancel for active data collection sync runs")
    write_cancel_signal()

    with db_connection() as conn:
        try:
            rows = data_collection_repo.get_running_sync_runs(conn)
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
            data_collection_repo.request_cancel_running_syncs(conn)
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

    data_collection_repo.delete_bod_complete_instruments(conn)

    check_sync_cancelled(conn, sync_id)

    data_collection_repo.import_current_instruments_from_json(conn, duckdb_path)

    logger.info(
        "DuckDB current instruments insert time: %.2f seconds",
        round(time.time() - insert_started_at, 2),
    )

    total_rows = data_collection_repo.count_bod_complete_instruments(conn)
    logger.info("Current instruments inserted into DB: %s", total_rows)

    return total_rows


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
        request_pause_seconds = float(payload.get("request_pause_seconds", 0.05))
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
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0] or 0)
    except Exception:
        return 0


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
        "upstox_ohlcv_daily": "ohlcv_daily"
    }.get(sync_type or "")


def safe_active_job_started_count(conn, sync_type: Optional[str], started_at) -> Optional[int]:
    table_name = table_name_for_sync_type(sync_type)

    if not table_name or not started_at:
        return None

    try:
        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE synced_at < ?;
        """, [started_at]).fetchone()
        return int(row[0] or 0)
    except Exception:
        return None


def get_data_collection_summary_service():
    logger.info("Fetching data collection summary")

    with db_connection() as conn:
        mark_stale_sync_runs(conn)
        connection_status = get_upstox_connection_status(conn)

        current_count = data_collection_repo.table_count(conn, "upstox_instruments")
        expired_count = data_collection_repo.table_count(conn, "upstox_expired_instruments")
        equity_count = data_collection_repo.table_count(conn, "upstox_equity_instruments")
        ohlcv_daily_count = data_collection_repo.table_count(conn, "ohlcv_daily")
        equity_news_count = data_collection_repo.table_count(conn, "equity_news")
        fundamentals_count = data_collection_repo.table_count(conn, "fundamentals")
        corporate_actions_count = data_collection_repo.table_count(conn, "corporate_actions")
        fii_dii_count = data_collection_repo.table_count(conn, "fii_dii_activity")

        total_runs = data_collection_repo.count_sync_runs(conn)
        last_run = data_collection_repo.get_last_sync_run(conn)
        current_run = data_collection_repo.last_success_run(conn, "upstox_current_instruments")
        expired_run = data_collection_repo.last_success_run(conn, "upstox_expired_instruments")
        equity_run = data_collection_repo.last_success_run(conn, "upstox_equity_instruments")
        ohlcv_run = data_collection_repo.last_success_run(conn, "upstox_ohlcv_daily")
        active_run = data_collection_repo.get_active_sync_run_detail(conn)

        active_job = active_run[0] if active_run else None
        active_job_started_at = active_run[2] if active_run and active_run[2] else None
        active_job_table = table_name_for_sync_type(active_job)
        active_job_current_records = (
            data_collection_repo.table_count(conn, active_job_table)
            if active_job_table else None
        )
        active_job_records_at_start = data_collection_repo.count_records_synced_before(
            conn,
            active_job_table or "",
            active_job_started_at,
        ) if active_job_table else None

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


def get_data_collection_runs_service():
    logger.info("Fetching recent data collection sync runs")

    with db_connection() as conn:
        rows = data_collection_repo.list_recent_sync_runs(conn)

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
            "triggered_by_role": row[11],
        }
        for row in rows
    ]


def sync_upstox_current_instruments_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    logger.info(
        "Starting current instruments sync: user_id=%s",
        (current_user or {}).get("user_id"),
    )
    started_at = datetime.now()
    sync_id = None
    local_file = None
    total_records = 0

    with db_connection() as conn:
        try:
            if clear_cancel_at_start:
                clear_cancel_signal()

            ensure_no_active_sync_run(conn)

            sync_id = create_sync_run(
                conn,
                "upstox_current_instruments",
                "running",
                "Current instrument dump started.",
                current_user=current_user,
            )

            local_file = download_upstox_master_gz_file_once()
            check_sync_cancelled(conn, sync_id)

            conn.execute("BEGIN TRANSACTION")

            total_records = import_current_instruments_from_local_file(
                conn=conn,
                sync_id=sync_id,
                local_file=local_file,
            )

            conn.execute("COMMIT")

            finish_sync_run(
                conn,
                sync_id,
                "success",
                "Current instruments downloaded and imported successfully.",
                total_records,
                started_at,
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "success",
                "message": "Current instruments downloaded and imported successfully.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
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
                    started_at,
                )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "cancelled",
                "message": "Current instrument dump cancelled.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
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
                    started_at,
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
                    started_at,
                )

            if clear_cancel_at_start:
                clear_cancel_signal()

            logger.exception("Current instrument dump failed: %s", error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to dump current instruments: {error}",
            )

        finally:
            delete_downloaded_master_file(local_file)


def sync_upstox_expired_instruments_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    logger.info(
        "Starting expired instruments sync: user_id=%s",
        (current_user or {}).get("user_id"),
    )
    started_at = datetime.now()
    sync_id = None
    expired_download = {
        "records": [],
        "group_statuses": [],
        "skipped_groups": 0,
    }
    total_records = 0

    with db_connection() as conn:
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
                current_user=current_user,
            )

            expired_download = download_expired_instruments_with_sdk(
                conn=conn,
                sync_id=sync_id,
                access_token=access_token,
                config=config,
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
                allow_cancelled_import=was_cancelled,
            )

            conn.execute("COMMIT")

            if was_cancelled:
                finish_sync_run(
                    conn,
                    sync_id,
                    "cancelled",
                    "Expired instrument SDK download cancelled. Completed records were saved.",
                    total_records,
                    started_at,
                )

                if clear_cancel_at_start:
                    clear_cancel_signal()

                return {
                    "status": "cancelled",
                    "message": (
                        "Expired instrument SDK download cancelled. "
                        "Completed records were saved."
                    ),
                    "total_records": total_records,
                    "duration_seconds": duration_seconds(started_at),
                }

            finish_sync_run(
                conn,
                sync_id,
                "success",
                "Expired instruments downloaded through Upstox SDK and imported successfully.",
                total_records,
                started_at,
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "success",
                "message": (
                    "Expired instruments downloaded through Upstox SDK "
                    "and imported successfully."
                ),
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
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
                    started_at,
                )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "cancelled",
                "message": "Expired instrument SDK download cancelled.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
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
                    started_at,
                )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "failed",
                "message": str(error_message),
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at),
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
                    started_at,
                )

            if clear_cancel_at_start:
                clear_cancel_signal()

            logger.exception("Expired instrument dump failed: %s", error)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to dump expired instruments through Upstox SDK: {error}",
            )


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
    current_page = normalize_page(page)
    current_page_size = normalize_page_size(page_size)
    offset = (current_page - 1) * current_page_size

    where_sql, params = build_preview_filters(
        search=search,
        source_type=source_type,
        segment=segment,
        instrument_type=instrument_type,
    )

    with db_connection() as conn:
        total_records = data_collection_repo.count_instruments_preview(
            conn, "upstox_instruments", where_sql, params
        )
        rows = data_collection_repo.list_instruments_preview(
            conn,
            "upstox_instruments",
            where_sql,
            params,
            "synced_at DESC, segment, trading_symbol",
            current_page_size,
            offset,
        )

    total_pages = max(
        1,
        int((total_records + current_page_size - 1) / current_page_size),
    )

    return {
        "rows": [row_to_instrument_preview(row) for row in rows],
        "page": current_page,
        "page_size": current_page_size,
        "total_pages": total_pages,
        "total_records": total_records,
    }


def get_upstox_expired_instruments_preview_service(
    search: str = "",
    source_type: str = "all",
    segment: str = "all",
    instrument_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    current_page = normalize_page(page)
    current_page_size = normalize_page_size(page_size)
    offset = (current_page - 1) * current_page_size

    where_sql, params = build_preview_filters(
        search=search,
        source_type=source_type,
        segment=segment,
        instrument_type=instrument_type,
    )

    with db_connection() as conn:
        total_records = data_collection_repo.count_instruments_preview(
            conn, "upstox_expired_instruments", where_sql, params
        )
        rows = data_collection_repo.list_instruments_preview(
            conn,
            "upstox_expired_instruments",
            where_sql,
            params,
            "synced_at DESC, expiry DESC, segment, trading_symbol",
            current_page_size,
            offset,
        )

    total_pages = max(
        1,
        int((total_records + current_page_size - 1) / current_page_size),
    )

    return {
        "rows": [row_to_instrument_preview(row) for row in rows],
        "page": current_page,
        "page_size": current_page_size,
        "total_pages": total_pages,
        "total_records": total_records,
    }
