from unittest.mock import Mock

import duckdb
import pytest

from app import database

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("message,expected", [
    ("Cannot open file: being used by another process", True),
    ("Cannot open file: file is already open", True),
    ("Unique file handle conflict: already attached", True),
    ("Failed to delete file test.wal: access is denied", True),
    ("Cannot open file: permission denied", False),
    ("Table does not exist", False),
])
def test_lock_error_classification(message, expected):
    assert database.is_transient_duckdb_lock_error(Exception(message)) == expected


def test_connection_retries_transient_lock(monkeypatch):
    connection = Mock()
    connect = Mock(side_effect=[duckdb.IOException("Cannot open file: file is already open"), connection])
    sleep = Mock()
    monkeypatch.setattr(database.duckdb, "connect", connect)
    monkeypatch.setattr(database.time, "sleep", sleep)
    assert database.get_connection() is connection
    assert connect.call_count == 2
    sleep.assert_called_once()


def test_connection_does_not_retry_unrelated_errors(monkeypatch):
    connect = Mock(side_effect=duckdb.IOException("Permission denied"))
    monkeypatch.setattr(database.duckdb, "connect", connect)
    with pytest.raises(duckdb.IOException):
        database.get_connection()
    connect.assert_called_once()


def test_retry_exhaustion_is_bounded(monkeypatch):
    connect = Mock(side_effect=duckdb.IOException("Cannot open file: file is already open"))
    monkeypatch.setattr(database.duckdb, "connect", connect)
    monkeypatch.setattr(database, "DB_CONNECT_RETRY_ATTEMPTS", 3)
    monkeypatch.setattr(database.time, "sleep", Mock())
    with pytest.raises(duckdb.IOException):
        database.get_connection()
    assert connect.call_count == 3
