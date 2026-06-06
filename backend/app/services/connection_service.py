import json
import logging
import uuid
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.repositories.app_metadata_repository import AppMetadataRepository
from app.repositories.base_repository import db_connection
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.user_telegram_repository import UserTelegramRepository

logger = logging.getLogger(__name__)

connection_repo = ConnectionRepository()
user_telegram_repo = UserTelegramRepository()
app_metadata_repo = AppMetadataRepository()


UPSTOX_PROVIDER = "upstox"
TELEGRAM_PROVIDER = "telegram"

UPSTOX_BASE_URL = "https://api.upstox.com/v2"
UPSTOX_AUTHORIZE_URL = f"{UPSTOX_BASE_URL}/login/authorization/dialog"
UPSTOX_TOKEN_URL = f"{UPSTOX_BASE_URL}/login/authorization/token"
UPSTOX_ACCESS_TOKEN_REQUEST_BASE_URL = (
    "https://api.upstox.com/v3/login/auth/token/request"
)

UPSTOX_EXPIRED_PERMISSION_TEST_PATH = "/expired-instruments/expiries"
UPSTOX_EXPIRED_PERMISSION_TEST_KEY = "NSE_INDEX|Nifty 50"

UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL = (
    f"{UPSTOX_BASE_URL}/market-quote/instruments/exchange"
)

UPSTOX_EXPIRED_OPTION_CONTRACT_PATH = "/expired-instruments/option/contract"
UPSTOX_EXPIRED_FUTURE_CONTRACT_PATH = "/expired-instruments/future/contract"
UPSTOX_EXPIRED_HISTORICAL_CANDLE_PATH = "/expired-instruments/historical-candle"

IST_TIMEZONE = "Asia/Kolkata"
REQUEST_TIMEOUT_SECONDS = 30


def safe_strip(value):
    return value.strip() if isinstance(value, str) else ""


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
    has_api_credentials = bool(api_key and api_secret and redirect_url)
    has_analytical_token = bool(analytical_token)
    has_access_token = bool(access_token)

    if has_api_credentials and has_access_token:
        return "connected"

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
        updated_at
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
    return connection_repo.get_by_provider(conn, provider)


def get_upstox_connection_raw(conn):
    return connection_repo.get_upstox(conn)


def get_telegram_connection_raw(conn):
    return connection_repo.get_telegram(conn)


def list_connections_service():
    logger.info("Listing external connections")

    with db_connection() as conn:
        rows = connection_repo.list_active(conn)

    return {
        "connections": [connection_to_response(row) for row in rows]
    }


def parse_upstox_error(error_body: str):
    try:
        payload = json.loads(error_body)
    except Exception:
        return {
            "raw": error_body,
            "error_code": None,
            "message": error_body
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


def is_expired_permission_error(error_code, message: str) -> bool:
    lowered_message = (message or "").lower()

    return (
        error_code == "UDAPI100067"
        or "read only token" in lowered_message
        or "permission" in lowered_message
        or "not authorized" in lowered_message
        or "not authorised" in lowered_message
        or "scope" in lowered_message
        or "upstox plus" in lowered_message
        or "expired instruments api" in lowered_message
    )


def upstox_api_get(access_token: str, path: str, params=None):
    token = normalize_upstox_token(access_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox access token is required."
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
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
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


def upstox_public_api_get(url: str):
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")

        raise HTTPException(
            status_code=error.code,
            detail=f"Unable to download Upstox public instruments: {error_body}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox public instruments CDN: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON received from Upstox public instruments CDN."
        )


def upstox_token_post(payload: dict):
    encoded_payload = urllib.parse.urlencode(payload).encode("utf-8")

    request = urllib.request.Request(
        UPSTOX_TOKEN_URL,
        data=encoded_payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox token API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox token API."
        )


def upstox_access_token_request_post(client_id: str, client_secret: str):
    clean_client_id = safe_strip(client_id)
    clean_client_secret = safe_strip(client_secret)

    if not clean_client_id or not clean_client_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API key and API secret are required to request access token approval."
        )

    request_url = (
        f"{UPSTOX_ACCESS_TOKEN_REQUEST_BASE_URL}/"
        f"{urllib.parse.quote(clean_client_id, safe='')}"
    )

    encoded_payload = json.dumps({
        "client_secret": clean_client_secret
    }).encode("utf-8")

    request = urllib.request.Request(
        request_url,
        data=encoded_payload,
        method="POST",
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "OpenAnalytics/1.0"
        }
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            return json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"],
                "error_code": parsed_error["error_code"],
                "raw": parsed_error["raw"]
            }
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Upstox access token request API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Upstox access token request API."
        )


