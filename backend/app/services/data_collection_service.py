import gzip
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

APP_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = APP_ROOT / "data" / "upstox"
MASTER_INSTRUMENT_FILE = DATA_DIR / "upstox_instruments.json"

# One-time current instruments master download.
# This downloads the official gz file once, extracts it locally,
# then DuckDB imports from the local JSON file.
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
STALE_RUNNING_RUN_HOURS = 2
DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 4

CANCEL_SIGNAL_DIR = APP_ROOT / "runtime"
CANCEL_SIGNAL_FILE = CANCEL_SIGNAL_DIR / "upstox_data_collection.cancel"


class SyncCancelled(Exception):
    pass


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

    return str(value)


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
            detail="Upstox connection token is not saved. Please save token in Connections first."
        )

    return row[0]


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


def create_sync_run(conn, sync_type: str, status_text: str, message: str = "") -> str:
    sync_id = str(uuid.uuid4())

    conn.execute("""
        INSERT INTO upstox_sync_runs (
            sync_id,
            sync_type,
            status,
            started_at,
            finished_at,
            duration_seconds,
            message,
            total_records
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL, NULL, ?, 0);
    """, [
        sync_id,
        sync_type,
        status_text,
        message
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
        headers={"User-Agent": "OpenAnalytics/1.0"}
    )

    print("Downloading Upstox current instruments master file once...")
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


def get_current_instrument_count(conn) -> int:
    try:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM upstox_instruments
            WHERE source_type = 'bod_complete';
        """).fetchone()

        return int(row[0] or 0)
    except Exception:
        return 0


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


def upstox_api_get(access_token: str, path: str, params: Optional[Dict[str, str]] = None):
    query_string = ""

    if params:
        query_string = "?" + urllib.parse.urlencode(params)

    request = urllib.request.Request(
        f"{UPSTOX_BASE_URL}{path}{query_string}",
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            content = response.read().decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        raise HTTPException(
            status_code=error.code,
            detail=error_body or f"Upstox API request failed: {error.code}"
        )
    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox API: {error}"
        )


def get_expiries(access_token: str, underlying_key: str) -> List[str]:
    response = upstox_api_get(
        access_token,
        "/expired-instruments/expiries",
        {"instrument_key": underlying_key}
    )

    return response.get("data") or []


def get_expired_option_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str
) -> List[Dict[str, Any]]:
    response = upstox_api_get(
        access_token,
        "/expired-instruments/option/contract",
        {
            "instrument_key": underlying_key,
            "expiry_date": expiry_date
        }
    )

    return response.get("data") or []


def get_expired_future_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str
) -> List[Dict[str, Any]]:
    response = upstox_api_get(
        access_token,
        "/expired-instruments/future/contract",
        {
            "instrument_key": underlying_key,
            "expiry_date": expiry_date
        }
    )

    return response.get("data") or []


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


def insert_expired_instruments(
    conn,
    rows: List[Dict[str, Any]],
    source_type: str,
    sync_id: str
) -> int:
    if not rows:
        return 0

    check_sync_cancelled(conn, sync_id)

    mapped_rows = [map_expired_instrument(row, source_type) for row in rows]

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
            "total_sync_runs": total_runs,
            "last_sync_at": str(last_run[3]) if last_run and last_run[3] else None,
            "last_duration_seconds": last_run[4] if last_run else None,
            "current_last_sync_at": str(current_run[0]) if current_run and current_run[0] else None,
            "current_duration_seconds": current_run[1] if current_run else None,
            "expired_last_sync_at": str(expired_run[0]) if expired_run and expired_run[0] else None,
            "expired_duration_seconds": expired_run[1] if expired_run else None,
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
                total_records
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
                "total_records": row[7]
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
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        existing_count = get_current_instrument_count(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_current_instruments",
            "running",
            "Current instrument dump started."
        )

        local_file = download_upstox_master_file_once(force_download=False)

        check_sync_cancelled(conn, sync_id)

        if (
            existing_count > 0
            and local_file.exists()
            and local_file.stat().st_size > 0
        ):
            total_records = existing_count

            finish_sync_run(
                conn,
                sync_id,
                "success",
                "Current instruments already exist. Reused local/database records.",
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "success",
                "message": "Current instruments already exist. No re-import needed.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at)
            }

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
            "Current instruments dumped successfully from local master file.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Current instruments dumped successfully from local master file.",
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
            "Expired instrument dump started."
        )

        for underlying_key in DEFAULT_UNDERLYING_KEYS:
            check_sync_cancelled(conn, sync_id)

            expiries = get_expiries(access_token, underlying_key)

            check_sync_cancelled(conn, sync_id)

            for expiry_date in expiries:
                check_sync_cancelled(conn, sync_id)

                conn.execute("""
                    DELETE FROM upstox_expired_instruments
                    WHERE underlying_key = ?
                      AND expiry = ?;
                """, [underlying_key, expiry_date])

                check_sync_cancelled(conn, sync_id)

                option_rows = get_expired_option_contracts(
                    access_token,
                    underlying_key,
                    expiry_date
                )

                total_records += insert_expired_instruments(
                    conn,
                    option_rows,
                    "expired_option",
                    sync_id
                )

                conn.commit()
                time.sleep(API_SLEEP_SECONDS)
                check_sync_cancelled(conn, sync_id)

                future_rows = get_expired_future_contracts(
                    access_token,
                    underlying_key,
                    expiry_date
                )

                total_records += insert_expired_instruments(
                    conn,
                    future_rows,
                    "expired_future",
                    sync_id
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

    current_result = sync_upstox_current_instruments_service(
        current_user,
        clear_cancel_at_start=True
    )

    total_records = int(current_result.get("total_records") or 0)

    if current_result.get("status") == "cancelled":
        return {
            "status": "cancelled",
            "message": "Current Upstox instrument dump cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at),
            "jobs": {
                "current": current_result
            }
        }

    return {
        "status": "success",
        "message": "Current Upstox master instruments completed successfully. Expired instruments were not run because they require a non-read-only Upstox token.",
        "total_records": total_records,
        "duration_seconds": duration_seconds(started_at),
        "jobs": {
            "current": current_result
        }
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