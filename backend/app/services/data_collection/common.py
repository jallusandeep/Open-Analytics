# backend\app\services\data_collection\common.py
# Shared imports, constants, DB helpers, run-state helpers, cancellation, rate limiting.

import gzip
import hashlib
import json
import re
import shutil
import time
import email.utils
from collections import deque
from io import StringIO
import uuid
import pandas as pd
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
OHLCV_CHUNK_STATUS_SCHEMA_READY = False


REQUEST_TIMEOUT_SECONDS = 180
UPSTOX_STANDARD_MAX_REQUESTS_PER_SECOND = 50
UPSTOX_STANDARD_MAX_REQUESTS_PER_MINUTE = 500
UPSTOX_STANDARD_MAX_REQUESTS_PER_30_MINUTES = 2000
UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS = 0.05
UPSTOX_RATE_LIMIT_DEFAULT_429_SLEEP_SECONDS = 1800
UPSTOX_RATE_LIMIT_MAX_RETRY_SLEEP_SECONDS = 1800
STALE_RUNNING_RUN_HOURS = 2
STALE_RUNNING_HEARTBEAT_MINUTES = 15
SYNC_RUN_HEARTBEAT_SECONDS = 30
DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 4

CANCEL_SIGNAL_DIR = APP_ROOT / "runtime"
CANCEL_SIGNAL_FILE = CANCEL_SIGNAL_DIR / "upstox_data_collection.cancel"
SYNC_RUN_HEARTBEATS: Dict[str, datetime] = {}

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
OHLCV_SAVED_BOUNDS_INSTRUMENT_FILTER_LIMIT = 1000000

OHLCV_ALLOWED_SOURCES = {OHLCV_CURRENT_SOURCE, OHLCV_EXPIRED_SOURCE}
OHLCV_ALLOWED_MODES = {OHLCV_HISTORICAL_MODE, OHLCV_INTRADAY_MODE}
OHLCV_DEFAULT_SOURCES = [OHLCV_CURRENT_SOURCE]
OHLCV_DEFAULT_MODES = [OHLCV_HISTORICAL_MODE]
OHLCV_DEFAULT_INTERVALS = ["day"]
OHLCV_DEFAULT_BATCH_SIZE = 25
OHLCV_DEFAULT_REQUEST_DELAY_MS = 500
OHLCV_DEFAULT_BATCH_DELAY_SECONDS = 2
OHLCV_DEFAULT_RETRY_COUNT = 3
OHLCV_REQUEST_TIMEOUT_SECONDS = 30
OHLCV_CURRENT_HISTORY_START_DATE = date(2000, 1, 1)
OHLCV_INTRADAY_HISTORY_START_DATE = date(2022, 1, 1)
OHLCV_CURRENT_DAILY_MAX_DAYS = 3653
OHLCV_CURRENT_INTRADAY_SMALL_MAX_DAYS = 31
OHLCV_CURRENT_INTRADAY_LARGE_MAX_DAYS = 92
OHLCV_EXPIRED_MAX_DAYS = 3650
EQUITY_STOCK_ISIN_PREFIX = "INE"
OHLCV_CURRENT_NSE_EQUITY_TYPES = ("BE", "BZ", "EQ", "EQUITY", "SM", "ST")
OHLCV_CURRENT_BSE_EQUITY_TYPES = ("A", "B", "E", "EQ", "EQUITY", "M", "MS", "MT", "P", "T", "TS", "X", "XT", "Z", "ZP")

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

    def wait_for_slot(self, heartbeat_callback: Optional[Callable[[], None]] = None):
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
            sleep_with_heartbeat(sleep_seconds, heartbeat_callback)


def get_http_exception_header(error: HTTPException, header_name: str) -> Optional[str]:
    headers = getattr(error, "headers", None) or {}
    clean_header_name = header_name.lower()

    for key, value in headers.items():
        if str(key).lower() == clean_header_name:
            return str(value)

    return None


def parse_retry_after_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None

    clean_value = str(value).strip()

    try:
        return max(0.0, float(clean_value))
    except ValueError:
        pass

    try:
        retry_at = email.utils.parsedate_to_datetime(clean_value)
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=datetime.now().astimezone().tzinfo)

        return max(0.0, (retry_at - datetime.now(retry_at.tzinfo)).total_seconds())
    except Exception:
        return None


