"""Archive expired current instruments without losing their stored metadata."""

from datetime import datetime
from zoneinfo import ZoneInfo


ARCHIVE_COLUMNS = (
    "instrument_key", "segment", "name", "exchange", "instrument_type",
    "trading_symbol", "exchange_token", "expiry", "strike_price", "lot_size",
    "minimum_lot", "freeze_quantity", "tick_size", "weekly", "underlying_key",
    "underlying_symbol", "underlying_type", "source_type", "raw_json", "synced_at",
)


def archive_expired_instruments(conn, *, today=None, in_transaction=False):
    """Move contracts after their expiry day (India time), atomically.

    Existing archived contracts win over master-file duplicates. Callers doing
    a master refresh can include this operation in their own transaction.
    """
    today = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    if not in_transaction:
        conn.execute("BEGIN TRANSACTION")
    try:
        columns = ", ".join(ARCHIVE_COLUMNS)
        selected = ", ".join(
            "COALESCE(c.raw_json, to_json(c))" if column == "raw_json"
            else f"c.{column}" for column in ARCHIVE_COLUMNS
        )
        conn.execute(f"""
            INSERT INTO upstox_expired_instruments ({columns})
            SELECT {selected} FROM upstox_instruments c
            WHERE c.expiry < ? AND NOT EXISTS (
                SELECT 1 FROM upstox_expired_instruments e
                WHERE e.instrument_key IS NOT DISTINCT FROM c.instrument_key
                  AND e.expiry = c.expiry
            )
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY c.instrument_key, c.expiry ORDER BY c.synced_at DESC
            ) = 1
        """, [today])
        conn.execute("DELETE FROM upstox_instruments WHERE expiry < ?", [today])
        if not in_transaction:
            conn.execute("COMMIT")
    except Exception:
        if not in_transaction:
            conn.execute("ROLLBACK")
        raise