def handle_upstox_notifier_webhook_service(request):
    client_id = safe_strip(getattr(request, "client_id", None))
    access_token = normalize_upstox_token(getattr(request, "access_token", None))
    token_type = safe_strip(getattr(request, "token_type", None)) or "Bearer"
    message_type = safe_strip(getattr(request, "message_type", None))
    expires_at = safe_strip(getattr(request, "expires_at", None))
    issued_at = safe_strip(getattr(request, "issued_at", None))

    if message_type and message_type != "access_token":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Upstox notifier message type."
        )

    if not client_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox notifier client_id is required."
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox notifier access_token is required."
        )

    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upstox connection is not configured."
            )

        connection_id = existing[0]
        saved_api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])
        redirect_url = safe_strip(existing[4])
        analytical_token = normalize_upstox_token(existing[5])

        if saved_api_key and saved_api_key != client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox notifier client_id does not match saved API key."
            )

        expiry_date = parse_upstox_epoch_millis(expires_at)

        if not expiry_date:
            expiry_date = get_next_upstox_access_token_expiry(get_ist_now())

        issued_date = parse_upstox_epoch_millis(issued_at)
        token_updated_at = issued_date or get_ist_now()

        next_status = get_upstox_save_status(
            api_key=saved_api_key,
            api_secret=api_secret,
            redirect_url=redirect_url,
            analytical_token=analytical_token,
            access_token=access_token
        )

        conn.execute("""
            UPDATE external_connections
            SET
                access_token = ?,
                token_type = ?,
                access_token_expires_at = ?,
                token_updated_at = ?,
                connection_status = ?,
                record_status = 'S',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = 'upstox_notifier'
            WHERE connection_id = ?;
        """, [
            access_token,
            token_type,
            expiry_date.strftime("%Y-%m-%d %H:%M:%S"),
            token_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            next_status,
            connection_id
        ])

        clear_upstox_expiry_notification_marker(conn)

        try:
            bot_token = get_telegram_bot_token(conn)
            chat_ids = get_admin_super_admin_telegram_chat_ids(conn)
            notify_message = build_upstox_token_saved_from_webhook_message(
                expiry_date=expiry_date
            )

            for chat_id in chat_ids:
                try:
                    send_telegram_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message=notify_message
                    )
                except Exception as error:
                    print(f"Unable to send Upstox token saved Telegram alert: {error}")

        except Exception as notify_error:
            print(f"Unable to notify Telegram after Upstox webhook save: {notify_error}")

        conn.commit()

        return {
            "status": "success",
            "message": "Upstox access token received from notifier and saved successfully."
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process Upstox notifier webhook: {e}"
        )

    finally:
        conn.close()


def download_upstox_active_instruments(exchange: str = "complete"):
    exchange_code = safe_strip(exchange) if exchange else "complete"

    if not exchange_code:
        exchange_code = "complete"

    url = f"{UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL}/{exchange_code}.json"
    return upstox_public_api_get(url)


