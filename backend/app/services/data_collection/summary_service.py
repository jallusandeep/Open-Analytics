# backend\app\services\data_collection\summary_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def safe_table_count(conn, table_name: str) -> int:
    if not table_name:
        return 0

    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {table_name};").fetchone()[0] or 0)
    except Exception as error:
        print(f"Data collection count unavailable for {table_name}: {error}")
        return 0


def safe_fetchone(conn, query: str, params: Optional[List[Any]] = None):
    try:
        return conn.execute(query, params or []).fetchone()
    except Exception as error:
        print(f"Data collection query unavailable: {error}")
        return None


def safe_fetchall(conn, query: str, params: Optional[List[Any]] = None):
    try:
        return conn.execute(query, params or []).fetchall()
    except Exception as error:
        print(f"Data collection query unavailable: {error}")
        return []


def safe_mark_stale_sync_runs(conn):
    try:
        mark_stale_sync_runs(conn)
    except Exception as error:
        print(f"Data collection stale run cleanup skipped: {error}")


def safe_last_success_run(conn, sync_type: str):
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


def table_name_for_sync_type(sync_type: Optional[str]) -> Optional[str]:
    return {
        "upstox_current_instruments": "upstox_instruments",
        "upstox_expired_instruments": "upstox_expired_instruments",
        "upstox_equity_instruments": "upstox_equity_instruments",
        "upstox_ohlcv_daily": "upstox_ohlcv_candles",
        UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE: "upstox_market_holidays",
        UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE: "upstox_company_fundamentals",
        UPSTOX_EQUITY_NEWS_SYNC_TYPE: "equity_news",
        UPSTOX_IPO_SYNC_TYPE: "upstox_ipo_list",
        IPO_GMP_SCRAPER_SYNC_TYPE: "ipo_gmp_scraper"
    }.get(sync_type or "")


def safe_active_job_started_count(conn, sync_type: Optional[str], started_at) -> Optional[int]:
    table_name = table_name_for_sync_type(sync_type)

    if not table_name or not started_at:
        return None

    timestamp_column = "ingested_at" if table_name in ("upstox_ohlcv_candles", "equity_news", "upstox_ipo_list") else "synced_at"

    if table_name == "ipo_gmp_scraper":
        timestamp_column = "scraped_at"

    try:
        row = conn.execute(f"""
            SELECT COUNT(*)
            FROM {table_name}
            WHERE {timestamp_column} < ?;
        """, [started_at]).fetchone()
        return int(row[0] or 0)
    except Exception:
        return None


def get_disk_space_summary() -> dict:
    try:
        usage = shutil.disk_usage(APP_ROOT)
    except Exception:
        return {
            "path": str(APP_ROOT),
            "total_bytes": None,
            "used_bytes": None,
            "free_bytes": None,
            "used_percent": None,
            "free_percent": None
        }

    used_bytes = usage.total - usage.free

    return {
        "path": str(APP_ROOT),
        "total_bytes": usage.total,
        "used_bytes": used_bytes,
        "free_bytes": usage.free,
        "used_percent": round((used_bytes / usage.total) * 100, 2) if usage.total else None,
        "free_percent": round((usage.free / usage.total) * 100, 2) if usage.total else None
    }


