import threading
import base64
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.database import get_connection
from app.services.connection_service import (
    get_app_metadata_value,
    get_ist_now,
    get_upstox_connection_raw,
    parse_db_datetime,
    safe_strip,
    set_app_metadata_value,
    upstox_access_token_request_post
)
from app.telegram_alerts_msg.message_templates import (
    build_upstox_access_token_reminder_message,
    build_upstox_analytical_token_reminder_message
)
from app.telegram_alerts_msg.telegram_sender import (
    get_admin_super_admin_telegram_chat_ids,
    get_telegram_bot_token,
    send_telegram_message
)


IST_TIMEZONE = "Asia/Kolkata"
IST_TZINFO = timezone(timedelta(hours=5, minutes=30))

UPSTOX_TOKEN_CHECK_HOUR = 3
UPSTOX_TOKEN_CHECK_MINUTE = 30
UPSTOX_REMINDER_INTERVAL_SECONDS = 60 * 60
UPSTOX_TOKEN_EXPIRY_WARNING_DAYS = 1
UPSTOX_ANALYTICAL_TOKEN_VALIDITY_DAYS = 365

_connection_scheduler_thread = None
_connection_scheduler_stop_event = threading.Event()
_connection_scheduler_lock = threading.Lock()


def get_connection_scheduler_ist_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(IST_TIMEZONE))
    except ZoneInfoNotFoundError:
        return datetime.now(IST_TZINFO)


def get_next_upstox_check_time(now: datetime | None = None) -> datetime:
    current_time = now or get_connection_scheduler_ist_now()

    next_check = current_time.replace(
        hour=UPSTOX_TOKEN_CHECK_HOUR,
        minute=UPSTOX_TOKEN_CHECK_MINUTE,
        second=0,
        microsecond=0
    )

    if current_time >= next_check:
        next_check = next_check + timedelta(days=1)

    return next_check


def get_seconds_until_next_upstox_check(now: datetime | None = None) -> int:
    current_time = now or get_connection_scheduler_ist_now()
    next_check = get_next_upstox_check_time(current_time)
    wait_seconds = int((next_check - current_time).total_seconds())

    return max(wait_seconds, 60)


def parse_jwt_expiry(token: str):
    token_value = safe_strip(token)

    if not token_value:
        return None


def get_analytical_token_expiry(token: str, token_updated_at):
    token_value = safe_strip(token)

    if not token_value:
        return None

    jwt_expiry = parse_jwt_expiry(token_value)

    if jwt_expiry:
        return jwt_expiry

    saved_at = parse_db_datetime(token_updated_at) or get_ist_now()

    return saved_at + timedelta(days=UPSTOX_ANALYTICAL_TOKEN_VALIDITY_DAYS)

    try:
        parts = token_value.split(".")

        if len(parts) < 2:
            return None

        payload = parts[1]
        payload += "=" * (-len(payload) % 4)
        decoded_payload = base64.urlsafe_b64decode(payload.encode("utf-8"))
        data = json.loads(decoded_payload.decode("utf-8"))
        expires_at = data.get("exp")

        if not expires_at:
            return None

        parsed_date = datetime.fromtimestamp(
            int(expires_at),
            ZoneInfo(IST_TIMEZONE)
        )

        return parsed_date.replace(tzinfo=None)

    except Exception:
        return None


def get_token_expiry_state(token: str, expiry_date, now: datetime):
    if not token:
        return "missing"

    if not expiry_date:
        return "expiry_missing"

    if expiry_date <= now:
        return "expired"

    if expiry_date <= now + timedelta(days=UPSTOX_TOKEN_EXPIRY_WARNING_DAYS):
        return "expires_soon"

    return "valid"


def format_token_status(label: str, state: str, expiry_date) -> str:
    expiry_label = (
        expiry_date.strftime("%d %b %Y, %I:%M %p")
        if expiry_date
        else "--"
    )

    if state == "missing":
        return f"{label}: missing"

    if state == "expiry_missing":
        return f"{label}: saved, but expiry time is missing"

    if state == "expired":
        return f"{label}: expired at {expiry_label} IST"

    if state == "expires_soon":
        return f"{label}: expires at {expiry_label} IST"

    return f"{label}: valid until {expiry_label} IST"