def save_upstox_connection_service(request, current_user):
    api_key = safe_strip(getattr(request, "api_key", None))
    api_secret = safe_strip(getattr(request, "api_secret", None))
    redirect_url = safe_strip(getattr(request, "redirect_url", None))
    analytical_token = normalize_upstox_token(
        getattr(request, "analytical_token", None)
    )
    access_token = normalize_upstox_token(getattr(request, "access_token", None))

    if (
        not api_key
        and not api_secret
        and not redirect_url
        and not analytical_token
        and not access_token
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Enter Upstox API key, API secret, redirect URL, analytical token, "
                "or manual access token."
            )
        )

    has_partial_api_credentials = bool(api_key or api_secret or redirect_url)
    has_complete_api_credentials = bool(api_key and api_secret and redirect_url)

    if has_partial_api_credentials and not has_complete_api_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API key, API secret, and redirect URL are required together."
        )

    saved_at = get_ist_now()
    access_token_expires_at = add_one_year(saved_at).strftime("%Y-%m-%d %H:%M:%S")
    user_id = current_user["user_id"]

    logger.info("Saving Upstox connection: user_id=%s", user_id)

    with db_connection() as conn:
        try:
            existing = connection_repo.get_upstox(conn)

            if existing:
                connection_id = existing[0]
                connection_repo.update_upstox_token(
                    conn,
                    connection_id=connection_id,
                    access_token=access_token,
                    access_token_expires_at=access_token_expires_at,
                    updated_by=user_id,
                )
            else:
                connection_id = str(uuid.uuid4())
                connection_repo.insert_upstox(
                    conn,
                    connection_id=connection_id,
                    access_token=access_token,
                    access_token_expires_at=access_token_expires_at,
                    created_by=user_id,
                )

            app_metadata_repo.clear_upstox_expiry_notification_markers(conn)
            conn.commit()

            logger.info("Upstox connection saved: connection_id=%s", connection_id)

            return {
                "status": "success",
                "message": "Upstox analytics token saved successfully."
            }

        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to save Upstox analytics token: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to save Upstox analytics token: {e}"
            )


def validate_upstox_expired_permission(access_token: str):
    try:
        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "instrument_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
            }
        )

    except HTTPException as primary_error:
        primary_detail = primary_error.detail
        primary_error_code = None
        primary_message = ""

        if isinstance(primary_detail, dict):
            primary_error_code = primary_detail.get("error_code")
            primary_message = primary_detail.get("message") or ""
        else:
            primary_message = str(primary_detail)

        if is_expired_permission_error(primary_error_code, primary_message):
            raise

        if primary_error.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Upstox token is invalid or expired. Please save a fresh token."
            )

        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "instrument_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
            }
        )


def get_upstox_expired_option_contracts(
    access_token: str,
    instrument_key: str,
    expiry_date: str
):
    return upstox_api_get(
        access_token=access_token,
        path=UPSTOX_EXPIRED_OPTION_CONTRACT_PATH,
        params={
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }
    )


def get_upstox_expired_future_contracts(
    access_token: str,
    instrument_key: str,
    expiry_date: str
):
    return upstox_api_get(
        access_token=access_token,
        path=UPSTOX_EXPIRED_FUTURE_CONTRACT_PATH,
        params={
            "instrument_key": instrument_key,
            "expiry_date": expiry_date
        }
    )


def get_upstox_expired_historical_candles(
    access_token: str,
    expired_instrument_key: str,
    interval: str,
    to_date: str,
    from_date: str
):
    safe_expired_instrument_key = urllib.parse.quote(
        expired_instrument_key,
        safe=""
    )

    safe_interval = urllib.parse.quote(interval, safe="")
    safe_to_date = urllib.parse.quote(to_date, safe="")
    safe_from_date = urllib.parse.quote(from_date, safe="")

    path = (
        f"{UPSTOX_EXPIRED_HISTORICAL_CANDLE_PATH}/"
        f"{safe_expired_instrument_key}/"
        f"{safe_interval}/"
        f"{safe_to_date}/"
        f"{safe_from_date}"
    )

    return upstox_api_get(
        access_token=access_token,
        path=path
    )


def update_connection_test_status(
    conn,
    connection_id: str,
    current_user: dict,
    connection_status: str
):
    connection_repo.update_test_status(
        conn,
        connection_id=connection_id,
        connection_status=connection_status,
        updated_by=current_user["user_id"],
    )
    conn.commit()


