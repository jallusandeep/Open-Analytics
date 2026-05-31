import json
import uuid
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"
UPSTOX_BASE_URL = "https://api.upstox.com/v2"

# Test only the API we actually need for expired instruments.
# Do not test /user/profile because some valid tokens may fail there with user authorization errors.
UPSTOX_EXPIRED_PERMISSION_TEST_PATH = "/expired-instruments/expiries"
UPSTOX_EXPIRED_PERMISSION_TEST_KEY = "NSE_INDEX|Nifty 50"


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


def get_upstox_connection_raw(conn):
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
    """, [UPSTOX_PROVIDER]).fetchone()


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


def save_upstox_connection_service(request, current_user):
    access_token = request.access_token.strip() if request.access_token else ""

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox access token is required."
        )

    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if existing:
            connection_id = existing[0]

            conn.execute("""
                UPDATE external_connections
                SET
                    api_key = NULL,
                    api_secret = NULL,
                    redirect_url = NULL,
                    access_token = ?,
                    connection_status = 'saved',
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [
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
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                connection_id,
                UPSTOX_PROVIDER,
                None,
                None,
                None,
                access_token,
                "saved",
                "S",
                1,
                current_user["user_id"],
                current_user["user_id"]
            ])

        conn.commit()

        return {
            "status": "success",
            "message": "Upstox token saved successfully."
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
            detail=f"Unable to save Upstox connection: {e}"
        )

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
            ),
            "message": first_error.get("message") or str(payload)
        }

    return {
        "raw": payload,
        "error_code": payload.get("errorCode") or payload.get("error_code"),
        "message": payload.get("message") or str(payload)
    }


def upstox_api_get(access_token: str, path: str, params=None):
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
        with urllib.request.urlopen(request, timeout=30) as response:
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


def validate_upstox_expired_permission(access_token: str):
    try:
        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "underlying_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
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

        if primary_error_code == "UDAPI100067" or "read only token" in primary_message.lower():
            raise

        if primary_error.status_code == status.HTTP_401_UNAUTHORIZED:
            raise

        return upstox_api_get(
            access_token=access_token,
            path=UPSTOX_EXPIRED_PERMISSION_TEST_PATH,
            params={
                "instrument_key": UPSTOX_EXPIRED_PERMISSION_TEST_KEY
            }
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
        access_token = existing[5]

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Access token is required before testing Upstox connection."
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

            if error_code == "UDAPI100067" or "read only token" in message.lower():
                update_connection_test_status(
                    conn=conn,
                    connection_id=connection_id,
                    current_user=current_user,
                    connection_status="limited"
                )

                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        "Upstox token is valid, but Expired Instruments API is not permitted "
                        "with this token. Please generate a normal OAuth token from your "
                        "Upstox Plus enabled app and save it again."
                    )
                )

            update_connection_test_status(
                conn=conn,
                connection_id=connection_id,
                current_user=current_user,
                connection_status="limited"
            )

            raise HTTPException(
                status_code=e.status_code,
                detail=(
                    "Unable to verify Expired Instruments API permission. "
                    f"Upstox response: {message or detail}"
                )
            )

        update_connection_test_status(
            conn=conn,
            connection_id=connection_id,
            current_user=current_user,
            connection_status="connected"
        )

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