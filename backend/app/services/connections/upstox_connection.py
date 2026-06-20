from .common import *  # noqa: F401,F403
from .upstox_api import *  # noqa: F401,F403
from .upstox_tokens import *  # noqa: F401,F403


def refresh_connection_statuses_for_list(conn):
    now_time = get_ist_now()

    upstox_row = get_upstox_connection_raw(conn)

    if upstox_row:
        connection_id = upstox_row[0]
        api_key = safe_strip(upstox_row[2])
        api_secret = safe_strip(upstox_row[3])
        redirect_url = safe_strip(upstox_row[4])
        analytical_token = normalize_upstox_token(upstox_row[5])
        access_token = normalize_upstox_token(upstox_row[6])
        access_token_expires_at = parse_db_datetime(upstox_row[7])
        current_status = safe_strip(upstox_row[8]) or "saved"

        next_status = current_status
        has_full_oauth_connection = bool(
            api_key
            and api_secret
            and access_token
        )
        is_access_token_expired = bool(
            access_token
            and access_token_expires_at
            and access_token_expires_at <= now_time
        )

        if current_status != "disconnected":
            if is_access_token_expired:
                next_status = "limited" if analytical_token else "failed"
            elif current_status == "connected" and has_full_oauth_connection:
                next_status = "connected"
            else:
                next_status = get_upstox_save_status(
                    api_key=api_key,
                    api_secret=api_secret,
                    redirect_url=redirect_url,
                    analytical_token=analytical_token,
                    access_token=access_token
                )

        if next_status != current_status:
            conn.execute("""
                UPDATE external_connections
                SET
                    connection_status = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = 'system_refresh'
                WHERE connection_id = ?;
            """, [
                next_status,
                connection_id
            ])

            conn.commit()

        should_request_token = (
            current_status != "disconnected"
            and (
                is_access_token_expired
                or next_status in ("limited", "failed")
            )
        )

        if should_request_token:
            maybe_request_upstox_access_token_and_send_reminder(
                conn=conn,
                reason=(
                    "Upstox access token expired"
                    if is_access_token_expired
                    else f"Upstox status is {next_status}"
                ),
                previous_status=current_status,
                current_status=next_status
            )