def test_upstox_connection_service(current_user):
    logger.info("Testing Upstox connection: user_id=%s", current_user.get("user_id"))

    with db_connection() as conn:
        try:
            existing = connection_repo.get_upstox(conn)

            if not existing or existing[7] == "disconnected":
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Upstox connection is not configured.",
                )

            connection_id = existing[0]
            access_token = normalize_upstox_token(existing[5])

            if not access_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Access token is required before testing Upstox connection.",
                )

            try:
                validate_upstox_expired_permission(access_token)

            except HTTPException as e:
                detail = e.detail
                error_code = None
                message = ""

                if isinstance(detail, dict):
                    error_code = detail.get("error_code")
                    message = detail.get("message") or ""
                else:
                    message = str(detail)

                if e.status_code == status.HTTP_403_FORBIDDEN or is_expired_permission_error(
                    error_code, message
                ):
                    update_connection_test_status(
                        conn=conn,
                        connection_id=connection_id,
                        current_user=current_user,
                        connection_status="connected",
                    )
                    return {
                        "status": "success",
                        "message": "Upstox analytics token verified successfully.",
                    }

                if e.status_code == status.HTTP_401_UNAUTHORIZED:
                    update_connection_test_status(
                        conn=conn,
                        connection_id=connection_id,
                        current_user=current_user,
                        connection_status="failed",
                    )
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=(
                            "Upstox token is invalid or expired. "
                            "Please save a fresh analytics token."
                        ),
                    )

                update_connection_test_status(
                    conn=conn,
                    connection_id=connection_id,
                    current_user=current_user,
                    connection_status="limited",
                )
                return {
                    "status": "limited",
                    "message": f"Upstox token check returned: {message or detail}",
                }

            update_connection_test_status(
                conn=conn,
                connection_id=connection_id,
                current_user=current_user,
                connection_status="connected",
            )

            logger.info("Upstox connection test succeeded: connection_id=%s", connection_id)

            return {
                "status": "success",
                "message": "Upstox analytics token verified successfully.",
            }

        except HTTPException:
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to test Upstox connection: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to test Upstox connection: {e}",
            )


def disconnect_upstox_connection_service(current_user):
    logger.info("Disconnecting Upstox: user_id=%s", current_user.get("user_id"))

    with db_connection() as conn:
        try:
            existing = connection_repo.get_upstox(conn)

            if not existing or existing[7] == "disconnected":
                return {
                    "status": "success",
                    "message": "Upstox connection is already disconnected."
                }

            connection_id = existing[0]
            connection_repo.disconnect(conn, connection_id, current_user["user_id"])
            conn.commit()

            logger.info("Upstox disconnected: connection_id=%s", connection_id)

            return {
                "status": "success",
                "message": "Upstox disconnected successfully."
            }

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to disconnect Upstox: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to disconnect Upstox: {e}"
            )


def telegram_api_request(bot_token: str, method_name: str, payload=None, query_params=None):
    clean_bot_token = safe_strip(bot_token)

    if not clean_bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is required."
        )

    query_string = ""

    if query_params:
        query_string = "?" + urllib.parse.urlencode(query_params)

    url = f"{TELEGRAM_BASE_URL}/bot{clean_bot_token}/{method_name}{query_string}"
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "OpenAnalytics/1.0"
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        method="POST" if payload is not None else "GET",
        headers=headers
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            result = json.loads(content)

            if not result.get("ok", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("description") or "Telegram API request failed."
                )

            return result

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")

        try:
            payload = json.loads(error_body)
            message = payload.get("description") or str(payload)
        except Exception:
            message = error_body or str(error)

        raise HTTPException(
            status_code=error.code,
            detail=f"Telegram API error: {message}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Telegram API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Telegram API."
        )


def validate_telegram_bot_token(bot_token: str):
    bot_response = telegram_api_request(
        bot_token=bot_token,
        method_name="getMe"
    )

    bot_data = bot_response.get("result") or {}

    if not bot_data.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token could not be verified."
        )

    return bot_data


def get_telegram_bot_token(conn):
    existing = get_telegram_connection_raw(conn)

    if not existing or existing[7] == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram bot is not configured by admin."
        )

    bot_token = safe_strip(existing[5] or existing[2])

    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is missing."
        )

    return bot_token


def get_telegram_bot_info(conn):
    bot_token = get_telegram_bot_token(conn)
    bot_data = validate_telegram_bot_token(bot_token)

    bot_username = safe_strip(bot_data.get("username"))
    bot_name = safe_strip(bot_data.get("first_name")) or "Telegram bot"

    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot username is missing. Please check the bot in BotFather."
        )

    return {
        "bot_token": bot_token,
        "bot_username": bot_username,
        "bot_name": bot_name
    }


def clear_telegram_webhook(bot_token: str):
    telegram_api_request(
        bot_token=bot_token,
        method_name="deleteWebhook",
        query_params={
            "drop_pending_updates": "false"
        }
    )


