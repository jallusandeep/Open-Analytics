from datetime import date

import duckdb
import pytest

from app.db.schema_instruments import ensure_instrument_schema
from app.services.instrument_expiry import archive_expired_instruments

pytestmark = pytest.mark.unit


@pytest.fixture
def conn():
    database = duckdb.connect(":memory:")
    def safe_execute(connection, sql):
        connection.execute(sql.replace("ADD COLUMN ", "ADD COLUMN IF NOT EXISTS "))
    ensure_instrument_schema(database, safe_execute)
    yield database
    database.close()


def test_archives_only_past_expiry_and_preserves_metadata(conn):
    conn.execute("""INSERT INTO upstox_instruments
        (instrument_key, expiry, name, strike_price, raw_json, source_type)
        VALUES ('past', '2026-09-13', 'Contract', 123.45, '{"isin":"original"}', 'bod_complete'),
               ('today', '2026-09-14', NULL, NULL, NULL, NULL),
               ('future', '2026-09-15', NULL, NULL, NULL, NULL),
               ('equity', NULL, NULL, NULL, NULL, NULL)""")
    archive_expired_instruments(conn, today=date(2026, 9, 14))
    assert conn.execute("SELECT instrument_key FROM upstox_instruments ORDER BY 1").fetchall() == [
        ('equity',), ('future',), ('today',)
    ]
    assert conn.execute("SELECT name, strike_price, raw_json, source_type FROM upstox_expired_instruments").fetchone() == (
        'Contract', 123.45, '{"isin":"original"}', 'bod_complete'
    )


def test_repeat_refresh_does_not_duplicate_or_overwrite_archive(conn):
    conn.execute("INSERT INTO upstox_expired_instruments (instrument_key, expiry, name) VALUES ('past', '2026-09-13', 'Existing')")
    conn.execute("INSERT INTO upstox_instruments (instrument_key, expiry, name) VALUES ('past', '2026-09-13', 'Master'), ('new', '2026-09-13', 'New'), ('new', '2026-09-13', 'New')")
    archive_expired_instruments(conn, today=date(2026, 9, 14))
    archive_expired_instruments(conn, today=date(2026, 9, 14))
    assert conn.execute("SELECT name FROM upstox_expired_instruments ORDER BY instrument_key").fetchall() == [('New',), ('Existing',)]
    assert conn.execute("SELECT COUNT(*) FROM upstox_instruments").fetchone()[0] == 0


def test_archive_participates_in_refresh_transaction(conn):
    conn.execute("INSERT INTO upstox_instruments (instrument_key, expiry) VALUES ('past', '2026-09-13')")
    conn.execute("BEGIN TRANSACTION")
    archive_expired_instruments(conn, today=date(2026, 9, 14), in_transaction=True)
    conn.execute("ROLLBACK")
    assert conn.execute("SELECT COUNT(*) FROM upstox_instruments").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM upstox_expired_instruments").fetchone()[0] == 0


def test_master_only_fields_are_preserved_in_raw_json(conn):
    conn.execute("INSERT INTO upstox_instruments (instrument_key, expiry, isin, short_name) VALUES ('past', '2026-09-13', 'ISIN123', 'Short')")
    archive_expired_instruments(conn, today=date(2026, 9, 14))
    assert conn.execute("SELECT raw_json->>'isin', raw_json->>'short_name' FROM upstox_expired_instruments").fetchone() == ('ISIN123', 'Short')
