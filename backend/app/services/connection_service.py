import json
import uuid
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"
TELEGRAM_PROVIDER = "telegram"

UPSTOX_BASE_URL = "https://api.upstox.com/v2"

UPSTOX_AUTHORIZE_URL = f"{UPSTOX_BASE_URL}/login/authorization/dialog"
UPSTOX_TOKEN_URL = f"{UPSTOX_BASE_URL}/login/authorization/token"

UPSTOX_PROFILE_TEST_PATH = "/user/profile"
UPSTOX_EXPIRED_PERMISSION_TEST_PATH = "/expired-instruments/expiries"
UPSTOX_EXPIRED_PERMISSION_TEST_KEY = "NSE_INDEX|Nifty 50"

UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL = (
    f"{UPSTOX_BASE_URL}/market-quote/instruments/exchange"
)

UPSTOX_EXPIRED_OPTION_CONTRACT_PATH = "/expired-instruments/option/contract"
UPSTOX_EXPIRED_FUTURE_CONTRACT_PATH = "/expired-instruments/future/contract"
UPSTOX_EXPIRED_HISTORICAL_CANDLE_PATH = "/expired-instruments/historical-candle"

TELEGRAM_BASE_URL = "https://api.telegram.org"

REQUEST_TIMEOUT_SECONDS = 30


def safe_strip(value):
    return value.strip() if isinstance(value, str) else ""


def normalize_upstox_token(access_token: str) -> str:
    token = safe_strip(access_token)

    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    return token


def connection_to_response(row):
    if not row:
        return None

    (
        connection_id,
        provider,
        api_key,
        api_secret,
        redirect_url,
        access_token,
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
        "has_access_token": bool(access_token),
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
            access_token,
            connection_status,
            last_tested_at,
            created_at,
            updated_at
        FROM external_connections
        WHERE provider = ?
        LIMIT 1;
    """, [provider]).fetchone()


def get_upstox_connection_raw(conn):
    return get_connection_raw_by_provider(conn, UPSTOX_PROVIDER)


def get_telegram_connection_raw(conn):
    return get_connection_raw_by_provider(conn, TELEGRAM_PROVIDER)


def list_connections_service():
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                connection_id,
                provider,
                api_key,
                api_secret,
                redirect_url,
                access_token,
                connection_status,
                last_tested_at,
                created_at,
                updated_at
            FROM external_connections
            WHERE record_status = 'S'
            ORDER BY provider;
        """).fetchall()

        return {
            "connections": [connection_to_response(row) for row in rows]
        }

    finally:
        conn.close()


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


def build_upstox_authorization_url(api_key: str, redirect_url: str, state: str = ""):
    if not safe_strip(api_key):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API key is required."
        )

    if not safe_strip(redirect_url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox redirect URL is required."
        )

    params = {
        "response_type": "code",
        "client_id": safe_strip(api_key),
        "redirect_uri": safe_strip(redirect_url)
    }

    if safe_strip(state):
        params["state"] = safe_strip(state)

    return f"{UPSTOX_AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


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


