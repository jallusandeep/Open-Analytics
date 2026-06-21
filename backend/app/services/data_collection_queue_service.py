import threading
import time
import traceback
from typing import Any, Callable, Dict, Optional

from app.database import get_connection
from app.services.data_collection_service import mark_stale_sync_runs


DATA_COLLECTION_JOB_QUEUE_WAIT_SECONDS = 5
DATA_COLLECTION_MANUAL_PRIORITY = 0
DATA_COLLECTION_SCHEDULED_PRIORITY = 10

_job_queue = []
_job_sequence = 0
_queue_condition = threading.Condition()
_worker_lock = threading.Lock()
_worker_thread: Optional[threading.Thread] = None


def has_active_data_collection_job() -> bool:
    conn = get_connection()

    try:
        mark_stale_sync_runs(conn)

        row = conn.execute("""
            SELECT 1
            FROM upstox_sync_runs
            WHERE status IN ('running', 'cancel_requested')
            LIMIT 1;
        """).fetchone()

        return bool(row)
    finally:
        conn.close()


def wait_for_data_collection_slot():
    while has_active_data_collection_job():
        time.sleep(DATA_COLLECTION_JOB_QUEUE_WAIT_SECONDS)


def data_collection_queue_worker():
    while True:
        item = get_next_data_collection_job()

        try:
            item["target"](**item["kwargs"])
        except Exception as error:
            print(
                "Queued data collection job failed: "
                f"{item.get('job_name') or item['target'].__name__} - {error}"
            )
            traceback.print_exc()


def get_next_data_collection_job() -> Dict[str, Any]:
    while True:
        with _queue_condition:
            while not _job_queue:
                _queue_condition.wait(timeout=DATA_COLLECTION_JOB_QUEUE_WAIT_SECONDS)

        wait_for_data_collection_slot()

        with _queue_condition:
            if not _job_queue:
                continue

            next_index = min(
                range(len(_job_queue)),
                key=lambda index: (
                    _job_queue[index]["priority"],
                    _job_queue[index]["sequence"]
                )
            )
            return _job_queue.pop(next_index)


def ensure_data_collection_queue_worker_started():
    global _worker_thread

    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return

        _worker_thread = threading.Thread(
            target=data_collection_queue_worker,
            daemon=True
        )
        _worker_thread.start()


def get_data_collection_queue_summary() -> Dict[str, Any]:
    with _queue_condition:
        jobs = [
            item.get("job_name") or item["target"].__name__
            for item in sorted(
                _job_queue,
                key=lambda item: (item["priority"], item["sequence"])
            )
        ]

    return {
        "count": len(jobs),
        "jobs": jobs
    }


def enqueue_data_collection_job(
    target: Callable[..., Any],
    *,
    job_name: Optional[str] = None,
    kwargs: Optional[Dict[str, Any]] = None,
    priority: int = DATA_COLLECTION_MANUAL_PRIORITY
) -> int:
    global _job_sequence

    ensure_data_collection_queue_worker_started()

    active_job_offset = 1 if has_active_data_collection_job() else 0
    normalized_priority = int(priority)

    with _queue_condition:
        queue_position = (
            active_job_offset
            + sum(1 for item in _job_queue if item["priority"] <= normalized_priority)
            + 1
        )

        _job_queue.append({
            "target": target,
            "job_name": job_name or target.__name__,
            "kwargs": kwargs or {},
            "priority": normalized_priority,
            "sequence": _job_sequence
        })
        _job_sequence += 1
        _queue_condition.notify()

    return queue_position
