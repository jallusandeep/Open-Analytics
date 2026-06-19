import calendar
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.database import get_connection
from app.services.data_collection_service import (
    sync_ipo_gmp_scraper_service,
    sync_upstox_company_fundamentals_service,
    sync_upstox_current_instruments_service,
    sync_upstox_equity_news_service,
    sync_upstox_expired_instruments_service,
    sync_upstox_ipo_calendar_service,
    sync_upstox_market_holidays_service,
    sync_upstox_ohlcv_daily_service
)
from app.services.data_collection_queue_service import (
    DATA_COLLECTION_SCHEDULED_PRIORITY,
    enqueue_data_collection_job
)


IST_TIMEZONE = "Asia/Kolkata"
IST_TZINFO = timezone(timedelta(hours=5, minutes=30))
SCHEDULER_INTERVAL_SECONDS = 30

VALID_JOB_TYPES = {
    "current_instruments": {
        "label": "Current Instruments",
        "sync_type": "upstox_current_instruments"
    },
    "expired_instruments": {
        "label": "Expired Instruments",
        "sync_type": "upstox_expired_instruments"
    },
    "ohlcv_daily": {
        "label": "OHLCV Candles",
        "sync_type": "upstox_ohlcv_daily"
    },
    "company_fundamentals": {
        "label": "Company Fundamentals",
        "sync_type": "upstox_company_fundamentals"
    },
    "market_holidays": {
        "label": "Market Calendar",
        "sync_type": "upstox_market_holidays"
    },
    "equity_news": {
        "label": "Equity News",
        "sync_type": "upstox_equity_news"
    },
    "ipo_calendar": {
        "label": "IPO Calendar",
        "sync_type": "upstox_ipo_calendar"
    },
    "ipo_scraper": {
        "label": "IPO Scrapper",
        "sync_type": "ipo_gmp_scraper"
    }
}

SCHEDULABLE_JOB_TYPES = tuple(VALID_JOB_TYPES.keys())
SCHEDULABLE_JOB_TYPE_SQL = ", ".join(["?"] * len(SCHEDULABLE_JOB_TYPES))
VALID_SCHEDULE_FREQUENCIES = ("daily", "weekly", "monthly")

_scheduler_thread = None
_scheduler_stop_event = threading.Event()
_scheduler_lock = threading.Lock()


def get_system_scheduler_user():
    return {
        "user_id": "system",
        "login_id": "system",
        "email": "system@openanalytics.local",
        "full_name": "System Scheduler",
        "role": "system"
    }


def get_user_id(current_user: Optional[dict]) -> str:
    if not current_user:
        return "system"

    return (
        current_user.get("user_id")
        or current_user.get("login_id")
        or current_user.get("email")
        or "system"
    )


def get_ist_now() -> datetime:
    try:
        return datetime.now(ZoneInfo(IST_TIMEZONE))
    except ZoneInfoNotFoundError:
        return datetime.now(IST_TZINFO)


def parse_schedule_time(schedule_time: str) -> tuple[int, int]:
    clean_value = str(schedule_time or "").strip()

    if clean_value.upper().endswith(("AM", "PM")):
        for time_format in ("%I:%M %p", "%I:%M%p"):
            try:
                parsed_time = datetime.strptime(clean_value.upper(), time_format)
                return parsed_time.hour, parsed_time.minute
            except ValueError:
                continue

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule time must be a valid 12-hour time like 02:30 PM."
        )

    try:
        parts = clean_value.split(":")
        if len(parts) != 2:
            raise ValueError

        hour = int(parts[0])
        minute = int(parts[1])
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule time must be in HH:MM format."
        )

    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule time must be a valid 24-hour time."
        )

    return hour, minute


def normalize_schedule_time(schedule_time: str) -> str:
    hour, minute = parse_schedule_time(schedule_time)
    return f"{hour:02d}:{minute:02d}"


