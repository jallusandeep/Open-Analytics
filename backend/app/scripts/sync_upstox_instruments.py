import argparse
import gzip
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import quote

import duckdb
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "backend" / "app" / "db" / "open_analytics.duckdb"

UPSTOX_BASE_URL = "https://api.upstox.com/v2"

INSTRUMENT_FILES = {
    "bod_complete": "https://assets.upstox.com/market-quote/instruments/exchange/complete.json.gz",
    "suspended": "https://assets.upstox.com/market-quote/instruments/exchange/suspended-instrument.json.gz",
}

DEFAULT_UNDERLYING_KEYS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Fin Service",
    "NSE_INDEX|Nifty Midcap Select",
    "BSE_INDEX|SENSEX",
    "BSE_INDEX|BANKEX",
]

REQUEST_TIMEOUT_SECONDS = 60
API_SLEEP_SECONDS = 0.35


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def now_ist_text():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def normalize_expiry(value: Any) -> Optional[str]:
    if value in (None, "", 0):
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

        if len(value) == 10 and value[4] == "-" and value[7] == "-":
            return value

        try:
            number_value = int(value)
            return datetime.fromtimestamp(number_value / 1000, tz=timezone.utc).date().isoformat()
        except Exception:
            return value

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
        except Exception:
            return None

    return None


def safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value)


def safe_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def safe_bool(value: Any) -> Optional[bool]:
    if value is None:
        return None
    return bool(value)


