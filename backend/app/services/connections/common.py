import json
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.config import settings
from app.database import get_connection
from app.telegram_alerts_msg.message_templates import (
    build_telegram_connected_message,
    build_telegram_test_message,
    build_upstox_token_saved_from_webhook_message
)
from app.telegram_alerts_msg.telegram_sender import (
    get_admin_super_admin_telegram_chat_ids,
    get_telegram_bot_info,
    get_telegram_bot_token,
    get_telegram_updates,
    get_user_telegram_connection_raw,
    send_telegram_message,
    clear_telegram_webhook,
    validate_telegram_bot_token
)


UPSTOX_PROVIDER = "upstox"
TELEGRAM_PROVIDER = "telegram"

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_AUTHORIZE_URL = f"{UPSTOX_BASE_URL}/login/authorization/dialog"
UPSTOX_TOKEN_URL = f"{UPSTOX_BASE_URL}/login/authorization/token"
UPSTOX_ACCESS_TOKEN_REQUEST_BASE_URL = (
    "https://api.upstox.com/v3/login/auth/token/request"
)
UPSTOX_MARKET_HOLIDAYS_PATH = "/market/holidays"

UPSTOX_EXPIRED_PERMISSION_TEST_PATH = "/expired-instruments/expiries"
UPSTOX_EXPIRED_PERMISSION_TEST_KEY = "NSE_INDEX|Nifty 50"

UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL = (
    f"{UPSTOX_BASE_URL}/market-quote/instruments/exchange"
)

UPSTOX_EXPIRED_OPTION_CONTRACT_PATH = "/expired-instruments/option/contract"
UPSTOX_EXPIRED_FUTURE_CONTRACT_PATH = "/expired-instruments/future/contract"
UPSTOX_EXPIRED_HISTORICAL_CANDLE_PATH = "/expired-instruments/historical-candle"

IST_TIMEZONE = "Asia/Kolkata"
UPSTOX_REMINDER_START_HOUR = 6
UPSTOX_REMINDER_END_HOUR = 22
UPSTOX_REMINDER_REPEAT_MINUTES = 60
REQUEST_TIMEOUT_SECONDS = 30




def safe_strip(value):
    return value.strip() if isinstance(value, str) else ""


def get_upstox_notifier_webhook_url() -> str:
    return safe_strip(settings.UPSTOX_NOTIFIER_WEBHOOK_URL)


def mask_identifier(value: str) -> str:
    clean_value = safe_strip(value)

    if not clean_value:
        return ""

    if len(clean_value) <= 8:
        return "***"

    return f"***{clean_value[-8:]}"


def get_ist_now():
    try:
        return datetime.now(ZoneInfo(IST_TIMEZONE)).replace(tzinfo=None)
    except ZoneInfoNotFoundError:
        return datetime.utcnow() + timedelta(hours=5, minutes=30)


def get_next_upstox_access_token_expiry(value: datetime) -> datetime:
    expiry_time = value.replace(hour=3, minute=30, second=0, microsecond=0)

    if value >= expiry_time:
        expiry_time = expiry_time + timedelta(days=1)

    return expiry_time


def normalize_upstox_token(access_token: str) -> str:
    token = safe_strip(access_token)

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return token


def get_upstox_save_status(
    api_key: str,
    api_secret: str,
    redirect_url: str,
    analytical_token: str,
    access_token: str
):
    has_analytical_token = bool(analytical_token)
    has_access_token = bool(access_token)

    if has_analytical_token or has_access_token:
        return "limited"

    return "saved"


def parse_db_datetime(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value

    clean_value = str(value).strip()

    for date_format in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d/%m/%Y"
    ):
        try:
            parsed_date = datetime.strptime(clean_value, date_format)

            if date_format in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
                parsed_date = parsed_date.replace(hour=23, minute=59, second=59)

            return parsed_date
        except ValueError:
            pass

    try:
        parsed_date = datetime.fromisoformat(clean_value.replace("Z", "+00:00"))

        if parsed_date.tzinfo is not None:
            parsed_date = parsed_date.astimezone(ZoneInfo(IST_TIMEZONE))
            parsed_date = parsed_date.replace(tzinfo=None)

        return parsed_date
    except Exception:
        return None


def parse_upstox_epoch_millis(value):
    clean_value = safe_strip(value)

    if not clean_value:
        return None

    try:
        timestamp_millis = int(clean_value)
    except ValueError:
        return parse_db_datetime(clean_value)

    try:
        parsed_date = datetime.fromtimestamp(
            timestamp_millis / 1000,
            ZoneInfo(IST_TIMEZONE)
        )
        return parsed_date.replace(tzinfo=None)
    except Exception:
        return None


def connection_to_response(row):
    if not row:
        return None

    (
        connection_id,
        provider,
        api_key,
        api_secret,
        redirect_url,
        analytical_token,
        access_token,
        access_token_expires_at,
        connection_status,
        last_tested_at,
        created_at,
        updated_at,
        analytical_token_updated_at
    ) = row

    return {
        "connection_id": connection_id,
        "provider": provider,
        "api_key": api_key,
        "redirect_url": redirect_url,
        "connection_status": connection_status,
        "has_api_secret": bool(api_secret),
        "has_analytical_token": bool(analytical_token),
        "has_access_token": bool(access_token),
        "access_token_expires_at": (
            str(access_token_expires_at) if access_token_expires_at else None
        ),
        "last_tested_at": str(last_tested_at) if last_tested_at else None,
        "created_at": str(created_at) if created_at else None,
        "updated_at": str(updated_at) if updated_at else None
    }


def get_connection_raw_by_provider(conn, provider: str):
    return conn.execute("""
        SELECT
            connection_id,
            provider,
            api_key,
            api_secret,
            redirect_url,
            analytical_token,
            access_token,
            access_token_expires_at,
            connection_status,
            last_tested_at,
            created_at,
            updated_at,
            analytical_token_updated_at
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [provider]).fetchone()


def get_upstox_connection_raw(conn):
    return get_connection_raw_by_provider(conn, UPSTOX_PROVIDER)


def get_telegram_connection_raw(conn):
    return get_connection_raw_by_provider(conn, TELEGRAM_PROVIDER)
