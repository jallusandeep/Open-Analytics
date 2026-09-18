from datetime import date, datetime, timedelta

import duckdb

from app.engines.data_quality import DataQualityConfig, ensure_data_quality_schema, run_data_quality_engine


def base_db():
    conn = duckdb.connect(':memory:')
    conn.execute("CREATE TABLE security_listing_reference (instrument_key VARCHAR, isin VARCHAR, exchange VARCHAR, segment VARCHAR, trading_symbol VARCHAR)")
    conn.execute("CREATE TABLE security_reference (isin VARCHAR)")
    conn.execute("CREATE TABLE security_type_mapping (exchange VARCHAR, segment VARCHAR, source_type VARCHAR, security_type VARCHAR, instrument_type VARCHAR, gbo_type VARCHAR, is_active BOOLEAN)")
    conn.execute("CREATE TABLE ohlcv_daily (instrument_key VARCHAR, trading_symbol VARCHAR, date DATE, open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume BIGINT)")
    conn.execute("INSERT INTO security_reference VALUES ('INE002A01018')")
    conn.execute("INSERT INTO security_listing_reference VALUES ('NSE_EQ|INE002A01018', 'INE002A01018', 'NSE', 'NSE_EQ', 'RELIANCE')")
    conn.execute("INSERT INTO security_type_mapping VALUES ('NSE', 'NSE_EQ', 'EQ', '', 'EQUITY', 'COMMON_EQUITY', true)")
    ensure_data_quality_schema(conn)
    return conn


def test_data_quality_detects_structural_missing_stale_and_gap_issues():
    conn = base_db()
    start = date(2025, 1, 6)
    rows = []
    for offset in range(10):
        day = start + timedelta(days=offset)
        if day.weekday() >= 5 or day == date(2025, 1, 9):
            continue
        close = 100 if day < date(2025, 1, 14) else 200
        rows.append(('NSE_EQ|INE002A01018', 'RELIANCE', day, close, close + 1, close - 1, close, 1000))
    rows.append(('NSE_EQ|INE002A01018', 'RELIANCE', date(2025, 1, 15), 100, 90, 95, 100, -1))
    conn.executemany('INSERT INTO ohlcv_daily VALUES (?, ?, ?, ?, ?, ?, ?, ?)', rows)
    result = run_data_quality_engine(conn, date(2025, 1, 15), DataQualityConfig(stale_price_sessions=2, abnormal_gap_pct=40))
    codes = {row[0] for row in conn.execute('SELECT issue_code FROM data_quality_issues').fetchall()}
    assert {'MISSING_SESSION', 'STALE_PRICE', 'ABNORMAL_GAP', 'INVALID_OHLC', 'NEGATIVE_VOLUME'} <= codes
    assert result['status'] == 'CRITICAL' and result['instruments'] == 1
    summary = conn.execute('SELECT missing_sessions, invalid_ohlc_count, negative_volume_count, data_quality_status FROM data_quality_instrument_summary').fetchone()
    assert summary == (1, 1, 1, 'CRITICAL')
    conn.close()


def test_data_quality_validates_news_fundamentals_and_reference():
    conn = base_db()
    conn.execute("INSERT INTO security_type_mapping VALUES ('NSE', 'NSE_EQ', 'BE', '', NULL, NULL, true)")
    conn.execute("CREATE TABLE equity_news (news_id VARCHAR, instrument_key VARCHAR, title VARCHAR, source VARCHAR, published_at TIMESTAMP)")
    conn.execute("INSERT INTO equity_news VALUES ('1', 'UNKNOWN', 'Story', NULL, NULL)")
    conn.execute("CREATE TABLE upstox_company_fundamentals (fundamental_id VARCHAR, isin VARCHAR, endpoint VARCHAR, report_date DATE, time_period VARCHAR, statement_type VARCHAR, latest_promoter_holding_pct DOUBLE)")
    conn.execute("INSERT INTO upstox_company_fundamentals VALUES ('F1', 'INE002A01018', 'holdings', DATE '2025-01-01', 'annual', NULL, 120)")
    result = run_data_quality_engine(conn, date(2025, 1, 31))
    codes = {row[0] for row in conn.execute('SELECT issue_code FROM data_quality_issues').fetchall()}
    assert {'MISSING_TIMESTAMP', 'UNKNOWN_INSTRUMENT', 'MISSING_SOURCE', 'INVALID_HOLDING', 'UNMAPPED_SECURITY_TYPE'} <= codes
    assert result['datasets']['news'] == 1 and result['datasets']['fundamentals'] == 1
    conn.close()
