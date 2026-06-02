import json
from fastapi import APIRouter, HTTPException, Depends

from app.database import get_connection
from app.audit import save_user_history, create_sync_log, create_audit_log
from app.dependencies import get_current_user


router = APIRouter(tags=["Users"])


def parse_json_value(value):
    """
    DuckDB may return JSON as string.
    This helper converts it safely.
    """
    if value is None:
        return None

    if isinstance(value, (dict, list)):
        return value

    try:
        return json.loads(value)
    except Exception:
        return value


def user_row_to_dict(row):
    """
    Converts users table row into dictionary.
    """

    if not row:
        return None

    return {
        "user_id": row[0],
        "login_id": row[1],
        "full_name": row[2],
        "email": row[3],
        "mobile_number": row[4],
        "role": row[5],
        "access_restrictions": parse_json_value(row[6]),
        "is_active": row[7],
        "record_status": row[8],
        "version_no": row[9],
        "created_at": str(row[10]) if row[10] else None,
        "created_by": row[11],
        "updated_at": str(row[12]) if row[12] else None,
        "updated_by": row[13],
    }


@router.get("/users")
def get_users():
    """
    Get active users only.
    Soft-deleted users are hidden.
    """

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                version_no,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM users
            WHERE COALESCE(record_status, 'S') != 'D'
            ORDER BY created_at DESC;
        """).fetchall()

        return {
            "status": "success",
            "count": len(rows),
            "users": [user_row_to_dict(row) for row in rows]
        }

    finally:
        conn.close()


@router.get("/users/me")
def get_logged_in_user(current_user: dict = Depends(get_current_user)):
    """
    Get logged-in user profile.
    Frontend calls this after login.
    """

    conn = get_connection()

    try:
        user_id = current_user.get("user_id")

        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid logged-in user")

        row = conn.execute("""
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                version_no,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D';
        """, [user_id]).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "status": "success",
            "user": user_row_to_dict(row)
        }

    finally:
        conn.close()


@router.get("/users/{user_id}")
def get_user(user_id: str):
    """
    Get single user by user_id.
    """

    conn = get_connection()

    try:
        row = conn.execute("""
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                version_no,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D';
        """, [user_id]).fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="User not found")

        return {
            "status": "success",
            "user": user_row_to_dict(row)
        }

    finally:
        conn.close()


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: dict):
    """
    Update user with version control.

    Flow:
    1. Read existing user
    2. Save old row into users_history
    3. Update users table
    4. Insert sync_log
    5. Insert audit_logs
    """

    conn = get_connection()

    try:
        existing_row = conn.execute("""
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                version_no,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D';
        """, [user_id]).fetchone()

        if not existing_row:
            raise HTTPException(status_code=404, detail="User not found")

        old_user = user_row_to_dict(existing_row)

        current_version = old_user.get("version_no") or 1
        new_version = current_version + 1

        new_full_name = payload.get("full_name", old_user["full_name"])
        new_mobile_number = payload.get("mobile_number", old_user["mobile_number"])
        new_role = payload.get("role", old_user["role"])
        new_access_restrictions = payload.get(
            "access_restrictions",
            old_user["access_restrictions"]
        )
        new_is_active = payload.get("is_active", old_user["is_active"])

        changed_by = payload.get("changed_by", user_id)

        save_user_history(
            conn=conn,
            user_id=user_id,
            action_type="UPDATE",
            changed_by=changed_by
        )

        conn.execute("""
            UPDATE users
            SET
                full_name = ?,
                mobile_number = ?,
                role = ?,
                access_restrictions = ?,
                is_active = ?,
                record_status = 'U',
                version_no = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE user_id = ?;
        """, [
            new_full_name,
            new_mobile_number,
            new_role,
            json.dumps(new_access_restrictions) if new_access_restrictions is not None else None,
            new_is_active,
            new_version,
            changed_by,
            user_id
        ])

        new_user = {
            **old_user,
            "full_name": new_full_name,
            "mobile_number": new_mobile_number,
            "role": new_role,
            "access_restrictions": new_access_restrictions,
            "is_active": new_is_active,
            "record_status": "U",
            "version_no": new_version,
            "updated_by": changed_by
        }

        create_sync_log(
            conn=conn,
            table_name="users",
            record_id=user_id,
            action_type="UPDATE",
            version_no=new_version,
            changed_by=changed_by
        )

        create_audit_log(
            conn=conn,
            user_id=changed_by,
            action="UPDATE_USER",
            table_name="users",
            record_id=user_id,
            old_value=old_user,
            new_value=new_user
        )

        conn.commit()

        return {
            "status": "success",
            "message": "User updated successfully",
            "user_id": user_id,
            "version_no": new_version
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


@router.delete("/users/{user_id}")
def delete_user(user_id: str, changed_by: str | None = None):
    """
    Soft delete user with version control.
    It does not remove the row.
    It marks record_status = D and is_active = FALSE.
    """

    conn = get_connection()

    try:
        existing_row = conn.execute("""
            SELECT
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                version_no,
                created_at,
                created_by,
                updated_at,
                updated_by
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D';
        """, [user_id]).fetchone()

        if not existing_row:
            raise HTTPException(status_code=404, detail="User not found")

        old_user = user_row_to_dict(existing_row)

        current_version = old_user.get("version_no") or 1
        new_version = current_version + 1

        changed_by_user = changed_by or user_id

        save_user_history(
            conn=conn,
            user_id=user_id,
            action_type="DELETE",
            changed_by=changed_by_user
        )

        conn.execute("""
            UPDATE users
            SET
                record_status = 'D',
                is_active = FALSE,
                version_no = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE user_id = ?;
        """, [
            new_version,
            changed_by_user,
            user_id
        ])

        deleted_user = {
            **old_user,
            "record_status": "D",
            "is_active": False,
            "version_no": new_version,
            "updated_by": changed_by_user
        }

        create_sync_log(
            conn=conn,
            table_name="users",
            record_id=user_id,
            action_type="DELETE",
            version_no=new_version,
            changed_by=changed_by_user
        )

        create_audit_log(
            conn=conn,
            user_id=changed_by_user,
            action="DELETE_USER",
            table_name="users",
            record_id=user_id,
            old_value=old_user,
            new_value=deleted_user
        )

        conn.commit()

        return {
            "status": "success",
            "message": "User deleted successfully",
            "user_id": user_id,
            "version_no": new_version
        }

    except HTTPException:
        conn.rollback()
        raise

    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        conn.close()


@router.get("/users/{user_id}/history")
def get_user_history(user_id: str):
    """
    Shows all previous versions of a user.
    """

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                history_id,
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                record_status,
                action_type,
                version_no,
                changed_at,
                changed_by
            FROM users_history
            WHERE user_id = ?
            ORDER BY changed_at DESC;
        """, [user_id]).fetchall()

        history = []

        for row in rows:
            history.append({
                "history_id": row[0],
                "user_id": row[1],
                "login_id": row[2],
                "full_name": row[3],
                "email": row[4],
                "mobile_number": row[5],
                "role": row[6],
                "access_restrictions": parse_json_value(row[7]),
                "is_active": row[8],
                "record_status": row[9],
                "action_type": row[10],
                "version_no": row[11],
                "changed_at": str(row[12]) if row[12] else None,
                "changed_by": row[13]
            })

        return {
            "status": "success",
            "user_id": user_id,
            "count": len(history),
            "history": history
        }

    finally:
        conn.close()


