import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.database import get_connection
from app.dependencies import get_current_user


router = APIRouter(prefix="/table-views", tags=["Table Views"])


class TableViewRequest(BaseModel):
    table_id: str = Field(min_length=1, max_length=2000)
    name: str = Field(min_length=1, max_length=80)
    columns: list[str] = Field(min_length=1, max_length=300)
    is_default: bool = False
    is_shared: bool = False


def ensure_table():
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS table_views (
                view_id VARCHAR PRIMARY KEY,
                table_id VARCHAR NOT NULL,
                owner_user_id VARCHAR NOT NULL,
                name VARCHAR NOT NULL,
                columns_json JSON NOT NULL,
                is_default BOOLEAN NOT NULL DEFAULT FALSE,
                is_shared BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    finally:
        conn.close()


@router.get("")
def list_table_views(table_id: str = Query(min_length=1, max_length=2000), current_user: dict = Depends(get_current_user)):
    ensure_table()
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT v.view_id, v.name, v.columns_json, v.is_default, v.is_shared, v.owner_user_id,
                   COALESCE(NULLIF(TRIM(u.full_name), ''), u.email, v.owner_user_id)
            FROM table_views
            v LEFT JOIN users u ON u.user_id = v.owner_user_id
            WHERE table_id = ? AND (is_shared = TRUE OR owner_user_id = ?)
            ORDER BY is_shared DESC, name
        """, [table_id, current_user["user_id"]]).fetchall()
        return {"views": [{
            "id": row[0], "name": row[1], "columns": json.loads(row[2]) if isinstance(row[2], str) else row[2],
            "default": bool(row[3]), "shared": bool(row[4]), "owner": row[5] == current_user["user_id"], "ownerName": row[6]
        } for row in rows]}
    finally:
        conn.close()


@router.post("")
def save_table_view(payload: TableViewRequest, current_user: dict = Depends(get_current_user)):
    ensure_table()
    conn = get_connection()
    try:
        duplicate = conn.execute("""
            SELECT view_id FROM table_views
            WHERE table_id = ? AND lower(name) = lower(?) AND (owner_user_id = ? OR is_shared = TRUE)
        """, [payload.table_id, payload.name.strip(), current_user["user_id"]]).fetchone()
        if duplicate:
            raise HTTPException(status_code=409, detail="A view with this name already exists.")
        if payload.is_default:
            conn.execute("UPDATE table_views SET is_default = FALSE WHERE table_id = ? AND owner_user_id = ?", [payload.table_id, current_user["user_id"]])
        view_id = str(uuid4())
        conn.execute("""
            INSERT INTO table_views (view_id, table_id, owner_user_id, name, columns_json, is_default, is_shared)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [view_id, payload.table_id, current_user["user_id"], payload.name.strip(), json.dumps(payload.columns), payload.is_default, payload.is_shared])
        conn.commit()
        return {"id": view_id, "name": payload.name.strip(), "columns": payload.columns, "default": payload.is_default, "shared": payload.is_shared, "owner": True, "ownerName": current_user.get("full_name") or current_user.get("email") or current_user["user_id"]}
    finally:
        conn.close()