def get_telegram_updates(bot_token: str):
    return telegram_api_request(
        bot_token=bot_token,
        method_name="getUpdates",
        query_params={
            "limit": 100,
            "timeout": 2,
            "allowed_updates": json.dumps([
                "message",
                "edited_message",
                "channel_post",
                "edited_channel_post"
            ])
        }
    )


def send_telegram_message(bot_token: str, chat_id: str, message: str):
    return telegram_api_request(
        bot_token=bot_token,
        method_name="sendMessage",
        payload={
            "chat_id": chat_id,
            "text": message
        }
    )


def get_admin_super_admin_telegram_chat_ids(conn):
    return connection_repo.get_admin_super_admin_telegram_chat_ids(conn)


def get_app_metadata_value(conn, key: str):
    return app_metadata_repo.get_value(conn, key)


def set_app_metadata_value(conn, key: str, value: str):
    app_metadata_repo.set_value(conn, key, value)


def clear_upstox_expiry_notification_marker(conn):
    app_metadata_repo.clear_upstox_expiry_notification_markers(conn)


def notify_admin_super_admins_upstox_token_expiry_service():
    logger.debug("Checking Upstox token expiry notifications")

    with db_connection() as conn:
        try:
            upstox_connection = connection_repo.get_upstox(conn)

            if not upstox_connection:
                return {
                    "status": "skipped",
                    "message": "Upstox connection is not configured.",
                }

            access_token = safe_strip(upstox_connection[5])
            expiry_value = upstox_connection[6]

            if not access_token or not expiry_value:
                return {
                    "status": "skipped",
                    "message": "Upstox analytics token or expiry date is missing.",
                }

            expiry_date = parse_db_datetime(expiry_value)

            if not expiry_date:
                return {
                    "status": "skipped",
                    "message": "Upstox analytics token expiry date is invalid.",
                }

            now = get_ist_now()
            today = now.date()
            expiry_day = expiry_date.date()
            days_left = (expiry_day - today).days

            if days_left > 1:
                return {
                    "status": "skipped",
                    "message": "Upstox analytics token is not near expiry.",
                }

            notified_date = app_metadata_repo.get_value(
                conn, "upstox_analytics_token_expiry_notified_date"
            )
            notified_expiry = app_metadata_repo.get_value(
                conn, "upstox_analytics_token_expiry_notified_expiry"
            )

            today_key = today.isoformat()
            expiry_key = expiry_day.isoformat()

            if notified_date == today_key and notified_expiry == expiry_key:
                return {
                    "status": "skipped",
                    "message": "Upstox analytics token expiry notification already sent today.",
                }

            bot_token = get_telegram_bot_token(conn)
            chat_ids = get_admin_super_admin_telegram_chat_ids(conn)

            if not chat_ids:
                return {
                    "status": "skipped",
                    "message": "No connected admin/super admin Telegram users found.",
                }

            if days_left < 0:
                message = (
                    "Open Analytics alert: Upstox analytics token has expired. "
                    "Please update the token in Connections."
                )
            elif days_left == 0:
                message = (
                    "Open Analytics alert: Upstox analytics token expires today. "
                    "Please update the token in Connections."
                )
            else:
                message = (
                    "Open Analytics alert: Upstox analytics token expires tomorrow. "
                    "Please update the token in Connections."
                )

            sent_count = 0

            for chat_id in chat_ids:
                try:
                    send_telegram_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message=message,
                    )
                    sent_count += 1
                except Exception as error:
                    logger.warning(
                        "Unable to send Upstox token expiry Telegram alert: %s",
                        error,
                    )

            app_metadata_repo.set_value(
                conn, "upstox_analytics_token_expiry_notified_date", today_key
            )
            app_metadata_repo.set_value(
                conn, "upstox_analytics_token_expiry_notified_expiry", expiry_key
            )
            conn.commit()

            logger.info(
                "Upstox token expiry notification sent to %s admin user(s)",
                sent_count,
            )

            return {
                "status": "success",
                "message": (
                    f"Upstox analytics token expiry notification sent to "
                    f"{sent_count} admin user(s)."
                ),
            }

        except HTTPException:
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to notify Upstox analytics token expiry: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to notify Upstox analytics token expiry: {e}",
            )


