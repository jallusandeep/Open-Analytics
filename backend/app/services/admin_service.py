import json
import math
import uuid
from fastapi import HTTPException, status

from app.database import get_connection
from app.security import hash_password


VALID_ROLES = ["user", "admin", "super_admin"]


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

    filters = []
    params = []

    if search:
        search_value = f"%{search.lower()}%"
        filters.append("""
            (
                lower(coalesce(login_id, '')) LIKE ?
                OR lower(coalesce(email, '')) LIKE ?
                OR lower(coalesce(full_name, '')) LIKE ?
                OR lower(coalesce(mobile_number, '')) LIKE ?
                OR lower(coalesce(role, '')) LIKE ?
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
        filters.append("role = ?")
        params.append(role)

    if is_active is not None:
        filters.append("is_active = ?")
        params.append(is_active)

    where_clause = ""
    if filters:
        where_clause = "WHERE " + " AND ".join(filters)

    conn = get_connection()

    total_records = conn.execute(
        f"SELECT COUNT(*) FROM users {where_clause}",
        params
    ).fetchone()[0]

    rows = conn.execute(
        f"""
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
            updated_at
        FROM users
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ?
        OFFSET ?
        """,
        params + [page_size, offset]
    ).fetchall()

    conn.close()

    users = []
    for row in rows:
        users.append({
            "user_id": row[0],
            "login_id": row[1],
            "full_name": row[2],
            "email": row[3],
            "mobile_number": row[4],
            "role": row[5],
            "access_restrictions": row[6],
            "is_active": row[7],
            "created_at": str(row[8]),
            "updated_at": str(row[9])
        })

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

    conn = get_connection()

    existing = conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE email = ? OR login_id = ?
        """,
        [request.email, request.login_id]
    ).fetchone()

    if existing:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email or Login ID already exists"
        )

    user_id = str(uuid.uuid4())
    password_hash = hash_password(request.password)

    access_restrictions = None
    if request.role == "user":
        access_restrictions = json.dumps(request.access_restrictions or [])

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
            request.login_id,
            request.full_name,
            request.email,
            request.mobile_number,
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
            updated_at
        FROM users
        WHERE user_id = ?
        """,
        [user_id]
    ).fetchone()

    conn.close()

    return {
        "user_id": created_user[0],
        "login_id": created_user[1],
        "full_name": created_user[2],
        "email": created_user[3],
        "mobile_number": created_user[4],
        "role": created_user[5],
        "access_restrictions": created_user[6],
        "is_active": created_user[7],
        "created_at": str(created_user[8]),
        "updated_at": str(created_user[9])
    }


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
        """,
        [user_id]
    ).fetchone()

    if not target_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    target_user_id, target_role = target_user

    if current_user["role"] == "admin" and target_role in ["admin", "super_admin"]:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot delete admin or super admin"
        )

    conn.execute(
        """
        UPDATE users
        SET is_active = FALSE,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ?
        """,
        [user_id]
    )

    conn.close()

    return {
        "message": "User deactivated successfully",
        "user_id": user_id
    }   