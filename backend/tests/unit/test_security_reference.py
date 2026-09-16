import json
from datetime import date

import duckdb
import pytest
from fastapi import HTTPException
from app.db.schema_instruments import ensure_instrument_schema
from app.services.security_reference import ensure_reference_schema, sync_reference, valid_isin
from app.api.v1 import security_reference_routes as api

pytestmark = pytest.mark.unit
ISIN = 'INE002A01018'

@pytest.fixture
def db(monkeypatch):
    conn = duckdb.connect(':memory:')
    def safe(conn, sql):
        try:
            conn.execute(sql)
        except duckdb.CatalogException:
            pass
    ensure_instrument_schema(conn, safe)
    ensure_reference_schema(conn)
    class Proxy:
        def execute(self, *args): return conn.execute(*args)
        def commit(self): conn.commit()
        def rollback(self): conn.rollback()
        def close(self): pass
    monkeypatch.setattr(api, 'get_connection', Proxy)
    yield conn
    conn.close()


def instrument(conn, exchange='NSE', symbol='RELIANCE', kind='EQ', isin=ISIN):
    key = f'{exchange}_EQ|{isin}'
    conn.execute("INSERT INTO upstox_instruments (instrument_key, isin, exchange, segment, instrument_type, trading_symbol, name, short_name, lot_size, tick_size, raw_json) VALUES (?, ?, ?, ?, ?, ?, 'Reliance Industries Limited', 'Reliance', 1, 5, '{}')", [key, isin, exchange, exchange+'_EQ', kind, symbol])
    return key


def test_isin_validation():
    assert valid_isin(ISIN.lower()) == ISIN
    assert valid_isin('INE002A01019') is None
    assert valid_isin('12345') is None


def test_one_isin_two_listings_and_derivative_link(db):
    key = instrument(db)
    instrument(db, 'BSE', '500325')
    instrument(db, 'BSE', 'ETF', 'ETF', 'INE009A01021')
    db.execute("INSERT INTO upstox_instruments (instrument_key, instrument_type, underlying_key, expiry) VALUES ('NSE_FO|123', 'FUT', ?, DATE '2099-01-01')", [key])
    counts = sync_reference(db)
    assert counts['securities'] == 2 and counts['listings'] == 3
    assert db.execute('SELECT listing_count, primary_exchange, is_cross_listed, futures_available, options_available FROM security_reference WHERE isin=?', [ISIN]).fetchone() == (2, 'NSE', True, True, False)
    assert db.execute('SELECT COUNT(*) FROM security_listing_reference WHERE is_primary_listing').fetchone()[0] == 2
    assert sync_reference(db)['updated'] == 0


def test_upload_preserved_on_sync_and_source_identity_protected(db):
    instrument(db)
    sync_reference(db)
    result = api.upload('securities', api.Upload(rows=[dict(isin=ISIN, sector=' Energy  ', company_name='My company', flag='U')]))
    assert result['updated'] == 1
    sync_reference(db)
    assert db.execute('SELECT sector, company_name FROM security_reference').fetchone() == ('Energy', 'My company')
    with pytest.raises(HTTPException):
        api.upload('securities', api.Upload(rows=[dict(isin=ISIN, primary_symbol='WRONG', flag='U')]))
    api.upload('securities', api.Upload(rows=[dict(isin=ISIN, flag='D')]))
    assert db.execute('SELECT sector, company_name FROM security_reference').fetchone() == (None, 'Reliance Industries Limited')


def test_missing_listing_not_declared_delisted_and_symbol_history(db):
    instrument(db)
    instrument(db, 'BSE', '500325')
    sync_reference(db)
    db.execute("UPDATE upstox_instruments SET trading_symbol='RELIANCE_NEW' WHERE exchange='NSE'")
    sync_reference(db)
    assert db.execute("SELECT old_value, new_value FROM security_identifier_history WHERE identifier_type='SYMBOL:NSE'").fetchone() == ('RELIANCE', 'RELIANCE_NEW')
    db.execute("DELETE FROM upstox_instruments WHERE exchange='BSE'")
    sync_reference(db)
    assert db.execute('SELECT listing_count, has_bse_listing, is_delisted FROM security_reference').fetchone() == (1, False, None)
    assert db.execute("SELECT is_active, listing_status FROM security_listing_reference WHERE exchange='BSE'").fetchone() == (False, 'NOT_IN_CURRENT_INSTRUMENTS')