def save_telegram_connection_service(request, current_user):
    bot_token = safe_strip(getattr(request, "bot_token", None))

    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is required.",
        )

    bot_data = validate_telegram_bot_token(bot_token)
    bot_username = safe_strip(bot_data.get("username"))
    bot_label = bot_username or bot_data.get("first_name") or "Telegram bot"

    logger.info("Saving Telegram connection: user_id=%s", current_user.get("user_id"))

    with db_connection() as conn:
        try:
            existing = connection_repo.get_telegram(conn)

            if existing:
                connection_id = existing[0]
                connection_repo.update_telegram(
                    conn,
                    connection_id=connection_id,
                    bot_token=bot_token,
                    bot_username=bot_username,
                    updated_by=current_user["user_id"],
                )
            else:
                connection_id = str(uuid.uuid4())
                connection_repo.insert_telegram(
                    conn,
                    connection_id=connection_id,
                    bot_token=bot_token,
                    bot_username=bot_username,
                    created_by=current_user["user_id"],
                )

            conn.commit()

            logger.info("Telegram connection saved: connection_id=%s", connection_id)

            return {
                "status": "success",
                "message": f"Telegram bot verified and saved successfully for {bot_label}.",
            }

        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to save Telegram connection: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to save Telegram connection: {e}",
            )


def test_telegram_connection_service(current_user):
    logger.info("Testing Telegram connection: user_id=%s", current_user.get("user_id"))

    with db_connection() as conn:
        bot_info = get_telegram_bot_info(conn)

    return {
        "status": "success",
        "message": (
            f"Telegram bot token verified successfully for @{bot_info['bot_username']}."
        ),
    }


def disconnect_telegram_connection_service(current_user):
    logger.info("Disconnecting Telegram: user_id=%s", current_user.get("user_id"))

    with db_connection() as conn:
        try:
            existing = connection_repo.get_telegram(conn)

            if not existing or existing[7] == "disconnected":
                return {
                    "status": "success",
                    "message": "Telegram connection is already disconnected.",
                }

            connection_id = existing[0]
            connection_repo.disconnect(conn, connection_id, current_user["user_id"])
            conn.commit()

            return {
                "status": "success",
                "message": "Telegram disconnected successfully.",
            }

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to disconnect Telegram: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to disconnect Telegram: {e}",
            )


def telegram_user_connection_to_response(row):
    if not row:
        return {
            "status": "success",
            "message": "Telegram is not connected.",
            "connection_status": "not_connected",
            "telegram_username": None,
            "telegram_first_name": None,
            "telegram_last_name": None,
            "updated_at": None
        }

    (
        telegram_connection_id,
        user_id,
        telegram_chat_id,
        telegram_username,
        telegram_first_name,
        telegram_last_name,
        link_token,
        connection_status,
        updated_at
    ) = row

    return {
        "status": "success",
        "message": "Telegram connection status loaded.",
        "connection_status": connection_status or "pending",
        "telegram_username": telegram_username,
        "telegram_first_name": telegram_first_name,
        "telegram_last_name": telegram_last_name,
        "updated_at": str(updated_at) if updated_at else None
    }


def get_user_telegram_connection_raw(conn, user_id: str):
    return user_telegram_repo.get_by_user_id(conn, user_id)


def get_my_telegram_connection_status_service(current_user):
    with db_connection() as conn:
        row = user_telegram_repo.get_by_user_id(conn, current_user["user_id"])

    return telegram_user_connection_to_response(row)


def start_my_telegram_connection_service(current_user):
    user_id = current_user["user_id"]
    logger.info("Starting Telegram user link: user_id=%s", user_id)

    with db_connection() as conn:
        try:
            bot_info = get_telegram_bot_info(conn)
            existing = user_telegram_repo.get_by_user_id(conn, user_id)

            if existing:
                telegram_connection_id = existing[0]
                link_token = str(uuid.uuid4())
                user_telegram_repo.reset_pending_link(
                    conn,
                    telegram_connection_id=telegram_connection_id,
                    link_token=link_token,
                    user_id=user_id,
                )
            else:
                telegram_connection_id = str(uuid.uuid4())
                link_token = str(uuid.uuid4())
                user_telegram_repo.insert_pending(
                    conn,
                    telegram_connection_id=telegram_connection_id,
                    user_id=user_id,
                    link_token=link_token,
                )

            conn.commit()

            telegram_url = f"https://t.me/{bot_info['bot_username']}?start={link_token}"

            return {
                "status": "success",
                "message": (
                    "Telegram link generated. Open it, tap Start, "
                    "then click Verify Telegram."
                ),
                "telegram_url": telegram_url,
                "bot_username": bot_info["bot_username"],
                "connection_status": "pending",
            }

        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to start Telegram connection: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to start Telegram connection: {e}",
            )