def get_upstox_token_status():
    conn = get_connection()

    try:
        upstox_connection = get_upstox_connection_raw(conn)

        if not upstox_connection:
            return {
                "configured": False,
                "valid": False,
                "message": "Upstox connection is not configured."
            }

        analytical_token = safe_strip(upstox_connection[5])
        access_token = safe_strip(upstox_connection[6])
        access_expiry_value = upstox_connection[7]
        analytical_token_updated_at = upstox_connection[12]
        access_expiry_date = parse_db_datetime(access_expiry_value)
        analytical_expiry_date = get_analytical_token_expiry(
            token=analytical_token,
            token_updated_at=analytical_token_updated_at
        )
        now = get_ist_now()

        access_state = get_token_expiry_state(
            token=access_token,
            expiry_date=access_expiry_date,
            now=now
        )
        analytical_state = get_token_expiry_state(
            token=analytical_token,
            expiry_date=analytical_expiry_date,
            now=now
        )

        token_is_valid = (
            access_state in ("valid", "expires_soon")
            and analytical_state in ("valid", "missing")
        )

        return {
            "configured": True,
            "valid": token_is_valid,
            "message": "Upstox tokens are valid." if token_is_valid else "Upstox token requires update."
        }

    finally:
        conn.close()


def notify_admin_super_admins_upstox_token_expiry_service():
    conn = get_connection()

    try:
        upstox_connection = get_upstox_connection_raw(conn)

        if not upstox_connection:
            return {
                "status": "skipped",
                "message": "Upstox connection is not configured.",
                "token_valid": False
            }

        api_key = safe_strip(upstox_connection[2])
        api_secret = safe_strip(upstox_connection[3])
        analytical_token = safe_strip(upstox_connection[5])
        access_token = safe_strip(upstox_connection[6])
        access_expiry_value = upstox_connection[7]
        analytical_token_updated_at = upstox_connection[12]

        now = get_ist_now()
        access_expiry_date = parse_db_datetime(access_expiry_value)
        analytical_expiry_date = get_analytical_token_expiry(
            token=analytical_token,
            token_updated_at=analytical_token_updated_at
        )

        access_state = get_token_expiry_state(
            token=access_token,
            expiry_date=access_expiry_date,
            now=now
        )
        analytical_state = get_token_expiry_state(
            token=analytical_token,
            expiry_date=analytical_expiry_date,
            now=now
        )

        access_needs_reminder = access_state in (
            "missing",
            "expiry_missing",
            "expired"
        )
        analytical_needs_reminder = analytical_state not in ("valid", "missing")

        if not access_needs_reminder and not analytical_needs_reminder:
            return {
                "status": "skipped",
                "message": "Upstox tokens are still valid.",
                "token_valid": True
            }

        access_last_sent_value = get_app_metadata_value(
            conn,
            "upstox_access_token_reminder_last_sent_at"
        )
        access_last_sent_at = parse_db_datetime(access_last_sent_value)

        analytical_last_sent_value = get_app_metadata_value(
            conn,
            "upstox_analytical_token_reminder_last_sent_at"
        )
        analytical_last_sent_at = parse_db_datetime(analytical_last_sent_value)

        access_should_send = access_needs_reminder and not (
            access_last_sent_at
            and now - access_last_sent_at < timedelta(hours=1)
        )

        analytical_should_send = analytical_needs_reminder and not (
            analytical_last_sent_at
            and now - analytical_last_sent_at < timedelta(hours=1)
        )

        if not access_should_send and not analytical_should_send:
            conn.commit()

            return {
                "status": "skipped",
                "message": "Upstox token reminder already sent within the last hour.",
                "token_valid": False
            }

        auto_request_status = "skipped"
        auto_request_message = "Upstox API key or API secret is missing."

        if access_should_send and api_key and api_secret:
            try:
                token_request_response = upstox_access_token_request_post(
                    client_id=api_key,
                    client_secret=api_secret
                )

                auto_request_status = "success"
                auto_request_message = (
                    token_request_response.get("message")
                    or "Upstox access token approval request triggered."
                )

                set_app_metadata_value(
                    conn,
                    "upstox_access_token_request_last_triggered_at",
                    now.strftime("%Y-%m-%d %H:%M:%S")
                )

            except HTTPException as request_error:
                request_detail = request_error.detail

                if isinstance(request_detail, dict):
                    auto_request_message = (
                        request_detail.get("message")
                        or str(request_detail)
                    )
                else:
                    auto_request_message = str(request_detail)

                auto_request_status = "failed"

            except Exception as request_error:
                auto_request_status = "failed"
                auto_request_message = str(request_error)

        try:
            bot_token = get_telegram_bot_token(conn)
        except HTTPException:
            conn.commit()

            return {
                "status": "skipped",
                "message": "Telegram bot is not configured. Upstox token reminder check was still processed.",
                "token_valid": False
            }

        chat_ids = get_admin_super_admin_telegram_chat_ids(conn)

        if not chat_ids:
            conn.commit()

            return {
                "status": "skipped",
                "message": "No connected admin/super admin Telegram users found.",
                "token_valid": False
            }

        reminder_messages = []

        if access_should_send:
            access_status_text = format_token_status(
                label="Access token",
                state=access_state,
                expiry_date=access_expiry_date
            )

            if auto_request_status == "success":
                approval_text = (
                    "Backend has triggered the Upstox access token approval request. "
                    "Please approve it from Upstox app/web or WhatsApp."
                )
            else:
                approval_text = (
                    "Backend could not trigger the Upstox approval request automatically. "
                    "Please open Open Analytics > Connections and generate the Upstox access token."
                )

            reminder_messages.append(
                build_upstox_access_token_reminder_message(
                    token_status_text=access_status_text,
                    approval_text=approval_text,
                    auto_request_status=auto_request_status,
                    auto_request_message=auto_request_message
                )
            )

            set_app_metadata_value(
                conn,
                "upstox_access_token_reminder_last_sent_at",
                now.strftime("%Y-%m-%d %H:%M:%S")
            )

        if analytical_should_send:
            analytical_status_text = format_token_status(
                label="Analytical token",
                state=analytical_state,
                expiry_date=analytical_expiry_date
            )

            reminder_messages.append(
                build_upstox_analytical_token_reminder_message(
                    token_status_text=analytical_status_text
                )
            )

            set_app_metadata_value(
                conn,
                "upstox_analytical_token_reminder_last_sent_at",
                now.strftime("%Y-%m-%d %H:%M:%S")
            )

        sent_count = 0

        for message in reminder_messages:
            for chat_id in chat_ids:
                try:
                    send_telegram_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message=message
                    )
                    sent_count += 1
                except Exception as error:
                    print(f"Unable to send Upstox token Telegram reminder: {error}")

        conn.commit()

        return {
            "status": "success",
            "message": f"Upstox token reminder sent to {sent_count} admin/super admin delivery target(s).",
            "token_valid": False
        }

    except HTTPException:
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to notify Upstox access token expiry: {e}"
        )

    finally:
        conn.close()