def format_schedule_label(schedule_time: str) -> str:
    hour, minute = parse_schedule_time(schedule_time)
    value = datetime(2000, 1, 1, hour, minute)
    return value.strftime("%I:%M %p")


def validate_job_type(job_type: str) -> str:
    clean_job_type = str(job_type or "").strip()

    if clean_job_type not in VALID_JOB_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid job type. Use current_instruments, expired_instruments, "
                "ohlcv_daily, company_fundamentals, market_holidays, "
                "equity_news, ipo_calendar, or ipo_scraper."
            )
        )

    return clean_job_type


def normalize_time_format(time_format: str) -> str:
    clean_time_format = str(time_format or "24").strip()

    if clean_time_format not in ("12", "24"):
        return "24"

    return clean_time_format


def normalize_schedule_frequency(schedule_frequency: str) -> str:
    clean_frequency = str(schedule_frequency or "daily").strip().lower()

    if clean_frequency not in VALID_SCHEDULE_FREQUENCIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Schedule repeat must be daily, weekly, or monthly."
        )

    return clean_frequency


def add_month_preserving_day(value: datetime) -> datetime:
    next_month = value.month + 1
    next_year = value.year

    if next_month > 12:
        next_month = 1
        next_year += 1

    max_day = calendar.monthrange(next_year, next_month)[1]
    return value.replace(year=next_year, month=next_month, day=min(value.day, max_day))


def add_frequency_interval(value: datetime, schedule_frequency: str) -> datetime:
    frequency = normalize_schedule_frequency(schedule_frequency)

    if frequency == "weekly":
        return value + timedelta(days=7)

    if frequency == "monthly":
        return add_month_preserving_day(value)

    return value + timedelta(days=1)


def calculate_next_run_at(
    schedule_time: str,
    is_active: bool = True,
    schedule_frequency: str = "daily"
) -> Optional[datetime]:
    if not is_active:
        return None

    frequency = normalize_schedule_frequency(schedule_frequency)
    hour, minute = parse_schedule_time(schedule_time)
    now = get_ist_now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if next_run <= now:
        next_run = add_frequency_interval(next_run, frequency)

    return next_run.replace(tzinfo=None)


def calculate_next_run_at_after_run(
    schedule_time: str,
    schedule_frequency: str,
    run_at: datetime,
    is_active: bool = True
) -> Optional[datetime]:
    if not is_active:
        return None

    hour, minute = parse_schedule_time(schedule_time)
    next_run = add_frequency_interval(run_at, schedule_frequency).replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0
    )

    return next_run.replace(tzinfo=None)


def row_to_schedule(row) -> Dict[str, Any]:
    return {
        "schedule_id": row[0],
        "job_type": row[1],
        "job_label": VALID_JOB_TYPES.get(row[1], {}).get("label", row[1]),
        "schedule_time": row[2],
        "schedule_label": row[3],
        "time_format": row[4],
        "schedule_frequency": row[5] or "daily",
        "timezone": row[6],
        "is_active": bool(row[7]),
        "last_run_date": str(row[8]) if row[8] else None,
        "last_run_at": str(row[9]) if row[9] else None,
        "next_run_at": str(row[10]) if row[10] else None,
        "created_at": str(row[11]) if row[11] else None,
        "updated_at": str(row[12]) if row[12] else None,
        "updated_by": row[13]
    }


def get_data_collection_schedules_service():
    conn = get_connection()

    try:
        rows = conn.execute(f"""
            SELECT
                schedule_id,
                job_type,
                schedule_time,
                schedule_label,
                time_format,
                schedule_frequency,
                timezone,
                is_active,
                last_run_date,
                last_run_at,
                next_run_at,
                created_at,
                updated_at,
                updated_by
            FROM upstox_data_collection_schedules
            WHERE record_status = 'S'
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
            ORDER BY job_type, schedule_frequency, schedule_time;
        """, list(SCHEDULABLE_JOB_TYPES)).fetchall()

        return [row_to_schedule(row) for row in rows]

    finally:
        conn.close()


