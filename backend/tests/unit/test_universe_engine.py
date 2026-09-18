from datetime import date, timedelta

import duckdb

from app.engines.universe import UniverseEngineConfig, ensure_universe_engine_schema, run_universe_engine


def test_universe_engine_calculates_history_liquidity_price_and_market_cap():
    conn = duckdb.connect(':memory:')
    conn.execute("""CREATE TABLE security_listing_reference (
        instrument_key VARCHAR, isin VARCHAR, exchange VARCHAR, is_active BOOLEAN
    )""")
    conn.execute("""CREATE TABLE ohlcv_daily (
        instrument_key VARCHAR, date DATE, close DOUBLE, volume BIGINT
    )""")
    conn.execute("""CREATE TABLE upstox_company_fundamentals (
        isin VARCHAR, market_cap_inr_value DOUBLE, report_date DATE, synced_at TIMESTAMP
    )""")
    conn.execute("INSERT INTO security_listing_reference VALUES ('NSE_EQ|INE002A01018', 'INE002A01018', 'NSE', true)")
    start = date(2025, 1, 1)
    rows = [('NSE_EQ|INE002A01018', start + timedelta(days=offset), 100 + offset, 200000) for offset in range(30)]
    conn.executemany('INSERT INTO ohlcv_daily VALUES (?, ?, ?, ?)', rows)
    conn.execute("INSERT INTO upstox_company_fundamentals VALUES ('INE002A01018', 1000000000, DATE '2025-01-15', TIMESTAMP '2025-01-16 10:00:00')")
    ensure_universe_engine_schema(conn)
    result = run_universe_engine(conn, date(2025, 1, 30), UniverseEngineConfig(minimum_coverage_pct=90))
    assert result['instruments'] == 1 and result['research_eligible'] == 1 and result['trading_eligible'] == 1
    row = conn.execute("""SELECT valid_ohlcv_days, eligible_21d, avg_traded_value_20d,
                                  price_eligible, market_cap, market_cap_rank, market_cap_bucket
                           FROM universe_ohlcv_metrics""").fetchone()
    assert row == (30, True, 23900000.0, True, 1000000000.0, 1, 'LARGE_CAP')
    assert conn.execute('SELECT COUNT(*) FROM universe_market_cap_history').fetchone()[0] == 1
    conn.close()


def test_universe_engine_marks_low_price_and_illiquid_security():
    conn = duckdb.connect(':memory:')
    conn.execute("CREATE TABLE security_listing_reference (instrument_key VARCHAR, isin VARCHAR, exchange VARCHAR, is_active BOOLEAN)")
    conn.execute("CREATE TABLE ohlcv_daily (instrument_key VARCHAR, date DATE, close DOUBLE, volume BIGINT)")
    conn.execute("INSERT INTO security_listing_reference VALUES ('BSE_EQ|INE002A01018', 'INE002A01018', 'BSE', true)")
    conn.executemany('INSERT INTO ohlcv_daily VALUES (?, ?, ?, ?)', [('BSE_EQ|INE002A01018', date(2025, 1, 1) + timedelta(days=offset), 5, 0) for offset in range(25)])
    result = run_universe_engine(conn, date(2025, 1, 25))
    assert result['research_eligible'] == 1 and result['trading_eligible'] == 0
    assert conn.execute('SELECT penny_stock_flag, liquidity_eligible, trading_exclusion_reason FROM universe_ohlcv_metrics').fetchone() == (
        True, False, 'Liquidity below configured threshold; Below configured minimum price'
    )
    conn.close()