def test_index_dates_and_atomic_upload(db):
    instrument(db)
    sync_reference(db)
    row = dict(isin=ISIN, index_code='NIFTY_50', index_name='Nifty 50', effective_from='2024-01-01', flag='A')
    assert api.upload('indices', api.Upload(rows=[row]))['added'] == 1
    with pytest.raises(HTTPException):
        api.upload('indices', api.Upload(rows=[dict(row, index_code='OTHER'), dict(row, effective_from='2025-01-01')]))
    assert db.execute('SELECT COUNT(*) FROM security_index_membership').fetchone()[0] == 1


def test_download_template_and_pagination_filters(db):
    instrument(db)
    sync_reference(db)
    result = api.list_rows('securities', search='Reliance', page=1, page_size=50)
    assert result['total_records'] == 1
    assert result['rows'][0]['isin'] == ISIN
    csv = api.download('securities', template=True).body.decode('utf-8-sig')
    assert 'company_name' in csv.splitlines()[0] and csv.splitlines()[0].endswith(',flag')
    assert 'flag' not in api.download('securities').body.decode('utf-8-sig').splitlines()[0].split(',')


def test_profile_sector_mapping_preserves_upload(db):
    instrument(db)
    sync_reference(db)
    db.execute("CREATE TABLE upstox_company_fundamentals (fundamental_id VARCHAR, isin VARCHAR, sector VARCHAR, endpoint VARCHAR, data_status VARCHAR, synced_at TIMESTAMP)")
    db.execute("INSERT INTO upstox_company_fundamentals VALUES ('1', ?, 'Refineries', 'company_profile', 'success', CURRENT_TIMESTAMP)", [ISIN])
    counts = sync_reference(db)
    assert counts['profile_updated'] == 1
    assert db.execute('SELECT sector, classification_source FROM security_reference').fetchone() == ('Refineries', 'Upstox Company Profile')
    api.upload('securities', api.Upload(rows=[dict(isin=ISIN, sector='Energy', flag='U')]))
    sync_reference(db)
    assert db.execute('SELECT sector FROM security_reference').fetchone()[0] == 'Energy'


def test_reference_refresh_uses_profile_endpoint_and_keeps_instruments_on_key_failure(monkeypatch):
    from app.services import reference_sync as job
    from app.services.data_collection import instrument_sync_service, company_fundamentals_service
    monkeypatch.setattr(instrument_sync_service, 'sync_upstox_current_instruments_service', lambda user: {'status': 'success', 'reference_data': {'securities': 1, 'listings': 2}})
    def profile(user, config, clear_cancel_at_start):
        assert config['endpoints'] == ['company_profile']
        assert config['skip_existing'] is True
        raise HTTPException(400, 'Upstox access token required')
    monkeypatch.setattr(company_fundamentals_service, 'sync_upstox_company_fundamentals_service', profile)
    job.run_reference_refresh({'user_id': 'admin'})
    assert job.STATE['status'] == 'partial_success'
    assert job.STATE['counts']['securities'] == 1


@pytest.mark.parametrize('view', ['securities', 'listings', 'indices', 'identifiers'])
def test_reference_admin_only(view):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.dependencies import get_current_user
    app = FastAPI()
    app.include_router(api.router)
    app.dependency_overrides[get_current_user] = lambda: {'user_id': 'trader', 'role': 'user'}
    with TestClient(app) as client:
        assert client.get(f'/reference-data/tables/{view}').status_code == 403
        assert client.post(f'/reference-data/tables/{view}/upload', json={'rows': []}).status_code == 403
        assert client.post('/reference-data/sync').status_code == 403