def exchange_upstox_authorization_code(
    api_key: str,
    api_secret: str,
    redirect_url: str,
    authorization_code: str
):
    clean_api_key = safe_strip(api_key)
    clean_api_secret = safe_strip(api_secret)
    clean_redirect_url = safe_strip(redirect_url)
    clean_authorization_code = safe_strip(authorization_code)

    if not clean_api_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API key is required."
        )

    if not clean_api_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox API secret is required."
        )

    if not clean_redirect_url:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox redirect URL is required."
        )

    if not clean_authorization_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox authorization code is required."
        )

    payload = urllib.parse.urlencode({
        "code": clean_authorization_code,
        "client_id": clean_api_key,
        "client_secret": clean_api_secret,
        "redirect_uri": clean_redirect_url,
        "grant_type": "authorization_code"
    }).encode("utf-8")

    request = urllib.request.Request(
        UPSTOX_TOKEN_URL,
        data=payload,
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
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Empty response received from Upstox token API."
                )

            token_response = json.loads(content)

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")
        parsed_error = parse_upstox_error(error_body)

        raise HTTPException(
            status_code=error.code,
            detail={
                "message": parsed_error["message"] or "Unable to exchange Upstox authorization code.",
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

    access_token = normalize_upstox_token(token_response.get("access_token", ""))

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Upstox token API did not return an access token."
        )

    return token_response


def download_upstox_active_instruments(exchange: str = "complete"):
    exchange_code = safe_strip(exchange) if exchange else "complete"

    if not exchange_code:
        exchange_code = "complete"

    url = f"{UPSTOX_PUBLIC_INSTRUMENTS_BASE_URL}/{exchange_code}.json"
    return upstox_public_api_get(url)


def validate_upstox_token(access_token: str):
    token = normalize_upstox_token(access_token)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox access token is required."
        )

    try:
        profile_response = upstox_api_get(
            access_token=token,
            path=UPSTOX_PROFILE_TEST_PATH
        )

        if not isinstance(profile_response, dict):
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Invalid response received from Upstox profile API."
            )

        return profile_response

    except HTTPException as e:
        detail = e.detail
        message = ""

        if isinstance(detail, dict):
            message = detail.get("message") or ""
        else:
            message = str(detail)

        error_code = detail.get("error_code") if isinstance(detail, dict) else None

        if error_code == "UDAPI100067" or "read only token" in message.lower():
            return {
                "status": "limited",
                "message": message or "Upstox token is read only."
            }

        if e.status_code == status.HTTP_403_FORBIDDEN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    "Upstox token was rejected by Upstox authorization. "
                    f"Upstox response: {message or detail}"
                )
            )

        if e.status_code == status.HTTP_401_UNAUTHORIZED:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Upstox token is invalid or expired. Please save a fresh OAuth access token."
            )

        raise HTTPException(
            status_code=e.status_code,
            detail=f"Unable to validate Upstox token. Upstox response: {message or detail}"
        )


def get_upstox_profile_label(profile_response):
    try:
        data = profile_response.get("data") or {}
        user_name = data.get("user_name")
        user_id = data.get("user_id")

        if user_name and user_id:
            return f"{user_name} ({user_id})"

        if user_name:
            return user_name

        if user_id:
            return user_id

    except Exception:
        pass

    return None


def resolve_upstox_access_token_from_request(request):
    authorization_code = safe_strip(getattr(request, "authorization_code", None))
    manual_access_token = normalize_upstox_token(getattr(request, "access_token", None))

    api_key = safe_strip(getattr(request, "api_key", None))
    api_secret = safe_strip(getattr(request, "api_secret", None))
    redirect_url = safe_strip(getattr(request, "redirect_url", None))

    if authorization_code:
        token_response = exchange_upstox_authorization_code(
            api_key=api_key,
            api_secret=api_secret,
            redirect_url=redirect_url,
            authorization_code=authorization_code
        )

        return {
            "access_token": normalize_upstox_token(token_response.get("access_token")),
            "api_key": api_key,
            "api_secret": api_secret,
            "redirect_url": redirect_url,
            "used_oauth_code": True
        }

    if manual_access_token:
        return {
            "access_token": manual_access_token,
            "api_key": api_key,
            "api_secret": api_secret,
            "redirect_url": redirect_url,
            "used_oauth_code": False
        }

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Enter either Upstox authorization code or access token."
    )