def create_tables(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS upstox_instruments (
            instrument_key VARCHAR,
            source_type VARCHAR,
            segment VARCHAR,
            name VARCHAR,
            exchange VARCHAR,
            isin VARCHAR,
            instrument_type VARCHAR,
            trading_symbol VARCHAR,
            short_name VARCHAR,
            exchange_token VARCHAR,
            expiry DATE,
            strike_price DOUBLE,
            lot_size BIGINT,
            minimum_lot BIGINT,
            freeze_quantity DOUBLE,
            tick_size DOUBLE,
            weekly BOOLEAN,
            underlying_key VARCHAR,
            underlying_symbol VARCHAR,
            underlying_type VARCHAR,
            security_type VARCHAR,
            raw_json JSON,
            synced_at TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS upstox_expired_instruments (
            instrument_key VARCHAR,
            segment VARCHAR,
            name VARCHAR,
            exchange VARCHAR,
            instrument_type VARCHAR,
            trading_symbol VARCHAR,
            exchange_token VARCHAR,
            expiry DATE,
            strike_price DOUBLE,
            lot_size BIGINT,
            minimum_lot BIGINT,
            freeze_quantity DOUBLE,
            tick_size DOUBLE,
            weekly BOOLEAN,
            underlying_key VARCHAR,
            underlying_symbol VARCHAR,
            underlying_type VARCHAR,
            source_type VARCHAR,
            raw_json JSON,
            synced_at TIMESTAMP
        )
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS upstox_sync_runs (
            sync_id VARCHAR,
            sync_type VARCHAR,
            status VARCHAR,
            started_at TIMESTAMP,
            finished_at TIMESTAMP,
            message VARCHAR,
            total_records BIGINT
        )
        """
    )


def insert_sync_run(conn, sync_id: str, sync_type: str, status: str, message: str, total_records: int):
    conn.execute(
        """
        INSERT INTO upstox_sync_runs (
            sync_id,
            sync_type,
            status,
            started_at,
            finished_at,
            message,
            total_records
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            sync_id,
            sync_type,
            status,
            datetime.now(),
            datetime.now(),
            message,
            total_records,
        ],
    )


def download_gzip_json(url: str) -> List[Dict[str, Any]]:
    response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
    response.raise_for_status()

    try:
        content = gzip.decompress(response.content)
        return json.loads(content.decode("utf-8"))
    except Exception:
        return response.json()


def map_current_instrument(row: Dict[str, Any], source_type: str):
    return [
        safe_text(row.get("instrument_key")),
        source_type,
        safe_text(row.get("segment")),
        safe_text(row.get("name")),
        safe_text(row.get("exchange")),
        safe_text(row.get("isin")),
        safe_text(row.get("instrument_type")),
        safe_text(row.get("trading_symbol")),
        safe_text(row.get("short_name")),
        safe_text(row.get("exchange_token")),
        normalize_expiry(row.get("expiry")),
        safe_float(row.get("strike_price")),
        safe_int(row.get("lot_size")),
        safe_int(row.get("minimum_lot")),
        safe_float(row.get("freeze_quantity")),
        safe_float(row.get("tick_size")),
        safe_bool(row.get("weekly")),
        safe_text(row.get("underlying_key")),
        safe_text(row.get("underlying_symbol")),
        safe_text(row.get("underlying_type")),
        safe_text(row.get("security_type")),
        json.dumps(row, ensure_ascii=False),
        datetime.now(),
    ]


def sync_current_instruments(conn) -> int:
    total = 0

    for source_type, url in INSTRUMENT_FILES.items():
        print(f"Downloading {source_type}: {url}")
        rows = download_gzip_json(url)

        conn.execute("DELETE FROM upstox_instruments WHERE source_type = ?", [source_type])

        mapped_rows = [map_current_instrument(row, source_type) for row in rows]

        conn.executemany(
            """
            INSERT INTO upstox_instruments (
                instrument_key,
                source_type,
                segment,
                name,
                exchange,
                isin,
                instrument_type,
                trading_symbol,
                short_name,
                exchange_token,
                expiry,
                strike_price,
                lot_size,
                minimum_lot,
                freeze_quantity,
                tick_size,
                weekly,
                underlying_key,
                underlying_symbol,
                underlying_type,
                security_type,
                raw_json,
                synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            mapped_rows,
        )

        total += len(mapped_rows)
        print(f"Saved {len(mapped_rows)} records for {source_type}")

    return total


def get_auth_headers(access_token: str):
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }


def upstox_get(access_token: str, path: str, params: Optional[Dict[str, str]] = None):
    url = f"{UPSTOX_BASE_URL}{path}"
    response = requests.get(
        url,
        headers=get_auth_headers(access_token),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code == 429:
        time.sleep(2)
        response = requests.get(
            url,
            headers=get_auth_headers(access_token),
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    response.raise_for_status()
    return response.json()


def get_expiries(access_token: str, underlying_key: str) -> List[str]:
    response = upstox_get(
        access_token,
        "/expired-instruments/expiries",
        {"instrument_key": underlying_key},
    )

    return response.get("data") or []


def get_expired_option_contracts(access_token: str, underlying_key: str, expiry_date: str) -> List[Dict[str, Any]]:
    response = upstox_get(
        access_token,
        "/expired-instruments/option/contract",
        {
            "instrument_key": underlying_key,
            "expiry_date": expiry_date,
        },
    )

    return response.get("data") or []


def get_expired_future_contracts(access_token: str, underlying_key: str, expiry_date: str) -> List[Dict[str, Any]]:
    response = upstox_get(
        access_token,
        "/expired-instruments/future/contract",
        {
            "instrument_key": underlying_key,
            "expiry_date": expiry_date,
        },
    )

    return response.get("data") or []


def map_expired_instrument(row: Dict[str, Any], source_type: str):
    return [
        safe_text(row.get("instrument_key")),
        safe_text(row.get("segment")),
        safe_text(row.get("name")),
        safe_text(row.get("exchange")),
        safe_text(row.get("instrument_type")),
        safe_text(row.get("trading_symbol")),
        safe_text(row.get("exchange_token")),
        normalize_expiry(row.get("expiry")),
        safe_float(row.get("strike_price")),
        safe_int(row.get("lot_size")),
        safe_int(row.get("minimum_lot")),
        safe_float(row.get("freeze_quantity")),
        safe_float(row.get("tick_size")),
        safe_bool(row.get("weekly")),
        safe_text(row.get("underlying_key")),
        safe_text(row.get("underlying_symbol")),
        safe_text(row.get("underlying_type")),
        source_type,
        json.dumps(row, ensure_ascii=False),
        datetime.now(),
    ]


def insert_expired_rows(conn, rows: List[Dict[str, Any]], source_type: str) -> int:
    if not rows:
        return 0

    mapped_rows = [map_expired_instrument(row, source_type) for row in rows]

    conn.executemany(
        """
        INSERT INTO upstox_expired_instruments (
            instrument_key,
            segment,
            name,
            exchange,
            instrument_type,
            trading_symbol,
            exchange_token,
            expiry,
            strike_price,
            lot_size,
            minimum_lot,
            freeze_quantity,
            tick_size,
            weekly,
            underlying_key,
            underlying_symbol,
            underlying_type,
            source_type,
            raw_json,
            synced_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        mapped_rows,
    )

    return len(mapped_rows)


def discover_underlying_keys(conn) -> List[str]:
    rows = conn.execute(
        """
        SELECT DISTINCT underlying_key
        FROM upstox_instruments
        WHERE source_type = 'bod_complete'
          AND underlying_key IS NOT NULL
          AND TRIM(underlying_key) <> ''
          AND segment IN ('NSE_FO', 'BSE_FO', 'NCD_FO', 'BCD_FO')
        ORDER BY underlying_key
        """
    ).fetchall()

    discovered = [row[0] for row in rows if row and row[0]]

    for key in DEFAULT_UNDERLYING_KEYS:
        if key not in discovered:
            discovered.insert(0, key)

    return discovered


def sync_expired_instruments(
    conn,
    access_token: str,
    underlying_keys: Iterable[str],
    clear_existing: bool = False,
) -> int:
    total = 0

    if clear_existing:
        conn.execute("DELETE FROM upstox_expired_instruments")

    for underlying_key in underlying_keys:
        print(f"Fetching expiries for {underlying_key}")

        try:
            expiries = get_expiries(access_token, underlying_key)
        except requests.HTTPError as error:
            print(f"Failed expiries for {underlying_key}: {error}")
            continue
        except Exception as error:
            print(f"Failed expiries for {underlying_key}: {error}")
            continue

        for expiry_date in expiries:
            print(f"Fetching expired contracts: {underlying_key} / {expiry_date}")

            conn.execute(
                """
                DELETE FROM upstox_expired_instruments
                WHERE underlying_key = ?
                  AND expiry = ?
                """,
                [underlying_key, expiry_date],
            )

            try:
                option_rows = get_expired_option_contracts(access_token, underlying_key, expiry_date)
                inserted_options = insert_expired_rows(conn, option_rows, "expired_option")
                total += inserted_options
                print(f"Saved expired options: {inserted_options}")
            except requests.HTTPError as error:
                print(f"Failed expired options for {underlying_key} {expiry_date}: {error}")
            except Exception as error:
                print(f"Failed expired options for {underlying_key} {expiry_date}: {error}")

            time.sleep(API_SLEEP_SECONDS)

            try:
                future_rows = get_expired_future_contracts(access_token, underlying_key, expiry_date)
                inserted_futures = insert_expired_rows(conn, future_rows, "expired_future")
                total += inserted_futures
                print(f"Saved expired futures: {inserted_futures}")
            except requests.HTTPError as error:
                print(f"Failed expired futures for {underlying_key} {expiry_date}: {error}")
            except Exception as error:
                print(f"Failed expired futures for {underlying_key} {expiry_date}: {error}")

            time.sleep(API_SLEEP_SECONDS)

    return total


def parse_args():
    parser = argparse.ArgumentParser(description="Sync Upstox instruments into DuckDB.")

    parser.add_argument(
        "--access-token",
        default=os.getenv("UPSTOX_ACCESS_TOKEN"),
        help="Upstox access token. Prefer setting UPSTOX_ACCESS_TOKEN env variable.",
    )

    parser.add_argument(
        "--current",
        action="store_true",
        help="Download current BOD and suspended instruments.",
    )

    parser.add_argument(
        "--expired",
        action="store_true",
        help="Download expired option and future instruments.",
    )

    parser.add_argument(
        "--all-expired-underlyings",
        action="store_true",
        help="Discover all current F&O underlying keys from BOD instruments and fetch expired contracts for them.",
    )

    parser.add_argument(
        "--underlying-key",
        action="append",
        default=[],
        help="Specific underlying key. Example: --underlying-key 'NSE_INDEX|Nifty 50'",
    )

    parser.add_argument(
        "--clear-expired",
        action="store_true",
        help="Clear upstox_expired_instruments before syncing expired instruments.",
    )

    return parser.parse_args()


def main():
    args = parse_args()

    sync_id = f"upstox-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    conn = get_connection()
    create_tables(conn)

    total_records = 0

    try:
        if args.current:
            count = sync_current_instruments(conn)
            total_records += count
            insert_sync_run(
                conn,
                sync_id,
                "upstox_current_instruments",
                "success",
                "Current instruments synced successfully.",
                count,
            )

        if args.expired:
            if not args.access_token:
                raise RuntimeError(
                    "Access token missing. Set UPSTOX_ACCESS_TOKEN or pass --access-token."
                )

            if args.all_expired_underlyings:
                underlying_keys = discover_underlying_keys(conn)
            elif args.underlying_key:
                underlying_keys = args.underlying_key
            else:
                underlying_keys = DEFAULT_UNDERLYING_KEYS

            count = sync_expired_instruments(
                conn=conn,
                access_token=args.access_token,
                underlying_keys=underlying_keys,
                clear_existing=args.clear_expired,
            )

            total_records += count
            insert_sync_run(
                conn,
                sync_id,
                "upstox_expired_instruments",
                "success",
                "Expired instruments synced successfully.",
                count,
            )

        if not args.current and not args.expired:
            print("Nothing selected. Use --current, --expired, or both.")
            return

        print("========================================")
        print("Upstox instrument sync completed")
        print(f"Database      : {DB_PATH}")
        print(f"Total records : {total_records}")
        print("========================================")

    except Exception as error:
        insert_sync_run(
            conn,
            sync_id,
            "upstox_instruments",
            "failed",
            str(error),
            total_records,
        )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()