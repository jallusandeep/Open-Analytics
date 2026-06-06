from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

from app.config import settings
from app.database import get_connection


security = HTTPBearer()


def safe_touch_session_last_seen(session_id: str):
    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE user_sessions
            SET last_seen_at = CURRENT_TIMESTAMP
            WHERE session_id = ?
            """,
            [session_id]
        )
        conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
    finally:
        conn.close()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )

    conn = get_connection()

    try:
        session = conn.execute(
            """
            SELECT session_id
            FROM user_sessions
            WHERE user_id = ?
              AND access_token = ?
              AND COALESCE(is_active, TRUE) = TRUE
              AND (
                expires_at IS NULL
                OR expires_at >= CURRENT_TIMESTAMP
              )
            LIMIT 1
            """,
            [user_id, token]
        ).fetchone()

        if not session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session expired or logged out"
            )

        user = conn.execute(
            """
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                created_at
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D'
            """,
            [user_id]
        ).fetchone()

    finally:
        conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )

    (
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        role,
        access_restrictions,
        is_active,
        created_at
    ) = user

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    safe_touch_session_last_seen(session[0])

    return {
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name,
        "email": email,
        "mobile_number": mobile_number,
        "role": role,
        "access_restrictions": access_restrictions,
        "is_active": is_active,
        "created_at": str(created_at)
    }


def require_admin_or_super_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

    return current_user


def require_super_admin(current_user: dict = Depends(get_current_user)):
    if current_user["role"] != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required"
        )

    return current_user