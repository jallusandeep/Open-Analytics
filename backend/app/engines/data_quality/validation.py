"""Cross-dataset validation before quantitative calculations consume source data."""

from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
import json
import math
import uuid


@dataclass(frozen=True)
class DataQualityConfig:
    warning_coverage_pct: float = 95.0
    critical_coverage_pct: float = 80.0
    stale_price_sessions: int = 5
    abnormal_gap_pct: float = 40.0
    critical_missing_streak: int = 50
    future_timestamp_tolerance_minutes: int = 5


def ensure_data_quality_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_runs (
            run_id VARCHAR PRIMARY KEY,
            as_of_date DATE NOT NULL,
            status VARCHAR NOT NULL,
            total_records_checked BIGINT DEFAULT 0,
            total_issues BIGINT DEFAULT 0,
            critical_issues BIGINT DEFAULT 0,
            warning_issues BIGINT DEFAULT 0,
            info_issues BIGINT DEFAULT 0,
            configuration_json VARCHAR,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_issues (
            issue_id VARCHAR PRIMARY KEY,
            run_id VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            record_key VARCHAR,
            instrument_key VARCHAR,
            issue_date DATE,
            column_name VARCHAR,
            issue_code VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            observed_value VARCHAR,
            expected_value VARCHAR,
            message VARCHAR,
            corporate_action_flag BOOLEAN DEFAULT FALSE,
            detected_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_ohlcv_daily (
            run_id VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            date DATE NOT NULL,
            is_valid BOOLEAN,
            quality_status VARCHAR,
            quality_score DOUBLE,
            missing_flag BOOLEAN,
            duplicate_flag BOOLEAN,
            invalid_ohlc_flag BOOLEAN,
            stale_flag BOOLEAN,
            outlier_flag BOOLEAN,
            corporate_action_flag BOOLEAN,
            issue_count INTEGER,
            critical_issue_count INTEGER,
            exclusion_reason VARCHAR,
            PRIMARY KEY (run_id, instrument_key, date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_instrument_summary (
            run_id VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            as_of_date DATE NOT NULL,
            expected_sessions INTEGER,
            available_sessions INTEGER,
            missing_sessions INTEGER,
            coverage_pct DOUBLE,
            duplicate_count INTEGER,
            invalid_ohlc_count INTEGER,
            null_price_count INTEGER,
            nonpositive_price_count INTEGER,
            negative_volume_count INTEGER,
            zero_volume_count INTEGER,
            stale_price_days INTEGER,
            abnormal_gap_count INTEGER,
            largest_missing_streak INTEGER,
            latest_valid_date DATE,
            issue_count INTEGER,
            critical_issue_count INTEGER,
            warning_issue_count INTEGER,
            data_quality_score DOUBLE,
            data_quality_status VARCHAR,
            exclusion_reason VARCHAR,
            PRIMARY KEY (run_id, instrument_key)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS data_quality_dataset_summary (
            run_id VARCHAR NOT NULL,
            dataset VARCHAR NOT NULL,
            records_checked BIGINT,
            issue_count BIGINT,
            critical_issue_count BIGINT,
            warning_issue_count BIGINT,
            info_issue_count BIGINT,
            quality_status VARCHAR,
            PRIMARY KEY (run_id, dataset)
        )
    """)


def _tables(conn):
    return {row[0] for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _columns(conn, table):
    return {row[1] for row in conn.execute(f"PRAGMA table_info('{table}')").fetchall()}


def _text(value):
    return None if value is None else str(value)


def _issue(issues, run_id, dataset, code, severity, message, record_key=None, instrument_key=None,
           issue_date=None, column=None, observed=None, expected=None, corporate_action=False):
    issues.append({"issue_id": str(uuid.uuid4()), "run_id": run_id, "dataset": dataset,
                   "record_key": record_key, "instrument_key": instrument_key, "issue_date": issue_date,
                   "column_name": column, "issue_code": code, "severity": severity,
                   "observed_value": _text(observed), "expected_value": _text(expected), "message": message,
                   "corporate_action_flag": corporate_action, "detected_at": datetime.now()})


def _missing_streak(expected, observed):
    longest = current = 0
    for session in expected:
        current = 0 if session in observed else current + 1
        longest = max(longest, current)
    return longest


def _calendar_sessions(start, end, holidays):
    sessions = []
    current = start
    while current <= end:
        if current.weekday() < 5 and current not in holidays:
            sessions.append(current)
        current += timedelta(days=1)
    return sessions


def _corporate_action_dates(conn):
    if "corporate_action_normalized" in _tables(conn):
        rows = conn.execute("SELECT isin, effective_date, corporate_action_type FROM corporate_action_normalized WHERE adjustment_valid IS TRUE AND effective_date IS NOT NULL").fetchall()
        if rows:
            result = {}
            for isin, effective_date, action_type in rows:
                result.setdefault(isin, {})[effective_date] = action_type
            return result
    if "corporate_actions" not in _tables(conn):
        return {}
    result = {}
    for isin, ex_date, action_type in conn.execute("SELECT isin, ex_date, action_type FROM corporate_actions WHERE isin IS NOT NULL AND ex_date IS NOT NULL").fetchall():
        result.setdefault(isin, {})[ex_date] = action_type
    return result


def _validate_ohlcv(conn, run_id, as_of_date, config, issues):
    if "ohlcv_daily" not in _tables(conn):
        return [], 0
    listing = {}
    if "security_listing_reference" in _tables(conn):
        listing = {row[0]: {"isin": row[1], "exchange": row[2], "symbol": row[3]} for row in conn.execute(
            "SELECT instrument_key, isin, exchange, trading_symbol FROM security_listing_reference").fetchall()}
    rows = conn.execute("""
        SELECT instrument_key, trading_symbol, date, open, high, low, close, volume
        FROM ohlcv_daily WHERE date <= ? ORDER BY instrument_key, date
    """, [as_of_date]).fetchall()
    grouped = {}
    for row in rows:
        grouped.setdefault(row[0], []).append(row)
    duplicate_counts = {}
    if "upstox_ohlcv_candles" in _tables(conn):
        duplicate_counts = {row[0]: int(row[1]) for row in conn.execute("""
            SELECT instrument_key, SUM(copies - 1) FROM (
                SELECT instrument_key, candle_date, COUNT(*) copies
                FROM upstox_ohlcv_candles
                WHERE candle_date <= ? AND unit='days' AND interval_value=1
                GROUP BY instrument_key, candle_date HAVING COUNT(*) > 1
            ) GROUP BY instrument_key
        """, [as_of_date]).fetchall()}
    # The compatibility table normally has a primary key, but validate and
    # collapse duplicates defensively before writing row-level results.
    for instrument_key, instrument_rows in list(grouped.items()):
        by_date = {}
        for row in instrument_rows:
            by_date[row[2]] = row
        duplicate_counts[instrument_key] = duplicate_counts.get(instrument_key, 0) + len(instrument_rows) - len(by_date)
        grouped[instrument_key] = [by_date[key] for key in sorted(by_date)]
    holidays = set()
    if "upstox_market_holidays" in _tables(conn):
        holidays = {row[0] for row in conn.execute("SELECT holiday_date FROM upstox_market_holidays WHERE is_trading_day IS FALSE").fetchall()}
    action_dates = _corporate_action_dates(conn)
    latest_market_date = max((row[2] for row in rows), default=as_of_date)
    evaluation_date = min(as_of_date, latest_market_date)
    summaries, daily_records = [], []
    for instrument_key, candles in grouped.items():
        identity = listing.get(instrument_key, {})
        isin = identity.get("isin")
        expected = _calendar_sessions(candles[0][2], evaluation_date, holidays)
        observed_dates = {row[2] for row in candles}
        missing = [session for session in expected if session not in observed_dates]
        coverage = round(len(observed_dates) * 100 / len(expected), 2) if expected else 0
        longest_gap = _missing_streak(expected, observed_dates)
        counters = {"invalid": 0, "null": 0, "nonpositive": 0, "negative_volume": 0,
                    "zero_volume": 0, "stale": 0, "gap": 0}
        previous_close = None
        same_close_run = 0
        instrument_issue_start = len(issues)
        for candle in candles:
            _, symbol, candle_date, open_price, high, low, close, volume = candle
            flags, reasons = {"invalid": False, "stale": False, "outlier": False, "corporate": False}, []
            values = [open_price, high, low, close]
            if any(value is None for value in values):
                counters["null"] += 1; flags["invalid"] = True; reasons.append("Null price")
                _issue(issues, run_id, "OHLCV", "NULL_PRICE", "CRITICAL", "OHLC price is null.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, observed=values, expected="All OHLC prices")
            elif any(not math.isfinite(float(value)) or value <= 0 for value in values):
                counters["nonpositive"] += 1; flags["invalid"] = True; reasons.append("Nonpositive price")
                _issue(issues, run_id, "OHLCV", "NONPOSITIVE_PRICE", "CRITICAL", "OHLC price is zero, negative, or non-finite.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, observed=values, expected="> 0")
            elif high < max(open_price, low, close) or low > min(open_price, high, close):
                counters["invalid"] += 1; flags["invalid"] = True; reasons.append("Invalid OHLC structure")
                _issue(issues, run_id, "OHLCV", "INVALID_OHLC", "CRITICAL", "High/low violates OHLC structural rules.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, observed=values, expected="high >= open/close/low and low <= open/close/high")
            if volume is not None and volume < 0:
                counters["negative_volume"] += 1; flags["invalid"] = True; reasons.append("Negative volume")
                _issue(issues, run_id, "OHLCV", "NEGATIVE_VOLUME", "CRITICAL", "Volume cannot be negative.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, "volume", volume, ">= 0")
            if not volume:
                counters["zero_volume"] += 1
            if previous_close is not None and close is not None and close == previous_close:
                same_close_run += 1
            else:
                same_close_run = 0
            if same_close_run >= config.stale_price_sessions:
                counters["stale"] += 1; flags["stale"] = True; reasons.append("Stale close")
                _issue(issues, run_id, "OHLCV", "STALE_PRICE", "WARNING", "Close price has not changed for the configured number of sessions.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, "close", close, "Changing market close")
            if previous_close and close:
                gap_pct = abs((close / previous_close - 1) * 100)
                if gap_pct >= config.abnormal_gap_pct:
                    action = action_dates.get(isin, {}).get(candle_date)
                    flags["outlier"] = True; flags["corporate"] = bool(action); counters["gap"] += 1
                    severity = "INFO" if action else "WARNING"
                    code = "CORPORATE_ACTION_MOVE" if action else "ABNORMAL_GAP"
                    _issue(issues, run_id, "OHLCV", code, severity, f"Close-to-close move is {gap_pct:.2f}%" + (f" near {action}." if action else "."), instrument_key + ':' + str(candle_date), instrument_key, candle_date, "close", gap_pct, f"<{config.abnormal_gap_pct}%", bool(action))
            expected_symbol = identity.get("symbol")
            if expected_symbol and symbol and symbol != expected_symbol:
                _issue(issues, run_id, "OHLCV", "SYMBOL_MISMATCH", "WARNING", "OHLCV symbol differs from the current reference listing.", instrument_key + ':' + str(candle_date), instrument_key, candle_date, "trading_symbol", symbol, expected_symbol)
            row_issues = [item for item in issues[instrument_issue_start:] if item["record_key"] == instrument_key + ':' + str(candle_date)]
            critical = sum(item["severity"] == "CRITICAL" for item in row_issues)
            score = max(0, 100 - critical * 25 - sum(item["severity"] == "WARNING" for item in row_issues) * 5)
            daily_records.append((run_id, instrument_key, candle_date, not flags["invalid"], "CRITICAL" if critical else "WARNING" if row_issues else "HEALTHY", score, False, False, flags["invalid"], flags["stale"], flags["outlier"], flags["corporate"], len(row_issues), critical, '; '.join(reasons) or None))
            previous_close = close
        for missing_date in missing:
            severity = "CRITICAL" if longest_gap >= config.critical_missing_streak else "WARNING"
            _issue(issues, run_id, "OHLCV", "MISSING_SESSION", severity, "Expected exchange session has no daily candle.", instrument_key + ':' + str(missing_date), instrument_key, missing_date, expected="Daily candle")
            daily_records.append((run_id, instrument_key, missing_date, False, severity, 0 if severity == "CRITICAL" else 70, True, False, False, False, False, False, 1, int(severity == "CRITICAL"), "Missing trading session"))
        duplicates = duplicate_counts.get(instrument_key, 0)
        if duplicates:
            _issue(issues, run_id, "OHLCV", "DUPLICATE_CANDLE", "CRITICAL", "Multiple source daily candles exist for the same instrument and date.", instrument_key, instrument_key, observed=duplicates, expected=0)
        instrument_issues = issues[instrument_issue_start:]
        critical = sum(item["severity"] == "CRITICAL" for item in instrument_issues)
        warning = sum(item["severity"] == "WARNING" for item in instrument_issues)
        coverage_penalty = max(0, 100 - coverage) * 0.5
        score = round(max(0, 100 - critical * 15 - warning * 3 - coverage_penalty), 2)
        status = "CRITICAL" if critical or coverage < config.critical_coverage_pct or longest_gap >= config.critical_missing_streak else "WARNING" if warning or coverage < config.warning_coverage_pct else "HEALTHY"
        reasons = sorted({item["message"] for item in instrument_issues if item["severity"] in {"CRITICAL", "WARNING"}})
        summaries.append((run_id, instrument_key, as_of_date, len(expected), len(observed_dates), len(missing), coverage,
                          duplicates, counters["invalid"], counters["null"], counters["nonpositive"], counters["negative_volume"],
                          counters["zero_volume"], counters["stale"], counters["gap"], longest_gap,
                          max(observed_dates) if observed_dates else None, len(instrument_issues), critical, warning, score, status, '; '.join(reasons) or None))
    if daily_records:
        conn.executemany("INSERT INTO data_quality_ohlcv_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", daily_records)
    if summaries:
        conn.executemany("INSERT INTO data_quality_instrument_summary VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", summaries)
    return summaries, len(rows)


def _validate_fundamentals(conn, run_id, as_of_date, issues):
    if "upstox_company_fundamentals" not in _tables(conn):
        return 0
    columns = _columns(conn, "upstox_company_fundamentals")
    rows = conn.execute("SELECT * FROM upstox_company_fundamentals").fetchall()
    names = [item[0] for item in conn.description]
    records = [dict(zip(names, row)) for row in rows]
    seen = set()
    ratio_fields = [field for field in ("pe_ratio_company", "pb_ratio_company", "roa_company", "roe_company", "roce_company") if field in columns]
    holding_fields = [field for field in ("latest_promoter_holding_pct", "latest_fii_holding_pct", "latest_dii_holding_pct", "latest_public_holding_pct") if field in columns]
    for record in records:
        key = (record.get("isin"), record.get("endpoint"), record.get("report_date"), record.get("time_period"), record.get("statement_type"))
        record_key = str(record.get("fundamental_id") or key)
        if key in seen:
            _issue(issues, run_id, "FUNDAMENTALS", "DUPLICATE_PERIOD", "WARNING", "Duplicate reporting period and endpoint.", record_key, column="report_date", observed=key)
        seen.add(key)
        report_date = record.get("report_date")
        if report_date and report_date > as_of_date:
            _issue(issues, run_id, "FUNDAMENTALS", "FUTURE_REPORT_DATE", "CRITICAL", "Reporting date is in the future.", record_key, issue_date=report_date, column="report_date", observed=report_date, expected=f"<= {as_of_date}")
        for field in ratio_fields:
            value = record.get(field)
            limit = 10000 if field.startswith(("pe_", "pb_")) else 1000
            if value is not None and (not math.isfinite(float(value)) or abs(value) > limit):
                _issue(issues, run_id, "FUNDAMENTALS", "IMPOSSIBLE_RATIO", "WARNING", "Ratio is outside the plausible validation range.", record_key, column=field, observed=value, expected=f"absolute value <= {limit}")
        for field in holding_fields:
            value = record.get(field)
            if value is not None and not 0 <= value <= 100:
                _issue(issues, run_id, "FUNDAMENTALS", "INVALID_HOLDING", "CRITICAL", "Shareholding percentage must be between 0 and 100.", record_key, column=field, observed=value, expected="0..100")
    return len(records)


def _validate_news(conn, run_id, issues):
    if "equity_news" not in _tables(conn):
        return 0
    columns = _columns(conn, "equity_news")
    selected = [field for field in ("news_id", "instrument_key", "title", "heading", "url", "article_link", "source", "provider", "published_at", "published_time_ms") if field in columns]
    result = conn.execute(f"SELECT {','.join(selected)} FROM equity_news")
    records = [dict(zip(selected, row)) for row in result.fetchall()]
    reference_keys = set()
    if "security_listing_reference" in _tables(conn):
        reference_keys = {row[0] for row in conn.execute("SELECT instrument_key FROM security_listing_reference").fetchall()}
    seen = set(); now = datetime.now()
    for record in records:
        record_key = str(record.get("news_id") or "")
        identity = record.get("article_link") or record.get("url") or record.get("heading") or record.get("title")
        normalized = str(identity or '').strip().lower()
        if normalized and normalized in seen:
            _issue(issues, run_id, "NEWS", "DUPLICATE_STORY", "WARNING", "Duplicate article link or headline.", record_key, record.get("instrument_key"), column="article_link", observed=identity)
        seen.add(normalized)
        published = record.get("published_at")
        if not published and record.get("published_time_ms"):
            try: published = datetime.fromtimestamp(record["published_time_ms"] / 1000)
            except (ValueError, TypeError, OSError): published = None
        if not published:
            _issue(issues, run_id, "NEWS", "MISSING_TIMESTAMP", "CRITICAL", "News story has no valid publication timestamp.", record_key, record.get("instrument_key"), column="published_at")
        elif published > now + timedelta(minutes=5):
            _issue(issues, run_id, "NEWS", "FUTURE_TIMESTAMP", "CRITICAL", "News publication timestamp is in the future.", record_key, record.get("instrument_key"), column="published_at", observed=published, expected=f"<= {now}")
        if reference_keys and record.get("instrument_key") not in reference_keys:
            _issue(issues, run_id, "NEWS", "UNKNOWN_INSTRUMENT", "WARNING", "News instrument key is not mapped to a reference listing.", record_key, record.get("instrument_key"), column="instrument_key", observed=record.get("instrument_key"))
        if not str(record.get("source") or record.get("provider") or '').strip():
            _issue(issues, run_id, "NEWS", "MISSING_SOURCE", "WARNING", "News source is missing.", record_key, record.get("instrument_key"), column="source")
    return len(records)


def _validate_corporate_actions(conn, run_id, as_of_date, issues):
    if "corporate_action_normalized" in _tables(conn):
        normalized = conn.execute("""
            SELECT action_id, isin, corporate_action_type, effective_date, adjustment_status,
                   adjustment_valid, validation_message, price_adjustment_factor, total_return_factor
            FROM corporate_action_normalized
        """).fetchall()
        if normalized:
            for action_id, isin, action_type, effective_date, status, valid, message, price_factor, total_factor in normalized:
                if not valid:
                    _issue(issues, run_id, "CORPORATE_ACTIONS", "INVALID_ADJUSTMENT", "CRITICAL",
                           message or "Corporate action adjustment requires review.", action_id,
                           issue_date=effective_date, column="adjustment_status", observed=status, expected="APPLIED")
                if effective_date and effective_date > as_of_date + timedelta(days=366 * 2):
                    _issue(issues, run_id, "CORPORATE_ACTIONS", "INVALID_EFFECTIVE_DATE", "CRITICAL",
                           "Corporate action effective date is implausibly far in the future.", action_id,
                           issue_date=effective_date, column="effective_date", observed=effective_date)
            return len(normalized)
    if "corporate_actions" not in _tables(conn):
        return 0
    result = conn.execute("SELECT isin, trading_symbol, action_type, ex_date, record_date, amount, ratio FROM corporate_actions")
    records = result.fetchall(); seen = set(); day_types = {}
    for isin, symbol, action_type, ex_date, record_date, amount, ratio in records:
        key = (isin, action_type, ex_date, amount, ratio); record_key = '|'.join(str(value or '') for value in key)
        if key in seen:
            _issue(issues, run_id, "CORPORATE_ACTIONS", "DUPLICATE_ACTION", "WARNING", "Duplicate corporate action record.", record_key, issue_date=ex_date)
        seen.add(key)
        if not ex_date or ex_date > as_of_date + timedelta(days=366 * 2):
            _issue(issues, run_id, "CORPORATE_ACTIONS", "INVALID_EFFECTIVE_DATE", "CRITICAL", "Corporate action has a missing or implausible ex-date.", record_key, issue_date=ex_date, column="ex_date", observed=ex_date)
        if record_date and ex_date and record_date < ex_date:
            _issue(issues, run_id, "CORPORATE_ACTIONS", "DATE_ORDER", "WARNING", "Record date precedes ex-date.", record_key, issue_date=ex_date, column="record_date", observed=record_date, expected=f">= {ex_date}")
        if str(action_type or '').lower() in {"split", "stock_split", "bonus", "bonus_issue", "rights", "rights_issue"} and not str(ratio or '').strip():
            _issue(issues, run_id, "CORPORATE_ACTIONS", "MISSING_RATIO", "CRITICAL", "Ratio-based corporate action has no ratio.", record_key, issue_date=ex_date, column="ratio")
        day_types.setdefault((isin, ex_date), set()).add(str(action_type or '').upper())
    for (isin, ex_date), types in day_types.items():
        if len(types & {"SPLIT", "STOCK_SPLIT", "BONUS", "BONUS_ISSUE"}) > 1:
            _issue(issues, run_id, "CORPORATE_ACTIONS", "CONFLICTING_ACTIONS", "WARNING", "Split and bonus actions share the same effective date and require review.", f"{isin}|{ex_date}", issue_date=ex_date, observed=sorted(types))
    return len(records)


def _validate_reference(conn, run_id, issues):
    tables = _tables(conn); checked = 0
    if "security_listing_reference" in tables:
        rows = conn.execute("SELECT instrument_key, isin, exchange, segment FROM security_listing_reference").fetchall(); checked += len(rows)
        master_isins = {row[0] for row in conn.execute("SELECT isin FROM security_reference").fetchall()} if "security_reference" in tables else set()
        for instrument_key, isin, exchange, segment in rows:
            if master_isins and isin not in master_isins:
                _issue(issues, run_id, "REFERENCE", "ORPHAN_LISTING", "CRITICAL", "Exchange listing has no security-master record.", instrument_key, instrument_key, column="isin", observed=isin)
            if segment not in {"NSE_EQ", "BSE_EQ"} or exchange not in {"NSE", "BSE"}:
                _issue(issues, run_id, "REFERENCE", "INVALID_EXCHANGE_SEGMENT", "WARNING", "Reference listing exchange or segment is outside the equity scope.", instrument_key, instrument_key, column="segment", observed=f"{exchange}/{segment}")
    if "security_type_mapping" in tables:
        rows = conn.execute("SELECT exchange, segment, source_type, security_type, instrument_type, gbo_type FROM security_type_mapping WHERE is_active IS TRUE").fetchall(); checked += len(rows)
        for exchange, segment, source_type, security_type, instrument_type, gbo_type in rows:
            if not instrument_type or not gbo_type:
                key = f"{exchange}|{segment}|{source_type}|{security_type or ''}"
                _issue(issues, run_id, "REFERENCE", "UNMAPPED_SECURITY_TYPE", "WARNING", "Active source type has no complete normalized mapping.", key, column="instrument_type/gbo_type", observed=f"{instrument_type}/{gbo_type}")
    return checked


def _persist_issues(conn, issues):
    if not issues: return
    columns = [row[1] for row in conn.execute("PRAGMA table_info('data_quality_issues')").fetchall()]
    conn.executemany(f"INSERT INTO data_quality_issues ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [[issue.get(column) for column in columns] for issue in issues])


def run_data_quality_engine(conn, as_of_date=None, config=None):
    ensure_data_quality_schema(conn)
    config = config or DataQualityConfig()
    as_of_date = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date or date.today()
    run_id = str(uuid.uuid4()); started = datetime.now(); issues = []
    conn.execute("INSERT INTO data_quality_runs (run_id, as_of_date, status, configuration_json, started_at) VALUES (?, ?, 'RUNNING', ?, ?)", [run_id, as_of_date, json.dumps(asdict(config), sort_keys=True), started])
    summaries, ohlcv_checked = _validate_ohlcv(conn, run_id, as_of_date, config, issues)
    checked = {"OHLCV": ohlcv_checked,
               "FUNDAMENTALS": _validate_fundamentals(conn, run_id, as_of_date, issues),
               "NEWS": _validate_news(conn, run_id, issues),
               "CORPORATE_ACTIONS": _validate_corporate_actions(conn, run_id, as_of_date, issues),
               "REFERENCE": _validate_reference(conn, run_id, issues)}
    _persist_issues(conn, issues)
    for dataset, count in checked.items():
        related = [issue for issue in issues if issue["dataset"] == dataset]
        critical = sum(issue["severity"] == "CRITICAL" for issue in related)
        warning = sum(issue["severity"] == "WARNING" for issue in related)
        info = sum(issue["severity"] == "INFO" for issue in related)
        status = "CRITICAL" if critical else "WARNING" if warning else "HEALTHY"
        conn.execute("INSERT INTO data_quality_dataset_summary VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [run_id, dataset, count, len(related), critical, warning, info, status])
    critical = sum(issue["severity"] == "CRITICAL" for issue in issues)
    warning = sum(issue["severity"] == "WARNING" for issue in issues)
    info = sum(issue["severity"] == "INFO" for issue in issues)
    status = "CRITICAL" if critical else "WARNING" if warning else "HEALTHY"
    conn.execute("""UPDATE data_quality_runs SET status=?, total_records_checked=?, total_issues=?, critical_issues=?, warning_issues=?, info_issues=?, finished_at=? WHERE run_id=?""",
                 [status, sum(checked.values()), len(issues), critical, warning, info, datetime.now(), run_id])
    return {"run_id": run_id, "as_of_date": as_of_date.isoformat(), "status": status,
            "records_checked": sum(checked.values()), "instruments": len(summaries), "issues": len(issues),
            "critical": critical, "warning": warning, "info": info,
            "datasets": {name.lower(): count for name, count in checked.items()}}