def list_connections_service():
    conn = get_connection()

    try:
        refresh_connection_statuses_for_list(conn)

        rows = conn.execute("""
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
            WHERE record_status = 'S'
            ORDER BY provider;
        """).fetchall()

        return {
            "connections": [connection_to_response(row) for row in rows]
        }

    finally:
        conn.close()


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

    #Commented as below code is not required
    #has_partial_api_credentials = bool(api_key or api_secret or redirect_url)
    #has_complete_api_credentials = bool(api_key and api_secret and redirect_url)

    # if has_partial_api_credentials and not has_complete_api_credentials:
    #     raise HTTPException(
    #         status_code=status.HTTP_400_BAD_REQUEST,
    #         detail="Upstox API key, API secret, and redirect URL are required together."
    #     )

    saved_at = get_ist_now()
    access_token_expires_at = None

    if access_token:
        access_token_expires_at = get_next_upstox_access_token_expiry(
            saved_at
        ).strftime("%Y-%m-%d %H:%M:%S")

    connection_status = get_upstox_save_status(
        api_key=api_key,
        api_secret=api_secret,
        redirect_url=redirect_url,
        analytical_token=analytical_token,
        access_token=access_token
    )

    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if existing:
            connection_id = existing[0]
            existing_api_key = safe_strip(existing[2])
            existing_api_secret = safe_strip(existing[3])
            existing_redirect_url = safe_strip(existing[4])
            existing_analytical_token = normalize_upstox_token(existing[5])
            existing_access_token = normalize_upstox_token(existing[6])
            existing_access_token_expires_at = existing[7]

            next_api_key = api_key or existing_api_key or None
            next_api_secret = api_secret or existing_api_secret or None
            next_redirect_url = redirect_url or existing_redirect_url or None
            next_analytical_token = (
                analytical_token or existing_analytical_token or None
            )
            next_access_token = access_token or existing_access_token or None
            next_access_token_expires_at = (
                access_token_expires_at
                if access_token
                else existing_access_token_expires_at
            )

            next_status = get_upstox_save_status(
                api_key=next_api_key,
                api_secret=next_api_secret,
                redirect_url=next_redirect_url,
                analytical_token=next_analytical_token,
                access_token=next_access_token
            )

            conn.execute("""
                UPDATE external_connections
                SET
                    api_key = ?,
                    api_secret = ?,
                    redirect_url = ?,
                    analytical_token = ?,
                    analytical_token_updated_at = CASE
                        WHEN ? IS NOT NULL AND TRIM(?) <> '' THEN CURRENT_TIMESTAMP
                        ELSE analytical_token_updated_at
                    END,
                    access_token = ?,
                    access_token_expires_at = ?,
                    token_updated_at = CASE
                        WHEN ? IS NOT NULL AND TRIM(?) <> '' THEN CURRENT_TIMESTAMP
                        ELSE token_updated_at
                    END,
                    connection_status = ?,
                    record_status = 'S',
                    last_tested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [
                next_api_key,
                next_api_secret,
                next_redirect_url,
                next_analytical_token,
                analytical_token,
                analytical_token,
                next_access_token,
                next_access_token_expires_at,
                access_token,
                access_token,
                next_status,
                current_user["user_id"],
                connection_id
            ])

            connection_status = next_status

        else:
            connection_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO external_connections (
                    connection_id,
                    provider,
                    api_key,
                    api_secret,
                    redirect_url,
                    analytical_token,
                    analytical_token_updated_at,
                    access_token,
                    access_token_expires_at,
                    token_updated_at,
                    connection_status,
                    record_status,
                    version_no,
                    last_tested_at,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
            """, [
                connection_id,
                UPSTOX_PROVIDER,
                api_key or None,
                api_secret or None,
                redirect_url or None,
                analytical_token or None,
                access_token or None,
                access_token_expires_at,
                connection_status,
                "S",
                1,
                current_user["user_id"],
                current_user["user_id"]
            ])

        clear_upstox_expiry_notification_marker(conn)
        conn.commit()

        if connection_status == "connected":
            message = "Upstox API credentials and access token saved successfully."
        elif connection_status == "limited":
            message = "Upstox token saved with limited connection."
        else:
            message = "Upstox API credentials saved. Generate or add an access token to connect."

        return {
            "status": connection_status if connection_status != "connected" else "success",
            "message": message
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


def get_upstox_authorize_url_service(current_user):
    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Save Upstox API key, API secret, and redirect URL first."
            )

        api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])
        redirect_url = safe_strip(existing[4])

        if not api_key or not api_secret or not redirect_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Save Upstox API key, API secret, and redirect URL first."
            )

        query_string = urllib.parse.urlencode({
            "response_type": "code",
            "client_id": api_key,
            "redirect_uri": redirect_url
        })

        return {
            "status": "success",
            "authorize_url": f"{UPSTOX_AUTHORIZE_URL}?{query_string}",
            "message": "Open this URL to authorize Upstox."
        }

    finally:
        conn.close()


