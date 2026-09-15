import json
import urllib.error
from contextlib import contextmanager

import duckdb
import pytest
from cryptography.fernet import Fernet
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.v1.ai_connection_routes import router
from app.db.schema_ai import ensure_ai_schema
from app.dependencies import get_current_user
from app.schemas.ai_connection_schema import AiConnectionRequest, AiModelListRequest
from app.services import ai_connections as service

pytestmark = pytest.mark.unit
USER = {"user_id": "admin-test", "role": "admin"}


@pytest.fixture
def db(monkeypatch):
    conn = duckdb.connect(":memory:")
    ensure_ai_schema(conn)

    class Connection:
        def execute(self, *args):
            return conn.execute(*args)

        def commit(self):
            conn.commit()

        def rollback(self):
            conn.rollback()

        def close(self):
            pass

    monkeypatch.setattr(service, "get_connection", Connection)
    monkeypatch.setattr(service.settings, "CONNECTION_ENCRYPTION_KEY", Fernet.generate_key().decode())
    yield conn
    conn.close()


def create(provider="openai", **kwargs):
    return service.save_ai_connection(AiConnectionRequest(
        name=provider, provider=provider, model="test-model", api_key="test-secret-key", **kwargs
    ), USER)["connection_id"]


def test_multiple_same_provider_connections_and_one_default(db):
    first, second, third = create(), create(), create("gemini", is_default=True)
    assert db.execute("SELECT COUNT(*) FROM ai_connections").fetchone()[0] == 3
    assert db.execute("SELECT connection_id FROM ai_connections WHERE is_default").fetchall() == [(third,)]
    service.select_default(second, USER)
    assert db.execute("SELECT connection_id FROM ai_connections WHERE is_default").fetchall() == [(second,)]
    service.delete_ai_connection(second)
    assert db.execute("SELECT COUNT(*) FROM ai_connections WHERE is_default").fetchone()[0] == 1
    assert {row[0] for row in db.execute("SELECT connection_id FROM ai_connections").fetchall()} == {first, third}


def test_key_is_encrypted_hidden_and_retained_on_edit(db):
    connection_id = create()
    encrypted = db.execute("SELECT encrypted_api_key FROM ai_connections").fetchone()[0]
    assert "test-secret-key" not in encrypted
    listed = service.list_ai_connections()
    assert "test-secret-key" not in str(listed) and encrypted not in str(listed)
    assert listed["connections"][0]["has_api_key"]
    service.save_ai_connection(AiConnectionRequest(name="Renamed", provider="openai", model="test-model"), USER, connection_id)
    assert service.get_query_connection()["api_key"] == "test-secret-key"
    assert db.execute("SELECT is_default FROM ai_connections").fetchone()[0]


def test_failed_save_does_not_change_default(db):
    connection_id = create()
    with pytest.raises(HTTPException):
        service.save_ai_connection(AiConnectionRequest(name="Invalid", provider="gemini", model="test-model", is_default=True), USER)
    assert db.execute("SELECT connection_id FROM ai_connections WHERE is_default").fetchall() == [(connection_id,)]


@pytest.mark.parametrize("provider", ["openai", "gemini"])
def test_models_load_with_saved_key_without_exposing_credentials(db, monkeypatch, provider):
    connection_id = create(provider)
    captured = []

    @contextmanager
    def urlopen(request, timeout):
        captured.append(request)
        class Response:
            def read(self, limit):
                if provider == "openai":
                    return json.dumps({"data": [{"id": "test-model"}]}).encode()
                return json.dumps({"models": [
                    {"name": "models/test-model", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/embed", "supportedGenerationMethods": ["embedContent"]}
                ]}).encode()
        yield Response()
    monkeypatch.setattr(service.urllib.request, "urlopen", urlopen)
    response = service.discover_models(AiModelListRequest(provider=provider, connection_id=connection_id))
    assert response == {"models": [{"value": "test-model", "label": "test-model"}]}
    assert "test-secret-key" not in str(response)
    assert "test-secret-key" not in captured[0].full_url
    assert captured[0].data is None


def test_gemini_model_pagination(monkeypatch):
    calls = []
    @contextmanager
    def urlopen(request, timeout):
        calls.append(request.full_url)
        class Response:
            def read(self, limit):
                return json.dumps({"models": [{"name": f"models/model-{len(calls)}", "supportedGenerationMethods": ["generateContent"]}], **({"nextPageToken": "next"} if len(calls) == 1 else {})}).encode()
        yield Response()
    monkeypatch.setattr(service.urllib.request, "urlopen", urlopen)
    response = service.discover_models(AiModelListRequest(provider="gemini", api_key="test-key"))
    assert len(response["models"]) == 2
    assert "pageToken=next" in calls[1]


def test_provider_errors_do_not_leak_key_and_test_status_is_saved(db, monkeypatch):
    connection_id = create()

    def reject(*args, **kwargs):
        raise urllib.error.HTTPError("url", 401, "test-secret-key", {}, None)

    monkeypatch.setattr(service.urllib.request, "urlopen", reject)
    with pytest.raises(HTTPException) as error:
        service.test_ai_connection(connection_id)
    assert "test-secret-key" not in error.value.detail
    assert db.execute("SELECT connection_status FROM ai_connections").fetchone()[0] == "failed"


@pytest.mark.parametrize("user", [
    {"role": "user", "user_id": "trader"},
    {"role": "admin", "user_id": "denied", "access_restrictions": ["app:deny:admin"]},
])
@pytest.mark.parametrize("method,path", [("get", ""), ("post", "/models"), ("post", "/id/test"), ("delete", "/id")])
def test_traders_and_denied_admins_cannot_use_shared_ai_keys(user, method, path):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: user
    with TestClient(app) as client:
        response = client.request(method, "/connections/ai" + path, json={"prompt": "hello"})
    assert response.status_code == 403