def create_data_collection_schedule_service(payload: dict, current_user: dict):
    job_type = validate_job_type(payload.get("job_type"))
    schedule_time = normalize_schedule_time(payload.get("schedule_time"))
    schedule_label = format_schedule_label(schedule_time)
    time_format = normalize_time_format(payload.get("time_format"))
    schedule_frequency = normalize_schedule_frequency(payload.get("schedule_frequency"))
    is_active = bool(payload.get("is_active", True))
    schedule_id = str(__import__("uuid").uuid4())
    user_id = get_user_id(current_user)
    next_run_at = calculate_next_run_at(schedule_time, is_active, schedule_frequency)

    conn = get_connection()

    try:
        existing = conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE job_type = ?
              AND schedule_time = ?
              AND schedule_frequency = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [job_type, schedule_time, schedule_frequency]).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This schedule already exists for the selected job."
            )

        conn.execute("""
            INSERT INTO upstox_data_collection_schedules (
                schedule_id,
                job_type,
                schedule_time,
                schedule_label,
                time_format,
                schedule_frequency,
                timezone,
                is_active,
                last_run_date,
                last_run_at,
                next_run_at,
                record_status,
                version_no,
                created_by,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'S', 1, ?, ?);
        """, [
            schedule_id,
            job_type,
            schedule_time,
            schedule_label,
            time_format,
            schedule_frequency,
            IST_TIMEZONE,
            is_active,
            next_run_at,
            user_id,
            user_id
        ])

        conn.commit()

        return {
            "status": "success",
            "message": "Schedule created successfully.",
            "schedule_id": schedule_id
        }

    finally:
        conn.close()