def execute_connection_scheduler_once():
    if not _connection_scheduler_lock.acquire(blocking=False):
        return {
            "status": "skipped",
            "message": "Connection scheduler is already running.",
            "token_valid": False
        }

    try:
        return notify_admin_super_admins_upstox_token_expiry_service()
    except Exception as error:
        print(f"Connection scheduler tick failed: {error}")

        return {
            "status": "failed",
            "message": str(error),
            "token_valid": False
        }
    finally:
        _connection_scheduler_lock.release()


def connection_scheduler_loop():
    print("Connection scheduler started.")

    while not _connection_scheduler_stop_event.is_set():
        now = get_connection_scheduler_ist_now()
        today_check_time = now.replace(
            hour=UPSTOX_TOKEN_CHECK_HOUR,
            minute=UPSTOX_TOKEN_CHECK_MINUTE,
            second=0,
            microsecond=0
        )

        if now < today_check_time:
            wait_seconds = get_seconds_until_next_upstox_check(now)
            _connection_scheduler_stop_event.wait(wait_seconds)
            continue

        result = execute_connection_scheduler_once() or {}

        if result.get("token_valid"):
            wait_seconds = get_seconds_until_next_upstox_check()
        else:
            wait_seconds = UPSTOX_REMINDER_INTERVAL_SECONDS

        _connection_scheduler_stop_event.wait(wait_seconds)

    print("Connection scheduler stopped.")


def start_connection_scheduler():
    global _connection_scheduler_thread

    if _connection_scheduler_thread and _connection_scheduler_thread.is_alive():
        return

    _connection_scheduler_stop_event.clear()

    _connection_scheduler_thread = threading.Thread(
        target=connection_scheduler_loop,
        name="open-analytics-connection-scheduler",
        daemon=True
    )

    _connection_scheduler_thread.start()


def stop_connection_scheduler():
    global _connection_scheduler_thread

    _connection_scheduler_stop_event.set()

    if _connection_scheduler_thread and _connection_scheduler_thread.is_alive():
        _connection_scheduler_thread.join(timeout=5)

    _connection_scheduler_thread = None