def get_data_collection_summary_service():
    conn = get_connection()

    try:
        safe_mark_stale_sync_runs(conn)
        connection_status = get_upstox_connection_status(conn)

        current_count = safe_table_count(conn, "upstox_instruments")
        expired_count = safe_table_count(conn, "upstox_expired_instruments")
        equity_count = safe_table_count(conn, "upstox_equity_instruments")
        ohlcv_daily_count = safe_table_count(conn, "upstox_ohlcv_candles")
        market_holidays_count = safe_table_count(conn, "upstox_market_holidays")
        equity_news_count = safe_table_count(conn, "equity_news")
        ipo_count = safe_table_count(conn, "upstox_ipo_list")
        ipo_gmp_scraper_count = safe_table_count(conn, "ipo_gmp_scraper")
        company_fundamentals_count = safe_table_count(conn, "upstox_company_fundamentals")
        legacy_fundamentals_count = safe_table_count(conn, "fundamentals")
        corporate_actions_count = safe_table_count(conn, "corporate_actions")
        fii_dii_count = safe_table_count(conn, "fii_dii_activity")

        total_runs_row = safe_fetchone(conn, """
            SELECT COUNT(*)
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
            );
        """)
        total_runs = int(total_runs_row[0] or 0) if total_runs_row else 0

        last_run = safe_fetchone(conn, """
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
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
            )
            ORDER BY started_at DESC
            LIMIT 1;
        """)

        current_run = safe_last_success_run(conn, "upstox_current_instruments")
        expired_run = safe_last_success_run(conn, "upstox_expired_instruments")
        equity_run = safe_last_success_run(conn, "upstox_equity_instruments")
        ohlcv_run = safe_last_success_run(conn, "upstox_ohlcv_daily")
        market_holidays_run = safe_last_success_run(conn, UPSTOX_MARKET_HOLIDAYS_SYNC_TYPE)
        equity_news_run = safe_last_success_run(conn, UPSTOX_EQUITY_NEWS_SYNC_TYPE)
        ipo_run = safe_last_success_run(conn, UPSTOX_IPO_SYNC_TYPE)
        ipo_gmp_scraper_run = safe_last_success_run(conn, IPO_GMP_SCRAPER_SYNC_TYPE)
        company_fundamentals_run = safe_last_success_run(conn, UPSTOX_COMPANY_FUNDAMENTALS_SYNC_TYPE)

        active_run = safe_fetchone(conn, """
            SELECT sync_type, status, started_at
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            ORDER BY started_at DESC
            LIMIT 1;
        """)

        active_job = active_run[0] if active_run else None
        active_job_started_at = active_run[2] if active_run and active_run[2] else None
        active_job_table = table_name_for_sync_type(active_job)
        active_job_current_records = (
            safe_table_count(conn, active_job_table)
            if active_job_table else None
        )
        active_job_records_at_start = safe_active_job_started_count(
            conn,
            active_job,
            active_job_started_at
        )

        return {
            "connection_status": connection_status,
            "disk_space": get_disk_space_summary(),
            "total_current_instruments": current_count,
            "total_expired_instruments": expired_count,
            "total_equity_instruments": equity_count,
            "total_ohlcv_daily": ohlcv_daily_count,
            "total_market_holidays": market_holidays_count,
            "total_equity_news": equity_news_count,
            "total_ipo_calendar": ipo_count,
            "total_ipos": ipo_count,
            "total_ipo_gmp_scraper": ipo_gmp_scraper_count,
            "total_ipo_scraper": ipo_gmp_scraper_count,
            "total_company_fundamentals": company_fundamentals_count,
            "total_fundamentals": company_fundamentals_count,
            "total_legacy_fundamentals": legacy_fundamentals_count,
            "total_corporate_actions": corporate_actions_count,
            "total_fii_dii_activity": fii_dii_count,
            "total_sync_runs": total_runs,
            "last_sync_at": str(last_run[3]) if last_run and last_run[3] else None,
            "last_duration_seconds": last_run[4] if last_run else None,
            "current_last_sync_at": str(current_run[0]) if current_run and current_run[0] else None,
            "current_duration_seconds": current_run[1] if current_run else None,
            "expired_last_sync_at": str(expired_run[0]) if expired_run and expired_run[0] else None,
            "expired_duration_seconds": expired_run[1] if expired_run else None,
            "equity_last_sync_at": str(equity_run[0]) if equity_run and equity_run[0] else None,
            "equity_duration_seconds": equity_run[1] if equity_run else None,
            "ohlcv_daily_last_sync_at": str(ohlcv_run[0]) if ohlcv_run and ohlcv_run[0] else None,
            "ohlcv_daily_duration_seconds": ohlcv_run[1] if ohlcv_run else None,
            "market_holidays_last_sync_at": str(market_holidays_run[0]) if market_holidays_run and market_holidays_run[0] else None,
            "market_holidays_duration_seconds": market_holidays_run[1] if market_holidays_run else None,
            "equity_news_last_sync_at": str(equity_news_run[0]) if equity_news_run and equity_news_run[0] else None,
            "equity_news_duration_seconds": equity_news_run[1] if equity_news_run else None,
            "ipo_calendar_last_sync_at": str(ipo_run[0]) if ipo_run and ipo_run[0] else None,
            "ipo_calendar_duration_seconds": ipo_run[1] if ipo_run else None,
            "ipo_gmp_scraper_last_sync_at": str(ipo_gmp_scraper_run[0]) if ipo_gmp_scraper_run and ipo_gmp_scraper_run[0] else None,
            "ipo_gmp_scraper_duration_seconds": ipo_gmp_scraper_run[1] if ipo_gmp_scraper_run else None,
            "ipo_scraper_last_sync_at": str(ipo_gmp_scraper_run[0]) if ipo_gmp_scraper_run and ipo_gmp_scraper_run[0] else None,
            "ipo_scraper_duration_seconds": ipo_gmp_scraper_run[1] if ipo_gmp_scraper_run else None,
            "company_fundamentals_last_sync_at": str(company_fundamentals_run[0]) if company_fundamentals_run and company_fundamentals_run[0] else None,
            "company_fundamentals_duration_seconds": company_fundamentals_run[1] if company_fundamentals_run else None,
            "active_job": active_job,
            "active_job_status": active_run[1] if active_run else None,
            "active_job_started_at": str(active_job_started_at) if active_job_started_at else None,
            "active_job_current_records": active_job_current_records,
            "active_job_records_at_start": active_job_records_at_start,
            "active_job_records_added": (
                active_job_current_records - active_job_records_at_start
                if active_job_current_records is not None
                and active_job_records_at_start is not None
                else None
            )
        }

    finally:
        conn.close()


def get_data_collection_runs_service():
    conn = get_connection()

    try:
        rows = safe_fetchall(conn, """
            SELECT
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
            FROM upstox_sync_runs
            WHERE sync_type IN (
                'upstox_current_instruments',
                'upstox_expired_instruments',
                'upstox_equity_instruments',
                'upstox_ohlcv_daily',
                'upstox_market_holidays',
                'upstox_company_fundamentals',
                'upstox_equity_news',
                'upstox_ipo_calendar',
                'ipo_gmp_scraper'
            )
            ORDER BY started_at DESC
            LIMIT 25;
        """)

        return [
            {
                "sync_id": row[0],
                "sync_type": row[1],
                "status": row[2],
                "started_at": str(row[3]) if row[3] else None,
                "finished_at": str(row[4]) if row[4] else None,
                "duration_seconds": row[5],
                "message": row[6],
                "total_records": row[7],
                "trigger_source": row[8] or "manual",
                "triggered_by_id": row[9],
                "triggered_by_name": row[10],
                "triggered_by_role": row[11]
            }
            for row in rows
        ]

    finally:
        conn.close()
