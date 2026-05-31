import argparse
import gzip
import json
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import duckdb
import requests


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DB_PATH = PROJECT_ROOT / "backend" / "app" / "db" / "open_analytics.duckdb"

DATA_DIR = PROJECT_ROOT / "backend" / "app" / "data" / "upstox"
MASTER_INSTRUMENT_FILE = DATA_DIR / "upstox_instruments.json"

UPSTOX_BASE_URL = "https://api.upstox.com/v2"

CURRENT_INSTRUMENTS_URL = (
    "https://api.upstox.com/v2/market-quote/instruments/exchange/complete.json"
)

INSTRUMENT_FILES = {
    "bod_complete": {
        "url": CURRENT_INSTRUMENTS_URL,
        "path": MASTER_INSTRUMENT_FILE,
    }
}

DEFAULT_UNDERLYING_KEYS = [
    "NSE_INDEX|Nifty 50",
    "NSE_INDEX|Nifty Bank",
    "NSE_INDEX|Nifty Fin Service",
    "NSE_INDEX|Nifty Midcap Select",
    "BSE_INDEX|SENSEX",
    "BSE_INDEX|BANKEX",
]

REQUEST_TIMEOUT_SECONDS = 180
API_SLEEP_SECONDS = 0.35
DOWNLOAD_CHUNK_SIZE = 1024 * 1024 * 4


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH))


