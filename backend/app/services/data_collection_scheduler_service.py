import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import HTTPException, status

from app.database import get_connection
from app.services.connection_service import (
    notify_admin_super_admins_upstox_token_expiry_service
)
from app.services.data_collection_service import (
    sync_upstox_current_instruments_service,
    sync_upstox_expired_instruments_service
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
    }
}

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
            detail="Invalid job type. Use current_instruments or expired_instruments."
        )

    return clean_job_type


def normalize_time_format(time_format: str) -> str:
    clean_time_format = str(time_format or "24").strip()

    if clean_time_format not in ("12", "24"):
        return "24"

    return clean_time_format


def calculate_next_run_at(
    schedule_time: str,
    is_active: bool = True
) -> Optional[datetime]:
    if not is_active:
        return None

    hour, minute = parse_schedule_time(schedule_time)
    now = get_ist_now()
    next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

    if next_run <= now:
        next_run += timedelta(days=1)

    return next_run.replace(tzinfo=None)


def calculate_next_run_at_after_today(
    schedule_time: str,
    is_active: bool = True
) -> Optional[datetime]:
    if not is_active:
        return None

    hour, minute = parse_schedule_time(schedule_time)
    now = get_ist_now()
    next_run = (now + timedelta(days=1)).replace(
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
        "timezone": row[5],
        "is_active": bool(row[6]),
        "last_run_date": str(row[7]) if row[7] else None,
        "last_run_at": str(row[8]) if row[8] else None,
        "next_run_at": str(row[9]) if row[9] else None,
        "created_at": str(row[10]) if row[10] else None,
        "updated_at": str(row[11]) if row[11] else None,
        "updated_by": row[12]
    }


def get_data_collection_schedules_service():
    conn = get_connection()

    try:
        rows = conn.execute("""
            SELECT
                schedule_id,
                job_type,
                schedule_time,
                schedule_label,
                time_format,
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
              AND job_type IN ('current_instruments', 'expired_instruments')
            ORDER BY job_type, schedule_time;
        """).fetchall()

        return [row_to_schedule(row) for row in rows]

    finally:
        conn.close()


def create_data_collection_schedule_service(payload: dict, current_user: dict):
    job_type = validate_job_type(payload.get("job_type"))
    schedule_time = normalize_schedule_time(payload.get("schedule_time"))
    schedule_label = format_schedule_label(schedule_time)
    time_format = normalize_time_format(payload.get("time_format"))
    is_active = bool(payload.get("is_active", True))
    schedule_id = str(__import__("uuid").uuid4())
    user_id = get_user_id(current_user)
    next_run_at = calculate_next_run_at(schedule_time, is_active)

    conn = get_connection()

    try:
        existing = conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE job_type = ?
              AND schedule_time = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [job_type, schedule_time]).fetchone()

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
            VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, 'S', 1, ?, ?);
        """, [
            schedule_id,
            job_type,
            schedule_time,
            schedule_label,
            time_format,
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
    is_active = bool(payload.get("is_active", True))
    user_id = get_user_id(current_user)
    next_run_at = calculate_next_run_at(schedule_time, is_active)

    conn = get_connection()

    try:
        current = conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments')
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id]).fetchone()

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
              AND schedule_id <> ?
              AND record_status = 'S'
            LIMIT 1;
        """, [job_type, schedule_time, schedule_id]).fetchone()

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This schedule already exists for the selected job."
            )

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET
                job_type = ?,
                schedule_time = ?,
                schedule_label = ?,
                time_format = ?,
                timezone = ?,
                is_active = ?,
                next_run_at = ?,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments')
              AND record_status = 'S';
        """, [
            job_type,
            schedule_time,
            schedule_label,
            time_format,
            IST_TIMEZONE,
            is_active,
            next_run_at,
            user_id,
            schedule_id
        ])

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
        row = conn.execute("""
            SELECT schedule_time, is_active
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments')
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id]).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found."
            )

        schedule_time = row[0]
        next_is_active = not bool(row[1])
        next_run_at = calculate_next_run_at(schedule_time, next_is_active)

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET
                is_active = ?,
                next_run_at = ?,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments')
              AND record_status = 'S';
        """, [
            next_is_active,
            next_run_at,
            user_id,
            schedule_id
        ])

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
        row = conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments')
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id]).fetchone()

        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found."
            )

        conn.execute("""
            UPDATE upstox_data_collection_schedules
            SET
                record_status = 'D',
                is_active = FALSE,
                next_run_at = NULL,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN ('current_instruments', 'expired_instruments');
        """, [user_id, schedule_id])

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

    return conn.execute("""
        SELECT
            schedule_id,
            job_type,
            schedule_time,
            last_run_date,
            is_active,
            next_run_at
        FROM upstox_data_collection_schedules
        WHERE record_status = 'S'
          AND job_type IN ('current_instruments', 'expired_instruments')
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
    """, [today, current_run_at, current_time]).fetchall()


def mark_schedule_started(
    conn,
    schedule_id: str,
    schedule_time: str,
    run_date: str
):
    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET
            last_run_date = ?,
            last_run_at = CURRENT_TIMESTAMP,
            next_run_at = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = 'system_scheduler'
        WHERE schedule_id = ?
          AND job_type IN ('current_instruments', 'expired_instruments')
          AND record_status = 'S';
    """, [
        run_date,
        calculate_next_run_at_after_today(schedule_time, True),
        schedule_id
    ])

    conn.commit()


def update_schedule_next_run(
    conn,
    schedule_id: str,
    schedule_time: str,
    is_active: bool
):
    conn.execute("""
        UPDATE upstox_data_collection_schedules
        SET
            next_run_at = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = 'system_scheduler'
        WHERE schedule_id = ?
          AND job_type IN ('current_instruments', 'expired_instruments')
          AND record_status = 'S';
    """, [
        calculate_next_run_at(schedule_time, is_active),
        schedule_id
    ])

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

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsupported scheduled job type."
    )


def run_upstox_access_token_reminder_check():
    try:
        notify_admin_super_admins_upstox_token_expiry_service()
    except Exception as error:
        print(f"Upstox access token reminder check failed: {error}")


def execute_due_schedules_once():
    if not _scheduler_lock.acquire(blocking=False):
        return

    conn = get_connection()

    try:
        run_upstox_access_token_reminder_check()

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

            if not is_active:
                continue

            if last_run_date == today:
                continue

            try:
                mark_schedule_started(
                    conn=conn,
                    schedule_id=schedule_id,
                    schedule_time=schedule_time,
                    run_date=today
                )

                run_schedule_job(
                    schedule_id=schedule_id,
                    job_type=job_type
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