def parse_rate_limit_reset_seconds(value: Optional[str]) -> Optional[float]:
    if not value:
        return None

    clean_value = str(value).strip()

    try:
        numeric_value = float(clean_value)
    except ValueError:
        return parse_retry_after_seconds(clean_value)

    now_epoch = time.time()

    if numeric_value > 10_000_000_000:
        numeric_value = numeric_value / 1000

    if numeric_value > now_epoch:
        return max(0.0, numeric_value - now_epoch)

    return max(0.0, numeric_value)


def get_rate_limit_retry_sleep_seconds(error: HTTPException, fallback_seconds: float) -> float:
    header_values = [
        parse_retry_after_seconds(get_http_exception_header(error, "Retry-After")),
        parse_rate_limit_reset_seconds(get_http_exception_header(error, "X-RateLimit-Reset")),
        parse_rate_limit_reset_seconds(get_http_exception_header(error, "RateLimit-Reset"))
    ]
    valid_values = [value for value in header_values if value is not None]

    if valid_values:
        return min(
            max(valid_values) + UPSTOX_RATE_LIMIT_SAFETY_SLEEP_SECONDS,
            UPSTOX_RATE_LIMIT_MAX_RETRY_SLEEP_SECONDS
        )

    if error.status_code == 429:
        return min(
            UPSTOX_RATE_LIMIT_DEFAULT_429_SLEEP_SECONDS,
            UPSTOX_RATE_LIMIT_MAX_RETRY_SLEEP_SECONDS
        )

    return min(fallback_seconds, UPSTOX_RATE_LIMIT_MAX_RETRY_SLEEP_SECONDS)


def is_upstox_auth_token_error(error: HTTPException) -> bool:
    error_text = str(getattr(error, "detail", "") or "").lower()

    return (
        error.status_code in (401, 403)
        or "udapi100050" in error_text
        or "invalid token" in error_text
        or "token is invalid" in error_text
        or "token expired" in error_text
        or "expired token" in error_text
        or "unauthorized" in error_text
        or "unauthorised" in error_text
    )


def sleep_with_heartbeat(seconds: float, heartbeat_callback: Optional[Callable[[], None]] = None):
    remaining_seconds = max(0.0, float(seconds or 0))

    while remaining_seconds > 0:
        if heartbeat_callback:
            heartbeat_callback()

        sleep_seconds = min(1, remaining_seconds)
        time.sleep(sleep_seconds)
        remaining_seconds -= sleep_seconds

    if heartbeat_callback:
        heartbeat_callback()


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
          AND (
              COALESCE(last_heartbeat_at, started_at)
                  < CURRENT_TIMESTAMP - (? * INTERVAL '1 minute')
              OR started_at < CURRENT_TIMESTAMP - (? * INTERVAL '1 hour')
          );
    """, [STALE_RUNNING_HEARTBEAT_MINUTES, STALE_RUNNING_RUN_HOURS])

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
            last_heartbeat_at,
            finished_at,
            duration_seconds,
            message,
            total_records,
            trigger_source,
            triggered_by_id,
            triggered_by_name,
            triggered_by_role
        )
        VALUES (?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, NULL, ?, 0, ?, ?, ?, ?);
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


def heartbeat_sync_run(conn, sync_id: Optional[str], force: bool = False):
    if not sync_id:
        return

    now = datetime.now()
    last_heartbeat = SYNC_RUN_HEARTBEATS.get(sync_id)

    if (
        not force
        and last_heartbeat
        and (now - last_heartbeat).total_seconds() < SYNC_RUN_HEARTBEAT_SECONDS
    ):
        return

    conn.execute("""
        UPDATE upstox_sync_runs
        SET last_heartbeat_at = CURRENT_TIMESTAMP
        WHERE sync_id = ?
          AND status IN ('running', 'cancel_requested');
    """, [sync_id])
    conn.commit()
    SYNC_RUN_HEARTBEATS[sync_id] = now


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
            last_heartbeat_at = CURRENT_TIMESTAMP,
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
    SYNC_RUN_HEARTBEATS.pop(sync_id, None)


def check_sync_cancelled(conn, sync_id: str):
    heartbeat_sync_run(conn, sync_id)

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
