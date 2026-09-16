"""Universe history, liquidity, price and market-cap metrics derived from daily OHLCV."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
import json


@dataclass(frozen=True)
class UniverseEngineConfig:
    minimum_coverage_pct: float = 95.0
    maximum_recent_missing_days: int = 5
    minimum_price: float = 10.0
    maximum_stale_calendar_days: int = 7
    minimum_avg_traded_value_20d: float = 10_000_000.0
    minimum_traded_days_20d: int = 15
    maximum_zero_volume_days_20d: int = 5


def ensure_universe_engine_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS universe_ohlcv_metrics (
            instrument_key VARCHAR NOT NULL,
            isin VARCHAR,
            exchange VARCHAR,
            as_of_date DATE NOT NULL,
            first_trade_date DATE,
            last_trade_date DATE,
            calendar_age_days INTEGER,
            trading_history_days INTEGER,
            valid_ohlcv_days INTEGER,
            missing_ohlcv_days INTEGER,
            trading_coverage_pct DOUBLE,
            max_missing_streak INTEGER,
            recent_missing_days INTEGER,
            historical_missing_days INTEGER,
            eligible_5d BOOLEAN,
            eligible_21d BOOLEAN,
            eligible_63d BOOLEAN,
            eligible_126d BOOLEAN,
            eligible_252d BOOLEAN,
            eligible_1y BOOLEAN,
            eligible_3y BOOLEAN,
            eligible_5y BOOLEAN,
            eligible_short_term_risk BOOLEAN,
            eligible_long_term_risk BOOLEAN,
            eligible_beta BOOLEAN,
            eligible_factor_model BOOLEAN,
            avg_volume_5d DOUBLE,
            avg_volume_20d DOUBLE,
            avg_volume_60d DOUBLE,
            avg_traded_value_5d DOUBLE,
            avg_traded_value_20d DOUBLE,
            avg_traded_value_60d DOUBLE,
            median_traded_value_20d DOUBLE,
            median_traded_value_60d DOUBLE,
            traded_days_20d INTEGER,
            traded_days_60d INTEGER,
            zero_volume_days_20d INTEGER,
            zero_volume_days_60d INTEGER,
            liquidity_score DOUBLE,
            liquidity_percentile DOUBLE,
            liquidity_bucket VARCHAR,
            liquidity_eligible BOOLEAN,
            last_price DOUBLE,
            median_price_20d DOUBLE,
            penny_stock_flag BOOLEAN,
            price_stale_flag BOOLEAN,
            price_eligible BOOLEAN,
            price_exclusion_reason VARCHAR,
            market_cap DOUBLE,
            free_float_market_cap DOUBLE,
            market_cap_rank INTEGER,
            free_float_market_cap_rank INTEGER,
            market_cap_percentile DOUBLE,
            market_cap_bucket VARCHAR,
            research_eligible BOOLEAN,
            trading_eligible BOOLEAN,
            research_exclusion_reason VARCHAR,
            trading_exclusion_reason VARCHAR,
            configuration_json VARCHAR,
            calculated_at TIMESTAMP,
            PRIMARY KEY (instrument_key, as_of_date)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS universe_market_cap_history (
            isin VARCHAR NOT NULL,
            effective_date DATE NOT NULL,
            market_cap DOUBLE,
            free_float_market_cap DOUBLE,
            source VARCHAR,
            source_updated_at TIMESTAMP,
            PRIMARY KEY (isin, effective_date, source)
        )
    """)


def _average(values):
    values = [float(value) for value in values if value is not None]
    return sum(values) / len(values) if values else None


def _median(values):
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None
    middle = len(values) // 2
    return values[middle] if len(values) % 2 else (values[middle - 1] + values[middle]) / 2


def _window(candles, size):
    return candles[-size:]


def _maximum_missing_streak(expected_dates, observed_dates):
    longest = current = 0
    for session in expected_dates:
        current = 0 if session in observed_dates else current + 1
        longest = max(longest, current)
    return longest


def _eligible(valid_days, required_days, coverage_pct, config):
    return valid_days >= required_days and coverage_pct >= config.minimum_coverage_pct


def _rank_market_caps(records):
    ranked = sorted((record for record in records if record.get("market_cap") is not None), key=lambda row: row["market_cap"], reverse=True)
    count = len(ranked)
    for rank, record in enumerate(ranked, 1):
        record["market_cap_rank"] = rank
        record["market_cap_percentile"] = round((count - rank + 1) * 100 / count, 2) if count else None
        record["market_cap_bucket"] = "LARGE_CAP" if rank <= 100 else "MID_CAP" if rank <= 250 else "SMALL_CAP"


