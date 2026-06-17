import gzip
import hashlib
import json
import re
import time
from collections import deque
from io import StringIO
import uuid
import pandas as pd
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
UPSTOX_MARKET_HOLIDAYS_URL = "https://api.upstox.com/v2/market/holidays"
UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE = "upstox_market_holidays"

UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE = "upstox_company_fundamentals"
UPSTOX_FUNDAMENTALS_BASE_URL = "https://api.upstox.com/v2/fundamentals"

UPSTOX_EQUITY_NEWS_SYNC_TYPE = "upstox_equity_news"
UPSTOX_EQUITY_NEWS_URL = "https://api.upstox.com/v2/news"
UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL = 30
UPSTOX_NEWS_MAX_PAGE_SIZE = 100
UPSTOX_NEWS_MAX_PAGE_NUMBER = 100
UPSTOX_NEWS_DEFAULT_RETRY_COUNT = 3

UPSTOX_IPO_SYNC_TYPE = "upstox_ipo_calendar"
IPO_GMP_SCRAPER_SYNC_TYPE = "ipo_gmp_scraper"
IPO_GMP_SCRAPER_URL = "https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/"
IPO_GMP_SCRAPER_REQUIRED_COLUMNS = [
    "IPO Name",
    "IPO GMP",
    "Price Band",
    "Date",
    "Type",
    "Status",
    "Last Updated"
]

UPSTOX_IPO_LIST_URL = "https://api.upstox.com/v2/ipos"
UPSTOX_IPO_DETAIL_URL = "https://api.upstox.com/v2/ipos/{ipo_id}"
UPSTOX_IPO_MAX_RECORDS_PER_CALL = 30
UPSTOX_IPO_DEFAULT_STATUSES = ["upcoming", "open", "closed", "listed"]
UPSTOX_IPO_DEFAULT_ISSUE_TYPES = ["regular", "sme"]
UPSTOX_IPO_DEFAULT_RETRY_COUNT = 3

UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_PROFILE = "company_profile"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_BALANCE_SHEET = "balance_sheet"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_INCOME_STATEMENT = "income_statement"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CASH_FLOW = "cash_flow"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_SHARE_HOLDINGS = "share_holdings"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_KEY_RATIOS = "key_ratios"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CORPORATE_ACTIONS = "corporate_actions"
UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_COMPETITORS = "competitors"

UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS = {
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_PROFILE: {
        "label": "Company Profile",
        "path": "profile",
        "supports_statement_type": False,
        "supports_time_period": False,
        "supports_full_statement": False
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_BALANCE_SHEET: {
        "label": "Balance Sheet",
        "path": "balance-sheet",
        "supports_statement_type": True,
        "supports_time_period": False,
        "supports_full_statement": True
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_INCOME_STATEMENT: {
        "label": "Income Statement",
        "path": "income-statement",
        "supports_statement_type": True,
        "supports_time_period": True,
        "supports_full_statement": True
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CASH_FLOW: {
        "label": "Cash Flow",
        "path": "cash-flow",
        "supports_statement_type": True,
        "supports_time_period": False,
        "supports_full_statement": True
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_SHARE_HOLDINGS: {
        "label": "Share Holdings",
        "path": "share-holdings",
        "supports_statement_type": False,
        "supports_time_period": False,
        "supports_full_statement": False
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_KEY_RATIOS: {
        "label": "Key Ratios",
        "path": "key-ratios",
        "supports_statement_type": False,
        "supports_time_period": False,
        "supports_full_statement": False
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CORPORATE_ACTIONS: {
        "label": "Corporate Actions",
        "path": "corporate-actions",
        "supports_statement_type": False,
        "supports_time_period": False,
        "supports_full_statement": False
    },
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_COMPETITORS: {
        "label": "Competitors",
        "path": "competitors",
        "supports_statement_type": False,
        "supports_time_period": False,
        "supports_full_statement": False
    }
}

UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_ENDPOINTS = [
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_PROFILE,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_BALANCE_SHEET,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_INCOME_STATEMENT,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CASH_FLOW,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_SHARE_HOLDINGS,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_KEY_RATIOS,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CORPORATE_ACTIONS,
    UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_COMPETITORS
]
UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES = ["consolidated", "standalone"]
UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS = ["yearly", "quarterly"]
UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_BATCH_SIZE = 25
UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_REQUEST_DELAY_MS = 250
UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_RETRY_COUNT = 3
UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY = False


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
OHLCV_SAVED_BOUNDS_INSTRUMENT_FILTER_LIMIT = 1000

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
        "upstox_ohlcv_daily": "upstox_ohlcv_candles",
        UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE: "upstox_market_holidays",
        UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE: "upstox_company_fundamentals",
        UPSTOX_EQUITY_NEWS_SYNC_TYPE: "equity_news",
        UPSTOX_IPO_SYNC_TYPE: "upstox_ipo_list",
        IPO_GMP_SCRAPER_SYNC_TYPE: "ipo_gmp_scraper"
    }.get(sync_type or "")


def safe_active_job_started_count(conn, sync_type: Optional[str], started_at) -> Optional[int]:
    table_name = table_name_for_sync_type(sync_type)

    if not table_name or not started_at:
        return None

    timestamp_column = "ingested_at" if table_name in ("upstox_ohlcv_candles", "equity_news", "upstox_ipo_list") else "synced_at"

    if table_name == "ipo_gmp_scraper":
        timestamp_column = "scraped_at"

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
        market_holidays_count = safe_table_count(conn, "upstox_market_holidays")
        equity_news_count = safe_table_count(conn, "equity_news")
        ipo_count = safe_table_count(conn, "upstox_ipo_list")
        ipo_gmp_scraper_count = safe_table_count(conn, "ipo_gmp_scraper")
        company_fundamentals_count = safe_table_count(conn, "upstox_company_fundamentals")
        legacy_fundamentals_count = safe_table_count(conn, "fundamentals")
        corporate_actions_count = safe_table_count(conn, "corporate_actions")
        fii_dii_count = safe_table_count(conn, "fii_dii_activity")

        total_runs_row = safe_fetchone(conn, """
            SELECT COUNT(*)
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
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
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
            )
            ORDER BY started_at DESC
            LIMIT 1;
        """)

        current_run = safe_last_success_run(conn, "upstox_current_instruments")
        expired_run = safe_last_success_run(conn, "upstox_expired_instruments")
        equity_run = safe_last_success_run(conn, "upstox_equity_instruments")
        ohlcv_run = safe_last_success_run(conn, "upstox_ohlcv_daily")
        market_holidays_run = safe_last_success_run(conn, UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE)
        equity_news_run = safe_last_success_run(conn, UPSTOX_EQUITY_NEWS_SYNC_TYPE)
        ipo_run = safe_last_success_run(conn, UPSTOX_IPO_SYNC_TYPE)
        ipo_gmp_scraper_run = safe_last_success_run(conn, IPO_GMP_SCRAPER_SYNC_TYPE)
        company_fundamentals_run = safe_last_success_run(conn, UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE)

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
            "total_market_holidays": market_holidays_count,
            "total_equity_news": equity_news_count,
            "total_ipo_calendar": ipo_count,
            "total_ipos": ipo_count,
            "total_ipo_gmp_scraper": ipo_gmp_scraper_count,
            "total_ipo_scraper": ipo_gmp_scraper_count,
            "total_company_fundamentals": company_fundamentals_count,
            "total_fundamentals": company_fundamentals_count,
            "total_legacy_fundamentals": legacy_fundamentals_count,
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
            "market_holidays_last_sync_at": str(market_holidays_run[0]) if market_holidays_run and market_holidays_run[0] else None,
            "market_holidays_duration_seconds": market_holidays_run[1] if market_holidays_run else None,
            "equity_news_last_sync_at": str(equity_news_run[0]) if equity_news_run and equity_news_run[0] else None,
            "equity_news_duration_seconds": equity_news_run[1] if equity_news_run else None,
            "ipo_calendar_last_sync_at": str(ipo_run[0]) if ipo_run and ipo_run[0] else None,
            "ipo_calendar_duration_seconds": ipo_run[1] if ipo_run else None,
            "ipo_gmp_scraper_last_sync_at": str(ipo_gmp_scraper_run[0]) if ipo_gmp_scraper_run and ipo_gmp_scraper_run[0] else None,
            "ipo_gmp_scraper_duration_seconds": ipo_gmp_scraper_run[1] if ipo_gmp_scraper_run else None,
            "ipo_scraper_last_sync_at": str(ipo_gmp_scraper_run[0]) if ipo_gmp_scraper_run and ipo_gmp_scraper_run[0] else None,
            "ipo_scraper_duration_seconds": ipo_gmp_scraper_run[1] if ipo_gmp_scraper_run else None,
            "company_fundamentals_last_sync_at": str(company_fundamentals_run[0]) if company_fundamentals_run and company_fundamentals_run[0] else None,
            "company_fundamentals_duration_seconds": company_fundamentals_run[1] if company_fundamentals_run else None,
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
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
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


def get_optional_upstox_access_token(conn) -> str:
    row = conn.execute("""
        SELECT access_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        return ""

    connection_status = row[1] or "saved"

    if connection_status == "disconnected":
        return ""

    return normalize_upstox_token(row[0])


def upstox_market_holidays_http_get_json(
    url: str,
    token: str = "",
    timeout: int = REQUEST_TIMEOUT_SECONDS
) -> dict:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "OpenAnalytics/1.0"
    }

    clean_token = normalize_upstox_token(token)

    if clean_token:
        headers["Authorization"] = f"Bearer {clean_token}"

    request = urllib.request.Request(url, headers=headers)

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
            detail=f"Unable to call Upstox Market Holidays API: {error}"
        )


def extract_market_holiday_rows(response: dict) -> List[dict]:
    if not isinstance(response, dict):
        return []

    data = response.get("data")

    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        return [data]

    return []


def normalize_market_holiday_record(record: dict) -> Optional[dict]:
    plain_record = model_to_dict(record)

    if not isinstance(plain_record, dict):
        return None

    holiday_date = normalize_expiry_value(plain_record.get("date"))

    if not holiday_date:
        return None

    closed_exchanges = plain_record.get("closed_exchanges")
    open_exchanges = plain_record.get("open_exchanges")

    if not isinstance(closed_exchanges, list):
        closed_exchanges = []

    if not isinstance(open_exchanges, list):
        open_exchanges = []

    return {
        "holiday_date": holiday_date,
        "description": plain_record.get("description"),
        "holiday_type": plain_record.get("holiday_type"),
        "closed_exchanges": json.dumps(closed_exchanges, ensure_ascii=False, default=str),
        "open_exchanges": json.dumps(open_exchanges, ensure_ascii=False, default=str),
        "is_trading_day": bool(open_exchanges),
        "raw_json": json.dumps(plain_record, ensure_ascii=False, default=str)
    }


def insert_market_holiday_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    unique_records = {}

    for record in records:
        normalized = normalize_market_holiday_record(record)

        if normalized and normalized.get("holiday_date"):
            unique_records[normalized["holiday_date"]] = normalized

    rows = list(unique_records.values())

    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_market_holidays (
            holiday_date,
            description,
            holiday_type,
            closed_exchanges,
            open_exchanges,
            is_trading_day,
            source_provider,
            raw_json,
            synced_at,
            updated_at
        )
        SELECT
            TRY_CAST(? AS DATE),
            ?,
            ?,
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            ?,
            'upstox',
            TRY_CAST(? AS JSON),
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            row.get("holiday_date"),
            row.get("description"),
            row.get("holiday_type"),
            row.get("closed_exchanges"),
            row.get("open_exchanges"),
            bool(row.get("is_trading_day")),
            row.get("raw_json")
        )
        for row in rows
    ])

    return len(rows)


def sync_upstox_market_holidays_service(
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

        access_token = get_optional_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE,
            "running",
            "Upstox market holidays sync started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        try:
            response = upstox_market_holidays_http_get_json(
                url=UPSTOX_MARKET_HOLIDAYS_URL,
                token=access_token
            )
        except HTTPException as error:
            if access_token and error.status_code in (400, 401, 403):
                response = upstox_market_holidays_http_get_json(
                    url=UPSTOX_MARKET_HOLIDAYS_URL,
                    token=""
                )
            else:
                raise

        check_sync_cancelled(conn, sync_id)

        records = extract_market_holiday_rows(response)

        conn.execute("BEGIN TRANSACTION")
        total_records = insert_market_holiday_records(conn, records)
        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Upstox market holidays synced successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Upstox market holidays synced successfully.",
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
                "Upstox market holidays sync cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Upstox market holidays sync cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Upstox market holidays sync failed: {error.detail}",
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
                f"Upstox market holidays sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Upstox market holidays: {error}"
        )

    finally:
        conn.close()



def json_dumps_for_db(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


def safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    try:
        clean_value = str(value).replace(",", "").replace("%", "").strip()
        if not clean_value:
            return None
        return float(clean_value)
    except Exception:
        return None


def ensure_upstox_company_fundamentals_tables(conn):
    global UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY

    if UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY:
        return

    def table_exists(table_name: str) -> bool:
        row = conn.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_name = ?;
        """, [table_name]).fetchone()

        return bool(row and row[0])

    def get_existing_columns(table_name: str) -> set:
        rows = conn.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = ?;
        """, [table_name]).fetchall()

        return {row[0] for row in rows}

    def add_column_if_missing(table_name: str, column_name: str, column_definition: str):
        existing_columns = get_existing_columns(table_name)

        if column_name in existing_columns:
            return

        conn.execute(f"""
            ALTER TABLE {table_name}
            ADD COLUMN {column_definition};
        """)

    def safe_create_index(index_sql: str):
        try:
            conn.execute(index_sql)
        except Exception as error:
            try:
                conn.rollback()
            except Exception:
                pass

            print(f"Skipped Company Fundamentals index: {error}")

    if not table_exists("upstox_company_fundamentals"):
        conn.execute("""
            CREATE TABLE upstox_company_fundamentals (
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
                units_in VARCHAR,
                latest_period VARCHAR,
                period_label VARCHAR,
                report_date DATE,
                sector VARCHAR,
                company_profile TEXT,
                sector_market_cap_inr_value DOUBLE,
                sector_market_cap_inr_unit VARCHAR,
                sector_market_cap_inr_formatted VARCHAR,
                sector_market_cap_usd_value DOUBLE,
                sector_market_cap_usd_unit VARCHAR,
                sector_market_cap_usd_formatted VARCHAR,
                market_cap_inr_value DOUBLE,
                market_cap_inr_unit VARCHAR,
                market_cap_inr_formatted VARCHAR,
                market_cap_usd_value DOUBLE,
                market_cap_usd_unit VARCHAR,
                market_cap_usd_formatted VARCHAR,
                period_count BIGINT DEFAULT 0,
                item_count BIGINT DEFAULT 0,
                latest_revenue DOUBLE,
                latest_operating_profit DOUBLE,
                latest_net_profit DOUBLE,
                latest_total_asset DOUBLE,
                latest_total_liability DOUBLE,
                latest_operating_cash_flow DOUBLE,
                latest_investing_cash_flow DOUBLE,
                latest_financing_cash_flow DOUBLE,
                latest_promoter_holding_pct DOUBLE,
                latest_fii_holding_pct DOUBLE,
                latest_dii_holding_pct DOUBLE,
                latest_public_holding_pct DOUBLE,
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
                corporate_action_count BIGINT DEFAULT 0,
                competitor_count BIGINT DEFAULT 0,
                summary_json JSON,
                history_json JSON,
                full_statement_json JSON,
                raw_data_json JSON,
                raw_json JSON,
                source_sync_id VARCHAR,
                source_provider_version VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    company_columns = [
        ("provider", "provider VARCHAR DEFAULT 'upstox'"),
        ("isin", "isin VARCHAR"),
        ("instrument_key", "instrument_key VARCHAR"),
        ("trading_symbol", "trading_symbol VARCHAR"),
        ("company_name", "company_name VARCHAR"),
        ("exchange", "exchange VARCHAR"),
        ("segment", "segment VARCHAR"),
        ("endpoint", "endpoint VARCHAR"),
        ("endpoint_label", "endpoint_label VARCHAR"),
        ("statement_type", "statement_type VARCHAR"),
        ("time_period", "time_period VARCHAR"),
        ("include_full_statement", "include_full_statement BOOLEAN DEFAULT FALSE"),
        ("api_status", "api_status VARCHAR"),
        ("data_status", "data_status VARCHAR DEFAULT 'success'"),
        ("units_in", "units_in VARCHAR"),
        ("latest_period", "latest_period VARCHAR"),
        ("period_label", "period_label VARCHAR"),
        ("report_date", "report_date DATE"),
        ("sector", "sector VARCHAR"),
        ("company_profile", "company_profile TEXT"),
        ("sector_market_cap_inr_value", "sector_market_cap_inr_value DOUBLE"),
        ("sector_market_cap_inr_unit", "sector_market_cap_inr_unit VARCHAR"),
        ("sector_market_cap_inr_formatted", "sector_market_cap_inr_formatted VARCHAR"),
        ("sector_market_cap_usd_value", "sector_market_cap_usd_value DOUBLE"),
        ("sector_market_cap_usd_unit", "sector_market_cap_usd_unit VARCHAR"),
        ("sector_market_cap_usd_formatted", "sector_market_cap_usd_formatted VARCHAR"),
        ("market_cap_inr_value", "market_cap_inr_value DOUBLE"),
        ("market_cap_inr_unit", "market_cap_inr_unit VARCHAR"),
        ("market_cap_inr_formatted", "market_cap_inr_formatted VARCHAR"),
        ("market_cap_usd_value", "market_cap_usd_value DOUBLE"),
        ("market_cap_usd_unit", "market_cap_usd_unit VARCHAR"),
        ("market_cap_usd_formatted", "market_cap_usd_formatted VARCHAR"),
        ("period_count", "period_count BIGINT DEFAULT 0"),
        ("item_count", "item_count BIGINT DEFAULT 0"),
        ("latest_revenue", "latest_revenue DOUBLE"),
        ("latest_operating_profit", "latest_operating_profit DOUBLE"),
        ("latest_net_profit", "latest_net_profit DOUBLE"),
        ("latest_total_asset", "latest_total_asset DOUBLE"),
        ("latest_total_liability", "latest_total_liability DOUBLE"),
        ("latest_operating_cash_flow", "latest_operating_cash_flow DOUBLE"),
        ("latest_investing_cash_flow", "latest_investing_cash_flow DOUBLE"),
        ("latest_financing_cash_flow", "latest_financing_cash_flow DOUBLE"),
        ("latest_promoter_holding_pct", "latest_promoter_holding_pct DOUBLE"),
        ("latest_fii_holding_pct", "latest_fii_holding_pct DOUBLE"),
        ("latest_dii_holding_pct", "latest_dii_holding_pct DOUBLE"),
        ("latest_public_holding_pct", "latest_public_holding_pct DOUBLE"),
        ("total_asset", "total_asset DOUBLE"),
        ("total_liability", "total_liability DOUBLE"),
        ("revenue", "revenue DOUBLE"),
        ("operating_profit", "operating_profit DOUBLE"),
        ("net_profit", "net_profit DOUBLE"),
        ("net_profit_growth", "net_profit_growth DOUBLE"),
        ("operating_cash_flow", "operating_cash_flow DOUBLE"),
        ("operating_cash_flow_pct_change", "operating_cash_flow_pct_change DOUBLE"),
        ("investing_cash_flow", "investing_cash_flow DOUBLE"),
        ("investing_cash_flow_pct_change", "investing_cash_flow_pct_change DOUBLE"),
        ("financing_cash_flow", "financing_cash_flow DOUBLE"),
        ("financing_cash_flow_pct_change", "financing_cash_flow_pct_change DOUBLE"),
        ("promoters_holding", "promoters_holding DOUBLE"),
        ("fii_holding", "fii_holding DOUBLE"),
        ("dii_holding", "dii_holding DOUBLE"),
        ("public_holding", "public_holding DOUBLE"),
        ("other_holding", "other_holding DOUBLE"),
        ("pe_ratio_company", "pe_ratio_company DOUBLE"),
        ("pe_ratio_sector", "pe_ratio_sector DOUBLE"),
        ("pb_ratio_company", "pb_ratio_company DOUBLE"),
        ("pb_ratio_sector", "pb_ratio_sector DOUBLE"),
        ("roa_company", "roa_company DOUBLE"),
        ("roa_sector", "roa_sector DOUBLE"),
        ("roe_company", "roe_company DOUBLE"),
        ("roe_sector", "roe_sector DOUBLE"),
        ("roce_company", "roce_company DOUBLE"),
        ("roce_sector", "roce_sector DOUBLE"),
        ("ev_ebitda_company", "ev_ebitda_company DOUBLE"),
        ("ev_ebitda_sector", "ev_ebitda_sector DOUBLE"),
        ("action_type", "action_type VARCHAR"),
        ("announcement_date", "announcement_date DATE"),
        ("ex_date", "ex_date DATE"),
        ("record_date", "record_date DATE"),
        ("action_amount", "action_amount DOUBLE"),
        ("action_ratio", "action_ratio VARCHAR"),
        ("additional_info", "additional_info TEXT"),
        ("competitor_instrument_key", "competitor_instrument_key VARCHAR"),
        ("competitor_isin", "competitor_isin VARCHAR"),
        ("competitor_company_profile", "competitor_company_profile TEXT"),
        ("competitor_sector", "competitor_sector VARCHAR"),
        ("competitor_market_cap_inr_value", "competitor_market_cap_inr_value DOUBLE"),
        ("competitor_market_cap_inr_unit", "competitor_market_cap_inr_unit VARCHAR"),
        ("competitor_market_cap_inr_formatted", "competitor_market_cap_inr_formatted VARCHAR"),
        ("competitor_market_cap_usd_value", "competitor_market_cap_usd_value DOUBLE"),
        ("competitor_market_cap_usd_unit", "competitor_market_cap_usd_unit VARCHAR"),
        ("competitor_market_cap_usd_formatted", "competitor_market_cap_usd_formatted VARCHAR"),
        ("corporate_action_count", "corporate_action_count BIGINT DEFAULT 0"),
        ("competitor_count", "competitor_count BIGINT DEFAULT 0"),
        ("summary_json", "summary_json JSON"),
        ("history_json", "history_json JSON"),
        ("full_statement_json", "full_statement_json JSON"),
        ("raw_data_json", "raw_data_json JSON"),
        ("raw_json", "raw_json JSON"),
        ("source_sync_id", "source_sync_id VARCHAR"),
        ("source_provider_version", "source_provider_version VARCHAR"),
        ("synced_at", "synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]

    for column_name, column_definition in company_columns:
        add_column_if_missing(
            "upstox_company_fundamentals",
            column_name,
            column_definition
        )

    conn.execute("""
        UPDATE upstox_company_fundamentals
        SET
            provider = COALESCE(NULLIF(TRIM(provider), ''), 'upstox'),
            include_full_statement = COALESCE(include_full_statement, FALSE),
            data_status = COALESCE(NULLIF(TRIM(data_status), ''), 'success'),
            sector_market_cap_inr_value = COALESCE(sector_market_cap_inr_value, market_cap_inr_value),
            sector_market_cap_inr_unit = COALESCE(sector_market_cap_inr_unit, market_cap_inr_unit),
            sector_market_cap_inr_formatted = COALESCE(sector_market_cap_inr_formatted, market_cap_inr_formatted),
            sector_market_cap_usd_value = COALESCE(sector_market_cap_usd_value, market_cap_usd_value),
            sector_market_cap_usd_unit = COALESCE(sector_market_cap_usd_unit, market_cap_usd_unit),
            sector_market_cap_usd_formatted = COALESCE(sector_market_cap_usd_formatted, market_cap_usd_formatted),
            latest_revenue = COALESCE(latest_revenue, revenue),
            latest_operating_profit = COALESCE(latest_operating_profit, operating_profit),
            latest_net_profit = COALESCE(latest_net_profit, net_profit),
            latest_total_asset = COALESCE(latest_total_asset, total_asset),
            latest_total_liability = COALESCE(latest_total_liability, total_liability),
            latest_operating_cash_flow = COALESCE(latest_operating_cash_flow, operating_cash_flow),
            latest_investing_cash_flow = COALESCE(latest_investing_cash_flow, investing_cash_flow),
            latest_financing_cash_flow = COALESCE(latest_financing_cash_flow, financing_cash_flow),
            latest_promoter_holding_pct = COALESCE(latest_promoter_holding_pct, promoters_holding),
            latest_fii_holding_pct = COALESCE(latest_fii_holding_pct, fii_holding),
            latest_dii_holding_pct = COALESCE(latest_dii_holding_pct, dii_holding),
            latest_public_holding_pct = COALESCE(latest_public_holding_pct, public_holding)
        WHERE provider IS NULL
           OR TRIM(provider) = ''
           OR include_full_statement IS NULL
           OR data_status IS NULL
           OR TRIM(data_status) = ''
           OR sector_market_cap_inr_value IS NULL
           OR sector_market_cap_inr_unit IS NULL
           OR sector_market_cap_inr_formatted IS NULL
           OR sector_market_cap_usd_value IS NULL
           OR sector_market_cap_usd_unit IS NULL
           OR sector_market_cap_usd_formatted IS NULL
           OR latest_revenue IS NULL
           OR latest_operating_profit IS NULL
           OR latest_net_profit IS NULL
           OR latest_total_asset IS NULL
           OR latest_total_liability IS NULL
           OR latest_operating_cash_flow IS NULL
           OR latest_investing_cash_flow IS NULL
           OR latest_financing_cash_flow IS NULL
           OR latest_promoter_holding_pct IS NULL
           OR latest_fii_holding_pct IS NULL
           OR latest_dii_holding_pct IS NULL
           OR latest_public_holding_pct IS NULL;
    """)

    if not table_exists("upstox_company_fundamentals_sync_status"):
        conn.execute("""
            CREATE TABLE upstox_company_fundamentals_sync_status (
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
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    status_columns = [
        ("provider", "provider VARCHAR DEFAULT 'upstox'"),
        ("isin", "isin VARCHAR"),
        ("instrument_key", "instrument_key VARCHAR"),
        ("trading_symbol", "trading_symbol VARCHAR"),
        ("endpoint", "endpoint VARCHAR"),
        ("statement_type", "statement_type VARCHAR"),
        ("time_period", "time_period VARCHAR"),
        ("include_full_statement", "include_full_statement BOOLEAN DEFAULT FALSE"),
        ("status", "status VARCHAR DEFAULT 'success'"),
        ("record_count", "record_count BIGINT DEFAULT 0"),
        ("last_error", "last_error VARCHAR"),
        ("source_sync_id", "source_sync_id VARCHAR"),
        ("checked_at", "checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("synced_at", "synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP"),
        ("updated_at", "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    ]

    for column_name, column_definition in status_columns:
        add_column_if_missing(
            "upstox_company_fundamentals_sync_status",
            column_name,
            column_definition
        )

    conn.execute("""
        UPDATE upstox_company_fundamentals_sync_status
        SET
            provider = COALESCE(NULLIF(TRIM(provider), ''), 'upstox'),
            include_full_statement = COALESCE(include_full_statement, FALSE),
            status = COALESCE(NULLIF(TRIM(status), ''), 'success'),
            checked_at = COALESCE(checked_at, synced_at, updated_at, CURRENT_TIMESTAMP),
            synced_at = COALESCE(synced_at, checked_at, updated_at, CURRENT_TIMESTAMP),
            updated_at = COALESCE(updated_at, checked_at, synced_at, CURRENT_TIMESTAMP)
        WHERE provider IS NULL
           OR TRIM(provider) = ''
           OR include_full_statement IS NULL
           OR status IS NULL
           OR TRIM(status) = ''
           OR checked_at IS NULL
           OR synced_at IS NULL
           OR updated_at IS NULL;
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_lookup
        ON upstox_company_fundamentals (
            provider,
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_preview
        ON upstox_company_fundamentals (
            endpoint,
            trading_symbol,
            isin,
            synced_at
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_lookup
        ON upstox_company_fundamentals_sync_status (
            provider,
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement,
            status
        );
    """)

    safe_create_index("""
        CREATE INDEX IF NOT EXISTS idx_upstox_company_fundamentals_status_sync
        ON upstox_company_fundamentals_sync_status (
            source_sync_id
        );
    """)

    UPSTOX_COMPANY_FUNDAMENTALS_SCHEMA_READY = True

def normalize_company_fundamentals_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    endpoints = normalize_string_list(
        payload.get("endpoints") or payload.get("selected_endpoints"),
        UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_ENDPOINTS
    )
    endpoints = [
        endpoint
        for endpoint in endpoints
        if endpoint in UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS
    ]

    statement_types = normalize_string_list(
        payload.get("statement_types") or payload.get("selected_statement_types"),
        UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES
    )
    statement_types = [
        item.lower()
        for item in statement_types
        if item.lower() in UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES
    ]

    time_periods = normalize_string_list(
        payload.get("time_periods") or payload.get("selected_time_periods"),
        UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS
    )
    time_periods = [
        item.lower()
        for item in time_periods
        if item.lower() in UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS
    ]

    if not endpoints:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Select at least one Company Fundamentals endpoint."
        )

    if not statement_types:
        statement_types = UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy()

    if not time_periods:
        time_periods = UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy()

    return {
        "endpoints": unique_preserve_order(endpoints),
        "statement_types": unique_preserve_order(statement_types),
        "time_periods": unique_preserve_order(time_periods),
        "include_full_statement": normalize_bool(payload.get("include_full_statement"), True),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "instrument_limit": normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000),
        "single_isin": safe_strip(payload.get("single_isin")).upper(),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key")),
        "batch_size": normalize_positive_int(
            payload.get("batch_size"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_BATCH_SIZE,
            1,
            500
        ),
        "request_delay_ms": normalize_positive_int(
            payload.get("request_delay_ms"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_REQUEST_DELAY_MS,
            0,
            60000
        ),
        "retry_count": normalize_positive_int(
            payload.get("retry_count"),
            UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_RETRY_COUNT,
            1,
            10
        )
    }


def get_default_company_fundamentals_options_payload() -> dict:
    return {
        "endpoints": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_ENDPOINTS.copy(),
        "statement_types": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy(),
        "time_periods": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy(),
        "include_full_statement": True,
        "skip_existing": True,
        "force_refresh": False,
        "instrument_limit": None,
        "single_isin": "",
        "single_instrument_key": "",
        "batch_size": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_BATCH_SIZE,
        "request_delay_ms": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_REQUEST_DELAY_MS,
        "retry_count": UPSTOX_COMPANY_FUNDAMENTAL_DEFAULT_RETRY_COUNT
    }


def get_upstox_company_fundamentals_options_service():
    return {
        "options": get_default_company_fundamentals_options_payload(),
        "endpoints": [
            {
                "value": endpoint,
                "label": definition["label"],
                "supports_statement_type": definition["supports_statement_type"],
                "supports_time_period": definition["supports_time_period"],
                "supports_full_statement": definition["supports_full_statement"]
            }
            for endpoint, definition in UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS.items()
        ],
        "statement_types": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_STATEMENT_TYPES.copy(),
        "time_periods": UPSTOX_COMPANY_FUNDAMENTAL_ALLOWED_TIME_PERIODS.copy()
    }


def fetch_company_fundamental_instruments(conn, config: dict) -> List[dict]:
    params = []

    where_sql = """
    WHERE isin IS NOT NULL
      AND TRIM(isin) <> ''
    """

    if config.get("single_isin"):
        where_sql += " AND UPPER(isin) = ?"
        params.append(config["single_isin"])

    if config.get("single_instrument_key"):
        where_sql += " AND instrument_key = ?"
        params.append(config["single_instrument_key"])

    limit_sql = ""

    if config.get("instrument_limit"):
        limit_sql = "LIMIT ?"
        params.append(config["instrument_limit"])

    rows = conn.execute(f"""
        SELECT *
        FROM (
            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                0 AS source_rank
            FROM upstox_equity_instruments
            {where_sql}

            UNION ALL

            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                1 AS source_rank
            FROM upstox_instruments
            {where_sql}
              AND source_type = 'bod_complete'
              AND (
                  UPPER(COALESCE(segment, '')) IN ('NSE_EQ', 'BSE_EQ')
                  OR UPPER(COALESCE(instrument_type, '')) IN ('EQ', 'EQUITY')
              )
        )
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY UPPER(isin)
            ORDER BY source_rank, trading_symbol, instrument_key
        ) = 1
        ORDER BY trading_symbol, isin
        {limit_sql};
    """, params + params + ([] if not config.get("instrument_limit") else [config["instrument_limit"]])).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": str(row[3] or "").upper(),
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[3])
    ]


def company_fundamentals_status_exists(
    conn,
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> bool:
    row = conn.execute("""
        SELECT 1
        FROM upstox_company_fundamentals
        WHERE provider = ?
          AND isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?
        LIMIT 1;
    """, [
        UPSTOX_PROVIDER,
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ]).fetchone()

    if row:
        return True

    status_row = conn.execute("""
        SELECT 1
        FROM upstox_company_fundamentals_sync_status
        WHERE isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?
          AND status = 'success'
        LIMIT 1;
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ]).fetchone()

    return bool(status_row)


def get_company_fundamentals_task_key(
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> tuple:
    return (
        safe_strip(isin).upper(),
        safe_strip(endpoint),
        safe_strip(statement_type),
        safe_strip(time_period),
        bool(include_full_statement)
    )


def build_company_fundamentals_existing_status_cache(
    conn,
    instruments: List[dict],
    tasks: List[dict]
) -> set:
    isins = unique_preserve_order([
        safe_strip(instrument.get("isin")).upper()
        for instrument in instruments
        if safe_strip(instrument.get("isin"))
    ])

    if not isins or not tasks:
        return set()

    seen_task_keys = set()
    task_keys = []

    for task in tasks:
        task_key = (
            safe_strip(task.get("endpoint")),
            safe_strip(task.get("statement_type")),
            safe_strip(task.get("time_period")),
            bool(task.get("include_full_statement"))
        )

        if task_key[0] and task_key not in seen_task_keys:
            seen_task_keys.add(task_key)
            task_keys.append(task_key)

    if not task_keys:
        return set()

    task_clauses = []
    params = [UPSTOX_PROVIDER]

    for endpoint, statement_type, time_period, include_full_statement in task_keys:
        task_clauses.append("""
            (
                endpoint = ?
                AND COALESCE(statement_type, '') = ?
                AND COALESCE(time_period, '') = ?
                AND include_full_statement = ?
            )
        """)
        params.extend([
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        ])

    isin_placeholders = ", ".join(["?"] * len(isins))
    params.extend(isins)

    existing_keys = set()

    rows = conn.execute(f"""
        SELECT isin, endpoint, statement_type, time_period, include_full_statement
        FROM upstox_company_fundamentals
        WHERE provider = ?
          AND ({" OR ".join(task_clauses)})
          AND UPPER(isin) IN ({isin_placeholders});
    """, params).fetchall()

    for row in rows:
        existing_keys.add(get_company_fundamentals_task_key(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4]
        ))

    status_params = []

    for endpoint, statement_type, time_period, include_full_statement in task_keys:
        status_params.extend([
            endpoint,
            statement_type,
            time_period,
            include_full_statement
        ])

    status_params.extend(isins)

    status_rows = conn.execute(f"""
        SELECT isin, endpoint, statement_type, time_period, include_full_statement
        FROM upstox_company_fundamentals_sync_status
        WHERE status = 'success'
          AND ({" OR ".join(task_clauses)})
          AND UPPER(isin) IN ({isin_placeholders});
    """, status_params).fetchall()

    for row in status_rows:
        existing_keys.add(get_company_fundamentals_task_key(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4]
        ))

    print(
        "[Company Fundamentals] Loaded saved status cache "
        f"for {len(existing_keys)} instrument/task combinations."
    )

    return existing_keys


def record_company_fundamentals_status(
    conn,
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool,
    status_value: str,
    record_count: int,
    sync_id: str,
    error_message: Optional[str] = None
):
    conn.execute("""
        DELETE FROM upstox_company_fundamentals_sync_status
        WHERE isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?;
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement)
    ])

    conn.execute("""
        INSERT INTO upstox_company_fundamentals_sync_status (
            isin,
            endpoint,
            statement_type,
            time_period,
            include_full_statement,
            status,
            record_count,
            last_error,
            source_sync_id,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
    """, [
        isin,
        endpoint,
        statement_type,
        time_period,
        bool(include_full_statement),
        status_value,
        int(record_count or 0),
        error_message,
        sync_id
    ])


def build_company_fundamentals_tasks(config: dict) -> List[dict]:
    tasks = []

    for endpoint in config["endpoints"]:
        definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]

        if definition["supports_statement_type"]:
            for statement_type in config["statement_types"]:
                if definition["supports_time_period"]:
                    for time_period in config["time_periods"]:
                        tasks.append({
                            "endpoint": endpoint,
                            "statement_type": statement_type,
                            "time_period": time_period,
                            "include_full_statement": bool(config["include_full_statement"])
                        })
                else:
                    tasks.append({
                        "endpoint": endpoint,
                        "statement_type": statement_type,
                        "time_period": None,
                        "include_full_statement": bool(config["include_full_statement"])
                    })
        else:
            tasks.append({
                "endpoint": endpoint,
                "statement_type": None,
                "time_period": None,
                "include_full_statement": False
            })

    return tasks


def build_company_fundamentals_url(
    isin: str,
    endpoint: str,
    statement_type: Optional[str],
    time_period: Optional[str],
    include_full_statement: bool
) -> str:
    definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]
    encoded_isin = urllib.parse.quote(isin, safe="")
    url = f"{UPSTOX_FUNDAMENTALS_BASE_URL}/{encoded_isin}/{definition['path']}"
    params = {}

    if definition["supports_statement_type"] and statement_type:
        params["type"] = statement_type

    if definition["supports_time_period"] and time_period:
        params["time_period"] = time_period

    if definition["supports_full_statement"]:
        params["fs"] = "true" if include_full_statement else "false"

    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    return url


def upstox_company_fundamentals_http_get_json(
    url: str,
    token: str,
    timeout: int = REQUEST_TIMEOUT_SECONDS
) -> dict:
    request = urllib.request.Request(
        url,
        headers={
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
            detail=f"Unable to call Upstox Company Fundamentals API: {error}"
        )


def fetch_company_fundamentals_with_retry(
    url: str,
    token: str,
    retry_count: int,
    rate_limiter: UpstoxRollingRateLimiter
) -> dict:
    attempts = max(1, int(retry_count or 1))
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot()
            return upstox_company_fundamentals_http_get_json(url=url, token=token)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = (
                error.status_code in (408, 429, 500, 502, 503, 504)
                or "timeout" in error_text
                or "rate" in error_text
            )

            if not should_retry or attempt >= attempts:
                raise

            sleep_seconds = min(30, 2 * attempt)
            print(
                "Upstox Company Fundamentals retry "
                f"{attempt}/{attempts} after {sleep_seconds}s: {error.detail}"
            )
            time.sleep(sleep_seconds)

    if last_error:
        raise last_error

    raise HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail="Unable to call Upstox Company Fundamentals API."
    )


def get_history_entries_from_category_rows(rows: Any, category_name: str) -> List[dict]:
    if not isinstance(rows, list):
        return []

    for row in rows:
        if not isinstance(row, dict):
            continue

        if safe_strip(row.get("category")).lower() == category_name:
            history = row.get("history")
            return history if isinstance(history, list) else []

    return []


def first_history_value(history: Any, value_key: str = "value"):
    if isinstance(history, list) and history:
        first_row = history[0]
        if isinstance(first_row, dict):
            return first_row.get(value_key)

    return None


def first_history_period(history: Any) -> Optional[str]:
    if isinstance(history, list) and history:
        first_row = history[0]
        if isinstance(first_row, dict):
            return first_row.get("period")

    return None


def get_ratio_pair(rows: Any, ratio_name: str) -> dict:
    if not isinstance(rows, list):
        return {"company": None, "sector": None}

    normalized_ratio_name = safe_strip(ratio_name).lower().replace(" ", "").replace("/", "")

    for row in rows:
        if not isinstance(row, dict):
            continue

        normalized_name = safe_strip(row.get("name")).lower().replace(" ", "").replace("/", "")

        if normalized_name == normalized_ratio_name:
            return {
                "company": safe_float(row.get("company_value")),
                "sector": safe_float(row.get("sector_value") or row.get("sector_benchmark"))
            }

    return {"company": None, "sector": None}


def normalize_company_fundamentals_record(
    response: dict,
    instrument: dict,
    task: dict,
    sync_id: str
) -> dict:
    endpoint = task["endpoint"]
    definition = UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINTS[endpoint]
    data = response.get("data") if isinstance(response, dict) else None
    data_dict = data if isinstance(data, dict) else {}
    data_list = data if isinstance(data, list) else []

    history_json = None
    summary_json = data
    full_statement_json = None
    latest_period = None
    period_count = 0
    item_count = len(data_list) if isinstance(data_list, list) else 0

    if isinstance(data, dict):
        full_statement_json = data.get("full_statement")

        for key in ("history", "income_statement", "cash_flow"):
            if isinstance(data.get(key), list):
                history_json = data.get(key)
                item_count = len(data.get(key))
                break

        if isinstance(history_json, list):
            if history_json and isinstance(history_json[0], dict):
                if isinstance(history_json[0].get("history"), list):
                    latest_period = first_history_period(history_json[0].get("history"))
                    period_count = len(history_json[0].get("history"))
                else:
                    latest_period = history_json[0].get("period")
                    period_count = len(history_json)

    elif isinstance(data, list):
        history_json = data
        item_count = len(data)

        if data and isinstance(data[0], dict):
            if isinstance(data[0].get("history"), list):
                latest_period = first_history_period(data[0].get("history"))
                period_count = len(data[0].get("history"))
            else:
                latest_period = data[0].get("period")
                period_count = len(data)

    sector_market_cap_inr = data_dict.get("sector_market_cap_inr") if isinstance(data_dict, dict) else {}
    sector_market_cap_usd = data_dict.get("sector_market_cap_usd") if isinstance(data_dict, dict) else {}

    income_rows = data_dict.get("income_statement") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_INCOME_STATEMENT else []
    cash_flow_rows = data_dict.get("cash_flow") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CASH_FLOW else []
    balance_history = data_dict.get("history") if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_BALANCE_SHEET else []

    revenue_history = get_history_entries_from_category_rows(income_rows, "revenue")
    operating_profit_history = get_history_entries_from_category_rows(income_rows, "operating_profit")
    net_profit_history = get_history_entries_from_category_rows(income_rows, "net_profit")

    operating_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "operating")
    investing_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "investing")
    financing_cash_flow_history = get_history_entries_from_category_rows(cash_flow_rows, "financing")

    latest_balance = balance_history[0] if isinstance(balance_history, list) and balance_history and isinstance(balance_history[0], dict) else {}

    shareholding_rows = data_list if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_SHARE_HOLDINGS else []
    promoter_history = get_history_entries_from_category_rows(shareholding_rows, "promoters")
    fii_history = get_history_entries_from_category_rows(shareholding_rows, "fii")
    dii_history = get_history_entries_from_category_rows(shareholding_rows, "dii") or get_history_entries_from_category_rows(shareholding_rows, "other_dii")
    public_history = get_history_entries_from_category_rows(shareholding_rows, "public")

    ratios_rows = data_list if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_KEY_RATIOS else []
    pe_ratio = get_ratio_pair(ratios_rows, "P/E")
    pb_ratio = get_ratio_pair(ratios_rows, "P/B")
    roa_ratio = get_ratio_pair(ratios_rows, "ROA")
    roe_ratio = get_ratio_pair(ratios_rows, "ROE")
    roce_ratio = get_ratio_pair(ratios_rows, "ROCE")
    ev_ebitda_ratio = get_ratio_pair(ratios_rows, "EV/EBITDA")

    return {
        "fundamental_id": str(uuid.uuid4()),
        "provider": UPSTOX_PROVIDER,
        "isin": instrument.get("isin"),
        "instrument_key": instrument.get("instrument_key"),
        "trading_symbol": instrument.get("trading_symbol"),
        "company_name": instrument.get("name"),
        "exchange": instrument.get("exchange"),
        "segment": instrument.get("segment"),
        "endpoint": endpoint,
        "endpoint_label": definition["label"],
        "statement_type": data_dict.get("type") or task.get("statement_type"),
        "time_period": data_dict.get("time_period") or task.get("time_period"),
        "include_full_statement": bool(task.get("include_full_statement")),
        "api_status": response.get("status") if isinstance(response, dict) else None,
        "units_in": data_dict.get("units_in"),
        "latest_period": latest_period,
        "sector": data_dict.get("sector"),
        "company_profile": data_dict.get("company_profile"),
        "sector_market_cap_inr_value": safe_float(sector_market_cap_inr.get("value") if isinstance(sector_market_cap_inr, dict) else None),
        "sector_market_cap_inr_unit": sector_market_cap_inr.get("unit") if isinstance(sector_market_cap_inr, dict) else None,
        "sector_market_cap_inr_formatted": sector_market_cap_inr.get("formatted") if isinstance(sector_market_cap_inr, dict) else None,
        "sector_market_cap_usd_value": safe_float(sector_market_cap_usd.get("value") if isinstance(sector_market_cap_usd, dict) else None),
        "sector_market_cap_usd_unit": sector_market_cap_usd.get("unit") if isinstance(sector_market_cap_usd, dict) else None,
        "sector_market_cap_usd_formatted": sector_market_cap_usd.get("formatted") if isinstance(sector_market_cap_usd, dict) else None,
        "period_count": int(period_count or 0),
        "item_count": int(item_count or 0),
        "latest_revenue": safe_float(first_history_value(revenue_history)),
        "latest_operating_profit": safe_float(first_history_value(operating_profit_history)),
        "latest_net_profit": safe_float(first_history_value(net_profit_history)),
        "latest_total_asset": safe_float(latest_balance.get("total_asset")),
        "latest_total_liability": safe_float(latest_balance.get("total_liability")),
        "latest_operating_cash_flow": safe_float(first_history_value(operating_cash_flow_history)),
        "latest_investing_cash_flow": safe_float(first_history_value(investing_cash_flow_history)),
        "latest_financing_cash_flow": safe_float(first_history_value(financing_cash_flow_history)),
        "latest_promoter_holding_pct": safe_float(first_history_value(promoter_history)),
        "latest_fii_holding_pct": safe_float(first_history_value(fii_history)),
        "latest_dii_holding_pct": safe_float(first_history_value(dii_history)),
        "latest_public_holding_pct": safe_float(first_history_value(public_history)),
        "pe_ratio_company": pe_ratio["company"],
        "pe_ratio_sector": pe_ratio["sector"],
        "pb_ratio_company": pb_ratio["company"],
        "pb_ratio_sector": pb_ratio["sector"],
        "roa_company": roa_ratio["company"],
        "roa_sector": roa_ratio["sector"],
        "roe_company": roe_ratio["company"],
        "roe_sector": roe_ratio["sector"],
        "roce_company": roce_ratio["company"],
        "roce_sector": roce_ratio["sector"],
        "ev_ebitda_company": ev_ebitda_ratio["company"],
        "ev_ebitda_sector": ev_ebitda_ratio["sector"],
        "corporate_action_count": len(data_list) if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_CORPORATE_ACTIONS else 0,
        "competitor_count": len(data_list) if endpoint == UPSTOX_COMPANY_FUNDAMENTAL_ENDPOINT_COMPETITORS else 0,
        "summary_json": json_dumps_for_db(summary_json),
        "history_json": json_dumps_for_db(history_json),
        "full_statement_json": json_dumps_for_db(full_statement_json),
        "raw_data_json": json_dumps_for_db(data),
        "raw_json": json_dumps_for_db(response),
        "source_sync_id": sync_id
    }


def insert_company_fundamentals_records(conn, records: List[dict]) -> int:
    if not records:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_company_fundamentals (
            fundamental_id,
            provider,
            isin,
            instrument_key,
            trading_symbol,
            company_name,
            exchange,
            segment,
            endpoint,
            endpoint_label,
            statement_type,
            time_period,
            include_full_statement,
            api_status,
            units_in,
            latest_period,
            sector,
            company_profile,
            sector_market_cap_inr_value,
            sector_market_cap_inr_unit,
            sector_market_cap_inr_formatted,
            sector_market_cap_usd_value,
            sector_market_cap_usd_unit,
            sector_market_cap_usd_formatted,
            period_count,
            item_count,
            latest_revenue,
            latest_operating_profit,
            latest_net_profit,
            latest_total_asset,
            latest_total_liability,
            latest_operating_cash_flow,
            latest_investing_cash_flow,
            latest_financing_cash_flow,
            latest_promoter_holding_pct,
            latest_fii_holding_pct,
            latest_dii_holding_pct,
            latest_public_holding_pct,
            pe_ratio_company,
            pe_ratio_sector,
            pb_ratio_company,
            pb_ratio_sector,
            roa_company,
            roa_sector,
            roe_company,
            roe_sector,
            roce_company,
            roce_sector,
            ev_ebitda_company,
            ev_ebitda_sector,
            corporate_action_count,
            competitor_count,
            summary_json,
            history_json,
            full_statement_json,
            raw_data_json,
            raw_json,
            source_sync_id,
            synced_at,
            updated_at
        )
        SELECT
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            TRY_CAST(? AS JSON),
            ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            record.get("fundamental_id"),
            record.get("provider"),
            record.get("isin"),
            record.get("instrument_key"),
            record.get("trading_symbol"),
            record.get("company_name"),
            record.get("exchange"),
            record.get("segment"),
            record.get("endpoint"),
            record.get("endpoint_label"),
            record.get("statement_type"),
            record.get("time_period"),
            bool(record.get("include_full_statement")),
            record.get("api_status"),
            record.get("units_in"),
            record.get("latest_period"),
            record.get("sector"),
            record.get("company_profile"),
            record.get("sector_market_cap_inr_value"),
            record.get("sector_market_cap_inr_unit"),
            record.get("sector_market_cap_inr_formatted"),
            record.get("sector_market_cap_usd_value"),
            record.get("sector_market_cap_usd_unit"),
            record.get("sector_market_cap_usd_formatted"),
            record.get("period_count"),
            record.get("item_count"),
            record.get("latest_revenue"),
            record.get("latest_operating_profit"),
            record.get("latest_net_profit"),
            record.get("latest_total_asset"),
            record.get("latest_total_liability"),
            record.get("latest_operating_cash_flow"),
            record.get("latest_investing_cash_flow"),
            record.get("latest_financing_cash_flow"),
            record.get("latest_promoter_holding_pct"),
            record.get("latest_fii_holding_pct"),
            record.get("latest_dii_holding_pct"),
            record.get("latest_public_holding_pct"),
            record.get("pe_ratio_company"),
            record.get("pe_ratio_sector"),
            record.get("pb_ratio_company"),
            record.get("pb_ratio_sector"),
            record.get("roa_company"),
            record.get("roa_sector"),
            record.get("roe_company"),
            record.get("roe_sector"),
            record.get("roce_company"),
            record.get("roce_sector"),
            record.get("ev_ebitda_company"),
            record.get("ev_ebitda_sector"),
            record.get("corporate_action_count"),
            record.get("competitor_count"),
            record.get("summary_json"),
            record.get("history_json"),
            record.get("full_statement_json"),
            record.get("raw_data_json"),
            record.get("raw_json"),
            record.get("source_sync_id")
        )
        for record in records
    ])

    return len(records)


def delete_existing_company_fundamentals_record(conn, record: dict):
    conn.execute("""
        DELETE FROM upstox_company_fundamentals
        WHERE provider = ?
          AND isin = ?
          AND endpoint = ?
          AND COALESCE(statement_type, '') = COALESCE(?, '')
          AND COALESCE(time_period, '') = COALESCE(?, '')
          AND include_full_statement = ?;
    """, [
        record.get("provider") or UPSTOX_PROVIDER,
        record.get("isin"),
        record.get("endpoint"),
        record.get("statement_type"),
        record.get("time_period"),
        bool(record.get("include_full_statement"))
    ])


def sync_upstox_company_fundamentals_service(
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
        "records_inserted": 0,
        "failed_items": 0
    }
    failed_items = []

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_company_fundamentals_tables(conn)
        normalized_config = normalize_company_fundamentals_config(
            config or get_default_company_fundamentals_options_payload()
        )
        analytical_token = get_saved_upstox_analytical_token(conn)

        instruments = fetch_company_fundamental_instruments(conn, normalized_config)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No equity instruments with ISIN were found. "
                    "Run Current Instruments or Equity Instruments first."
                )
            )

        tasks = build_company_fundamentals_tasks(normalized_config)

        sync_id = create_sync_run(
            conn,
            UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE,
            "running",
            "Company Fundamentals sync started.",
            current_user=current_user
        )

        rate_limiter = UpstoxRollingRateLimiter()
        existing_status_cache = (
            build_company_fundamentals_existing_status_cache(conn, instruments, tasks)
            if normalized_config["skip_existing"]
            and not normalized_config["force_refresh"]
            else set()
        )

        print(
            "[Company Fundamentals] Starting sync "
            f"instruments={len(instruments)} tasks_per_instrument={len(tasks)} "
            f"endpoints={normalized_config['endpoints']}"
        )

        for instrument_index, instrument in enumerate(instruments, start=1):
            check_sync_cancelled(conn, sync_id)

            if instrument_index > 1 and normalized_config["batch_size"]:
                if (instrument_index - 1) % normalized_config["batch_size"] == 0:
                    print(
                        "[Company Fundamentals] Batch checkpoint "
                        f"after {instrument_index - 1} instruments."
                    )
                    check_sync_cancelled(conn, sync_id)

            isin = safe_strip(instrument.get("isin")).upper()
            trading_symbol = safe_strip(instrument.get("trading_symbol")) or "--"

            if not isin:
                continue

            for task in tasks:
                check_sync_cancelled(conn, sync_id)

                endpoint = task["endpoint"]
                statement_type = task.get("statement_type")
                time_period = task.get("time_period")
                include_full_statement = bool(task.get("include_full_statement"))

                if (
                    normalized_config["skip_existing"]
                    and not normalized_config["force_refresh"]
                    and get_company_fundamentals_task_key(
                        isin=isin,
                        endpoint=endpoint,
                        statement_type=statement_type,
                        time_period=time_period,
                        include_full_statement=include_full_statement
                    ) in existing_status_cache
                ):
                    metrics["api_calls_skipped"] += 1
                    print(
                        "[Company Fundamentals] Skipped existing "
                        f"{trading_symbol} {isin} {endpoint} "
                        f"{statement_type or ''} {time_period or ''}."
                    )
                    continue

                url = build_company_fundamentals_url(
                    isin=isin,
                    endpoint=endpoint,
                    statement_type=statement_type,
                    time_period=time_period,
                    include_full_statement=include_full_statement
                )

                try:
                    print(
                        "[Company Fundamentals] API "
                        f"{instrument_index}/{len(instruments)} {trading_symbol} {isin} "
                        f"{endpoint} {statement_type or ''} {time_period or ''}"
                    )

                    response = fetch_company_fundamentals_with_retry(
                        url=url,
                        token=analytical_token,
                        retry_count=normalized_config["retry_count"],
                        rate_limiter=rate_limiter
                    )
                    metrics["api_calls_attempted"] += 1

                    record = normalize_company_fundamentals_record(
                        response=response,
                        instrument=instrument,
                        task=task,
                        sync_id=sync_id
                    )

                    conn.execute("BEGIN TRANSACTION")
                    delete_existing_company_fundamentals_record(conn, record)
                    inserted_count = insert_company_fundamentals_records(conn, [record])
                    record_company_fundamentals_status(
                        conn=conn,
                        isin=isin,
                        endpoint=endpoint,
                        statement_type=record.get("statement_type") or statement_type,
                        time_period=record.get("time_period") or time_period,
                        include_full_statement=include_full_statement,
                        status_value="success",
                        record_count=inserted_count,
                        sync_id=sync_id,
                        error_message=None
                    )
                    conn.execute("COMMIT")

                    total_records += inserted_count
                    metrics["records_inserted"] += inserted_count

                    if normalized_config["request_delay_ms"]:
                        time.sleep(normalized_config["request_delay_ms"] / 1000)

                except SyncCancelled:
                    raise
                except HTTPException as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    error_text = str(error.detail)
                    failed_items.append({
                        "isin": isin,
                        "trading_symbol": trading_symbol,
                        "endpoint": endpoint,
                        "statement_type": statement_type,
                        "time_period": time_period,
                        "include_full_statement": include_full_statement,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    try:
                        record_company_fundamentals_status(
                            conn=conn,
                            isin=isin,
                            endpoint=endpoint,
                            statement_type=statement_type,
                            time_period=time_period,
                            include_full_statement=include_full_statement,
                            status_value="failed",
                            record_count=0,
                            sync_id=sync_id,
                            error_message=error_text
                        )
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass

                    print(
                        "[Company Fundamentals] API failed "
                        f"{trading_symbol} {isin} {endpoint}: {error_text}"
                    )
                    continue
                except Exception as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    error_text = str(error)
                    failed_items.append({
                        "isin": isin,
                        "trading_symbol": trading_symbol,
                        "endpoint": endpoint,
                        "statement_type": statement_type,
                        "time_period": time_period,
                        "include_full_statement": include_full_statement,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    print(
                        "[Company Fundamentals] Save/API failed "
                        f"{trading_symbol} {isin} {endpoint}: {error_text}"
                    )
                    continue

        status_text = "success" if not failed_items else "partial_success"
        message = "Company Fundamentals synced successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_company_fundamentals_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(failed_items, output_file, ensure_ascii=False, indent=2, default=str)

            message = (
                "Company Fundamentals synced with some failed items. "
                f"Failed items saved to {failed_file}."
            )

        finish_sync_run(
            conn,
            sync_id,
            status_text,
            message,
            total_records,
            started_at
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

        if sync_id:
            saved_records = safe_table_count(conn, "upstox_company_fundamentals")
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Company Fundamentals sync cancelled. Completed rows were saved.",
                total_records,
                started_at
            )
        else:
            saved_records = 0

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Company Fundamentals sync cancelled. Completed rows were saved.",
            "total_records": total_records,
            "saved_records": saved_records,
            "duration_seconds": duration_seconds(started_at),
            "metrics": metrics
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Company Fundamentals sync failed: {error.detail}",
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
                f"Company Fundamentals sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Company Fundamentals: {error}"
        )

    finally:
        conn.close()


def build_company_fundamentals_preview_filters(
    search: str,
    endpoint: str,
    statement_type: str,
    time_period: str,
    segment: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_endpoint = endpoint.strip() if endpoint else "all"
    clean_statement_type = statement_type.strip() if statement_type else "all"
    clean_time_period = time_period.strip() if time_period else "all"
    clean_segment = segment.strip() if segment else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(isin, '')) LIKE ?
                OR LOWER(COALESCE(instrument_key, '')) LIKE ?
                OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                OR LOWER(COALESCE(company_name, '')) LIKE ?
                OR LOWER(COALESCE(endpoint_label, '')) LIKE ?
                OR LOWER(COALESCE(sector, '')) LIKE ?
                OR LOWER(COALESCE(company_profile, '')) LIKE ?
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

    if clean_endpoint != "all":
        where_clauses.append("endpoint = ?")
        params.append(clean_endpoint)

    if clean_statement_type != "all":
        where_clauses.append("statement_type = ?")
        params.append(clean_statement_type)

    if clean_time_period != "all":
        where_clauses.append("time_period = ?")
        params.append(clean_time_period)

    if clean_segment != "all":
        where_clauses.append("segment = ?")
        params.append(clean_segment)

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_company_fundamentals_preview(row):
    return {
        "fundamental_id": row[0],
        "isin": row[1],
        "instrument_key": row[2],
        "trading_symbol": row[3],
        "company_name": row[4],
        "exchange": row[5],
        "segment": row[6],
        "endpoint": row[7],
        "endpoint_label": row[8],
        "statement_type": row[9],
        "time_period": row[10],
        "include_full_statement": bool(row[11]),
        "api_status": row[12],
        "units_in": row[13],
        "latest_period": row[14],
        "sector": row[15],
        "company_profile": row[16],
        "sector_market_cap_inr_formatted": row[17],
        "sector_market_cap_usd_formatted": row[18],
        "period_count": row[19],
        "item_count": row[20],
        "latest_revenue": row[21],
        "latest_operating_profit": row[22],
        "latest_net_profit": row[23],
        "latest_total_asset": row[24],
        "latest_total_liability": row[25],
        "latest_operating_cash_flow": row[26],
        "latest_investing_cash_flow": row[27],
        "latest_financing_cash_flow": row[28],
        "latest_promoter_holding_pct": row[29],
        "latest_fii_holding_pct": row[30],
        "latest_dii_holding_pct": row[31],
        "latest_public_holding_pct": row[32],
        "pe_ratio_company": row[33],
        "pe_ratio_sector": row[34],
        "pb_ratio_company": row[35],
        "pb_ratio_sector": row[36],
        "roa_company": row[37],
        "roa_sector": row[38],
        "roe_company": row[39],
        "roe_sector": row[40],
        "roce_company": row[41],
        "roce_sector": row[42],
        "ev_ebitda_company": row[43],
        "ev_ebitda_sector": row[44],
        "corporate_action_count": row[45],
        "competitor_count": row[46],
        "summary_json": row[47],
        "history_json": row[48],
        "full_statement_json": row[49],
        "raw_data_json": row[50],
        "raw_json": row[51],
        "source_sync_id": row[52],
        "synced_at": str(row[53]) if row[53] else None,
        "updated_at": str(row[54]) if row[54] else None
    }


def get_upstox_company_fundamentals_preview_service(
    search: str = "",
    endpoint: str = "all",
    statement_type: str = "all",
    time_period: str = "all",
    segment: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        ensure_upstox_company_fundamentals_tables(conn)

        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_company_fundamentals_preview_filters(
            search=search,
            endpoint=endpoint,
            statement_type=statement_type,
            time_period=time_period,
            segment=segment
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_company_fundamentals
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                fundamental_id,
                isin,
                instrument_key,
                trading_symbol,
                company_name,
                exchange,
                segment,
                endpoint,
                endpoint_label,
                statement_type,
                time_period,
                include_full_statement,
                api_status,
                units_in,
                latest_period,
                sector,
                company_profile,
                sector_market_cap_inr_formatted,
                sector_market_cap_usd_formatted,
                period_count,
                item_count,
                latest_revenue,
                latest_operating_profit,
                latest_net_profit,
                latest_total_asset,
                latest_total_liability,
                latest_operating_cash_flow,
                latest_investing_cash_flow,
                latest_financing_cash_flow,
                latest_promoter_holding_pct,
                latest_fii_holding_pct,
                latest_dii_holding_pct,
                latest_public_holding_pct,
                pe_ratio_company,
                pe_ratio_sector,
                pb_ratio_company,
                pb_ratio_sector,
                roa_company,
                roa_sector,
                roe_company,
                roe_sector,
                roce_company,
                roce_sector,
                ev_ebitda_company,
                ev_ebitda_sector,
                corporate_action_count,
                competitor_count,
                CAST(COALESCE(summary_json, '{{}}') AS VARCHAR),
                CAST(COALESCE(history_json, '[]') AS VARCHAR),
                CAST(COALESCE(full_statement_json, '[]') AS VARCHAR),
                CAST(COALESCE(raw_data_json, '{{}}') AS VARCHAR),
                CAST(COALESCE(raw_json, '{{}}') AS VARCHAR),
                source_sync_id,
                synced_at,
                updated_at
            FROM upstox_company_fundamentals
            {where_sql}
            ORDER BY synced_at DESC, trading_symbol, endpoint, statement_type, time_period
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_company_fundamentals_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()



def ensure_upstox_news_ipo_tables(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS equity_news (
            news_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            instrument_key VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            company_name VARCHAR,
            isin VARCHAR,
            heading VARCHAR,
            title VARCHAR,
            summary TEXT,
            thumbnail VARCHAR,
            article_link VARCHAR,
            url VARCHAR,
            source VARCHAR,
            published_time_ms BIGINT,
            published_at TIMESTAMP,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    for column_sql in [
        "ALTER TABLE equity_news ADD COLUMN provider VARCHAR DEFAULT 'upstox';",
        "ALTER TABLE equity_news ADD COLUMN company_name VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN isin VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN heading VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN thumbnail VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN article_link VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN published_time_ms BIGINT;",
        "ALTER TABLE equity_news ADD COLUMN raw_json JSON;",
        "ALTER TABLE equity_news ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE equity_news ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_equity_news_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            instrument_key VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            page_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_list (
            ipo_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            symbol VARCHAR,
            name VARCHAR,
            status VARCHAR,
            isin VARCHAR,
            issue_type VARCHAR,
            issue_size DOUBLE,
            industry VARCHAR,
            minimum_price DOUBLE,
            maximum_price DOUBLE,
            bidding_start_date DATE,
            bidding_end_date DATE,
            total_subscription DOUBLE,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_details (
            ipo_id VARCHAR PRIMARY KEY,
            provider VARCHAR DEFAULT 'upstox',
            symbol VARCHAR,
            name VARCHAR,
            status VARCHAR,
            isin VARCHAR,
            issue_type VARCHAR,
            issue_size DOUBLE,
            industry VARCHAR,
            minimum_price DOUBLE,
            maximum_price DOUBLE,
            lot_size BIGINT,
            minimum_quantity BIGINT,
            face_value DOUBLE,
            tick_size DOUBLE,
            cut_off_price DOUBLE,
            listing_price DOUBLE,
            listing_exchange VARCHAR,
            bidding_start_date DATE,
            bidding_end_date DATE,
            daily_start_time VARCHAR,
            daily_end_time VARCHAR,
            allotment_date DATE,
            refund_date DATE,
            listing_date DATE,
            rhp_url VARCHAR,
            drhp_url VARCHAR,
            registrar_name VARCHAR,
            registrar_email VARCHAR,
            registrar_phone VARCHAR,
            total_subscription DOUBLE,
            timeline_json JSON,
            registrar_info_json JSON,
            raw_json JSON,
            source_sync_id VARCHAR,
            ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS upstox_ipo_sync_status (
            provider VARCHAR DEFAULT 'upstox',
            status_filter VARCHAR NOT NULL,
            issue_type_filter VARCHAR NOT NULL,
            status VARCHAR DEFAULT 'success',
            record_count BIGINT DEFAULT 0,
            page_count BIGINT DEFAULT 0,
            detail_count BIGINT DEFAULT 0,
            last_error VARCHAR,
            source_sync_id VARCHAR,
            checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


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

    for column_sql in [
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_gmp VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN price_band VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_date VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_type VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_status VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN last_updated VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN raw_json JSON;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN data_hash VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;",
        "ALTER TABLE ipo_gmp_scraper ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

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

    for column_sql in [
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN snapshot_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_sync_id VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_name VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_gmp VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN price_band VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_date VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_type VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_status VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN last_updated VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN raw_json JSON;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN data_hash VARCHAR;",
        "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;"
    ]:
        try:
            conn.execute(column_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass

    for index_sql in [
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_status ON ipo_gmp_scraper (ipo_status);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_updated ON ipo_gmp_scraper (updated_at);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_ipo_name ON ipo_gmp_scraper_snapshots (ipo_name);",
        "CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_sync ON ipo_gmp_scraper_snapshots (source_sync_id);"
    ]:
        try:
            conn.execute(index_sql)
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass


def get_saved_upstox_market_data_token(conn) -> str:
    row = conn.execute("""
        SELECT analytical_token, access_token, connection_status
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [UPSTOX_PROVIDER]).fetchone()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upstox connection is not configured.")

    if (row[2] or "saved") == "disconnected":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upstox connection is disconnected.")

    analytical_token = normalize_upstox_token(row[0])
    access_token = normalize_upstox_token(row[1])

    if analytical_token:
        return analytical_token

    if access_token:
        return access_token

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Upstox analytical token is missing.")


def upstox_news_ipo_http_get_json(url: str, token: str, purpose: str, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict:
    request = urllib.request.Request(
        url,
        headers={
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
        raise HTTPException(status_code=error.code, detail=error_text or str(error))
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to call Upstox {purpose} API: {error}")


def fetch_upstox_json_with_retry(url: str, token: str, retry_count: int, rate_limiter: UpstoxRollingRateLimiter, purpose: str) -> dict:
    attempts = max(1, int(retry_count or 1))
    last_error = None

    for attempt in range(1, attempts + 1):
        try:
            rate_limiter.wait_for_slot()
            return upstox_news_ipo_http_get_json(url=url, token=token, purpose=purpose)
        except HTTPException as error:
            last_error = error
            error_text = str(error.detail).lower()
            should_retry = error.status_code in (408, 429, 500, 502, 503, 504) or "timeout" in error_text or "rate" in error_text

            if not should_retry or attempt >= attempts:
                raise

            time.sleep(min(30, 2 * attempt))

    if last_error:
        raise last_error

    raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"Unable to call Upstox {purpose} API.")


def chunk_records(values: List[Any], chunk_size: int) -> List[List[Any]]:
    return [values[index:index + chunk_size] for index in range(0, len(values), chunk_size)]


def parse_upstox_epoch_ms(value: Any) -> Optional[datetime]:
    if value in (None, ""):
        return None

    try:
        return datetime.fromtimestamp(int(float(value)) / 1000)
    except Exception:
        return None


def normalize_news_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    return {
        "instrument_limit": normalize_optional_positive_int(payload.get("instrument_limit"), 1, 1000000),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key")),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "retry_count": normalize_positive_int(payload.get("retry_count"), UPSTOX_NEWS_DEFAULT_RETRY_COUNT, 1, 10)
    }

def normalize_equity_news_config(payload: Optional[dict]) -> dict:
    payload = payload or {}

    return {
        "batch_size": normalize_positive_int(
            payload.get("batch_size"),
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL,
            1,
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
        ),
        "page_size": normalize_positive_int(
            payload.get("page_size"),
            UPSTOX_NEWS_MAX_PAGE_SIZE,
            1,
            UPSTOX_NEWS_MAX_PAGE_SIZE
        ),
        "retry_count": normalize_positive_int(
            payload.get("retry_count"),
            UPSTOX_NEWS_DEFAULT_RETRY_COUNT,
            1,
            10
        ),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "instrument_limit": normalize_optional_positive_int(
            payload.get("instrument_limit"),
            1,
            1000000
        ),
        "single_instrument_key": safe_strip(payload.get("single_instrument_key"))
    }

def fetch_equity_news_instruments(conn, config: dict) -> List[dict]:
    params = []
    where_sql = """
    WHERE instrument_key IS NOT NULL
      AND TRIM(instrument_key) <> ''
    """

    if config.get("single_instrument_key"):
        where_sql += " AND instrument_key = ?"
        params.append(config["single_instrument_key"])

    limit_sql = ""

    if config.get("instrument_limit"):
        limit_sql = "LIMIT ?"
        params.append(config["instrument_limit"])

    rows = conn.execute(f"""
        SELECT instrument_key, trading_symbol, name, isin, exchange, segment
        FROM upstox_equity_instruments
        {where_sql}
        ORDER BY trading_symbol, instrument_key
        {limit_sql};
    """, params).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": row[3],
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[0])
    ]


def build_equity_news_url(
    instrument_keys: List[str],
    page_number: int,
    page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE
) -> str:
    params = {
        "category": "instrument_keys",
        "instrument_keys": ",".join(instrument_keys),
        "page_number": int(page_number),
        "page_size": min(
            max(1, int(page_size or UPSTOX_NEWS_MAX_PAGE_SIZE)),
            UPSTOX_NEWS_MAX_PAGE_SIZE
        )
    }
    return f"{UPSTOX_EQUITY_NEWS_URL}?{urllib.parse.urlencode(params)}"


def build_upstox_equity_news_url(
    instrument_keys: List[str],
    page_number: int,
    page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE
) -> str:
    return build_equity_news_url(
        instrument_keys=instrument_keys,
        page_number=page_number,
        page_size=page_size
    )


def extract_news_response_items(response: dict) -> List[dict]:
    data = response.get("data") if isinstance(response, dict) else None

    if not isinstance(data, dict):
        return []

    rows = []

    for instrument_key, articles in data.items():
        if isinstance(articles, list):
            for article in articles:
                if isinstance(article, dict):
                    rows.append({"instrument_key": instrument_key, "article": article})

    return rows


def extract_equity_news_rows(response: dict) -> List[dict]:
    return extract_news_response_items(response)


def fetch_equity_news_with_retry(
    url: str,
    token: str,
    retry_count: int,
    rate_limiter: UpstoxRollingRateLimiter
) -> dict:
    return fetch_upstox_json_with_retry(
        url=url,
        token=token,
        retry_count=retry_count,
        rate_limiter=rate_limiter,
        purpose="Equity News"
    )


def should_continue_news_pagination(response: dict, page_number: int, item_count: int, page_size: int = UPSTOX_NEWS_MAX_PAGE_SIZE) -> bool:
    if item_count <= 0:
        return False

    metadata = response.get("metadata") if isinstance(response, dict) else None

    if isinstance(metadata, dict):
        page = metadata.get("page")

        if isinstance(page, dict):
            total_pages = page.get("total_pages") or page.get("totalPages")

            if total_pages is not None:
                try:
                    return page_number < int(total_pages)
                except Exception:
                    pass

    for container in (
        response.get("data") if isinstance(response, dict) else None,
        metadata,
        response
    ):
        if not isinstance(container, dict):
            continue

        total_pages = container.get("total_pages") or container.get("totalPages")

        if total_pages is not None:
            try:
                return page_number < int(total_pages)
            except Exception:
                pass

    return item_count >= min(max(1, int(page_size or UPSTOX_NEWS_MAX_PAGE_SIZE)), UPSTOX_NEWS_MAX_PAGE_SIZE)


def normalize_equity_news_record(instrument_lookup: dict, response_item: dict, sync_id: str) -> Optional[dict]:
    instrument_key = safe_strip(response_item.get("instrument_key"))
    article = response_item.get("article")

    if not instrument_key or not isinstance(article, dict):
        return None

    instrument = instrument_lookup.get(instrument_key, {})
    heading = article.get("heading") or article.get("title")
    article_link = article.get("article_link") or article.get("link") or article.get("url")
    published_time_ms = article.get("published_time") or article.get("published_at")
    published_at = parse_upstox_epoch_ms(published_time_ms)
    unique_text = f"{instrument_key}|{article_link or ''}|{published_time_ms or ''}|{heading or ''}"

    return {
        "news_id": str(uuid.uuid5(uuid.NAMESPACE_URL, unique_text)),
        "provider": UPSTOX_PROVIDER,
        "instrument_key": instrument_key,
        "trading_symbol": instrument.get("trading_symbol"),
        "company_name": instrument.get("name"),
        "isin": instrument.get("isin"),
        "heading": heading,
        "title": heading,
        "summary": article.get("summary"),
        "thumbnail": article.get("thumbnail"),
        "article_link": article_link,
        "url": article_link,
        "source": article.get("source") or article.get("publisher"),
        "published_time_ms": int(published_time_ms) if str(published_time_ms or "").isdigit() else None,
        "published_at": published_at,
        "raw_json": json_dumps_for_db(article),
        "source_sync_id": sync_id
    }


def normalize_equity_news_records(response: dict, instruments: List[dict], sync_id: str) -> List[dict]:
    instrument_lookup = {
        safe_strip(instrument.get("instrument_key")): instrument
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    }

    records = []

    for response_item in extract_news_response_items(response):
        record = normalize_equity_news_record(
            instrument_lookup=instrument_lookup,
            response_item=response_item,
            sync_id=sync_id
        )

        if record:
            records.append(record)

    return records


def insert_equity_news_records(conn, records: List[dict]) -> int:
    rows_by_id = {record.get("news_id"): record for record in records if record.get("news_id")}
    rows = list(rows_by_id.values())

    if not rows:
        return 0

    conn.executemany("DELETE FROM equity_news WHERE news_id = ?;", [(row.get("news_id"),) for row in rows])

    conn.executemany("""
        INSERT INTO equity_news (
            news_id, provider, instrument_key, trading_symbol, company_name, isin,
            heading, title, summary, thumbnail, article_link, url, source,
            published_time_ms, published_at, raw_json, source_sync_id, ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("news_id"), row.get("provider"), row.get("instrument_key"),
            row.get("trading_symbol"), row.get("company_name"), row.get("isin"),
            row.get("heading"), row.get("title"), row.get("summary"), row.get("thumbnail"),
            row.get("article_link"), row.get("url"), row.get("source"),
            row.get("published_time_ms"), row.get("published_at"), row.get("raw_json"),
            row.get("source_sync_id")
        )
        for row in rows
    ])

    return len(rows)


def record_equity_news_status(conn, instrument_key: str, status_value: str, record_count: int, page_count: int, sync_id: str, error_message: Optional[str] = None):
    conn.execute("DELETE FROM upstox_equity_news_sync_status WHERE instrument_key = ?;", [instrument_key])
    conn.execute("""
        INSERT INTO upstox_equity_news_sync_status (
            provider, instrument_key, status, record_count, page_count, last_error,
            source_sync_id, checked_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """, [UPSTOX_PROVIDER, instrument_key, status_value, int(record_count or 0), int(page_count or 0), error_message, sync_id])


def record_equity_news_sync_status(
    conn,
    instrument_keys: List[str],
    status_value: str,
    record_count: int,
    sync_id: str,
    error_message: Optional[str] = None,
    page_count: int = 1
):
    clean_keys = [
        safe_strip(instrument_key)
        for instrument_key in instrument_keys
        if safe_strip(instrument_key)
    ]

    if not clean_keys:
        return

    per_instrument_count = int(record_count or 0)

    for instrument_key in clean_keys:
        record_equity_news_status(
            conn=conn,
            instrument_key=instrument_key,
            status_value=status_value,
            record_count=per_instrument_count,
            page_count=page_count,
            sync_id=sync_id,
            error_message=error_message
        )


def equity_news_batch_recently_checked(conn, instrument_keys: List[str]) -> bool:
    clean_keys = [
        safe_strip(instrument_key)
        for instrument_key in instrument_keys
        if safe_strip(instrument_key)
    ]

    if not clean_keys:
        return False

    placeholders = ", ".join(["?"] * len(clean_keys))

    try:
        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_equity_news_sync_status
            WHERE instrument_key IN ({placeholders})
              AND status = 'success'
              AND checked_at >= CURRENT_TIMESTAMP - INTERVAL '1 day';
        """, clean_keys).fetchone()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return False

    return bool(row and int(row[0] or 0) >= len(clean_keys))


def build_equity_news_recent_status_cache(conn, instruments: List[dict]) -> set:
    instrument_keys = unique_preserve_order([
        safe_strip(instrument.get("instrument_key"))
        for instrument in instruments
        if safe_strip(instrument.get("instrument_key"))
    ])

    if not instrument_keys:
        return set()

    placeholders = ", ".join(["?"] * len(instrument_keys))

    try:
        rows = conn.execute(f"""
            SELECT instrument_key
            FROM upstox_equity_news_sync_status
            WHERE instrument_key IN ({placeholders})
              AND status = 'success'
              AND checked_at >= CURRENT_TIMESTAMP - INTERVAL '1 day';
        """, instrument_keys).fetchall()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        return set()

    return {
        safe_strip(row[0])
        for row in rows
        if row and safe_strip(row[0])
    }


def fetch_equity_news_instruments(conn, config: Optional[dict] = None) -> List[dict]:
    config = config or {}

    instrument_limit = normalize_optional_positive_int(
        config.get("instrument_limit"),
        1,
        1000000
    )
    single_instrument_key = safe_strip(config.get("single_instrument_key"))

    params = []
    limit_sql = ""

    if single_instrument_key:
        single_filter_sql = " AND instrument_key = ?"
        params.append(single_instrument_key)
    else:
        single_filter_sql = ""

    if instrument_limit:
        limit_sql = "LIMIT ?"

    final_params = params + params

    if instrument_limit:
        final_params.append(instrument_limit)

    rows = conn.execute(f"""
        SELECT *
        FROM (
            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                0 AS source_rank
            FROM upstox_equity_instruments
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              {single_filter_sql}

            UNION ALL

            SELECT
                instrument_key,
                trading_symbol,
                name,
                isin,
                exchange,
                segment,
                1 AS source_rank
            FROM upstox_instruments
            WHERE instrument_key IS NOT NULL
              AND TRIM(instrument_key) <> ''
              AND source_type = 'bod_complete'
              AND (
                  UPPER(COALESCE(segment, '')) IN ('NSE_EQ', 'BSE_EQ')
                  OR UPPER(COALESCE(instrument_type, '')) IN ('EQ', 'EQUITY')
              )
              {single_filter_sql}
        )
        QUALIFY ROW_NUMBER() OVER (
            PARTITION BY instrument_key
            ORDER BY source_rank, trading_symbol, instrument_key
        ) = 1
        ORDER BY trading_symbol, instrument_key
        {limit_sql};
    """, final_params).fetchall()

    return [
        {
            "instrument_key": row[0],
            "trading_symbol": row[1],
            "name": row[2],
            "isin": row[3],
            "exchange": row[4],
            "segment": row[5]
        }
        for row in rows
        if row and safe_strip(row[0])
    ]

def sync_upstox_equity_news_service(
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
        "records_inserted": 0,
        "failed_items": 0
    }
    failed_items = []

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)

        normalized_config = normalize_equity_news_config(config or {})

        analytical_token = ""
        access_token = ""

        try:
            analytical_token = get_saved_upstox_analytical_token(conn)
        except HTTPException:
            analytical_token = ""

        try:
            access_token = get_optional_upstox_access_token(conn)
        except Exception:
            access_token = ""

        token = analytical_token or access_token

        if not token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Upstox analytical token or access token is missing. "
                    "Save token in Connections first."
                )
            )

        instruments = fetch_equity_news_instruments(conn, normalized_config)

        if not instruments:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "No equity instruments found. Run Current Instruments first, "
                    "then run Equity News again."
                )
            )

        sync_id = create_sync_run(
            conn,
            "upstox_equity_news",
            "running",
            "Equity News sync started.",
            current_user=current_user
        )

        rate_limiter = UpstoxRollingRateLimiter()

        batch_size = min(
            int(
                normalized_config.get("batch_size")
                or UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
            ),
            UPSTOX_NEWS_MAX_INSTRUMENT_KEYS_PER_CALL
        )
        page_size = min(
            int(
                normalized_config.get("page_size")
                or UPSTOX_NEWS_MAX_PAGE_SIZE
            ),
            UPSTOX_NEWS_MAX_PAGE_SIZE
        )
        retry_count = int(normalized_config.get("retry_count") or 3)
        force_refresh = bool(normalized_config.get("force_refresh", False))
        skip_existing = bool(normalized_config.get("skip_existing", True))
        recent_status_cache = (
            build_equity_news_recent_status_cache(conn, instruments)
            if skip_existing and not force_refresh
            else set()
        )

        print(
            "[Equity News] Starting sync "
            f"instruments={len(instruments)} "
            f"batch_size={batch_size} "
            f"page_size={page_size}"
        )

        for batch_start in range(0, len(instruments), batch_size):
            check_sync_cancelled(conn, sync_id)

            batch = instruments[batch_start:batch_start + batch_size]
            instrument_keys = [
                safe_strip(instrument.get("instrument_key"))
                for instrument in batch
                if safe_strip(instrument.get("instrument_key"))
            ]

            if not instrument_keys:
                continue

            if (
                skip_existing
                and not force_refresh
                and instrument_keys
                and all(instrument_key in recent_status_cache for instrument_key in instrument_keys)
            ):
                metrics["api_calls_skipped"] += 1
                print(
                    "[Equity News] Skipped batch because all instruments were "
                    "recently checked."
                )
                continue

            page_number = 1

            while page_number <= UPSTOX_NEWS_MAX_PAGE_NUMBER:
                check_sync_cancelled(conn, sync_id)

                url = build_upstox_equity_news_url(
                    instrument_keys=instrument_keys,
                    page_number=page_number,
                    page_size=page_size
                )

                try:
                    print(
                        "[Equity News] API batch "
                        f"{batch_start + 1}-{batch_start + len(batch)} "
                        f"of {len(instruments)}, page={page_number}"
                    )

                    response = fetch_equity_news_with_retry(
                        url=url,
                        token=token,
                        retry_count=retry_count,
                        rate_limiter=rate_limiter
                    )
                    metrics["api_calls_attempted"] += 1

                    records = normalize_equity_news_records(
                        response=response,
                        instruments=batch,
                        sync_id=sync_id
                    )

                    conn.execute("BEGIN TRANSACTION")

                    inserted_count = insert_equity_news_records(conn, records)

                    record_equity_news_sync_status(
                        conn=conn,
                        instrument_keys=instrument_keys,
                        status_value="success",
                        record_count=inserted_count,
                        sync_id=sync_id,
                        error_message=None
                    )

                    conn.execute("COMMIT")

                    total_records += inserted_count
                    metrics["records_inserted"] += inserted_count

                    print(
                        "[Equity News] Saved "
                        f"{inserted_count} rows for page={page_number}. "
                        f"Total saved={total_records}."
                    )

                    extracted_rows = extract_equity_news_rows(response)
                    has_more_pages = should_continue_news_pagination(
                        response=response,
                        page_number=page_number,
                        item_count=len(extracted_rows),
                        page_size=page_size
                    )

                    if not has_more_pages:
                        break

                    page_number += 1

                except SyncCancelled:
                    raise

                except HTTPException as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    error_text = str(error.detail)
                    failed_items.append({
                        "instrument_keys": instrument_keys,
                        "page_number": page_number,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    try:
                        record_equity_news_sync_status(
                            conn=conn,
                            instrument_keys=instrument_keys,
                            status_value="failed",
                            record_count=0,
                            sync_id=sync_id,
                            error_message=error_text
                        )
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass

                    print(
                        "[Equity News] API failed "
                        f"batch={batch_start + 1}-{batch_start + len(batch)} "
                        f"page={page_number}: {error_text}"
                    )
                    break

                except Exception as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                    error_text = str(error)
                    failed_items.append({
                        "instrument_keys": instrument_keys,
                        "page_number": page_number,
                        "error": error_text
                    })
                    metrics["failed_items"] += 1

                    print(
                        "[Equity News] Save/API failed "
                        f"batch={batch_start + 1}-{batch_start + len(batch)} "
                        f"page={page_number}: {error_text}"
                    )
                    break

        status_text = "success" if not failed_items else "partial_success"
        message = "Equity News synced successfully."

        if failed_items:
            failed_file = DATA_DIR / "upstox_equity_news_failed_items.json"

            with open(failed_file, "w", encoding="utf-8") as output_file:
                json.dump(
                    failed_items,
                    output_file,
                    ensure_ascii=False,
                    indent=2,
                    default=str
                )

            message = (
                "Equity News synced with some failed batches. "
                f"Failed items saved to {failed_file}."
            )

        finish_sync_run(
            conn,
            sync_id,
            status_text,
            message,
            total_records,
            started_at
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

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Equity News sync cancelled. Completed rows were saved.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Equity News sync cancelled. Completed rows were saved.",
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
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Equity News sync failed: {error.detail}",
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
                f"Equity News sync failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to sync Equity News: {error}"
        )

    finally:
        conn.close()


def normalize_ipo_config(payload: Optional[dict]) -> dict:
    payload = payload or {}
    statuses = normalize_string_list(payload.get("statuses") or payload.get("selected_statuses"), UPSTOX_IPO_DEFAULT_STATUSES)
    issue_types = normalize_string_list(payload.get("issue_types") or payload.get("selected_issue_types"), UPSTOX_IPO_DEFAULT_ISSUE_TYPES)

    return {
        "statuses": unique_preserve_order([item.lower() for item in statuses if item.lower() in UPSTOX_IPO_DEFAULT_STATUSES]) or UPSTOX_IPO_DEFAULT_STATUSES.copy(),
        "issue_types": unique_preserve_order([item.lower() for item in issue_types if item.lower() in UPSTOX_IPO_DEFAULT_ISSUE_TYPES]) or UPSTOX_IPO_DEFAULT_ISSUE_TYPES.copy(),
        "include_details": normalize_bool(payload.get("include_details"), True),
        "force_refresh": normalize_bool(payload.get("force_refresh"), False),
        "skip_existing": normalize_bool(payload.get("skip_existing"), True),
        "retry_count": normalize_positive_int(payload.get("retry_count"), UPSTOX_IPO_DEFAULT_RETRY_COUNT, 1, 10)
    }


def build_ipo_list_url(status_filter: str, issue_type_filter: str, page_number: int) -> str:
    params = {"status": status_filter, "issue_type": issue_type_filter, "page_number": int(page_number), "records": UPSTOX_IPO_MAX_RECORDS_PER_CALL}
    return f"{UPSTOX_IPO_LIST_URL}?{urllib.parse.urlencode(params)}"


def build_ipo_detail_url(ipo_id: str) -> str:
    return UPSTOX_IPO_DETAIL_URL.format(ipo_id=urllib.parse.quote(str(ipo_id), safe=""))


def extract_ipo_list_rows(response: dict) -> List[dict]:
    data = response.get("data") if isinstance(response, dict) else None
    if isinstance(data, dict):
        for key in ("ipos", "ipo", "data"):
            if isinstance(data.get(key), list):
                return data.get(key)
    if isinstance(data, list):
        return data
    return response.get("ipos") if isinstance(response, dict) and isinstance(response.get("ipos"), list) else []


def should_continue_ipo_pagination(response: dict, page_number: int, item_count: int) -> bool:
    if item_count <= 0:
        return False

    data = response.get("data") if isinstance(response, dict) else {}
    meta_data = response.get("meta_data") if isinstance(response, dict) else {}
    metadata = response.get("metadata") if isinstance(response, dict) else {}

    page_containers = []

    for metadata_container in (meta_data, metadata):
        if isinstance(metadata_container, dict) and isinstance(metadata_container.get("page"), dict):
            page_containers.append(metadata_container.get("page"))

    for container in page_containers + [data, meta_data, metadata, response]:
        if not isinstance(container, dict):
            continue
        total_pages = container.get("total_pages") or container.get("totalPages")
        if total_pages is not None:
            try:
                return page_number < int(total_pages)
            except Exception:
                pass
        total = container.get("total")
        if total is not None:
            try:
                return page_number * UPSTOX_IPO_MAX_RECORDS_PER_CALL < int(total)
            except Exception:
                pass

    return item_count >= UPSTOX_IPO_MAX_RECORDS_PER_CALL


def extract_ipo_detail_record(response: dict) -> Optional[dict]:
    data = response.get("data") if isinstance(response, dict) else None

    if isinstance(data, dict):
        return data

    return response if isinstance(response, dict) else None


def normalize_ipo_date(value: Any) -> Optional[str]:
    return normalize_expiry_value(value)


def normalize_ipo_list_record(record: dict, sync_id: str) -> Optional[dict]:
    if not isinstance(record, dict):
        return None

    ipo_id = safe_strip(record.get("id") or record.get("ipo_id"))
    if not ipo_id:
        return None

    return {
        "ipo_id": ipo_id,
        "provider": UPSTOX_PROVIDER,
        "symbol": record.get("symbol"),
        "name": record.get("name"),
        "status": record.get("status"),
        "isin": record.get("isin"),
        "issue_type": record.get("issue_type"),
        "issue_size": safe_float(record.get("issue_size")),
        "industry": record.get("industry") or record.get("company_sector"),
        "minimum_price": safe_float(record.get("minimum_price") or record.get("price_band_min")),
        "maximum_price": safe_float(record.get("maximum_price") or record.get("price_band_max")),
        "bidding_start_date": normalize_ipo_date(record.get("bidding_start_date") or record.get("open_date")),
        "bidding_end_date": normalize_ipo_date(record.get("bidding_end_date") or record.get("close_date")),
        "total_subscription": safe_float(record.get("total_subscription")),
        "raw_json": json_dumps_for_db(record),
        "source_sync_id": sync_id
    }


def normalize_ipo_detail_record(record: dict, sync_id: str) -> Optional[dict]:
    if not isinstance(record, dict):
        return None

    ipo_id = safe_strip(record.get("id") or record.get("ipo_id"))
    if not ipo_id:
        return None

    timeline = record.get("timeline") if isinstance(record.get("timeline"), dict) else {}
    registrar_info = record.get("registrar_info") if isinstance(record.get("registrar_info"), dict) else {}

    return {
        "ipo_id": ipo_id,
        "provider": UPSTOX_PROVIDER,
        "symbol": record.get("symbol"),
        "name": record.get("name"),
        "status": record.get("status"),
        "isin": record.get("isin"),
        "issue_type": record.get("issue_type"),
        "issue_size": safe_float(record.get("issue_size")),
        "industry": record.get("industry") or record.get("company_sector"),
        "minimum_price": safe_float(record.get("minimum_price") or record.get("price_band_min")),
        "maximum_price": safe_float(record.get("maximum_price") or record.get("price_band_max")),
        "lot_size": normalize_optional_positive_int(record.get("lot_size"), 1, 1000000000),
        "minimum_quantity": normalize_optional_positive_int(record.get("minimum_quantity"), 1, 1000000000),
        "face_value": safe_float(record.get("face_value")),
        "tick_size": safe_float(record.get("tick_size")),
        "cut_off_price": safe_float(record.get("cut_off_price")),
        "listing_price": safe_float(record.get("listing_price")),
        "listing_exchange": record.get("listing_exchange"),
        "bidding_start_date": normalize_ipo_date(record.get("bidding_start_date") or timeline.get("application_start_date")),
        "bidding_end_date": normalize_ipo_date(record.get("bidding_end_date") or timeline.get("application_end_date")),
        "daily_start_time": record.get("daily_start_time"),
        "daily_end_time": record.get("daily_end_time"),
        "allotment_date": normalize_ipo_date(timeline.get("allotment_date") or record.get("allotment_date")),
        "refund_date": normalize_ipo_date(timeline.get("refund_initiation_date") or record.get("refund_date")),
        "listing_date": normalize_ipo_date(timeline.get("listing_date") or record.get("listing_date")),
        "rhp_url": record.get("rhp_url"),
        "drhp_url": record.get("drhp_url"),
        "registrar_name": registrar_info.get("name") or registrar_info.get("registrar"),
        "registrar_email": registrar_info.get("email"),
        "registrar_phone": registrar_info.get("contact_number") or registrar_info.get("phone"),
        "total_subscription": safe_float(record.get("total_subscription")),
        "timeline_json": json_dumps_for_db(timeline),
        "registrar_info_json": json_dumps_for_db(registrar_info),
        "raw_json": json_dumps_for_db(record),
        "source_sync_id": sync_id
    }


def insert_ipo_list_records(conn, records: List[dict]) -> int:
    rows = list({record.get("ipo_id"): record for record in records if record.get("ipo_id")}.values())
    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ipo_list (
            ipo_id, provider, symbol, name, status, isin, issue_type, issue_size,
            industry, minimum_price, maximum_price, bidding_start_date, bidding_end_date,
            total_subscription, raw_json, source_sync_id, ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), ?, TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_id"), row.get("provider"), row.get("symbol"), row.get("name"),
            row.get("status"), row.get("isin"), row.get("issue_type"), row.get("issue_size"),
            row.get("industry"), row.get("minimum_price"), row.get("maximum_price"),
            row.get("bidding_start_date"), row.get("bidding_end_date"), row.get("total_subscription"),
            row.get("raw_json"), row.get("source_sync_id")
        )
        for row in rows
    ])
    return len(rows)


def insert_ipo_detail_records(conn, records: List[dict]) -> int:
    rows = list({record.get("ipo_id"): record for record in records if record.get("ipo_id")}.values())
    if not rows:
        return 0

    conn.executemany("""
        INSERT OR REPLACE INTO upstox_ipo_details (
            ipo_id, provider, symbol, name, status, isin, issue_type, issue_size,
            industry, minimum_price, maximum_price, lot_size, minimum_quantity,
            face_value, tick_size, cut_off_price, listing_price, listing_exchange,
            bidding_start_date, bidding_end_date, daily_start_time, daily_end_time,
            allotment_date, refund_date, listing_date, rhp_url, drhp_url,
            registrar_name, registrar_email, registrar_phone, total_subscription,
            timeline_json, registrar_info_json, raw_json, source_sync_id,
            ingested_at, updated_at
        )
        SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
               TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), ?, ?,
               TRY_CAST(? AS DATE), TRY_CAST(? AS DATE), TRY_CAST(? AS DATE),
               ?, ?, ?, ?, ?, ?, TRY_CAST(? AS JSON), TRY_CAST(? AS JSON),
               TRY_CAST(? AS JSON), ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_id"), row.get("provider"), row.get("symbol"), row.get("name"),
            row.get("status"), row.get("isin"), row.get("issue_type"), row.get("issue_size"),
            row.get("industry"), row.get("minimum_price"), row.get("maximum_price"),
            row.get("lot_size"), row.get("minimum_quantity"), row.get("face_value"),
            row.get("tick_size"), row.get("cut_off_price"), row.get("listing_price"),
            row.get("listing_exchange"), row.get("bidding_start_date"), row.get("bidding_end_date"),
            row.get("daily_start_time"), row.get("daily_end_time"), row.get("allotment_date"),
            row.get("refund_date"), row.get("listing_date"), row.get("rhp_url"), row.get("drhp_url"),
            row.get("registrar_name"), row.get("registrar_email"), row.get("registrar_phone"),
            row.get("total_subscription"), row.get("timeline_json"), row.get("registrar_info_json"),
            row.get("raw_json"), row.get("source_sync_id")
        )
        for row in rows
    ])

    return len(rows)


def sync_upstox_ipo_calendar_service(current_user: dict, config: Optional[dict] = None, clear_cancel_at_start: bool = True):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0
    metrics = {
        "api_calls_attempted": 0,
        "api_calls_skipped": 0,
        "list_records_saved": 0,
        "detail_records_saved": 0,
        "failed_groups": 0
    }

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)
        normalized_config = normalize_ipo_config(config)
        token = get_saved_upstox_access_token(conn)
        sync_id = create_sync_run(conn, UPSTOX_IPO_SYNC_TYPE, "running", "IPO Calendar sync started.", current_user=current_user)
        rate_limiter = UpstoxRollingRateLimiter()

        for status_filter in normalized_config["statuses"]:
            for issue_type_filter in normalized_config["issue_types"]:
                check_sync_cancelled(conn, sync_id)

                if normalized_config["skip_existing"] and not normalized_config["force_refresh"] and status_filter in ("closed", "listed"):
                    row = conn.execute("""
                        SELECT 1
                        FROM upstox_ipo_sync_status
                        WHERE status_filter = ?
                          AND issue_type_filter = ?
                          AND status = 'success'
                        LIMIT 1;
                    """, [status_filter, issue_type_filter]).fetchone()
                    if row:
                        metrics["api_calls_skipped"] += 1
                        continue

                page_number = 1
                page_count = 0
                group_count = 0
                detail_count = 0

                try:
                    while True:
                        check_sync_cancelled(conn, sync_id)
                        response = fetch_upstox_json_with_retry(
                            url=build_ipo_list_url(status_filter, issue_type_filter, page_number),
                            token=token,
                            retry_count=normalized_config["retry_count"],
                            rate_limiter=rate_limiter,
                            purpose="IPO"
                        )
                        metrics["api_calls_attempted"] += 1
                        page_count += 1
                        response_rows = extract_ipo_list_rows(response)
                        records = [record for record in (normalize_ipo_list_record(item, sync_id) for item in response_rows) if record]

                        conn.execute("BEGIN TRANSACTION")
                        saved_count = insert_ipo_list_records(conn, records)
                        conn.execute("COMMIT")

                        total_records += saved_count
                        group_count += saved_count
                        metrics["list_records_saved"] += saved_count

                        if normalized_config["include_details"] and records:
                            detail_records = []

                            for record in records:
                                check_sync_cancelled(conn, sync_id)
                                ipo_id = record.get("ipo_id")

                                if not ipo_id:
                                    continue

                                detail_response = fetch_upstox_json_with_retry(
                                    url=build_ipo_detail_url(ipo_id),
                                    token=token,
                                    retry_count=normalized_config["retry_count"],
                                    rate_limiter=rate_limiter,
                                    purpose="IPO Detail"
                                )
                                metrics["api_calls_attempted"] += 1

                                detail_record = normalize_ipo_detail_record(
                                    extract_ipo_detail_record(detail_response),
                                    sync_id
                                )

                                if detail_record:
                                    detail_records.append(detail_record)

                            if detail_records:
                                conn.execute("BEGIN TRANSACTION")
                                saved_detail_count = insert_ipo_detail_records(conn, detail_records)
                                conn.execute("COMMIT")
                                detail_count += saved_detail_count
                                metrics["detail_records_saved"] += saved_detail_count

                        if not should_continue_ipo_pagination(response, page_number, len(response_rows)):
                            break
                        page_number += 1

                    conn.execute("BEGIN TRANSACTION")
                    record_ipo_status(conn, status_filter, issue_type_filter, "success", group_count, page_count, detail_count, sync_id)
                    conn.execute("COMMIT")

                except SyncCancelled:
                    raise
                except Exception as error:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    metrics["failed_groups"] += 1
                    error_text = str(error.detail) if isinstance(error, HTTPException) else str(error)
                    try:
                        conn.execute("BEGIN TRANSACTION")
                        record_ipo_status(conn, status_filter, issue_type_filter, "failed", 0, page_count, 0, sync_id, error_text)
                        conn.execute("COMMIT")
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                    print(f"[IPO Calendar] Group failed {status_filter}/{issue_type_filter}: {error_text}")
                    continue

        status_text = "success" if metrics["failed_groups"] == 0 else "partial_success"
        message = "IPO Calendar synced successfully." if status_text == "success" else "IPO Calendar synced with some failed groups."
        finish_sync_run(conn, sync_id, status_text, message, total_records, started_at)

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {"status": status_text, "message": message, "total_records": total_records, "duration_seconds": duration_seconds(started_at), "metrics": metrics}

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass
        if sync_id:
            finish_sync_run(conn, sync_id, "cancelled", "IPO Calendar sync cancelled. Completed rows were saved.", total_records, started_at)
        if clear_cancel_at_start:
            clear_cancel_signal()
        return {"status": "cancelled", "message": "IPO Calendar sync cancelled. Completed rows were saved.", "total_records": total_records, "duration_seconds": duration_seconds(started_at), "metrics": metrics}
    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass
        if sync_id:
            finish_sync_run(conn, sync_id, "failed", f"IPO Calendar sync failed: {error.detail}", total_records, started_at)
        if clear_cancel_at_start:
            clear_cancel_signal()
        raise
    finally:
        conn.close()


def record_ipo_status(conn, status_filter: str, issue_type_filter: str, status_value: str, record_count: int, page_count: int, detail_count: int, sync_id: str, error_message: Optional[str] = None):
    conn.execute("DELETE FROM upstox_ipo_sync_status WHERE status_filter = ? AND issue_type_filter = ?;", [status_filter, issue_type_filter])
    conn.execute("""
        INSERT INTO upstox_ipo_sync_status (
            provider, status_filter, issue_type_filter, status, record_count, page_count,
            detail_count, last_error, source_sync_id, checked_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP);
    """, [UPSTOX_PROVIDER, status_filter, issue_type_filter, status_value, int(record_count or 0), int(page_count or 0), int(detail_count or 0), error_message, sync_id])


def get_upstox_equity_news_preview_service(search: str = "", segment: str = "all", source: str = "all", page: int = 1, page_size: int = 50):
    conn = get_connection()
    try:
        ensure_upstox_news_ipo_tables(conn)
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(instrument_key, '')) LIKE ?
                    OR LOWER(COALESCE(trading_symbol, '')) LIKE ?
                    OR LOWER(COALESCE(company_name, '')) LIKE ?
                    OR LOWER(COALESCE(isin, '')) LIKE ?
                    OR LOWER(COALESCE(heading, title, '')) LIKE ?
                    OR LOWER(COALESCE(summary, '')) LIKE ?
                    OR LOWER(COALESCE(source, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if source != "all":
            where_clauses.append("source = ?")
            params.append(source)

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        total_records = conn.execute(f"SELECT COUNT(*) FROM equity_news {where_sql};", params).fetchone()[0]
        rows = conn.execute(f"""
            SELECT news_id, instrument_key, trading_symbol, company_name, isin,
                   COALESCE(heading, title) AS heading, title, summary, thumbnail,
                   article_link, COALESCE(url, article_link) AS url, source,
                   published_time_ms, published_at, source_sync_id, ingested_at, updated_at
            FROM equity_news
            {where_sql}
            ORDER BY published_at DESC NULLS LAST, ingested_at DESC, trading_symbol
            LIMIT ? OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()
        total_pages = max(1, int((total_records + current_page_size - 1) / current_page_size))
        return {
            "rows": [
                {
                    "news_id": row[0], "instrument_key": row[1], "trading_symbol": row[2],
                    "company_name": row[3], "isin": row[4], "heading": row[5],
                    "title": row[6], "summary": row[7], "thumbnail": row[8],
                    "article_link": row[9], "url": row[10], "source": row[11],
                    "published_time_ms": row[12], "published_at": str(row[13]) if row[13] else None,
                    "source_sync_id": row[14], "ingested_at": str(row[15]) if row[15] else None,
                    "updated_at": str(row[16]) if row[16] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }
    finally:
        conn.close()


def get_upstox_ipo_calendar_preview_service(search: str = "", ipo_status: str = "all", issue_type: str = "all", page: int = 1, page_size: int = 50):
    conn = get_connection()
    try:
        ensure_upstox_news_ipo_tables(conn)
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        status_sql = """
            CASE
                WHEN LOWER(COALESCE(detail.status, ipo.status, '')) = 'listed'
                     OR detail.listing_date <= CURRENT_DATE THEN 'listed'
                WHEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date) IS NOT NULL
                     AND CURRENT_DATE < COALESCE(detail.bidding_start_date, ipo.bidding_start_date) THEN 'upcoming'
                WHEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date) IS NOT NULL
                     AND COALESCE(detail.bidding_end_date, ipo.bidding_end_date) IS NOT NULL
                     AND CURRENT_DATE BETWEEN COALESCE(detail.bidding_start_date, ipo.bidding_start_date)
                                         AND COALESCE(detail.bidding_end_date, ipo.bidding_end_date) THEN 'open'
                WHEN COALESCE(detail.bidding_end_date, ipo.bidding_end_date) IS NOT NULL
                     AND CURRENT_DATE > COALESCE(detail.bidding_end_date, ipo.bidding_end_date) THEN 'closed'
                ELSE LOWER(COALESCE(detail.status, ipo.status, 'upcoming'))
            END
        """
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(ipo.ipo_id, '')) LIKE ?
                    OR LOWER(COALESCE(detail.symbol, ipo.symbol, '')) LIKE ?
                    OR LOWER(COALESCE(detail.name, ipo.name, '')) LIKE ?
                    OR LOWER(COALESCE(detail.isin, ipo.isin, '')) LIKE ?
                    OR LOWER(COALESCE(detail.industry, ipo.industry, '')) LIKE ?
                    OR LOWER(COALESCE(ipo.derived_status, '')) LIKE ?
                    OR LOWER(COALESCE(detail.issue_type, ipo.issue_type, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if ipo_status != "all":
            where_clauses.append("ipo.derived_status = ?")
            params.append(ipo_status.lower())

        if issue_type != "all":
            where_clauses.append("LOWER(COALESCE(detail.issue_type, ipo.issue_type, '')) = ?")
            params.append(issue_type.lower())

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        from_sql = f"""
            FROM (
                SELECT
                    ipo.*,
                    {status_sql} AS derived_status
                FROM upstox_ipo_list ipo
                LEFT JOIN upstox_ipo_details detail
                    ON detail.ipo_id = ipo.ipo_id
            ) ipo
            LEFT JOIN upstox_ipo_details detail
                ON detail.ipo_id = ipo.ipo_id
        """
        total_records = conn.execute(f"SELECT COUNT(*) {from_sql} {where_sql};", params).fetchone()[0]
        rows = conn.execute(f"""
            SELECT
                ipo.ipo_id,
                COALESCE(detail.symbol, ipo.symbol),
                COALESCE(detail.name, ipo.name),
                ipo.derived_status,
                COALESCE(detail.isin, ipo.isin),
                COALESCE(detail.issue_type, ipo.issue_type),
                COALESCE(detail.issue_size, ipo.issue_size),
                COALESCE(detail.industry, ipo.industry),
                COALESCE(detail.minimum_price, ipo.minimum_price),
                COALESCE(detail.maximum_price, ipo.maximum_price),
                COALESCE(detail.bidding_start_date, ipo.bidding_start_date),
                COALESCE(detail.bidding_end_date, ipo.bidding_end_date),
                COALESCE(detail.total_subscription, ipo.total_subscription),
                COALESCE(detail.source_sync_id, ipo.source_sync_id),
                ipo.ingested_at,
                COALESCE(detail.updated_at, ipo.updated_at)
            {from_sql}
            {where_sql}
            ORDER BY COALESCE(detail.bidding_start_date, ipo.bidding_start_date) DESC NULLS LAST,
                     COALESCE(detail.name, ipo.name)
            LIMIT ? OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()
        total_pages = max(1, int((total_records + current_page_size - 1) / current_page_size))
        return {
            "rows": [
                {
                    "ipo_id": row[0], "symbol": row[1], "name": row[2], "status": row[3],
                    "isin": row[4], "issue_type": row[5], "issue_size": row[6], "industry": row[7],
                    "minimum_price": row[8], "maximum_price": row[9],
                    "bidding_start_date": str(row[10]) if row[10] else None,
                    "bidding_end_date": str(row[11]) if row[11] else None,
                    "total_subscription": row[12], "source_sync_id": row[13],
                    "ingested_at": str(row[14]) if row[14] else None,
                    "updated_at": str(row[15]) if row[15] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }
    finally:
        conn.close()



def normalize_ipo_gmp_value(value: Any) -> str:
    if value is None:
        return ""

    clean_value = str(value).strip()

    if clean_value.lower() in ("nan", "none", "null"):
        return ""

    return clean_value


def parse_ipo_gmp_number(value: Any) -> Optional[float]:
    clean_value = normalize_ipo_gmp_value(value)

    if not clean_value:
        return None

    normalized_value = (
        clean_value
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("INR", "")
        .strip()
    )
    matches = re.findall(r"-?\d+(?:\.\d+)?", normalized_value)

    if not matches:
        return None

    try:
        values = [float(match) for match in matches]
    except ValueError:
        return None

    return max(values) if values else None


def format_ipo_gmp_money(value: float) -> str:
    if value == int(value):
        return f"₹{int(value)}"

    return f"₹{value:.2f}"


def calculate_ipo_gmp_gain(ipo_gmp: Any, price_band: Any) -> Optional[str]:
    gmp_value = parse_ipo_gmp_number(ipo_gmp)
    price_band_value = parse_ipo_gmp_number(price_band)

    if gmp_value is None or price_band_value in (None, 0):
        return None

    estimated_listing = price_band_value + gmp_value
    gain_percent = (gmp_value / price_band_value) * 100

    return f"{format_ipo_gmp_money(estimated_listing)} ({gain_percent:.2f}%)"


def find_ipo_gmp_table_from_html(url: str):
    tables = pd.read_html(url)

    for df in tables:
        cols = [str(column).strip() for column in df.columns]

        if "IPO Name" in cols and "IPO GMP" in cols:
            df = df.copy()
            df.columns = cols
            return df

    raise ValueError("Target IPO GMP table was not found with pandas.read_html.")


def first_existing_path(paths: List[str]) -> Optional[str]:
    for path in paths:
        clean_path = safe_strip(path)

        if clean_path and Path(clean_path).exists():
            return clean_path

    return None


def find_ipo_gmp_table_with_selenium(url: str):
    import os
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "pandas.read_html failed and Selenium is not installed. "
                "Install selenium and ChromeDriver support, or fix read_html dependencies."
            )
        )

    options = webdriver.ChromeOptions()

    chrome_binary = first_existing_path(
        [
            os.environ.get("CHROME_BIN"),
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
    )

    if chrome_binary:
        options.binary_location = chrome_binary

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--window-size=1920,1080")

    chromedriver_path = first_existing_path(
        [
            os.environ.get("CHROMEDRIVER_PATH"),
            "/usr/bin/chromedriver"
        ]
    )
    service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()

    driver = None

    try:
        driver = webdriver.Chrome(
            service=service,
            options=options,
        )

        wait = WebDriverWait(driver, 25)

        driver.get(url)

        wait.until(
            EC.presence_of_all_elements_located(
                (By.TAG_NAME, "table")
            )
        )

        time.sleep(2)

        tables = driver.find_elements(By.TAG_NAME, "table")

        html_table = None

        for table in tables:
            table_text = table.text.strip()

            if (
                "IPO Name" in table_text
                and "IPO GMP" in table_text
                and "Price Band" in table_text
                and "Last Updated" in table_text
            ):
                html_table = table.get_attribute("outerHTML")
                break

        if html_table is None:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Target IPO GMP table was not found with Selenium.",
            )

        df = pd.read_html(StringIO(html_table))[0]
        df.columns = [str(column).strip() for column in df.columns]

        return df

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Selenium failed using "
                f"Chrome='{chrome_binary or 'auto'}', "
                f"ChromeDriver='{chromedriver_path or 'Selenium Manager'}'. "
                f"Error: {exc}"
            ),
        )

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def get_ipo_gmp_dataframe(url: str = IPO_GMP_SCRAPER_URL):
    try:
        return find_ipo_gmp_table_from_html(url)
    except Exception as error:
        print("IPO GMP read_html failed, trying Selenium fallback.")
        print(f"Reason: {error}")

    return find_ipo_gmp_table_with_selenium(url)


def normalize_ipo_gmp_dataframe(df):
    normalized_df = df.copy()
    normalized_df.columns = [str(column).strip() for column in normalized_df.columns]

    if (
        not set(IPO_GMP_SCRAPER_REQUIRED_COLUMNS).issubset(set(normalized_df.columns))
        and not normalized_df.empty
    ):
        first_row_values = [
            normalize_ipo_gmp_value(value)
            for value in normalized_df.iloc[0].tolist()
        ]

        if "IPO Name" in first_row_values and "IPO GMP" in first_row_values:
            normalized_df = normalized_df.iloc[1:].copy()
            normalized_df.columns = first_row_values

    normalized_df.columns = [str(column).strip() for column in normalized_df.columns]
    return normalized_df.reset_index(drop=True)


def normalize_ipo_gmp_record(row: dict, source_url: str) -> Optional[dict]:
    ipo_name = normalize_ipo_gmp_value(row.get("IPO Name"))

    if not ipo_name:
        return None

    raw_record = {
        key: normalize_ipo_gmp_value(value)
        for key, value in row.items()
    }

    return {
        "ipo_name": ipo_name,
        "ipo_gmp": normalize_ipo_gmp_value(row.get("IPO GMP")),
        "price_band": normalize_ipo_gmp_value(row.get("Price Band")),
        "ipo_date": normalize_ipo_gmp_value(row.get("Date")),
        "ipo_type": normalize_ipo_gmp_value(row.get("Type")),
        "ipo_status": normalize_ipo_gmp_value(row.get("Status")),
        "last_updated": normalize_ipo_gmp_value(row.get("Last Updated")),
        "source_url": source_url,
        "raw_json": json_dumps_for_db(raw_record)
    }


def get_ipo_gmp_record_hash(record: dict) -> str:
    comparable_record = {
        key: record.get(key) or ""
        for key in (
            "ipo_name",
            "ipo_gmp",
            "price_band",
            "ipo_date",
            "ipo_type",
            "ipo_status",
            "last_updated"
        )
    }

    payload = json.dumps(
        comparable_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scrape_ipo_gmp_records(source_url: str = IPO_GMP_SCRAPER_URL) -> List[dict]:
    df = normalize_ipo_gmp_dataframe(get_ipo_gmp_dataframe(source_url))

    missing_columns = [
        column
        for column in IPO_GMP_SCRAPER_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "IPO GMP scraper table is missing required columns: "
                + ", ".join(missing_columns)
            )
        )

    records = []

    for row in df.to_dict(orient="records"):
        record = normalize_ipo_gmp_record(row, source_url)

        if record:
            records.append(record)

    return list({
        record["ipo_name"].lower(): record
        for record in records
        if record.get("ipo_name")
    }.values())


def insert_ipo_gmp_scraper_records(
    conn,
    records: List[dict],
    source_sync_id: str
) -> int:
    rows = list({
        safe_strip(record.get("ipo_name")).lower(): record
        for record in records
        if safe_strip(record.get("ipo_name"))
    }.values())

    if not rows:
        return 0

    for row in rows:
        row["data_hash"] = get_ipo_gmp_record_hash(row)

    conn.executemany("""
        INSERT OR REPLACE INTO ipo_gmp_scraper (
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            source_sync_id,
            data_hash,
            scraped_at,
            updated_at
        )
        SELECT
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            TRY_CAST(? AS JSON),
            ?,
            ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            source_sync_id,
            row.get("data_hash")
        )
        for row in rows
    ])

    conn.executemany("""
        INSERT INTO ipo_gmp_scraper_snapshots (
            snapshot_id,
            source_sync_id,
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            data_hash,
            scraped_at
        )
        SELECT
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
            ?,
            CURRENT_TIMESTAMP;
    """, [
        (
            str(uuid.uuid4()),
            source_sync_id,
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            row.get("data_hash")
        )
        for row in rows
    ])

    return len(rows)


def sync_ipo_gmp_scraper_service(
    current_user: dict,
    config: Optional[dict] = None,
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
        ensure_upstox_news_ipo_tables(conn)

        payload = config or {}
        source_url = safe_strip(payload.get("source_url")) or IPO_GMP_SCRAPER_URL

        sync_id = create_sync_run(
            conn,
            IPO_GMP_SCRAPER_SYNC_TYPE,
            "running",
            "IPO GMP scraper started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        records = scrape_ipo_gmp_records(source_url=source_url)

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")
        total_records = insert_ipo_gmp_scraper_records(
            conn,
            records,
            sync_id
        )
        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "IPO GMP scraper completed successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "IPO GMP scraper completed successfully.",
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
                "IPO GMP scraper cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "IPO GMP scraper cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"IPO GMP scraper failed: {error.detail}",
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
                f"IPO GMP scraper failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run IPO GMP scraper: {error}"
        )

    finally:
        conn.close()


def get_ipo_gmp_scraper_preview_service(
    search: str = "",
    ipo_status: str = "all",
    ipo_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        ensure_upstox_news_ipo_tables(conn)

        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(ipo_name, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_gmp, '')) LIKE ?
                    OR LOWER(COALESCE(price_band, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_date, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_type, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_status, '')) LIKE ?
                    OR LOWER(COALESCE(last_updated, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if ipo_status != "all":
            where_clauses.append("LOWER(COALESCE(ipo_status, '')) = ?")
            params.append(ipo_status.lower())

        if ipo_type != "all":
            where_clauses.append("LOWER(COALESCE(ipo_type, '')) = ?")
            params.append(ipo_type.lower())

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM ipo_gmp_scraper
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                ipo_name,
                ipo_gmp,
                price_band,
                ipo_date,
                ipo_type,
                ipo_status,
                last_updated,
                source_url,
                scraped_at,
                updated_at
            FROM ipo_gmp_scraper
            {where_sql}
            ORDER BY updated_at DESC, ipo_name
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [
                {
                    "ipo_name": row[0],
                    "ipo_gmp": row[1],
                    "price_band": row[2],
                    "gain": calculate_ipo_gmp_gain(row[1], row[2]),
                    "ipo_date": row[3],
                    "ipo_type": row[4],
                    "ipo_status": row[5],
                    "last_updated": row[6],
                    "source_url": row[7],
                    "scraped_at": str(row[8]) if row[8] else None,
                    "updated_at": str(row[9]) if row[9] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

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

    interval_clauses = []
    params = [
        UPSTOX_PROVIDER,
        source
    ]

    for mode, unit, interval_value in interval_rows:
        interval_clauses.append("""
            (
                candles.candle_mode = ?
                AND candles.unit = ?
                AND candles.interval_value = ?
            )
        """)
        params.extend([mode, unit, interval_value])

    instrument_filter_sql = ""

    if len(instrument_keys) <= OHLCV_SAVED_BOUNDS_INSTRUMENT_FILTER_LIMIT:
        instrument_placeholders = ", ".join(["?"] * len(instrument_keys))
        instrument_filter_sql = (
            f" AND candles.instrument_key IN ({instrument_placeholders})"
        )
        params.extend(instrument_keys)

    rows = conn.execute(f"""
            SELECT
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value,
                MIN(candles.candle_date) AS min_date,
                MAX(candles.candle_date) AS max_date,
                COUNT(1) AS row_count
            FROM upstox_ohlcv_candles candles
            WHERE candles.provider = ?
              AND candles.instrument_source = ?
              AND ({" OR ".join(interval_clauses)})
              {instrument_filter_sql}
            GROUP BY
                candles.candle_mode,
                candles.instrument_key,
                candles.unit,
                candles.interval_value;
        """, params).fetchall()

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
    to_date: date,
    saved_bounds_cache: Optional[dict] = None
) -> bool:
    bounds = get_saved_ohlcv_date_bounds(
        conn=conn,
        source=source,
        mode=mode,
        instrument_key=instrument_key,
        unit=unit,
        interval_value=interval_value,
        saved_bounds_cache=saved_bounds_cache
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
                                to_date=chunk_to,
                                saved_bounds_cache=saved_bounds_cache
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

def build_market_holidays_preview_filters(
    search: str,
    holiday_type: str,
    exchange: str,
    trading_status: str
):
    where_clauses = []
    params = []

    clean_search = search.strip() if search else ""
    clean_holiday_type = holiday_type.strip() if holiday_type else "all"
    clean_exchange = exchange.strip() if exchange else "all"
    clean_trading_status = trading_status.strip() if trading_status else "all"

    if clean_search:
        where_clauses.append("""
            (
                LOWER(COALESCE(description, '')) LIKE ?
                OR LOWER(COALESCE(holiday_type, '')) LIKE ?
                OR LOWER(CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR)) LIKE ?
                OR LOWER(CAST(COALESCE(open_exchanges, '[]') AS VARCHAR)) LIKE ?
                OR CAST(holiday_date AS VARCHAR) LIKE ?
            )
        """)

        search_value = f"%{clean_search.lower()}%"
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            f"%{clean_search}%"
        ])

    if clean_holiday_type != "all":
        where_clauses.append("holiday_type = ?")
        params.append(clean_holiday_type)

    if clean_exchange != "all":
        exchange_value = f"%{clean_exchange}%"
        where_clauses.append("""
            (
                CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR) LIKE ?
                OR CAST(COALESCE(open_exchanges, '[]') AS VARCHAR) LIKE ?
            )
        """)
        params.extend([exchange_value, exchange_value])

    if clean_trading_status == "open":
        where_clauses.append("is_trading_day = TRUE")

    if clean_trading_status == "closed":
        where_clauses.append("is_trading_day = FALSE")

    where_sql = ""

    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    return where_sql, params


def row_to_market_holidays_preview(row):
    return {
        "holiday_date": str(row[0]) if row[0] else None,
        "description": row[1],
        "holiday_type": row[2],
        "closed_exchanges": row[3],
        "open_exchanges": row[4],
        "is_trading_day": bool(row[5]),
        "source_provider": row[6],
        "synced_at": str(row[7]) if row[7] else None,
        "updated_at": str(row[8]) if row[8] else None
    }


def get_upstox_market_holidays_preview_service(
    search: str = "",
    holiday_type: str = "all",
    exchange: str = "all",
    trading_status: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size

        where_sql, params = build_market_holidays_preview_filters(
            search=search,
            holiday_type=holiday_type,
            exchange=exchange,
            trading_status=trading_status
        )

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM upstox_market_holidays
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                holiday_date,
                description,
                holiday_type,
                CAST(COALESCE(closed_exchanges, '[]') AS VARCHAR) AS closed_exchanges,
                CAST(COALESCE(open_exchanges, '[]') AS VARCHAR) AS open_exchanges,
                is_trading_day,
                source_provider,
                synced_at,
                updated_at
            FROM upstox_market_holidays
            {where_sql}
            ORDER BY holiday_date DESC
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [row_to_market_holidays_preview(row) for row in rows],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

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
