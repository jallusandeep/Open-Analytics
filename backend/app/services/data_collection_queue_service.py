import queue
import threading
import time
import traceback
from typing import Any, Callable, Dict, Optional

from app.database import get_connection
from app.services.data_collection_service import mark_stale_sync_runs


DATA_COLLECTION_JOB_QUEUE_WAIT_SECONDS = 5

_job_queue = queue.Queue()
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
        item = _job_queue.get()

        try:
            wait_for_data_collection_slot()
            item["target"](**item["kwargs"])
        except Exception as error:
            print(
                "Queued data collection job failed: "
                f"{item.get('job_name') or item['target'].__name__} - {error}"
            )
            traceback.print_exc()
        finally:
            _job_queue.task_done()


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
    with _job_queue.mutex:
        jobs = [
            item.get("job_name") or item["target"].__name__
            for item in list(_job_queue.queue)
        ]

    return {
        "count": len(jobs),
        "jobs": jobs
    }


def enqueue_data_collection_job(
    target: Callable[..., Any],
    *,
    job_name: Optional[str] = None,
    kwargs: Optional[Dict[str, Any]] = None
) -> int:
    ensure_data_collection_queue_worker_started()

    active_job_offset = 1 if has_active_data_collection_job() else 0
    queue_size_before = _job_queue.qsize()

    _job_queue.put({
        "target": target,
        "job_name": job_name or target.__name__,
        "kwargs": kwargs or {}
    })

    return active_job_offset + queue_size_before + 1