def save_upstox_connection_service(request, current_user):
    resolved = resolve_upstox_access_token_from_request(request)

    access_token = resolved["access_token"]
    profile_response = validate_upstox_token(access_token)
    profile_label = get_upstox_profile_label(profile_response)

    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if existing:
            connection_id = existing[0]
            existing_api_key = existing[2]
            existing_api_secret = existing[3]
            existing_redirect_url = existing[4]

            api_key_to_save = resolved["api_key"] or existing_api_key
            api_secret_to_save = resolved["api_secret"] or existing_api_secret
            redirect_url_to_save = resolved["redirect_url"] or existing_redirect_url

            conn.execute("""
                UPDATE external_connections
                SET
                    api_key = ?,
                    api_secret = ?,
                    redirect_url = ?,
                    access_token = ?,
                    connection_status = 'connected',
                    record_status = 'S',
                    last_tested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [
                api_key_to_save,
                api_secret_to_save,
                redirect_url_to_save,
                access_token,
                current_user["user_id"],
                connection_id
            ])

        else:
            connection_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO external_connections (
                    connection_id,
                    provider,
                    api_key,
                    api_secret,
                    redirect_url,
                    access_token,
                    connection_status,
                    record_status,
                    version_no,
                    last_tested_at,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
            """, [
                connection_id,
                UPSTOX_PROVIDER,
                resolved["api_key"] or None,
                resolved["api_secret"] or None,
                resolved["redirect_url"] or None,
                access_token,
                "connected",
                "S",
                1,
                current_user["user_id"],
                current_user["user_id"]
            ])

        conn.commit()

        if profile_label:
            return {
                "status": "success",
                "message": f"Upstox token verified and saved successfully for {profile_label}."
            }

        return {
            "status": "success",
            "message": "Upstox token verified and saved successfully."
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
            detail=f"Unable to save Upstox connection: {e}"
        )

    finally:
        conn.close()


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
                detail="Upstox token is invalid or expired. Please save a fresh OAuth access token."
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
    conn.execute("""
        UPDATE external_connections
        SET
            connection_status = ?,
            last_tested_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = ?
        WHERE connection_id = ?;
    """, [
        connection_status,
        current_user["user_id"],
        connection_id
    ])

    conn.commit()


def test_upstox_connection_service(current_user):
    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing or existing[6] == "disconnected":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upstox connection is not configured."
            )

        connection_id = existing[0]
        access_token = normalize_upstox_token(existing[5])

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token is required before testing Upstox connection."
            )

        try:
            profile_response = validate_upstox_token(access_token)

        except HTTPException:
            update_connection_test_status(
                conn=conn,
                connection_id=connection_id,
                current_user=current_user,
                connection_status="failed"
            )
            raise

        profile_label = get_upstox_profile_label(profile_response)

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

            if e.status_code == status.HTTP_401_UNAUTHORIZED:
                update_connection_test_status(
                    conn=conn,
                    connection_id=connection_id,
                    current_user=current_user,
                    connection_status="failed"
                )

                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Upstox token is invalid or expired. Please save a fresh OAuth access token."
                )

            if e.status_code == status.HTTP_403_FORBIDDEN or is_expired_permission_error(error_code, message):
                update_connection_test_status(
                    conn=conn,
                    connection_id=connection_id,
                    current_user=current_user,
                    connection_status="limited"
                )

                if profile_label:
                    return {
                        "status": "limited",
                        "message": (
                            f"Upstox token is valid for {profile_label}, but Expired Instruments API "
                            "permission is not enabled for this Upstox app. Current instruments and profile "
                            "verification can work, but expired instruments need Upstox Plus/API permission."
                        )
                    }

                return {
                    "status": "limited",
                    "message": (
                        "Upstox token is valid, but Expired Instruments API permission is not enabled "
                        "for this Upstox app. Current instruments and profile verification can work, "
                        "but expired instruments need Upstox Plus/API permission."
                    )
                }

            update_connection_test_status(
                conn=conn,
                connection_id=connection_id,
                current_user=current_user,
                connection_status="limited"
            )

            return {
                "status": "limited",
                "message": (
                    "Upstox token is valid, but unable to verify Expired Instruments API permission. "
                    f"Upstox response: {message or detail}"
                )
            }

        update_connection_test_status(
            conn=conn,
            connection_id=connection_id,
            current_user=current_user,
            connection_status="connected"
        )

        if profile_label:
            return {
                "status": "success",
                "message": (
                    f"Upstox token verified successfully for {profile_label}. "
                    "Expired Instruments API permission is available."
                )
            }

        return {
            "status": "success",
            "message": "Upstox token verified successfully. Expired Instruments API permission is available."
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
            detail=f"Unable to test Upstox connection: {e}"
        )

    finally:
        conn.close()


