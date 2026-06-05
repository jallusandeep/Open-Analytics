SCHEDULE_COLUMNS = """
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
"""

JOB_TYPES_FILTER = "('current_instruments', 'expired_instruments')"


class ScheduleRepository:
    def list_active(self, conn):
        return conn.execute(f"""
            SELECT {SCHEDULE_COLUMNS}
            FROM upstox_data_collection_schedules
            WHERE record_status = 'S'
              AND job_type IN {JOB_TYPES_FILTER}
            ORDER BY job_type, schedule_time;
        """).fetchall()

    def find_duplicate(self, conn, job_type: str, schedule_time: str, exclude_id: str | None = None):
        if exclude_id:
            return conn.execute("""
                SELECT schedule_id
                FROM upstox_data_collection_schedules
                WHERE job_type = ?
                  AND schedule_time = ?
                  AND schedule_id <> ?
                  AND record_status = 'S'
                LIMIT 1;
            """, [job_type, schedule_time, exclude_id]).fetchone()

        return conn.execute("""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE job_type = ?
              AND schedule_time = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [job_type, schedule_time]).fetchone()

    def get_by_id(self, conn, schedule_id: str):
        return conn.execute(f"""
            SELECT schedule_id
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id]).fetchone()

    def get_toggle_state(self, conn, schedule_id: str):
        return conn.execute(f"""
            SELECT schedule_time, is_active
            FROM upstox_data_collection_schedules
            WHERE schedule_id = ?
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S'
            LIMIT 1;
        """, [schedule_id]).fetchone()

    def insert(
        self,
        conn,
        schedule_id: str,
        job_type: str,
        schedule_time: str,
        schedule_label: str,
        time_format: str,
        timezone: str,
        is_active: bool,
        next_run_at,
        user_id: str,
    ):
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
            timezone,
            is_active,
            next_run_at,
            user_id,
            user_id,
        ])

    def update(
        self,
        conn,
        schedule_id: str,
        job_type: str,
        schedule_time: str,
        schedule_label: str,
        time_format: str,
        timezone: str,
        is_active: bool,
        next_run_at,
        user_id: str,
    ):
        conn.execute(f"""
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
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S';
        """, [
            job_type,
            schedule_time,
            schedule_label,
            time_format,
            timezone,
            is_active,
            next_run_at,
            user_id,
            schedule_id,
        ])

    def toggle(self, conn, schedule_id: str, is_active: bool, next_run_at, user_id: str):
        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                is_active = ?,
                next_run_at = ?,
                version_no = version_no + 1,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE schedule_id = ?
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S';
        """, [is_active, next_run_at, user_id, schedule_id])

    def soft_delete(self, conn, schedule_id: str, user_id: str):
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
              AND job_type IN {JOB_TYPES_FILTER};
        """, [user_id, schedule_id])

    def get_due_schedules(self, conn, today: str, current_run_at, current_time: str):
        return conn.execute(f"""
            SELECT
                schedule_id,
                job_type,
                schedule_time,
                last_run_date,
                is_active,
                next_run_at
            FROM upstox_data_collection_schedules
            WHERE record_status = 'S'
              AND job_type IN {JOB_TYPES_FILTER}
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

    def mark_started(self, conn, schedule_id: str, run_date: str, next_run_at):
        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                last_run_date = ?,
                last_run_at = CURRENT_TIMESTAMP,
                next_run_at = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = 'system_scheduler'
            WHERE schedule_id = ?
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S';
        """, [run_date, next_run_at, schedule_id])

    def update_next_run(self, conn, schedule_id: str, next_run_at):
        conn.execute(f"""
            UPDATE upstox_data_collection_schedules
            SET
                next_run_at = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = 'system_scheduler'
            WHERE schedule_id = ?
              AND job_type IN {JOB_TYPES_FILTER}
              AND record_status = 'S';
        """, [next_run_at, schedule_id])