def update_data_collection_schedule_service(
    schedule_id: str,
    payload: dict,
    current_user: dict
):
    job_type = validate_job_type(payload.get("job_type"))
    schedule_time = normalize_schedule_time(payload.get("schedule_time"))
    schedule_label = format_schedule_label(schedule_time)
    time_format = normalize_time_format(payload.get("time_format"))
    schedule_frequency = normalize_schedule_frequency(payload.get("schedule_frequency"))
    is_active = bool(payload.get("is_active", True))
    user_id = get_user_id(current_user)
    next_run_at = calculate_next_run_at(schedule_time, is_active, schedule_frequency)

    conn = get_connection()

    try:
        current = conn.execute(f"""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id] + list(SCHEDULABLE_JOB_TYPES)).fetchone()

        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found."
            )

        existing = conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE job_type = ?
              AND schedule_time = ?
              AND schedule_frequency = ?
              AND schedule_id <> ?
              AND record_status = 'S'
            LIMIT 1;
        """, [job_type, schedule_time, schedule_frequency, schedule_id]).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This schedule already exists for the selected job."
            )

        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                job_type = ?,
                schedule_time = ?,
                schedule_label = ?,
                time_format = ?,
                schedule_frequency = ?,
                timezone = ?,
                is_active = ?,
                next_run_at = ?,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
              AND record_status = 'S';
        """, [
            job_type,
            schedule_time,
            schedule_label,
            time_format,
            schedule_frequency,
            IST_TIMEZONE,
            is_active,
            next_run_at,
            user_id,
            schedule_id
        ] + list(SCHEDULABLE_JOB_TYPES))

        conn.commit()

        return {
            "status": "success",
            "message": "Schedule updated successfully."
        }

    finally:
        conn.close()


def toggle_data_collection_schedule_service(schedule_id: str, current_user: dict):
    user_id = get_user_id(current_user)
    conn = get_connection()

    try:
        row = conn.execute(f"""
            SELECT schedule_time, is_active, schedule_frequency
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id] + list(SCHEDULABLE_JOB_TYPES)).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found."
            )

        schedule_time = row[0]
        next_is_active = not bool(row[1])
        schedule_frequency = normalize_schedule_frequency(row[2])
        next_run_at = calculate_next_run_at(
            schedule_time,
            next_is_active,
            schedule_frequency
        )

        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                is_active = ?,
                next_run_at = ?,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
              AND record_status = 'S';
        """, [
            next_is_active,
            next_run_at,
            user_id,
            schedule_id
        ] + list(SCHEDULABLE_JOB_TYPES))

        conn.commit()

        return {
            "status": "success",
            "message": "Schedule status updated successfully.",
            "is_active": next_is_active
        }

    finally:
        conn.close()


def delete_data_collection_schedule_service(schedule_id: str, current_user: dict):
    user_id = get_user_id(current_user)
    conn = get_connection()

    try:
        row = conn.execute(f"""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id] + list(SCHEDULABLE_JOB_TYPES)).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found."
            )

        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                record_status = 'D',
                is_active = FALSE,
                next_run_at = NULL,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL});
        """, [user_id, schedule_id] + list(SCHEDULABLE_JOB_TYPES))

        conn.commit()

        return {
            "status": "success",
            "message": "Schedule deleted successfully."
        }

    finally:
        conn.close()


def get_due_schedules(conn):
    now = get_ist_now()
    current_time = now.strftime("%H:%M")
    current_run_at = now.replace(tzinfo=None)
    today = now.date().isoformat()

    return conn.execute(f"""
        SELECT
            schedule_id,
            job_type,
            schedule_time,
            last_run_date,
            is_active,
            next_run_at,
            schedule_frequency
        FROM upstox_data_collection_schedules
        WHERE record_status = 'S'
          AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
          AND is_active = TRUE
          AND (
              last_run_date IS NULL
              OR CAST(last_run_date AS VARCHAR) <> ?
          )
          AND (
              next_run_at <= ?
              OR (
                  next_run_at IS NULL
                  AND schedule_time <= ?
              )
          )
        ORDER BY schedule_time;
    """, list(SCHEDULABLE_JOB_TYPES) + [today, current_run_at, current_time]).fetchall()


def mark_schedule_started(
    conn,
    schedule_id: str,
    schedule_time: str,
    schedule_frequency: str,
    run_date: str
):
    run_at = get_ist_now()

    conn.execute(f"""
        UPDATE upstox_data_collection_schedules
        SET
            last_run_date = ?,
            last_run_at = CURRENT_TIMESTAMP,
            next_run_at = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = 'system_scheduler'
        WHERE schedule_id = ?
          AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
          AND record_status = 'S';
    """, [
        run_date,
        calculate_next_run_at_after_run(
            schedule_time=schedule_time,
            schedule_frequency=schedule_frequency,
            run_at=run_at,
            is_active=True
        ),
        schedule_id
    ] + list(SCHEDULABLE_JOB_TYPES))

    conn.commit()


def update_schedule_next_run(
    conn,
    schedule_id: str,
    schedule_time: str,
    schedule_frequency: str,
    is_active: bool
):
    conn.execute(f"""
        UPDATE upstox_data_collection_schedules
        SET
            next_run_at = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = 'system_scheduler'
        WHERE schedule_id = ?
          AND job_type IN ({SCHEDULABLE_JOB_TYPE_SQL})
          AND record_status = 'S';
    """, [
        calculate_next_run_at(schedule_time, is_active, schedule_frequency),
        schedule_id
    ] + list(SCHEDULABLE_JOB_TYPES))

    conn.commit()


def run_schedule_job(schedule_id: str, job_type: str):
    system_user = get_system_scheduler_user()

    print(f"Data collection schedule triggered: {schedule_id} ({job_type})")

    if job_type == "current_instruments":
        return sync_upstox_current_instruments_service(
            current_user=system_user,
            clear_cancel_at_start=True
        )

    if job_type == "expired_instruments":
        return sync_upstox_expired_instruments_service(
            current_user=system_user,
            config={},
            clear_cancel_at_start=True
        )

    if job_type == "ohlcv_daily":
        return sync_upstox_ohlcv_daily_service(
            current_user=system_user,
            config=None,
            clear_cancel_at_start=True
        )

    if job_type == "company_fundamentals":
        return sync_upstox_company_fundamentals_service(
            current_user=system_user,
            config=None,
            clear_cancel_at_start=True
        )

    if job_type == "market_holidays":
        return sync_upstox_market_holidays_service(
            current_user=system_user,
            clear_cancel_at_start=True
        )

    if job_type == "equity_news":
        return sync_upstox_equity_news_service(
            current_user=system_user,
            config={},
            clear_cancel_at_start=True
        )

    if job_type == "ipo_calendar":
        return sync_upstox_ipo_calendar_service(
            current_user=system_user,
            config={},
            clear_cancel_at_start=True
        )
    
    if job_type == "ipo_scraper":
        return sync_ipo_gmp_scraper_service(
            current_user=system_user,
            config={},
            clear_cancel_at_start=True
        )

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported scheduled job type."
    )


def execute_due_schedules_once():
    if not _scheduler_lock.acquire(blocking=False):
        return

    conn = get_connection()

    try:
        rows = get_due_schedules(conn)

        if not rows:
            return

        today = get_ist_now().date().isoformat()

        for row in rows:
            schedule_id = row[0]
            job_type = row[1]
            schedule_time = row[2]
            last_run_date = str(row[3]) if row[3] else None
            is_active = bool(row[4])
            schedule_frequency = normalize_schedule_frequency(row[6])

            if not is_active:
                continue

            if last_run_date == today:
                continue

            try:
                mark_schedule_started(
                    conn=conn,
                    schedule_id=schedule_id,
                    schedule_time=schedule_time,
                    schedule_frequency=schedule_frequency,
                    run_date=today
                )

                enqueue_data_collection_job(
                    run_schedule_job,
                    job_name=f"scheduled:{job_type}",
                    kwargs={
                        "schedule_id": schedule_id,
                        "job_type": job_type
                    },
                    priority=DATA_COLLECTION_SCHEDULED_PRIORITY
                )

            except HTTPException as error:
                print(
                    "Scheduled data collection failed: "
                    f"{schedule_id} ({job_type}) - {error.detail}"
                )

                try:
                    update_schedule_next_run(
                        conn=conn,
                        schedule_id=schedule_id,
                        schedule_time=schedule_time,
                        schedule_frequency=schedule_frequency,
                        is_active=True
                    )
                except Exception as update_error:
                    print(f"Unable to update schedule next run: {update_error}")

            except Exception as error:
                print(
                    "Scheduled data collection failed: "
                    f"{schedule_id} ({job_type}) - {error}"
                )

                try:
                    update_schedule_next_run(
                        conn=conn,
                        schedule_id=schedule_id,
                        schedule_time=schedule_time,
                        schedule_frequency=schedule_frequency,
                        is_active=True
                    )
                except Exception as update_error:
                    print(f"Unable to update schedule next run: {update_error}")

    finally:
        conn.close()
        _scheduler_lock.release()



def scheduler_loop():
    print("Data collection scheduler started.")

    while not _scheduler_stop_event.is_set():
        try:
            execute_due_schedules_once()
        except Exception as error:
            print(f"Data collection scheduler tick failed: {error}")

        _scheduler_stop_event.wait(SCHEDULER_INTERVAL_SECONDS)

    print("Data collection scheduler stopped.")


def start_data_collection_scheduler():
    global _scheduler_thread

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _scheduler_stop_event.clear()

    _scheduler_thread = threading.Thread(
        target=scheduler_loop,
        name="open-analytics-data-collection-scheduler",
        daemon=True
    )

    _scheduler_thread.start()


def stop_data_collection_scheduler():
    global _scheduler_thread

    _scheduler_stop_event.set()

    if _scheduler_thread and _scheduler_thread.is_alive():
        _scheduler_thread.join(timeout=5)

    _scheduler_thread = None