def _rank_liquidity(records):
    ranked = sorted((record for record in records if record.get("avg_traded_value_20d") is not None), key=lambda row: row["avg_traded_value_20d"])
    count = len(ranked)
    for position, record in enumerate(ranked, 1):
        percentile = round(position * 100 / count, 2) if count else None
        record["liquidity_percentile"] = percentile
        record["liquidity_score"] = percentile
        record["liquidity_bucket"] = "HIGH" if percentile >= 67 else "MEDIUM" if percentile >= 34 else "LOW"


def _latest_market_caps(conn, as_of_date):
    tables = {row[0] for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    if "upstox_company_fundamentals" not in tables:
        return {}
    rows = conn.execute("""
        SELECT isin, market_cap_inr_value, report_date, synced_at
        FROM (
            SELECT isin, market_cap_inr_value, report_date, synced_at,
                   ROW_NUMBER() OVER (PARTITION BY isin ORDER BY COALESCE(report_date, CAST(synced_at AS DATE)) DESC, synced_at DESC) AS rank
            FROM upstox_company_fundamentals
            WHERE isin IS NOT NULL AND market_cap_inr_value IS NOT NULL
              AND COALESCE(report_date, CAST(synced_at AS DATE)) <= ?
        ) WHERE rank = 1
    """, [as_of_date]).fetchall()
    return {row[0]: {"market_cap": row[1], "effective_date": row[2] or row[3].date(), "source_updated_at": row[3]} for row in rows}


def _persist_market_cap_history(conn):
    tables = {row[0] for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    if "upstox_company_fundamentals" not in tables:
        return 0
    before = conn.execute("SELECT COUNT(*) FROM universe_market_cap_history").fetchone()[0]
    conn.execute("""
        INSERT INTO universe_market_cap_history
        SELECT isin, COALESCE(report_date, CAST(synced_at AS DATE)), market_cap_inr_value, NULL,
               'Upstox Company Fundamentals', synced_at
        FROM upstox_company_fundamentals
        WHERE isin IS NOT NULL AND market_cap_inr_value IS NOT NULL
        ON CONFLICT (isin, effective_date, source) DO UPDATE SET
            market_cap=excluded.market_cap, source_updated_at=excluded.source_updated_at
    """)
    return conn.execute("SELECT COUNT(*) FROM universe_market_cap_history").fetchone()[0] - before


def run_universe_engine(conn, as_of_date=None, config=None):
    """Calculate one survivorship-safe daily snapshot from stored daily OHLCV."""
    ensure_universe_engine_schema(conn)
    config = config or UniverseEngineConfig()
    as_of_date = as_of_date or date.today()
    if isinstance(as_of_date, str):
        as_of_date = date.fromisoformat(as_of_date)

    tables = {row[0] for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}
    if "ohlcv_daily" not in tables or "security_listing_reference" not in tables:
        return {"as_of_date": as_of_date.isoformat(), "instruments": 0, "message": "OHLCV or reference listings are unavailable."}

    listing_rows = conn.execute("""
        SELECT instrument_key, isin, exchange FROM security_listing_reference
        WHERE is_active IS TRUE
    """).fetchall()
    candles = conn.execute("""
        SELECT instrument_key, date, close, volume
        FROM ohlcv_daily
        WHERE date <= ? AND close IS NOT NULL AND close > 0
        ORDER BY instrument_key, date
    """, [as_of_date]).fetchall()
    by_instrument = {}
    for instrument_key, candle_date, close, volume in candles:
        by_instrument.setdefault(instrument_key, []).append((candle_date, float(close), float(volume or 0)))

    market_dates = {}
    for instrument_key, _, exchange in listing_rows:
        market_dates.setdefault(exchange, set()).update(row[0] for row in by_instrument.get(instrument_key, []))
    market_caps = _latest_market_caps(conn, as_of_date)
    records = []
    for instrument_key, isin, exchange in listing_rows:
        series = by_instrument.get(instrument_key, [])
        if not series:
            continue
        first_date, last_date = series[0][0], series[-1][0]
        observed_dates = {row[0] for row in series}
        expected_dates = sorted(day for day in market_dates.get(exchange, set()) if first_date <= day <= min(last_date, as_of_date))
        valid_days = len(series)
        expected_days = len(expected_dates) or valid_days
        missing_days = max(0, expected_days - valid_days)
        coverage_pct = round(valid_days * 100 / expected_days, 2) if expected_days else 0
        recent_market_dates = sorted(day for day in market_dates.get(exchange, set()) if day <= as_of_date)
        recent_missing = sum(day not in observed_dates for day in recent_market_dates[-config.maximum_recent_missing_days:])
        row = {"instrument_key": instrument_key, "isin": isin, "exchange": exchange, "as_of_date": as_of_date,
               "first_trade_date": first_date, "last_trade_date": last_date,
               "calendar_age_days": (as_of_date - first_date).days, "trading_history_days": expected_days,
               "valid_ohlcv_days": valid_days, "missing_ohlcv_days": missing_days,
               "trading_coverage_pct": coverage_pct, "max_missing_streak": _maximum_missing_streak(expected_dates, observed_dates),
               "recent_missing_days": recent_missing, "historical_missing_days": missing_days,
               "free_float_market_cap": None, "free_float_market_cap_rank": None}
        for label, required in (("5d", 6), ("21d", 22), ("63d", 64), ("126d", 127), ("252d", 253)):
            row[f"eligible_{label}"] = _eligible(valid_days, required, coverage_pct, config)
        row.update(eligible_1y=row["eligible_252d"], eligible_3y=_eligible(valid_days, 756, coverage_pct, config),
                   eligible_5y=_eligible(valid_days, 1260, coverage_pct, config),
                   eligible_short_term_risk=_eligible(valid_days, 21, coverage_pct, config),
                   eligible_long_term_risk=_eligible(valid_days, 252, coverage_pct, config),
                   eligible_beta=_eligible(valid_days, 253, coverage_pct, config),
                   eligible_factor_model=_eligible(valid_days, 253, coverage_pct, config))
        for size in (5, 20, 60):
            window = _window(series, size)
            row[f"avg_volume_{size}d"] = _average([item[2] for item in window])
            values = [item[1] * item[2] for item in window]
            row[f"avg_traded_value_{size}d"] = _average(values)
            if size in (20, 60):
                row[f"median_traded_value_{size}d"] = _median(values)
                row[f"traded_days_{size}d"] = sum(item[2] > 0 for item in window)
                row[f"zero_volume_days_{size}d"] = sum(item[2] <= 0 for item in window)
        row["liquidity_eligible"] = bool((row["avg_traded_value_20d"] or 0) >= config.minimum_avg_traded_value_20d
                                           and row["traded_days_20d"] >= config.minimum_traded_days_20d
                                           and row["zero_volume_days_20d"] <= config.maximum_zero_volume_days_20d)
        row["last_price"] = series[-1][1]
        row["median_price_20d"] = _median([item[1] for item in _window(series, 20)])
        row["penny_stock_flag"] = row["last_price"] < config.minimum_price
        row["price_stale_flag"] = (as_of_date - last_date).days > config.maximum_stale_calendar_days
        row["price_eligible"] = not row["penny_stock_flag"] and not row["price_stale_flag"]
        reasons = []
        if row["penny_stock_flag"]:
            reasons.append("Below configured minimum price")
        if row["price_stale_flag"]:
            reasons.append("Price is stale")
        row["price_exclusion_reason"] = "; ".join(reasons) or None
        cap = market_caps.get(isin, {})
        row["market_cap"] = cap.get("market_cap")
        records.append(row)

    _rank_liquidity(records)
    _rank_market_caps(records)
    now = datetime.now()
    columns = [row[1] for row in conn.execute("PRAGMA table_info('universe_ohlcv_metrics')").fetchall()]
    config_json = json.dumps(asdict(config), sort_keys=True)
    for row in records:
        research_reasons = []
        if not row["eligible_21d"]:
            research_reasons.append("Insufficient valid OHLCV history")
        if row["trading_coverage_pct"] < config.minimum_coverage_pct:
            research_reasons.append("OHLCV coverage below threshold")
        row["research_eligible"] = not research_reasons
        trading_reasons = list(research_reasons)
        if not row["liquidity_eligible"]:
            trading_reasons.append("Liquidity below configured threshold")
        if not row["price_eligible"]:
            trading_reasons.append(row["price_exclusion_reason"])
        row["trading_eligible"] = not trading_reasons
        row["research_exclusion_reason"] = "; ".join(filter(None, research_reasons)) or None
        row["trading_exclusion_reason"] = "; ".join(filter(None, trading_reasons)) or None
        row["configuration_json"] = config_json
        row["calculated_at"] = now
        conn.execute(f"INSERT OR REPLACE INTO universe_ohlcv_metrics ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", [row.get(column) for column in columns])
    history_added = _persist_market_cap_history(conn)
    return {"as_of_date": as_of_date.isoformat(), "instruments": len(records),
            "research_eligible": sum(row["research_eligible"] for row in records),
            "trading_eligible": sum(row["trading_eligible"] for row in records),
            "market_cap_history_added": history_added}