@router.get("/sync-log")
def get_sync_log():
    """
    Shows sync/version changes.
    """

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                sync_id,
                table_name,
                record_id,
                action_type,
                version_no,
                changed_at,
                changed_by,
                device_id
            FROM sync_log
            ORDER BY changed_at DESC;
        """).fetchall()

        logs = []

        for row in rows:
            logs.append({
                "sync_id": row[0],
                "table_name": row[1],
                "record_id": row[2],
                "action_type": row[3],
                "version_no": row[4],
                "changed_at": str(row[5]) if row[5] else None,
                "changed_by": row[6],
                "device_id": row[7]
            })

        return {
            "status": "success",
            "count": len(logs),
            "logs": logs
        }

    finally:
        conn.close()


@router.get("/audit-logs")
def get_audit_logs():
    """
    Shows readable audit logs.
    """

    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                audit_id,
                user_id,
                action,
                table_name,
                record_id,
                old_value,
                new_value,
                created_at
            FROM audit_logs
            ORDER BY created_at DESC;
        """).fetchall()

        logs = []

        for row in rows:
            logs.append({
                "audit_id": row[0],
                "user_id": row[1],
                "action": row[2],
                "table_name": row[3],
                "record_id": row[4],
                "old_value": parse_json_value(row[5]),
                "new_value": parse_json_value(row[6]),
                "created_at": str(row[7]) if row[7] else None
            })

        return {
            "status": "success",
            "count": len(logs),
            "logs": logs
        }

    finally:
        conn.close()