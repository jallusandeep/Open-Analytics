"""Normalize Upstox corporate actions and generate separate adjusted OHLCV series."""

from dataclasses import asdict, dataclass
from datetime import date, datetime
import hashlib
import json
import math
import re
import uuid


@dataclass(frozen=True)
class CorporateActionConfig:
    minimum_factor: float = 0.01
    maximum_factor: float = 100.0
    maximum_gap_difference_pct: float = 25.0


def ensure_corporate_action_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_action_normalized (
            action_id VARCHAR PRIMARY KEY,
            instrument_key VARCHAR,
            isin VARCHAR NOT NULL,
            trading_symbol VARCHAR,
            corporate_action_type VARCHAR NOT NULL,
            announcement_date DATE,
            ex_date DATE NOT NULL,
            record_date DATE,
            effective_date DATE NOT NULL,
            cash_dividend DOUBLE,
            rights_price DOUBLE,
            rights_ratio VARCHAR,
            bonus_ratio VARCHAR,
            split_ratio VARCHAR,
            price_adjustment_factor DOUBLE,
            volume_adjustment_factor DOUBLE,
            total_return_factor DOUBLE,
            adjustment_source VARCHAR,
            adjustment_status VARCHAR,
            adjustment_valid BOOLEAN,
            validation_message VARCHAR,
            raw_json VARCHAR,
            source_updated_at TIMESTAMP,
            normalized_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS corporate_action_adjustment_runs (
            run_id VARCHAR PRIMARY KEY,
            as_of_date DATE NOT NULL,
            status VARCHAR,
            actions_loaded INTEGER,
            actions_valid INTEGER,
            actions_review INTEGER,
            instruments_adjusted INTEGER,
            rows_written BIGINT,
            configuration_json VARCHAR,
            started_at TIMESTAMP,
            finished_at TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS adjusted_ohlcv_daily (
            run_id VARCHAR NOT NULL,
            instrument_key VARCHAR NOT NULL,
            date DATE NOT NULL,
            raw_open DOUBLE,
            raw_high DOUBLE,
            raw_low DOUBLE,
            raw_close DOUBLE,
            raw_volume BIGINT,
            adjusted_open DOUBLE,
            adjusted_high DOUBLE,
            adjusted_low DOUBLE,
            adjusted_close DOUBLE,
            adjusted_volume DOUBLE,
            total_return_close DOUBLE,
            price_adjustment_factor DOUBLE,
            volume_adjustment_factor DOUBLE,
            total_return_factor DOUBLE,
            corporate_action_flag BOOLEAN,
            corporate_action_type VARCHAR,
            adjustment_valid BOOLEAN,
            calculated_at TIMESTAMP,
            PRIMARY KEY (instrument_key, date)
        )
    """)


def _tables(conn):
    return {row[0] for row in conn.execute("SELECT table_name FROM information_schema.tables").fetchall()}


def _parse_date(value):
    if isinstance(value, date):
        return value
    text = str(value or '').strip()
    if not text:
        return None
    for pattern in ('%Y-%m-%d', '%d %b %Y', '%d %B %Y', '%d-%m-%Y', '%d/%m/%Y'):
        try: return datetime.strptime(text, pattern).date()
        except ValueError: pass
    return None


def _float(value):
    try:
        number = float(value)
        return number if math.isfinite(number) else None
    except (TypeError, ValueError):
        return None


def _details(item):
    result = {}
    for entry in item.get('event_details') or []:
        if isinstance(entry, dict):
            result[str(entry.get('name') or '').strip().lower()] = entry.get('value')
    return result


def _ratio(value):
    numbers = re.findall(r"\d+(?:\.\d+)?", str(value or ''))
    if len(numbers) < 2:
        return None
    left, right = float(numbers[0]), float(numbers[1])
    return (left, right) if left > 0 and right > 0 else None


def _type(value):
    clean = re.sub(r'[^a-z0-9]+', '_', str(value or '').strip().lower()).strip('_')
    aliases = {'dividend': 'CASH_DIVIDEND', 'cash_dividend': 'CASH_DIVIDEND',
               'split': 'STOCK_SPLIT', 'stock_split': 'STOCK_SPLIT', 'sub_division': 'STOCK_SPLIT',
               'reverse_split': 'REVERSE_SPLIT', 'consolidation': 'REVERSE_SPLIT',
               'bonus': 'BONUS_ISSUE', 'bonus_issue': 'BONUS_ISSUE',
               'rights': 'RIGHTS_ISSUE', 'rights_issue': 'RIGHTS_ISSUE',
               'demerger': 'DEMERGER', 'merger': 'MERGER', 'spin_off': 'SPIN_OFF',
               'capital_reduction': 'CAPITAL_REDUCTION', 'symbol_change': 'SYMBOL_CHANGE', 'isin_change': 'ISIN_CHANGE'}
    return aliases.get(clean, clean.upper() or 'OTHER')


def _stable_id(isin, action_type, ex_date, amount, ratio):
    value = f"{isin}|{action_type}|{ex_date}|{amount or ''}|{ratio or ''}"
    return hashlib.sha256(value.encode('utf-8')).hexdigest()[:32]


def _upstox_actions(conn):
    if 'upstox_company_fundamentals' not in _tables(conn):
        return []
    rows = conn.execute("""
        SELECT isin, instrument_key, trading_symbol, raw_data_json, synced_at
        FROM upstox_company_fundamentals
        WHERE endpoint='corporate_actions' AND raw_data_json IS NOT NULL
    """).fetchall()
    actions = []
    for isin, instrument_key, symbol, raw, synced_at in rows:
        try: payload = json.loads(raw) if isinstance(raw, str) else raw
        except (TypeError, ValueError): payload = []
        if isinstance(payload, dict): payload = payload.get('data') or payload.get('results') or []
        if not isinstance(payload, list): continue
        for item in payload:
            if not isinstance(item, dict): continue
            details = _details(item)
            action_type = _type(item.get('name') or item.get('action_type'))
            ex_date = _parse_date(item.get('expiry_date') or details.get('ex dividend date') or details.get('ex date'))
            amount = _float(item.get('amount') or details.get('amount'))
            ratio = item.get('ratio') or details.get('ratio') or details.get('bonus ratio') or details.get('split ratio') or details.get('rights ratio')
            actions.append({'isin': isin, 'instrument_key': instrument_key, 'trading_symbol': symbol,
                            'type': action_type, 'announcement_date': _parse_date(details.get('announcement date')),
                            'ex_date': ex_date, 'record_date': _parse_date(details.get('record date')),
                            'amount': amount, 'ratio': ratio, 'raw': item, 'source': 'Upstox Company Fundamentals',
                            'source_updated_at': synced_at})
    return actions


def _dedicated_actions(conn):
    if 'corporate_actions' not in _tables(conn): return []
    rows = conn.execute("SELECT instrument_key, isin, trading_symbol, action_type, ex_date, record_date, amount, ratio, raw_json, ingested_at FROM corporate_actions").fetchall()
    return [{'instrument_key': row[0], 'isin': row[1], 'trading_symbol': row[2], 'type': _type(row[3]),
             'announcement_date': None, 'ex_date': row[4], 'record_date': row[5], 'amount': row[6], 'ratio': row[7],
             'raw': row[8], 'source': 'Corporate Actions Table', 'source_updated_at': row[9]} for row in rows]


def _previous_close(conn, instrument_key, ex_date):
    row = conn.execute("SELECT close FROM ohlcv_daily WHERE instrument_key=? AND date<? AND close>0 ORDER BY date DESC LIMIT 1", [instrument_key, ex_date]).fetchone()
    return float(row[0]) if row else None


def _ex_close(conn, instrument_key, ex_date):
    row = conn.execute("SELECT close FROM ohlcv_daily WHERE instrument_key=? AND date>=? AND close>0 ORDER BY date LIMIT 1", [instrument_key, ex_date]).fetchone()
    return float(row[0]) if row else None


def _normalize_action(conn, source, config):
    action_type, ratio_text = source['type'], source.get('ratio')
    parsed_ratio = _ratio(ratio_text)
    price_factor = volume_factor = total_factor = 1.0
    status, valid, message = 'APPLIED', True, None
    previous_close = _previous_close(conn, source.get('instrument_key'), source.get('ex_date')) if source.get('instrument_key') and source.get('ex_date') else None
    if not source.get('isin') or not source.get('ex_date'):
        status, valid, message = 'INVALID', False, 'ISIN and ex-date are required.'
    elif action_type in {'STOCK_SPLIT', 'REVERSE_SPLIT'}:
        if parsed_ratio:
            price_factor = parsed_ratio[0] / parsed_ratio[1]
            volume_factor = 1 / price_factor
            total_factor = price_factor
        else: status, valid, message = 'NEEDS_REVIEW', False, 'Split ratio is missing or invalid.'
    elif action_type == 'BONUS_ISSUE':
        if parsed_ratio:
            bonus, held = parsed_ratio
            price_factor = held / (held + bonus); volume_factor = 1 / price_factor; total_factor = price_factor
        else: status, valid, message = 'NEEDS_REVIEW', False, 'Bonus ratio is missing or invalid.'
    elif action_type == 'CASH_DIVIDEND':
        amount = source.get('amount')
        if amount is not None and amount >= 0 and previous_close and amount < previous_close:
            total_factor = (previous_close - amount) / previous_close
        else: status, valid, message = 'NEEDS_REVIEW', False, 'Dividend amount or previous close is unavailable/invalid.'
    elif action_type == 'RIGHTS_ISSUE':
        if parsed_ratio and source.get('amount') is not None and previous_close:
            offered, held = parsed_ratio; rights_fraction = offered / held
            theoretical = (previous_close + rights_fraction * source['amount']) / (1 + rights_fraction)
            price_factor = theoretical / previous_close; total_factor = price_factor
        else: status, valid, message = 'NEEDS_REVIEW', False, 'Rights ratio, subscription price, or previous close is unavailable.'
    elif action_type in {'SYMBOL_CHANGE', 'ISIN_CHANGE'}:
        status, valid, message = 'IDENTITY_ONLY', True, 'No price factor required.'
    else:
        status, valid, message = 'NEEDS_REVIEW', False, 'Action requires an event-specific adjustment methodology.'
    if valid and not (config.minimum_factor <= price_factor <= config.maximum_factor and config.minimum_factor <= total_factor <= config.maximum_factor):
        status, valid, message = 'INVALID', False, 'Calculated factor is outside configured plausibility bounds.'
    ex_close = _ex_close(conn, source.get('instrument_key'), source.get('ex_date')) if source.get('instrument_key') and source.get('ex_date') else None
    if valid and previous_close and ex_close and action_type in {'STOCK_SPLIT', 'REVERSE_SPLIT', 'BONUS_ISSUE'}:
        observed = ex_close / previous_close
        difference = abs(observed - price_factor) / max(abs(price_factor), 1e-12) * 100
        if difference > config.maximum_gap_difference_pct:
            status, valid, message = 'NEEDS_REVIEW', False, f'Observed ex-date gap differs from factor by {difference:.2f}%.'
    action_id = _stable_id(source.get('isin'), action_type, source.get('ex_date'), source.get('amount'), ratio_text)
    return {'action_id': action_id, 'instrument_key': source.get('instrument_key'), 'isin': source.get('isin'),
            'trading_symbol': source.get('trading_symbol'), 'corporate_action_type': action_type,
            'announcement_date': source.get('announcement_date'), 'ex_date': source.get('ex_date'),
            'record_date': source.get('record_date'), 'effective_date': source.get('ex_date'),
            'cash_dividend': source.get('amount') if action_type == 'CASH_DIVIDEND' else None,
            'rights_price': source.get('amount') if action_type == 'RIGHTS_ISSUE' else None,
            'rights_ratio': ratio_text if action_type == 'RIGHTS_ISSUE' else None,
            'bonus_ratio': ratio_text if action_type == 'BONUS_ISSUE' else None,
            'split_ratio': ratio_text if action_type in {'STOCK_SPLIT', 'REVERSE_SPLIT'} else None,
            'price_adjustment_factor': price_factor, 'volume_adjustment_factor': volume_factor,
            'total_return_factor': total_factor, 'adjustment_source': source.get('source'),
            'adjustment_status': status, 'adjustment_valid': valid, 'validation_message': message,
            'raw_json': json.dumps(source.get('raw'), default=str), 'source_updated_at': source.get('source_updated_at'),
            'normalized_at': datetime.now()}


def run_corporate_action_engine(conn, as_of_date=None, config=None):
    ensure_corporate_action_schema(conn)
    config = config or CorporateActionConfig()
    as_of_date = date.fromisoformat(as_of_date) if isinstance(as_of_date, str) else as_of_date or date.today()
    run_id, started = str(uuid.uuid4()), datetime.now()
    sources = _dedicated_actions(conn) + _upstox_actions(conn)
    unique = {}
    for source in sources:
        key = (source.get('isin'), source.get('type'), source.get('ex_date'), source.get('amount'), str(source.get('ratio') or ''))
        unique[key] = source
    actions = [_normalize_action(conn, source, config) for source in unique.values()]
    action_columns = [row[1] for row in conn.execute("PRAGMA table_info('corporate_action_normalized')").fetchall()]
    for action in actions:
        conn.execute(f"INSERT OR REPLACE INTO corporate_action_normalized ({','.join(action_columns)}) VALUES ({','.join('?' for _ in action_columns)})", [action.get(column) for column in action_columns])
    valid_by_instrument = {}
    for action in actions:
        if action['adjustment_valid'] and action['effective_date'] and action['effective_date'] <= as_of_date and action.get('instrument_key'):
            valid_by_instrument.setdefault(action['instrument_key'], []).append(action)
    candles = conn.execute("SELECT instrument_key,date,open,high,low,close,volume FROM ohlcv_daily WHERE date<=? ORDER BY instrument_key,date", [as_of_date]).fetchall()
    now = datetime.now(); output = []
    for instrument_key, candle_date, open_price, high, low, close, volume in candles:
        future_actions = [action for action in valid_by_instrument.get(instrument_key, []) if action['effective_date'] > candle_date]
        price_factor = math.prod(action['price_adjustment_factor'] for action in future_actions)
        volume_factor = math.prod(action['volume_adjustment_factor'] for action in future_actions)
        total_factor = math.prod(action['total_return_factor'] for action in future_actions)
        day_actions = [action for action in valid_by_instrument.get(instrument_key, []) if action['effective_date'] == candle_date]
        types = ','.join(sorted({action['corporate_action_type'] for action in day_actions})) or None
        output.append((run_id, instrument_key, candle_date, open_price, high, low, close, volume,
                       open_price * price_factor if open_price is not None else None,
                       high * price_factor if high is not None else None, low * price_factor if low is not None else None,
                       close * price_factor if close is not None else None,
                       volume * volume_factor if volume is not None else None,
                       close * total_factor if close is not None else None,
                       price_factor, volume_factor, total_factor, bool(day_actions), types,
                       all(action['adjustment_valid'] for action in day_actions) if day_actions else True, now))
    if output:
        conn.executemany("INSERT OR REPLACE INTO adjusted_ohlcv_daily VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", output)
    valid = sum(action['adjustment_valid'] for action in actions); review = len(actions) - valid
    status = 'SUCCESS' if not review else 'PARTIAL_SUCCESS' if valid else 'NEEDS_REVIEW'
    conn.execute("INSERT INTO corporate_action_adjustment_runs VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                 [run_id, as_of_date, status, len(actions), valid, review, len(valid_by_instrument), len(output),
                  json.dumps(asdict(config), sort_keys=True), started, datetime.now()])
    return {'run_id': run_id, 'as_of_date': as_of_date.isoformat(), 'status': status, 'actions_loaded': len(actions),
            'actions_valid': valid, 'actions_review': review, 'instruments_adjusted': len(valid_by_instrument), 'rows_written': len(output)}
