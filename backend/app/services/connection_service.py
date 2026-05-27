import uuid
import urllib.error
import urllib.request

from fastapi import HTTPException, status

from app.database import get_connection


UPSTOX_PROVIDER = "upstox"
UPSTOX_INSTRUMENT_TEST_URL = "https://api.upstox.com/v2/instruments/NSE_EQ.json.gz"


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

        request = urllib.request.Request(
            UPSTOX_INSTRUMENT_TEST_URL,
            headers={"User-Agent": "OpenAnalytics/1.0"}
        )

        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                is_successful_response = 200 <= response.status < 300
        except urllib.error.URLError:
            is_successful_response = False

        if not is_successful_response:
            conn.execute("""
                UPDATE external_connections
                SET
                    connection_status = 'failed',
                    last_tested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [current_user["user_id"], connection_id])

            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to reach Upstox instrument registry."
            )

        conn.execute("""
            UPDATE external_connections
            SET
                connection_status = 'connected',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [current_user["user_id"], connection_id])

        conn.commit()

        return {
            "status": "success",
            "message": "Upstox connection verified successfully."
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