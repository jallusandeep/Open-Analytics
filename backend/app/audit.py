import uuid
import json
from typing import Any


def to_json(value: Any):
    if value is None:
        return None

    if isinstance(value, str):
        return value

    return json.dumps(value)


def create_sync_log(
    conn,
    table_name: str,
    record_id: str,
    action_type: str,
    version_no: int,
    changed_by: str | None = None,
    device_id: str | None = None
):
    conn.execute("""
        INSERT INTO sync_log (
            sync_id,
            table_name,
            record_id,
            action_type,
            version_no,
            changed_by,
            device_id
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
        str(uuid.uuid4()),
        table_name,
        record_id,
        action_type,
        version_no,
        changed_by,
        device_id
    ])


def save_user_history(
    conn,
    user_id: str,
    action_type: str,
    changed_by: str | None = None
):
    conn.execute("""
        INSERT INTO users_history (
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
            changed_by
        )
        SELECT
            ?,
            user_id,
            login_id,
            full_name,
            email,
            mobile_number,
            role,
            access_restrictions,
            is_active,
            'H',
            ?,
            version_no,
            ?
        FROM users
        WHERE user_id = ?;
    """, [
        str(uuid.uuid4()),
        action_type,
        changed_by,
        user_id
    ])


def create_audit_log(
    conn,
    user_id: str | None,
    action: str,
    table_name: str,
    record_id: str,
    old_value: Any = None,
    new_value: Any = None
):
    conn.execute("""
        INSERT INTO audit_logs (
            audit_id,
            user_id,
            action,
            table_name,
            record_id,
            old_value,
            new_value
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
    """, [
        str(uuid.uuid4()),
        user_id,
        action,
        table_name,
        record_id,
        to_json(old_value),
        to_json(new_value)
    ])