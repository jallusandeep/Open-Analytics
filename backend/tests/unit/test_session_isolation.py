import duckdb
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.user_routes import router
from app.dependencies import get_current_user
from app.security import create_access_token
from app.services import auth_service

pytestmark = pytest.mark.unit


def test_each_login_token_is_unique():
    claims = {"sub": "trader-one", "role": "user"}
    assert create_access_token(claims) != create_access_token(claims)


def test_logout_only_revokes_the_calling_session(monkeypatch):
    conn = duckdb.connect(":memory:")
    conn.execute("""CREATE TABLE user_sessions (
        session_id VARCHAR, user_id VARCHAR, is_active BOOLEAN,
        logged_out_at TIMESTAMP, last_seen_at TIMESTAMP
    )""")
    conn.execute("""INSERT INTO user_sessions VALUES
        ('session-a', 'trader-one', TRUE, NULL, CURRENT_TIMESTAMP),
        ('session-b', 'trader-one', TRUE, NULL, CURRENT_TIMESTAMP),
        ('session-c', 'trader-two', TRUE, NULL, CURRENT_TIMESTAMP)
    """)

    class Connection:
        def execute(self, *args):
            return conn.execute(*args)

        def commit(self):
            conn.commit()

        def rollback(self):
            conn.rollback()

        def close(self):
            pass

    monkeypatch.setattr(auth_service, "get_connection", Connection)
    try:
        auth_service.logout_user_service("trader-one", "session-a")
        assert conn.execute("SELECT session_id, is_active FROM user_sessions ORDER BY session_id").fetchall() == [
            ("session-a", False), ("session-b", True), ("session-c", True)
        ]
        auth_service.logout_user_service("trader-one", "session-c")
        assert conn.execute("SELECT is_active FROM user_sessions WHERE session_id = 'session-c'").fetchone()[0]
    finally:
        conn.close()


@pytest.mark.parametrize("method,path,payload", [
    ("get", "/users", None),
    ("get", "/users/another-trader", None),
    ("put", "/users/another-trader", {"role": "super_admin"}),
    ("delete", "/users/another-trader", None),
    ("get", "/users/another-trader/history", None),
    ("get", "/audit-logs", None),
    ("get", "/sync-log", None),
])
def test_trader_cannot_access_user_management(method, path, payload):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: {"user_id": "trader-one", "role": "user"}
    with TestClient(app) as client:
        assert client.request(method, path, json=payload).status_code == 403