def disconnect_upstox_connection_service(current_user):
    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing or existing[6] == "disconnected":
            return {
                "status": "success",
                "message": "Upstox connection is already disconnected."
            }

        connection_id = existing[0]

        conn.execute("""
            UPDATE external_connections
            SET
                record_status = 'D',
                connection_status = 'disconnected',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [current_user["user_id"], connection_id])

        conn.commit()

        return {
            "status": "success",
            "message": "Upstox disconnected successfully."
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to disconnect Upstox: {e}"
        )

    finally:
        conn.close()


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

    if not existing or existing[6] == "disconnected":
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
    clear_telegram_webhook(bot_token)

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


def save_telegram_connection_service(request, current_user):
    bot_token = safe_strip(getattr(request, "bot_token", None))

    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is required."
        )

    bot_data = validate_telegram_bot_token(bot_token)
    bot_username = safe_strip(bot_data.get("username"))
    bot_label = bot_username or bot_data.get("first_name") or "Telegram bot"

    conn = get_connection()

    try:
        existing = get_telegram_connection_raw(conn)

        if existing:
            connection_id = existing[0]

            conn.execute("""
                UPDATE external_connections
                SET
                    api_key = ?,
                    api_secret = NULL,
                    redirect_url = ?,
                    access_token = ?,
                    connection_status = 'connected',
                    record_status = 'S',
                    last_tested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [
                bot_token,
                bot_username,
                bot_token,
                current_user["user_id"],
                connection_id
            ])

        else:
            connection_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO external_connections (
                    connection_id,
                    provider,
                    api_key,
                    api_secret,
                    redirect_url,
                    access_token,
                    connection_status,
                    record_status,
                    version_no,
                    last_tested_at,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
            """, [
                connection_id,
                TELEGRAM_PROVIDER,
                bot_token,
                None,
                bot_username,
                bot_token,
                "connected",
                "S",
                1,
                current_user["user_id"],
                current_user["user_id"]
            ])

        conn.commit()

        return {
            "status": "success",
            "message": f"Telegram bot verified and saved successfully for {bot_label}."
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
            detail=f"Unable to save Telegram connection: {e}"
        )

    finally:
        conn.close()


def test_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_info = get_telegram_bot_info(conn)

        return {
            "status": "success",
            "message": f"Telegram bot token verified successfully for @{bot_info['bot_username']}."
        }

    finally:
        conn.close()


def disconnect_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        existing = get_telegram_connection_raw(conn)

        if not existing or existing[6] == "disconnected":
            return {
                "status": "success",
                "message": "Telegram connection is already disconnected."
            }

        connection_id = existing[0]

        conn.execute("""
            UPDATE external_connections
            SET
                record_status = 'D',
                connection_status = 'disconnected',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [current_user["user_id"], connection_id])

        conn.commit()

        return {
            "status": "success",
            "message": "Telegram disconnected successfully."
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to disconnect Telegram: {e}"
        )

    finally:
        conn.close()


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
    return conn.execute("""
        SELECT
            telegram_connection_id,
            user_id,
            telegram_chat_id,
            telegram_username,
            telegram_first_name,
            telegram_last_name,
            link_token,
            connection_status,
            updated_at
        FROM user_telegram_connections
        WHERE user_id = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [user_id]).fetchone()


def get_my_telegram_connection_status_service(current_user):
    conn = get_connection()

    try:
        row = get_user_telegram_connection_raw(conn, current_user["user_id"])
        return telegram_user_connection_to_response(row)

    finally:
        conn.close()


def start_my_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_info = get_telegram_bot_info(conn)
        user_id = current_user["user_id"]

        existing = get_user_telegram_connection_raw(conn, user_id)

        if existing:
            telegram_connection_id = existing[0]
            link_token = existing[6] or str(uuid.uuid4())

            conn.execute("""
                UPDATE user_telegram_connections
                SET
                    link_token = ?,
                    connection_status = CASE
                        WHEN telegram_chat_id IS NOT NULL AND telegram_chat_id <> '' THEN 'connected'
                        ELSE 'pending'
                    END,
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE telegram_connection_id = ?;
            """, [
                link_token,
                user_id,
                telegram_connection_id
            ])

        else:
            telegram_connection_id = str(uuid.uuid4())
            link_token = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO user_telegram_connections (
                    telegram_connection_id,
                    user_id,
                    telegram_chat_id,
                    telegram_username,
                    telegram_first_name,
                    telegram_last_name,
                    link_token,
                    connection_status,
                    record_status,
                    version_no,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                telegram_connection_id,
                user_id,
                None,
                None,
                None,
                None,
                link_token,
                "pending",
                "S",
                1,
                user_id,
                user_id
            ])

        conn.commit()

        telegram_url = f"https://t.me/{bot_info['bot_username']}?start={link_token}"

        return {
            "status": "success",
            "message": "Telegram link generated. Open it, tap Start, then click Verify Telegram.",
            "telegram_url": telegram_url,
            "bot_username": bot_info["bot_username"],
            "connection_status": "pending"
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
            detail=f"Unable to start Telegram connection: {e}"
        )

    finally:
        conn.close()


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
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        user_id = current_user["user_id"]

        existing = get_user_telegram_connection_raw(conn, user_id)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Click Connect Telegram first to generate your Telegram link."
            )

        telegram_connection_id = existing[0]
        link_token = safe_strip(existing[6])

        if not link_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram link token is missing. Click Connect Telegram again."
            )

        updates_response = get_telegram_updates(bot_token)
        matched = find_telegram_start_for_token(updates_response, link_token)

        if not matched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Telegram start message was not found. Open the generated Telegram link, "
                    "tap Start, then click Verify Telegram again."
                )
            )

        conn.execute("""
            UPDATE user_telegram_connections
            SET
                telegram_chat_id = ?,
                telegram_username = ?,
                telegram_first_name = ?,
                telegram_last_name = ?,
                connection_status = 'connected',
                record_status = 'S',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE telegram_connection_id = ?;
        """, [
            matched["telegram_chat_id"],
            matched["telegram_username"],
            matched["telegram_first_name"],
            matched["telegram_last_name"],
            user_id,
            telegram_connection_id
        ])

        conn.commit()

        send_telegram_message(
            bot_token=bot_token,
            chat_id=matched["telegram_chat_id"],
            message="Open Analytics Telegram connected successfully."
        )

        row = get_user_telegram_connection_raw(conn, user_id)
        response = telegram_user_connection_to_response(row)
        response["message"] = "Telegram connected successfully."

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

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to verify Telegram connection: {e}"
        )

    finally:
        conn.close()


def test_my_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        user_id = current_user["user_id"]

        row = get_user_telegram_connection_raw(conn, user_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not connected. Click Connect Telegram first."
            )

        telegram_chat_id = safe_strip(row[2])
        connection_status = safe_strip(row[7])

        if connection_status != "connected" or not telegram_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not verified yet. Click Verify Telegram first."
            )

        send_telegram_message(
            bot_token=bot_token,
            chat_id=telegram_chat_id,
            message="Open Analytics Telegram test message."
        )

        return {
            "status": "success",
            "message": "Telegram test message sent successfully."
        }

    finally:
        conn.close()