def get_message_from_telegram_update(update):
    if not isinstance(update, dict):
        return None

    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )

    if isinstance(message, dict):
        return message

    return None


def find_telegram_start_for_token(updates_response, link_token: str):
    updates = updates_response.get("result")

    if not isinstance(updates, list) or not updates:
        return None

    token_text = safe_strip(link_token)

    for update in reversed(updates):
        message = get_message_from_telegram_update(update)

        if not message:
            continue

        text = safe_strip(message.get("text"))

        if not text:
            continue

        if text == f"/start {token_text}" or text.endswith(f" {token_text}"):
            chat = message.get("chat") or {}
            from_user = message.get("from") or {}

            if not isinstance(chat, dict) or chat.get("id") is None:
                continue

            return {
                "telegram_chat_id": str(chat.get("id")),
                "telegram_username": from_user.get("username") or chat.get("username"),
                "telegram_first_name": from_user.get("first_name") or chat.get("first_name"),
                "telegram_last_name": from_user.get("last_name") or chat.get("last_name")
            }

    return None


def verify_my_telegram_connection_service(current_user):
    user_id = current_user["user_id"]
    logger.info("Verifying Telegram user link: user_id=%s", user_id)

    with db_connection() as conn:
        try:
            bot_token = get_telegram_bot_token(conn)
            existing = user_telegram_repo.get_by_user_id(conn, user_id)

            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Click Connect Telegram first to generate your Telegram link.",
                )

            telegram_connection_id = existing[0]
            link_token = safe_strip(existing[6])

            if not link_token:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Telegram link token is missing. Click Connect Telegram again.",
                )

            updates_response = get_telegram_updates(bot_token)
            matched = find_telegram_start_for_token(updates_response, link_token)

            if not matched:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Telegram start message was not found. Open the generated "
                        "Telegram link, tap Start, then click Verify Telegram again."
                    ),
                )

            user_telegram_repo.connect_user(
                conn,
                telegram_connection_id=telegram_connection_id,
                telegram_chat_id=matched["telegram_chat_id"],
                telegram_username=matched["telegram_username"],
                telegram_first_name=matched["telegram_first_name"],
                telegram_last_name=matched["telegram_last_name"],
                user_id=user_id,
            )
            conn.commit()

            send_telegram_message(
                bot_token=bot_token,
                chat_id=matched["telegram_chat_id"],
                message="Open Analytics Telegram connected successfully.",
            )

            row = user_telegram_repo.get_by_user_id(conn, user_id)
            response = telegram_user_connection_to_response(row)
            response["message"] = "Telegram connected successfully."

            logger.info("Telegram user link verified: user_id=%s", user_id)
            return response

        except HTTPException:
            try:
                conn.rollback()
            except Exception:
                pass
            raise

        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass

            logger.exception("Unable to verify Telegram connection: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to verify Telegram connection: {e}",
            )


def test_my_telegram_connection_service(current_user):
    user_id = current_user["user_id"]
    logger.info("Testing Telegram user link: user_id=%s", user_id)

    with db_connection() as conn:
        bot_token = get_telegram_bot_token(conn)
        row = user_telegram_repo.get_by_user_id(conn, user_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not connected. Click Connect Telegram first.",
            )

        telegram_chat_id = safe_strip(row[2])
        connection_status = safe_strip(row[7])

        if connection_status != "connected" or not telegram_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not verified yet. Click Verify Telegram first.",
            )

        send_telegram_message(
            bot_token=bot_token,
            chat_id=telegram_chat_id,
            message="Open Analytics Telegram test message.",
        )

    return {
        "status": "success",
        "message": "Telegram test message sent successfully.",
    }