def exchange_upstox_auth_code_service(request, current_user):
    auth_code = safe_strip(getattr(request, "code", None))

    if not auth_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upstox authorization code is required."
        )

    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Save Upstox API key, API secret, and redirect URL first."
            )

        connection_id = existing[0]
        api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])
        redirect_url = safe_strip(existing[4])
        analytical_token = normalize_upstox_token(existing[5])

        if not api_key or not api_secret or not redirect_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Save Upstox API key, API secret, and redirect URL first."
            )

        token_response = upstox_token_post({
            "code": auth_code,
            "client_id": api_key,
            "client_secret": api_secret,
            "redirect_uri": redirect_url,
            "grant_type": "authorization_code"
        })

        access_token = normalize_upstox_token(token_response.get("access_token"))
        token_type = safe_strip(token_response.get("token_type")) or "Bearer"

        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Upstox token API did not return an access token."
            )

        saved_at = get_ist_now()
        access_token_expires_at = get_next_upstox_access_token_expiry(
            saved_at
        ).strftime("%Y-%m-%d %H:%M:%S")

        next_status = "connected"

        conn.execute("""
            UPDATE external_connections
            SET
                access_token = ?,
                token_type = ?,
                access_token_expires_at = ?,
                token_updated_at = CURRENT_TIMESTAMP,
                connection_status = ?,
                record_status = 'S',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [
            access_token,
            token_type,
            access_token_expires_at,
            next_status,
            current_user["user_id"],
            connection_id
        ])

        clear_upstox_expiry_notification_marker(conn)
        conn.commit()

        return {
            "status": "connected",
            "message": "Upstox access token generated and saved successfully."
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
            detail=f"Unable to exchange Upstox authorization code: {e}"
        )

    finally:
        conn.close()


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


def get_upstox_token_test_result(token: str):
    if not token:
        return {
            "state": "missing",
            "message": "not saved"
        }

    try:
        validate_upstox_expired_permission(token)

        return {
            "state": "connected",
            "message": "connected"
        }

    except HTTPException as error:
        detail = error.detail
        error_code = None
        message = ""

        if isinstance(detail, dict):
            error_code = detail.get("error_code")
            message = detail.get("message") or ""
        else:
            message = str(detail)

        if error.status_code == status.HTTP_401_UNAUTHORIZED:
            return {
                "state": "invalid",
                "message": "invalid or expired"
            }

        if (
            error.status_code == status.HTTP_403_FORBIDDEN
            or is_expired_permission_error(error_code, message)
        ):
            return {
                "state": "limited",
                "message": "connected with limited permission"
            }

        return {
            "state": "failed",
            "message": message or detail or "verification failed"
        }


def get_upstox_analytical_token_test_result(token: str):
    if not token:
        return {
            "state": "missing",
            "message": "not saved"
        }

    try:
        upstox_api_get(token, UPSTOX_MARKET_HOLIDAYS_PATH)

        return {
            "state": "limited",
            "message": "verified for read-only market data"
        }
    except HTTPException as error:
        detail = error.detail
        message = detail

        if isinstance(detail, dict):
            message = detail.get("message") or detail.get("raw") or str(detail)

        return {
            "state": "failed",
            "message": safe_strip(str(message)) or "verification failed"
        }


def is_upstox_token_usable(test_result: dict) -> bool:
    return test_result.get("state") in ("connected", "limited")


def format_upstox_token_test_label(token_label: str, test_result: dict) -> str:
    return f"{token_label} {test_result.get('message', 'verification failed')}"


def test_upstox_connection_service(current_user):
    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing or existing[8] == "disconnected":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upstox connection is not configured."
            )

        connection_id = existing[0]
        api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])
        redirect_url = safe_strip(existing[4])
        analytical_token = normalize_upstox_token(existing[5])
        access_token = normalize_upstox_token(existing[6])

        if not access_token and not analytical_token:
            update_connection_test_status(
                conn=conn,
                connection_id=connection_id,
                current_user=current_user,
                connection_status="failed"
            )

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Analytical token or access token is required before testing Upstox connection."
            )

        analytical_result = get_upstox_analytical_token_test_result(
            analytical_token
        )
        access_result = get_upstox_token_test_result(access_token)

        has_usable_analytical_token = is_upstox_token_usable(analytical_result)
        has_usable_access_token = is_upstox_token_usable(access_result)

        if has_usable_access_token and api_key and api_secret:
            test_status = "connected"
        elif has_usable_access_token or has_usable_analytical_token:
            test_status = "limited"
        else:
            test_status = "failed"

        update_connection_test_status(
            conn=conn,
            connection_id=connection_id,
            current_user=current_user,
            connection_status=test_status
        )

        tested_parts = []

        if analytical_token:
            tested_parts.append(
                format_upstox_token_test_label("Analytical token", analytical_result)
            )

        if access_token:
            tested_parts.append(
                format_upstox_token_test_label("Access token", access_result)
            )

        message = ". ".join(tested_parts)

        if test_status == "failed":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"{message}. Please save a fresh token."
            )

        if test_status == "connected":
            return {
                "status": "connected",
                "message": f"{message}. Upstox connection verified successfully."
            }

        return {
            "status": "limited",
            "message": f"{message}. Upstox connection is limited."
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

        if not existing or existing[8] == "disconnected":
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
