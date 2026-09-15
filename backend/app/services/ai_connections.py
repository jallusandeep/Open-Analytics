"""Admin-managed AI connections; credentials never leave the backend."""
import json
import os
import socket
import threading
import urllib.error
import urllib.parse
import urllib.request
from uuid import uuid4
from functools import wraps

from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException

from app.config import settings
from app.database import DB_PATH, get_connection


PUBLIC_COLUMNS = "connection_id, name, provider, model, is_default, connection_status, last_tested_at, created_at, updated_at, updated_by"
PUBLIC_KEYS = PUBLIC_COLUMNS.split(", ")
WRITE_LOCK = threading.RLock()


def serialize_write(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        with WRITE_LOCK:
            return function(*args, **kwargs)
    return wrapped


def credential_cipher():
    key = settings.CONNECTION_ENCRYPTION_KEY.strip()
    if not key:
        # Persist independently of login secrets, beside the persistent database.
        key_file = DB_PATH.parent / ".ai-credentials.key"
        try:
            with WRITE_LOCK:
                if not key_file.exists():
                    key_file.parent.mkdir(parents=True, exist_ok=True)
                    descriptor = os.open(key_file, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                    with os.fdopen(descriptor, "wb") as output:
                        output.write(Fernet.generate_key())
                key = key_file.read_bytes()
        except OSError:
            raise HTTPException(503, "Unable to access the AI encryption key. Configure CONNECTION_ENCRYPTION_KEY on the server.") from None
    try:
        return Fernet(key)
    except (ValueError, TypeError):
        raise HTTPException(503, "Invalid server CONNECTION_ENCRYPTION_KEY configuration.") from None


def list_ai_connections():
    conn = get_connection()
    try:
        rows = conn.execute(f"SELECT {PUBLIC_COLUMNS} FROM ai_connections ORDER BY is_default DESC, name, connection_id").fetchall()
        return {"connections": [{**dict(zip(PUBLIC_KEYS, row)), "has_api_key": True} for row in rows]}
    finally:
        conn.close()


@serialize_write
def save_ai_connection(payload, user, connection_id=None):
    conn = get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        existing = None
        if connection_id:
            existing = conn.execute("SELECT encrypted_api_key, is_default, provider FROM ai_connections WHERE connection_id = ?", [connection_id]).fetchone()
            if not existing:
                raise HTTPException(404, "AI connection not found.")
            if existing[2] != payload.provider:
                raise HTTPException(400, "Create a new connection to change the provider.")
        api_key = (payload.api_key or "").strip()
        if not api_key and not existing:
            raise HTTPException(400, "API key is required for a new connection.")
        if any(char.isspace() for char in api_key):
            raise HTTPException(400, "API key must not contain whitespace.")
        encrypted = credential_cipher().encrypt(api_key.encode()).decode() if api_key else existing[0]
        is_default = payload.is_default or bool(existing and existing[1]) or not conn.execute("SELECT COUNT(*) FROM ai_connections WHERE is_default = TRUE").fetchone()[0]
        if is_default:
            conn.execute("UPDATE ai_connections SET is_default = FALSE WHERE is_default = TRUE")
        connection_id = connection_id or str(uuid4())
        values = [payload.name, payload.provider, payload.model, encrypted, is_default, user["user_id"]]
        if existing:
            conn.execute("""UPDATE ai_connections SET name=?, provider=?, model=?, encrypted_api_key=?,
                is_default=?, updated_by=?, connection_status='saved', last_tested_at=NULL,
                updated_at=CURRENT_TIMESTAMP WHERE connection_id=?""", values + [connection_id])
        else:
            conn.execute("""INSERT INTO ai_connections (name, provider, model, encrypted_api_key,
                is_default, updated_by, connection_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", values + [connection_id, user["user_id"]])
        conn.commit()
        return {"status": "success", "message": "AI connection saved.", "connection_id": connection_id}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@serialize_write
def select_default(connection_id, user):
    conn = get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        if not conn.execute("SELECT 1 FROM ai_connections WHERE connection_id=?", [connection_id]).fetchone():
            raise HTTPException(404, "AI connection not found.")
        conn.execute("UPDATE ai_connections SET is_default=FALSE WHERE is_default=TRUE")
        conn.execute("UPDATE ai_connections SET is_default=TRUE, updated_by=?, updated_at=CURRENT_TIMESTAMP WHERE connection_id=?", [user["user_id"], connection_id])
        conn.commit()
        return {"status": "success", "message": "Default AI connection updated."}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@serialize_write
def delete_ai_connection(connection_id):
    conn = get_connection()
    try:
        conn.execute("BEGIN TRANSACTION")
        removed = conn.execute("DELETE FROM ai_connections WHERE connection_id=? RETURNING is_default", [connection_id]).fetchone()
        if not removed:
            raise HTTPException(404, "AI connection not found.")
        if removed[0]:
            replacement = conn.execute("SELECT connection_id FROM ai_connections ORDER BY created_at, connection_id LIMIT 1").fetchone()
            if replacement:
                conn.execute("UPDATE ai_connections SET is_default=TRUE WHERE connection_id=?", [replacement[0]])
        conn.commit()
        return {"status": "success", "message": "AI connection deleted."}
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_query_connection(connection_id=None):
    conn = get_connection()
    try:
        where, params = ("connection_id=?", [connection_id]) if connection_id else ("is_default=TRUE", [])
        row = conn.execute(f"SELECT {PUBLIC_COLUMNS}, encrypted_api_key FROM ai_connections WHERE {where} LIMIT 1", params).fetchone()
        if not row:
            raise HTTPException(404, "No AI connection configured. Add a default connection first.")
        result = dict(zip(PUBLIC_KEYS, row[:-1]))
        try:
            result["api_key"] = credential_cipher().decrypt(row[-1].encode()).decode()
        except InvalidToken:
            raise HTTPException(503, "Unable to decrypt this AI key. Restore the server encryption key or replace the saved API key.") from None
        return result
    finally:
        conn.close()


def provider_request(connection, *, page_token=None, list_models=False):
    headers = {"Content-Type": "application/json"}
    model = urllib.parse.quote(connection.get("model", ""), safe="")
    if connection["provider"] == "openai":
        headers["Authorization"] = "Bearer " + connection["api_key"]
        url = "https://api.openai.com/v1/models" + ("" if list_models else f"/{model}")
    else:
        headers["x-goog-api-key"] = connection["api_key"]
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        if list_models:
            params = {"pageSize": 1000}
            if page_token:
                params["pageToken"] = page_token
            url += "?" + urllib.parse.urlencode(params)
        else:
            url += f"/{model}"
    request = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(2 * 1024 * 1024 + 1)
            if len(raw) > 2 * 1024 * 1024:
                raise HTTPException(502, "AI provider returned an oversized response.")
            return json.loads(raw)
    except urllib.error.HTTPError as error:
        messages = {401: "API key was rejected.", 403: "API key does not have permission for this model.",
                    404: "Model was not found or is not available to this key.", 429: "Provider rate limit or quota exceeded."}
        raise HTTPException(502, messages.get(error.code, "AI provider rejected the request. Check the model and provider configuration.")) from None
    except (urllib.error.URLError, TimeoutError, socket.timeout):
        raise HTTPException(502, "AI provider could not be reached or timed out.") from None
    except (ValueError, UnicodeError):
        raise HTTPException(502, "AI provider returned an invalid response.") from None


def test_ai_connection(connection_id):
    connection = get_query_connection(connection_id)
    status = "connected"
    try:
        provider_request(connection)
    except HTTPException:
        status = "failed"
        raise
    finally:
        conn = get_connection()
        try:
            conn.execute("UPDATE ai_connections SET connection_status=?, last_tested_at=CURRENT_TIMESTAMP WHERE connection_id=?", [status, connection_id])
        finally:
            conn.close()
    return {"status": "success", "message": "API key and model access verified."}



def discover_models(payload):
    key = (payload.api_key or "").strip()
    if payload.connection_id:
        saved = get_query_connection(payload.connection_id)
        if saved["provider"] != payload.provider:
            raise HTTPException(400, "Provider does not match the saved connection.")
        key = key or saved["api_key"]
    if not key or any(char.isspace() for char in key):
        raise HTTPException(400, "Enter a valid API key to load models.")
    connection = {"provider": payload.provider, "api_key": key}
    models = {}
    token = None
    seen_tokens = set()
    while True:
        response = provider_request(connection, list_models=True, page_token=token)
        if not isinstance(response, dict):
            raise HTTPException(502, "AI provider returned an invalid model list.")
        for item in response.get("data" if payload.provider == "openai" else "models", []):
            if payload.provider == "gemini" and "generateContent" not in item.get("supportedGenerationMethods", []):
                continue
            name = item.get("id") if payload.provider == "openai" else item.get("name", "").removeprefix("models/")
            if name:
                models[name] = {"value": name, "label": name}
        token = response.get("nextPageToken") if payload.provider == "gemini" else None
        if not token:
            break
        if token in seen_tokens or len(seen_tokens) >= 20:
            raise HTTPException(502, "AI provider returned an invalid model pagination response.")
        seen_tokens.add(token)
    return {"models": [models[key] for key in sorted(models)]}
