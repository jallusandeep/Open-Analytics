from datetime import datetime
from typing import Any, List, Optional

UPSTOX_PROVIDER = "upstox"
STALE_RUNNING_RUN_HOURS = 2
EXPIRED_SOURCE_OPTION = "expired_option_contract"
EXPIRED_SOURCE_FUTURE = "expired_future_contract"

SYNC_RUN_COLUMNS = """
    sync_id,
    sync_type,
    status,
    started_at,
    finished_at,
    duration_seconds,
    message,
    total_records,
    trigger_source,
    triggered_by_id,
    triggered_by_name,
    triggered_by_role
"""


class DataCollectionRepository:
    def get_upstox_connection_status(self, conn) -> str:
        row = conn.execute("""
            SELECT connection_status
            FROM external_connections
            WHERE provider = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [UPSTOX_PROVIDER]).fetchone()

        if not row:
            return "not_connected"

        return row[0] or "saved"

    def get_saved_upstox_access_token_row(self, conn):
        return conn.execute("""
            SELECT access_token, connection_status
            FROM external_connections
            WHERE provider = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [UPSTOX_PROVIDER]).fetchone()

    def mark_stale_sync_runs(self, conn):
        conn.execute("""
            UPDATE upstox_sync_runs
            SET
                status = 'failed',
                finished_at = CURRENT_TIMESTAMP,
                duration_seconds = date_diff('second', started_at, CURRENT_TIMESTAMP),
                message = 'Sync run was interrupted before completion.'
            WHERE status IN ('running', 'cancel_requested')
              AND started_at < CURRENT_TIMESTAMP - (? * INTERVAL '1 hour');
        """, [STALE_RUNNING_RUN_HOURS])
        conn.commit()

    def get_active_sync_run(self, conn):
        return conn.execute("""
            SELECT sync_type, status
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()

    def create_sync_run(
        self,
        conn,
        sync_id: str,
        sync_type: str,
        status_text: str,
        message: str,
        trigger_metadata: dict,
    ):
        conn.execute("""
            INSERT INTO upstox_sync_runs (
                sync_id,
                sync_type,
                status,
                started_at,
                finished_at,
                duration_seconds,
                message,
                total_records,
                trigger_source,
                triggered_by_id,
                triggered_by_name,
                triggered_by_role
            )
            VALUES (?, ?, ?, CURRENT_TIMESTAMP, NULL, NULL, ?, 0, ?, ?, ?, ?);
        """, [
            sync_id,
            sync_type,
            status_text,
            message,
            trigger_metadata["trigger_source"],
            trigger_metadata["triggered_by_id"],
            trigger_metadata["triggered_by_name"],
            trigger_metadata["triggered_by_role"],
        ])
        conn.commit()

    def finish_sync_run(
        self,
        conn,
        sync_id: str,
        status_text: str,
        message: str,
        total_records: int,
        duration_seconds: int,
    ):
        conn.execute("""
            UPDATE upstox_sync_runs
            SET
                status = ?,
                finished_at = CURRENT_TIMESTAMP,
                duration_seconds = ?,
                message = ?,
                total_records = ?
            WHERE sync_id = ?;
        """, [status_text, duration_seconds, message, total_records, sync_id])
        conn.commit()

    def get_sync_run_status(self, conn, sync_id: str):
        return conn.execute("""
            SELECT status
            FROM upstox_sync_runs
            WHERE sync_id = ?;
        """, [sync_id]).fetchone()

    def get_running_sync_runs(self, conn):
        return conn.execute("""
            SELECT sync_id, sync_type
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC;
        """).fetchall()

    def request_cancel_running_syncs(self, conn):
        conn.execute("""
            UPDATE upstox_sync_runs
            SET
                message = 'Cancel requested by user.',
                status = 'cancel_requested'
            WHERE status IN ('running', 'cancel_requested');
        """)
        conn.commit()

    def delete_bod_complete_instruments(self, conn):
        conn.execute("""
            DELETE FROM upstox_instruments
            WHERE source_type = 'bod_complete';
        """)

    def import_current_instruments_from_json(self, conn, duckdb_path: str):
        conn.execute("""
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
                'bod_complete' AS source_type,
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
            );
        """, [duckdb_path])

    def count_bod_complete_instruments(self, conn) -> int:
        return int(
            conn.execute("""
                SELECT COUNT(*)
                FROM upstox_instruments
                WHERE source_type = 'bod_complete';
            """).fetchone()[0] or 0
        )

    def ensure_expired_contract_sync_status_table(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_expired_contract_sync_status (
                underlying_key VARCHAR,
                expiry DATE,
                source_type VARCHAR,
                status VARCHAR DEFAULT 'success',
                record_count BIGINT DEFAULT 0,
                last_error VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def ensure_expired_underlying_sync_status_table(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS upstox_expired_underlying_sync_status (
                underlying_key VARCHAR,
                status VARCHAR DEFAULT 'success',
                expiry_count BIGINT DEFAULT 0,
                record_count BIGINT DEFAULT 0,
                include_options BOOLEAN DEFAULT TRUE,
                include_futures BOOLEAN DEFAULT TRUE,
                last_error VARCHAR,
                synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def has_expired_underlying_been_fully_checked(
        self,
        conn,
        underlying_key: str,
        include_options: bool,
        include_futures: bool,
    ) -> bool:
        self.ensure_expired_underlying_sync_status_table(conn)

        row = conn.execute("""
            SELECT status
            FROM upstox_expired_underlying_sync_status
            WHERE underlying_key = ?
              AND status = 'success'
              AND (? = FALSE OR include_options = TRUE)
              AND (? = FALSE OR include_futures = TRUE)
            LIMIT 1;
        """, [underlying_key, include_options, include_futures]).fetchone()

        return bool(row)

    def record_expired_underlying_status(
        self,
        conn,
        underlying_key: str,
        status_value: str,
        expiry_count: int,
        record_count: int,
        include_options: bool,
        include_futures: bool,
        error_message: Optional[str],
    ):
        self.ensure_expired_underlying_sync_status_table(conn)

        conn.execute("""
            DELETE FROM upstox_expired_underlying_sync_status
            WHERE underlying_key = ?
              AND include_options = ?
              AND include_futures = ?;
        """, [underlying_key, include_options, include_futures])

        conn.execute("""
            INSERT INTO upstox_expired_underlying_sync_status (
                underlying_key,
                status,
                expiry_count,
                record_count,
                include_options,
                include_futures,
                last_error,
                synced_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, [
            underlying_key,
            status_value,
            int(expiry_count or 0),
            int(record_count or 0),
            bool(include_options),
            bool(include_futures),
            error_message,
        ])

    def has_expired_contract_group_been_checked(
        self,
        conn,
        underlying_key: str,
        expiry_date: str,
        source_type: str,
    ) -> bool:
        existing_records = conn.execute("""
            SELECT COUNT(1)
            FROM upstox_expired_instruments
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?;
        """, [underlying_key, expiry_date, source_type]).fetchone()[0]

        if existing_records:
            return True

        self.ensure_expired_contract_sync_status_table(conn)

        status_row = conn.execute("""
            SELECT status
            FROM upstox_expired_contract_sync_status
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?
              AND status = 'success'
            LIMIT 1;
        """, [underlying_key, expiry_date, source_type]).fetchone()

        return bool(status_row)

    def record_expired_contract_group_status(
        self,
        conn,
        underlying_key: str,
        expiry_date: str,
        source_type: str,
        status_value: str,
        record_count: int,
        error_message: Optional[str],
    ):
        self.ensure_expired_contract_sync_status_table(conn)

        conn.execute("""
            DELETE FROM upstox_expired_contract_sync_status
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?;
        """, [underlying_key, expiry_date, source_type])

        conn.execute("""
            INSERT INTO upstox_expired_contract_sync_status (
                underlying_key,
                expiry,
                source_type,
                status,
                record_count,
                last_error,
                synced_at
            )
            VALUES (?, TRY_CAST(? AS DATE), ?, ?, ?, ?, CURRENT_TIMESTAMP);
        """, [
            underlying_key,
            expiry_date,
            source_type,
            status_value,
            int(record_count or 0),
            error_message,
        ])

    def get_configured_expired_underlying_keys(
        self,
        conn,
        segment: str,
        underlying_types: List[str],
    ) -> List[str]:
        type_placeholders = ", ".join(["?"] * len(underlying_types))

        rows = conn.execute(f"""
            SELECT underlying_key
            FROM upstox_instruments
            WHERE segment = ?
              AND underlying_key IS NOT NULL
              AND TRIM(underlying_key) <> ''
              AND UPPER(COALESCE(underlying_type, '')) IN ({type_placeholders})
            GROUP BY underlying_key
            ORDER BY
                CASE
                    WHEN MIN(UPPER(COALESCE(underlying_type, ''))) = 'INDEX' THEN 0
                    ELSE 1
                END,
                MIN(COALESCE(underlying_symbol, '')),
                underlying_key;
        """, [segment] + underlying_types).fetchall()

        return [row[0] for row in rows if row and row[0]]

    def delete_expired_instrument_group(
        self,
        conn,
        underlying_key: str,
        expiry_date: str,
        source_type: str,
    ):
        conn.execute("""
            DELETE FROM upstox_expired_instruments
            WHERE underlying_key = ?
              AND expiry = TRY_CAST(? AS DATE)
              AND source_type = ?;
        """, [underlying_key, expiry_date, source_type])

    def insert_expired_instruments_batch(self, conn, rows: list):
        conn.executemany("""
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
            SELECT
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                TRY_CAST(? AS DATE),
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                ?,
                TRY_CAST(? AS JSON),
                CURRENT_TIMESTAMP;
        """, rows)

    def table_count(self, conn, table_name: str) -> int:
        try:
            return int(conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0] or 0)
        except Exception:
            return 0

    def last_success_run(self, conn, sync_type: str):
        try:
            return conn.execute("""
                SELECT finished_at, duration_seconds
                FROM upstox_sync_runs
                WHERE sync_type = ?
                  AND status = 'success'
                ORDER BY finished_at DESC
                LIMIT 1;
            """, [sync_type]).fetchone()
        except Exception:
            return None

    def count_sync_runs(self, conn) -> int:
        return conn.execute("""
            SELECT COUNT(*)
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            );
        """).fetchone()[0]

    def get_last_sync_run(self, conn):
        return conn.execute("""
            SELECT
                sync_type,
                status,
                started_at,
                finished_at,
                duration_seconds,
                total_records
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            )
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()

    def get_active_sync_run_detail(self, conn):
        return conn.execute("""
            SELECT sync_type, status, started_at
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC
            LIMIT 1;
        """).fetchone()

    def count_records_synced_before(self, conn, table_name: str, started_at) -> Optional[int]:
        if not started_at:
            return None

        try:
            row = conn.execute(f"""
                SELECT COUNT(*)
                FROM {table_name}
                WHERE synced_at < ?;
            """, [started_at]).fetchone()
            return int(row[0] or 0)
        except Exception:
            return None

    def list_recent_sync_runs(self, conn, limit: int = 25):
        return conn.execute(f"""
            SELECT {SYNC_RUN_COLUMNS}
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily'
            )
            ORDER BY started_at DESC
            LIMIT ?;
        """, [limit]).fetchall()

    def count_instruments_preview(self, conn, table_name: str, where_sql: str, params: list) -> int:
        return conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_name}
            {where_sql};
        """, params).fetchone()[0]

    def list_instruments_preview(
        self,
        conn,
        table_name: str,
        where_sql: str,
        params: list,
        order_sql: str,
        page_size: int,
        offset: int,
    ):
        return conn.execute(f"""
            SELECT
                instrument_key,
                trading_symbol,
                name,
                segment,
                exchange,
                instrument_type,
                expiry,
                strike_price,
                lot_size,
                source_type,
                underlying_key,
                underlying_symbol,
                synced_at
            FROM {table_name}
            {where_sql}
            ORDER BY {order_sql}
            LIMIT ?
            OFFSET ?;
        """, params + [page_size, offset]).fetchall()
