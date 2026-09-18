from datetime import date, datetime, timedelta
import json

import duckdb

from app.engines.corporate_actions import ensure_corporate_action_schema, run_corporate_action_engine


def database():
    conn = duckdb.connect(':memory:')
    conn.execute("CREATE TABLE ohlcv_daily (instrument_key VARCHAR, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
    conn.execute("""CREATE TABLE corporate_actions (
        instrument_key VARCHAR, isin VARCHAR, trading_symbol VARCHAR, action_type VARCHAR,
        ex_date DATE, record_date DATE, amount DOUBLE, ratio VARCHAR, raw_json VARCHAR, ingested_at TIMESTAMP
    )""")
    ensure_corporate_action_schema(conn)
    return conn


def test_split_back_adjusts_prices_and_volume_without_touching_raw_data():
    conn = database()
    conn.executemany('INSERT INTO ohlcv_daily VALUES (?, ?, ?, ?, ?, ?, ?)', [
        ('NSE_EQ|TEST', date(2025, 1, 1), 100, 102, 99, 100, 1000),
        ('NSE_EQ|TEST', date(2025, 1, 2), 50, 51, 49, 50, 2000),
    ])
    conn.execute("INSERT INTO corporate_actions VALUES ('NSE_EQ|TEST','INE000A01000','TEST','stock split',DATE '2025-01-02',DATE '2025-01-02',NULL,'1:2',NULL,CURRENT_TIMESTAMP)")
    result = run_corporate_action_engine(conn, date(2025, 1, 2))
    assert result['actions_valid'] == 1
    before = conn.execute("SELECT raw_close, adjusted_close, adjusted_volume, total_return_close FROM adjusted_ohlcv_daily WHERE date=DATE '2025-01-01'").fetchone()
    after = conn.execute("SELECT raw_close, adjusted_close, adjusted_volume FROM adjusted_ohlcv_daily WHERE date=DATE '2025-01-02'").fetchone()
    assert before == (100, 50, 2000, 50) and after == (50, 50, 2000)
    assert conn.execute("SELECT close, volume FROM ohlcv_daily WHERE date=DATE '2025-01-01'").fetchone() == (100, 1000)
    conn.close()


def test_upstox_dividend_builds_total_return_series_only():
    conn = database()
    conn.execute("""CREATE TABLE upstox_company_fundamentals (
        isin VARCHAR, instrument_key VARCHAR, trading_symbol VARCHAR, endpoint VARCHAR,
        raw_data_json VARCHAR, synced_at TIMESTAMP
    )""")
    conn.executemany('INSERT INTO ohlcv_daily VALUES (?, ?, ?, ?, ?, ?, ?)', [
        ('NSE_EQ|DIV', date(2025, 1, 1), 100, 101, 99, 100, 1000),
        ('NSE_EQ|DIV', date(2025, 1, 2), 95, 96, 94, 95, 1000),
    ])
    payload = [{"name": "Dividend", "expiry_date": "02 Jan 2025", "amount": 5,
                "event_details": [{"name": "Record date", "value": "02 Jan 2025"}]}]
    conn.execute("INSERT INTO upstox_company_fundamentals VALUES ('INE000A01001','NSE_EQ|DIV','DIV','corporate_actions',?,CURRENT_TIMESTAMP)", [json.dumps(payload)])
    result = run_corporate_action_engine(conn, date(2025, 1, 2))
    assert result['actions_valid'] == 1
    row = conn.execute("SELECT adjusted_close,total_return_close,price_adjustment_factor,total_return_factor FROM adjusted_ohlcv_daily WHERE date=DATE '2025-01-01'").fetchone()
    assert row == (100, 95, 1, .95)
    action = conn.execute('SELECT corporate_action_type,cash_dividend,adjustment_source FROM corporate_action_normalized').fetchone()
    assert action == ('CASH_DIVIDEND', 5, 'Upstox Company Fundamentals')
    conn.close()
