import threading
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
    trigger_upstox_access_token_request
)
from app.telegram_alerts_msg.message_templates import (
    build_upstox_access_token_reminder_message
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

        access_token = safe_strip(upstox_connection[6])
        expiry_value = upstox_connection[7]
        expiry_date = parse_db_datetime(expiry_value)
        now = get_ist_now()

        token_is_missing = not access_token
        token_expiry_missing = bool(access_token and not expiry_date)
        token_is_expired = expiry_date is not None and expiry_date <= now

        token_is_valid = (
            not token_is_missing
            and not token_expiry_missing
            and not token_is_expired
        )

        return {
            "configured": True,
            "valid": token_is_valid,
            "message": "Upstox access token is valid." if token_is_valid else "Upstox access token requires update."
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
        access_token = safe_strip(upstox_connection[6])
        expiry_value = upstox_connection[7]

        now = get_ist_now()
        expiry_date = parse_db_datetime(expiry_value)

        token_is_missing = not access_token
        token_expiry_missing = bool(access_token and not expiry_date)
        token_is_expired = expiry_date is not None and expiry_date <= now

        if not token_is_missing and not token_expiry_missing and not token_is_expired:
            return {
                "status": "skipped",
                "message": "Upstox access token is still valid.",
                "token_valid": True
            }

        auto_request_status = "skipped"
        auto_request_message = "Upstox API key or API secret is missing."
        request_last_attempted_value = get_app_metadata_value(
            conn,
            "upstox_access_token_request_last_attempted_at"
        )
        request_last_attempted_at = parse_db_datetime(request_last_attempted_value)
        should_request_token = not (
            request_last_attempted_at
            and now - request_last_attempted_at < timedelta(hours=1)
        )

        if should_request_token and api_key and api_secret:
            try:
                token_request_response = trigger_upstox_access_token_request(
                    conn=conn,
                    client_id=api_key,
                    client_secret=api_secret
                )

                auto_request_status = "success"
                auto_request_message = token_request_response.get("message") or (
                    "Upstox access token approval request triggered."
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

        elif api_key and api_secret:
            auto_request_message = "Upstox access token request already attempted within the last hour."

        last_sent_value = get_app_metadata_value(
            conn,
            "upstox_access_token_reminder_last_sent_at"
        )
        last_sent_at = parse_db_datetime(last_sent_value)

        if last_sent_at and now - last_sent_at < timedelta(hours=1):
            conn.commit()

            return {
                "status": auto_request_status,
                "message": (
                    "Upstox token request check processed. Telegram reminder "
                    f"already sent within the last hour. Request status: {auto_request_message}"
                ),
                "token_valid": False
            }

        set_app_metadata_value(
            conn,
            "upstox_access_token_reminder_last_sent_at",
            now.strftime("%Y-%m-%d %H:%M:%S")
        )

        try:
            bot_token = get_telegram_bot_token(conn)
        except HTTPException:
            conn.commit()

            return {
                "status": "skipped",
                "message": "Telegram bot is not configured. Upstox auto request check was still processed.",
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

        if token_is_missing:
            token_status_text = "missing"
        elif token_expiry_missing:
            token_status_text = "saved, but expiry time is missing"
        else:
            token_status_text = (
                f"expired at {expiry_date.strftime('%d %b %Y, %I:%M %p')} IST"
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

        message = build_upstox_access_token_reminder_message(
            token_status_text=token_status_text,
            approval_text=approval_text,
            auto_request_status=auto_request_status,
            auto_request_message=auto_request_message
        )

        sent_count = 0

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
            "message": f"Upstox access token reminder sent to {sent_count} admin/super admin user(s).",
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