def normalize_path_for_duckdb(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


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


def insert_sync_run(
    conn,
    sync_id: str,
    sync_type: str,
    status: str,
    message: str,
    total_records: int,
):
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


def download_file_once(url: str, output_path: Path, force_download: bool = False) -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and output_path.stat().st_size > 0 and not force_download:
        print(f"Using existing local file: {output_path}")
        return output_path

    temp_download_path = output_path.with_suffix(output_path.suffix + ".download")
    temp_gzip_path = output_path.with_suffix(output_path.suffix + ".gz.download")

    print("Downloading active Upstox instruments list.")
    print("No token required for current instrument master.")
    print(f"URL  : {url}")
    print(f"Save : {output_path}")

    try:
        if url.lower().endswith(".gz"):
            with requests.get(
                url,
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()

                with open(temp_gzip_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if chunk:
                            file.write(chunk)

            with gzip.open(temp_gzip_path, "rb") as gzip_file:
                with open(temp_download_path, "wb") as output_file:
                    shutil.copyfileobj(gzip_file, output_file)

            temp_gzip_path.unlink(missing_ok=True)

        else:
            with requests.get(
                url,
                stream=True,
                timeout=REQUEST_TIMEOUT_SECONDS,
            ) as response:
                response.raise_for_status()

                with open(temp_download_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=DOWNLOAD_CHUNK_SIZE):
                        if chunk:
                            file.write(chunk)

        temp_download_path.replace(output_path)

        print(f"Download completed: {output_path}")
        print_current_file_sanity_check(output_path)

        return output_path

    except Exception:
        temp_download_path.unlink(missing_ok=True)
        temp_gzip_path.unlink(missing_ok=True)
        raise


def print_current_file_sanity_check(file_path: Path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)

        total = len(data) if isinstance(data, list) else 0
        print(f"Total active instruments found in file: {total}")

        if total > 0:
            sample = data[0]
            trading_symbol = sample.get("trading_symbol", "--")
            instrument_key = sample.get("instrument_key", "--")
            print(f"Sample Instrument: {trading_symbol} ({instrument_key})")

    except Exception as error:
        print(f"Sanity check skipped: {error}")


def get_existing_current_count(conn, source_type: str) -> int:
    try:
        row = conn.execute(
            """
            SELECT COUNT(*)
            FROM upstox_instruments
            WHERE source_type = ?
            """,
            [source_type],
        ).fetchone()

        return int(row[0] or 0)
    except Exception:
        return 0


def import_current_file_with_duckdb(
    conn,
    source_type: str,
    json_file_path: Path,
) -> int:
    duckdb_path = normalize_path_for_duckdb(json_file_path)
    source_type_sql = source_type.replace("'", "''")

    conn.execute("DROP TABLE IF EXISTS temp_upstox_current")

    read_start = time.time()

    print("Reading required current instrument columns directly inside DuckDB...")

    conn.execute(
        """
        CREATE TEMP TABLE temp_upstox_current AS
        SELECT *
        FROM read_json(
            ?,
            format = 'array',
            maximum_object_size = 16777216,
            columns = {
                instrument_key: 'VARCHAR',
                segment: 'VARCHAR',
                name: 'VARCHAR',
                exchange: 'VARCHAR',
                isin: 'VARCHAR',
                instrument_type: 'VARCHAR',
                trading_symbol: 'VARCHAR',
                short_name: 'VARCHAR',
                exchange_token: 'VARCHAR',
                expiry: 'VARCHAR',
                strike_price: 'DOUBLE',
                lot_size: 'BIGINT',
                minimum_lot: 'BIGINT',
                freeze_quantity: 'DOUBLE',
                tick_size: 'DOUBLE',
                weekly: 'BOOLEAN',
                underlying_key: 'VARCHAR',
                underlying_symbol: 'VARCHAR',
                underlying_type: 'VARCHAR',
                security_type: 'VARCHAR'
            }
        )
        """,
        [duckdb_path],
    )

    read_seconds = round(time.time() - read_start, 2)
    print(f"DuckDB JSON read time: {read_seconds} seconds")

    count = conn.execute("SELECT COUNT(*) FROM temp_upstox_current").fetchone()[0]
    print(f"DuckDB loaded temp rows: {count}")

    insert_start = time.time()

    conn.execute(
        f"""
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
        SELECT
            instrument_key,
            '{source_type_sql}' AS source_type,
            segment,
            name,
            exchange,
            isin,
            instrument_type,
            trading_symbol,
            short_name,
            exchange_token,

            CASE
                WHEN expiry IS NULL THEN NULL
                WHEN TRY_CAST(expiry AS BIGINT) IS NOT NULL
                    THEN CAST(epoch_ms(TRY_CAST(expiry AS BIGINT)) AS DATE)
                ELSE TRY_CAST(expiry AS DATE)
            END AS expiry,

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

            NULL AS raw_json,
            CURRENT_TIMESTAMP AS synced_at
        FROM temp_upstox_current
        """
    )

    insert_seconds = round(time.time() - insert_start, 2)
    print(f"DuckDB insert time: {insert_seconds} seconds")

    conn.execute("DROP TABLE IF EXISTS temp_upstox_current")

    return int(count or 0)


def sync_current_instruments(
    conn,
    force_download: bool = False,
    force_import: bool = False,
) -> int:
    total = 0

    conn.execute("PRAGMA threads=4")

    for source_type, file_config in INSTRUMENT_FILES.items():
        url = file_config["url"]
        path = file_config["path"]

        local_path = download_file_once(
            url=url,
            output_path=path,
            force_download=force_download,
        )

        existing_count = get_existing_current_count(conn, source_type)

        if (
            local_path.exists()
            and local_path.stat().st_size > 0
            and existing_count > 0
            and not force_download
            and not force_import
        ):
            print("Current instruments already exist in database.")
            print(f"Source type   : {source_type}")
            print(f"Existing rows : {existing_count}")
            print("Skipping re-import. Use --force-import to reload from local file.")
            total += existing_count
            continue

        print(f"Importing current instruments with DuckDB from local file: {local_path}")

        conn.execute("BEGIN TRANSACTION")

        try:
            print(f"Clearing old current records for source_type={source_type}")
            conn.execute(
                "DELETE FROM upstox_instruments WHERE source_type = ?",
                [source_type],
            )

            inserted_count = import_current_file_with_duckdb(
                conn=conn,
                source_type=source_type,
                json_file_path=local_path,
            )

            conn.execute("COMMIT")

        except Exception:
            conn.execute("ROLLBACK")
            raise

        total += inserted_count

        print(f"Saved {inserted_count} current records for {source_type}")

    return total


def get_auth_headers(access_token: str):
    return {
        "Accept": "application/json",
        "Authorization": f"Bearer {access_token}",
    }


def upstox_get(
    access_token: str,
    path: str,
    params: Optional[Dict[str, str]] = None,
):
    url = f"{UPSTOX_BASE_URL}{path}"

    response = requests.get(
        url,
        headers=get_auth_headers(access_token),
        params=params,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code == 429:
        print("Rate limited by Upstox. Retrying after 2 seconds...")
        time.sleep(2)

        response = requests.get(
            url,
            headers=get_auth_headers(access_token),
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

    if response.status_code == 401:
        raise RuntimeError(
            "Upstox returned 401 Unauthorized. Access token is missing, invalid, or expired."
        )

    response.raise_for_status()
    return response.json()


def upstox_get_with_param_fallback(
    access_token: str,
    path: str,
    underlying_key: str,
    expiry_date: Optional[str] = None,
):
    primary_params = {"underlying_key": underlying_key}
    fallback_params = {"instrument_key": underlying_key}

    if expiry_date:
        primary_params["expiry_date"] = expiry_date
        fallback_params["expiry_date"] = expiry_date

    try:
        return upstox_get(
            access_token=access_token,
            path=path,
            params=primary_params,
        )
    except Exception as primary_error:
        print(
            "Primary Upstox request failed using underlying_key. "
            "Retrying with instrument_key..."
        )
        print(f"Primary error: {primary_error}")

        return upstox_get(
            access_token=access_token,
            path=path,
            params=fallback_params,
        )


def get_expiries(access_token: str, underlying_key: str) -> List[str]:
    response = upstox_get_with_param_fallback(
        access_token=access_token,
        path="/expired-instruments/expiries",
        underlying_key=underlying_key,
    )

    return response.get("data") or []


def get_expired_option_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str,
) -> List[Dict[str, Any]]:
    response = upstox_get_with_param_fallback(
        access_token=access_token,
        path="/expired-instruments/option/contract",
        underlying_key=underlying_key,
        expiry_date=expiry_date,
    )

    return response.get("data") or []


def get_expired_future_contracts(
    access_token: str,
    underlying_key: str,
    expiry_date: str,
) -> List[Dict[str, Any]]:
    response = upstox_get_with_param_fallback(
        access_token=access_token,
        path="/expired-instruments/future/contract",
        underlying_key=underlying_key,
        expiry_date=expiry_date,
    )

    return response.get("data") or []


def normalize_expiry_for_python(value: Any) -> Optional[str]:
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
            return datetime.fromtimestamp(
                number_value / 1000,
                tz=timezone.utc,
            ).date().isoformat()
        except Exception:
            return value

    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(
                value / 1000,
                tz=timezone.utc,
            ).date().isoformat()
        except Exception:
            return None

    return None


def safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


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

    if isinstance(value, str):
        value = value.strip().lower()

        if value in ("true", "1", "yes", "y"):
            return True

        if value in ("false", "0", "no", "n"):
            return False

    return bool(value)


def map_expired_instrument(row: Dict[str, Any], source_type: str):
    return [
        safe_text(row.get("instrument_key")),
        safe_text(row.get("segment")),
        safe_text(row.get("name")),
        safe_text(row.get("exchange")),
        safe_text(row.get("instrument_type")),
        safe_text(row.get("trading_symbol")),
        safe_text(row.get("exchange_token")),
        normalize_expiry_for_python(row.get("expiry")),
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


def is_valid_expired_row(row: Dict[str, Any]) -> bool:
    if not isinstance(row, dict):
        return False

    instrument_key = safe_text(row.get("instrument_key"))
    trading_symbol = safe_text(row.get("trading_symbol"))
    expiry = normalize_expiry_for_python(row.get("expiry"))

    return bool(instrument_key or trading_symbol or expiry)


def insert_expired_rows(
    conn,
    rows: List[Dict[str, Any]],
    source_type: str,
) -> int:
    if not rows:
        return 0

    valid_rows = [row for row in rows if is_valid_expired_row(row)]

    if not valid_rows:
        return 0

    mapped_rows = [map_expired_instrument(row, source_type) for row in valid_rows]

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

    for key in reversed(DEFAULT_UNDERLYING_KEYS):
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
        print("Clearing all existing expired instruments.")
        conn.execute("DELETE FROM upstox_expired_instruments")

    for underlying_key in underlying_keys:
        print(f"Fetching expiries for {underlying_key}")

        try:
            expiries = get_expiries(access_token, underlying_key)
        except Exception as error:
            print(f"Failed expiries for {underlying_key}: {error}")
            continue

        print(f"Found {len(expiries)} expiries for {underlying_key}")

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
                option_rows = get_expired_option_contracts(
                    access_token=access_token,
                    underlying_key=underlying_key,
                    expiry_date=expiry_date,
                )

                inserted_options = insert_expired_rows(
                    conn=conn,
                    rows=option_rows,
                    source_type="expired_option",
                )

                total += inserted_options
                print(f"Saved expired options: {inserted_options}")

            except Exception as error:
                print(
                    f"Failed expired options for "
                    f"{underlying_key} {expiry_date}: {error}"
                )

            time.sleep(API_SLEEP_SECONDS)

            try:
                future_rows = get_expired_future_contracts(
                    access_token=access_token,
                    underlying_key=underlying_key,
                    expiry_date=expiry_date,
                )

                inserted_futures = insert_expired_rows(
                    conn=conn,
                    rows=future_rows,
                    source_type="expired_future",
                )

                total += inserted_futures
                print(f"Saved expired futures: {inserted_futures}")

            except Exception as error:
                print(
                    f"Failed expired futures for "
                    f"{underlying_key} {expiry_date}: {error}"
                )

            time.sleep(API_SLEEP_SECONDS)

    return total


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sync Upstox current and expired instruments into DuckDB."
    )

    parser.add_argument(
        "--access-token",
        default=os.getenv("UPSTOX_ACCESS_TOKEN"),
        help="Upstox access token. Prefer setting UPSTOX_ACCESS_TOKEN env variable.",
    )

    parser.add_argument(
        "--current",
        action="store_true",
        help="Download/import current active instruments from public Upstox master file.",
    )

    parser.add_argument(
        "--force-download",
        action="store_true",
        help="Force re-download of the Upstox current instrument master file.",
    )

    parser.add_argument(
        "--force-import",
        action="store_true",
        help="Force reload from local JSON into DuckDB even if records already exist.",
    )

    parser.add_argument(
        "--expired",
        action="store_true",
        help="Download expired option and future instruments. Requires access token.",
    )

    parser.add_argument(
        "--all-expired-underlyings",
        action="store_true",
        help="Discover all current F&O underlying keys from current instruments and fetch expired contracts for them.",
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
            count = sync_current_instruments(
                conn=conn,
                force_download=args.force_download,
                force_import=args.force_import,
            )

            total_records += count

            if args.force_download:
                message = "Current instruments re-downloaded and imported successfully."
            elif args.force_import:
                message = "Current instruments re-imported from local master file successfully."
            else:
                message = "Current instruments checked/imported successfully."

            insert_sync_run(
                conn=conn,
                sync_id=sync_id,
                sync_type="upstox_current_instruments",
                status="success",
                message=message,
                total_records=count,
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
                conn=conn,
                sync_id=sync_id,
                sync_type="upstox_expired_instruments",
                status="success",
                message="Expired instruments synced successfully.",
                total_records=count,
            )

        if not args.current and not args.expired:
            print("Nothing selected. Use --current, --expired, or both.")
            return

        print("========================================")
        print("Upstox instrument sync completed")
        print(f"Database      : {DB_PATH}")
        print(f"Data folder   : {DATA_DIR}")
        print(f"Total records : {total_records}")
        print("========================================")

    except Exception as error:
        insert_sync_run(
            conn=conn,
            sync_id=sync_id,
            sync_type="upstox_instruments",
            status="failed",
            message=str(error),
            total_records=total_records,
        )
        raise

    finally:
        conn.close()


if __name__ == "__main__":
    main()