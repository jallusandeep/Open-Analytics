import json
import math
import random
import string
import uuid

from fastapi import HTTPException, status

from app.database import get_connection
from app.security import hash_password
from app.telegram_alerts_msg.message_templates import build_user_account_updated_message
from app.telegram_alerts_msg.telegram_sender import send_user_telegram_alert


VALID_ROLES = ["user", "admin", "super_admin"]
LOGIN_ID_PREFIX_LENGTH = 5
LOGIN_ID_SUFFIX_LENGTH = 5
LOGIN_ID_GENERATION_ATTEMPTS = 50


def generate_candidate_login_id() -> str:
    prefix = "".join(random.choices(string.digits, k=LOGIN_ID_PREFIX_LENGTH))
    suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=LOGIN_ID_SUFFIX_LENGTH)
    )

    return f"{prefix}{suffix}"


def generate_unique_login_id(conn) -> str:
    for _ in range(LOGIN_ID_GENERATION_ATTEMPTS):
        login_id = generate_candidate_login_id()

        existing = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE login_id = ?
            """,
            [login_id]
        ).fetchone()

        if not existing:
            return login_id

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate unique login ID"
    )


def serialize_user_row(row):
    session_status = row[10] if len(row) > 10 else "offline"
    last_seen_at = row[11] if len(row) > 11 else None

    return {
        "user_id": row[0],
        "login_id": row[1],
        "full_name": row[2],
        "email": row[3],
        "mobile_number": row[4],
        "role": row[5],
        "access_restrictions": row[6],
        "is_active": row[7],
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
        "session_status": session_status or "offline",
        "last_seen_at": str(last_seen_at) if last_seen_at else None
    }


def list_users_service(
    page: int,
    page_size: int,
    search: str,
    role: str,
    is_active
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    filters = ["COALESCE(u.record_status, 'S') != 'D'"]
    params = []

    if search:
        search_value = f"%{search.lower()}%"
        filters.append("""
            (
                lower(coalesce(u.login_id, '')) LIKE ?
                OR lower(coalesce(u.email, '')) LIKE ?
                OR lower(coalesce(u.full_name, '')) LIKE ?
                OR lower(coalesce(u.mobile_number, '')) LIKE ?
                OR lower(coalesce(u.role, '')) LIKE ?
            )
        """)
        params.extend([
            search_value,
            search_value,
            search_value,
            search_value,
            search_value
        ])

    if role and role != "all":
        filters.append("u.role = ?")
        params.append(role)

    if is_active is not None:
        filters.append("u.is_active = ?")
        params.append(is_active)

    where_clause = "WHERE " + " AND ".join(filters)

    conn = get_connection()

    total_records = conn.execute(
        f"SELECT COUNT(*) FROM users u {where_clause}",
        params
    ).fetchone()[0]

    rows = conn.execute(
        f"""
        WITH active_sessions AS (
            SELECT
                user_id,
                COUNT(*) AS active_session_count,
                MAX(last_seen_at) AS last_seen_at
            FROM user_sessions
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND (
                expires_at IS NULL
                OR expires_at >= CURRENT_TIMESTAMP
              )
            GROUP BY user_id
        )
        SELECT
            u.user_id,
            u.login_id,
            u.full_name,
            u.email,
            u.mobile_number,
            u.role,
            CAST(u.access_restrictions AS VARCHAR),
            u.is_active,
            u.created_at,
            u.updated_at,
            CASE
                WHEN COALESCE(s.active_session_count, 0) > 0 THEN 'online'
                ELSE 'offline'
            END AS session_status,
            s.last_seen_at
        FROM users u
        LEFT JOIN active_sessions s
            ON s.user_id = u.user_id
        {where_clause}
        ORDER BY u.created_at DESC
        LIMIT ?
        OFFSET ?
        """,
        params + [page_size, offset]
    ).fetchall()

    conn.close()

    users = [serialize_user_row(row) for row in rows]

    total_pages = math.ceil(total_records / page_size) if total_records else 1

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "users": users
    }


def create_user_service(request, current_user):
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role"
        )

    if current_user["role"] == "admin" and request.role in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin can create only normal users"
        )

    clean_email = request.email.strip().lower()
    clean_mobile_number = request.mobile_number.strip() if request.mobile_number else None

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE (
            LOWER(email) = ?
            OR (
                ? IS NOT NULL
                AND mobile_number = ?
            )
        )
        AND COALESCE(record_status, 'S') != 'D'
        """,
        [clean_email, clean_mobile_number, clean_mobile_number]
    ).fetchone()

    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or mobile number already exists"
        )

    user_id = str(uuid.uuid4())
    login_id = generate_unique_login_id(conn)
    password_hash = hash_password(request.password)

    access_restrictions = None

    if request.role == "user":
        access_restrictions = json.dumps(
            request.access_restrictions or []
        )

    conn.execute(
        """
        INSERT INTO users (
            user_id,
            login_id,
            full_name,
            email,
            mobile_number,
            password_hash,
            role,
            access_restrictions,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            login_id,
            request.full_name.strip(),
            clean_email,
            clean_mobile_number,
            password_hash,
            request.role,
            access_restrictions,
            True
        ]
    )

    created_user = conn.execute(
        """
        SELECT
            user_id,
            login_id,
            full_name,
            email,
            mobile_number,
            role,
            CAST(access_restrictions AS VARCHAR),
            is_active,
            created_at,
            updated_at,
            'offline' AS session_status,
            NULL AS last_seen_at
        FROM users
        WHERE user_id = ?
        """,
        [user_id]
    ).fetchone()

    conn.close()

    return serialize_user_row(created_user)


def update_user_service(user_id: str, request, current_user: dict):
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role"
        )

    clean_email = request.email.strip().lower()
    clean_mobile_number = request.mobile_number.strip() if request.mobile_number else None
    is_self_update = user_id == current_user["user_id"]

    conn = get_connection()

    target_user = conn.execute(
        """
        SELECT
            user_id,
            login_id,
            role,
            is_active
        FROM users
        WHERE user_id = ?
          AND COALESCE(record_status, 'S') != 'D'
        """,
        [user_id]
    ).fetchone()

    if not target_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    target_role = target_user[2]
    target_is_active = target_user[3]

    if is_self_update and (
        request.role != target_role
        or request.is_active != target_is_active
    ):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role or active status"
        )

    if (
        current_user["role"] == "admin"
        and target_role == "super_admin"
    ):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot edit super admin"
        )

    if (
        current_user["role"] == "admin"
        and request.role in ["admin", "super_admin"]
        and (not is_self_update or request.role != target_role)
    ):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot assign admin roles"
        )

    existing_user = conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE (
            LOWER(email) = ?
            OR (
                ? IS NOT NULL
                AND mobile_number = ?
            )
        )
        AND user_id != ?
        AND COALESCE(record_status, 'S') != 'D'
        """,
        [
            clean_email,
            clean_mobile_number,
            clean_mobile_number,
            user_id
        ]
    ).fetchone()

    if existing_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or mobile number already exists"
        )

    access_restrictions = None

    if request.role == "user":
        access_restrictions = json.dumps(
            request.access_restrictions or []
        )

    clean_password = request.password.strip() if request.password else ""

    if clean_password:
        conn.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                email = ?,
                mobile_number = ?,
                password_hash = ?,
                role = ?,
                access_restrictions = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            [
                request.full_name.strip(),
                clean_email,
                clean_mobile_number,
                hash_password(clean_password),
                request.role,
                access_restrictions,
                request.is_active,
                user_id
            ]
        )
    else:
        conn.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                email = ?,
                mobile_number = ?,
                role = ?,
                access_restrictions = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            [
                request.full_name.strip(),
                clean_email,
                clean_mobile_number,
                request.role,
                access_restrictions,
                request.is_active,
                user_id
            ]
        )

    if not request.is_active:
        conn.execute(
            """
            UPDATE user_sessions
            SET
                is_active = FALSE,
                logged_out_at = CURRENT_TIMESTAMP,
                last_seen_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND COALESCE(is_active, TRUE) = TRUE
            """,
            [user_id]
        )

    updated_user = conn.execute(
        """
        WITH active_sessions AS (
            SELECT
                user_id,
                COUNT(*) AS active_session_count,
                MAX(last_seen_at) AS last_seen_at
            FROM user_sessions
            WHERE COALESCE(is_active, TRUE) = TRUE
              AND (
                expires_at IS NULL
                OR expires_at >= CURRENT_TIMESTAMP
              )
              AND user_id = ?
            GROUP BY user_id
        )
        SELECT
            u.user_id,
            u.login_id,
            u.full_name,
            u.email,
            u.mobile_number,
            u.role,
            CAST(u.access_restrictions AS VARCHAR),
            u.is_active,
            u.created_at,
            u.updated_at,
            CASE
                WHEN COALESCE(s.active_session_count, 0) > 0 THEN 'online'
                ELSE 'offline'
            END AS session_status,
            s.last_seen_at
        FROM users u
        LEFT JOIN active_sessions s
            ON s.user_id = u.user_id
        WHERE u.user_id = ?
        """,
        [user_id, user_id]
    ).fetchone()

    conn.close()

    send_user_telegram_alert(
        user_id=user_id,
        message=build_user_account_updated_message(serialize_user_row(updated_user))
    )

    return serialize_user_row(updated_user)


def delete_user_service(user_id: str, current_user: dict):
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )

    conn = get_connection()

    target_user = conn.execute(
        """
        SELECT user_id, role
        FROM users
        WHERE user_id = ?
          AND COALESCE(record_status, 'S') != 'D'
        """,
        [user_id]
    ).fetchone()

    if not target_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    target_role = target_user[1]

    if current_user["role"] == "admin" and target_role in ["admin", "super_admin"]:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot delete admin or super admin"
        )

    conn.execute(
        """
        DELETE FROM user_sessions
        WHERE user_id = ?
        """,
        [user_id]
    )

    conn.execute(
        """
        DELETE FROM users
        WHERE user_id = ?
        """,
        [user_id]
    )

    conn.close()

    return {
        "message": "User permanently deleted successfully",
        "user_id": user_id
    }