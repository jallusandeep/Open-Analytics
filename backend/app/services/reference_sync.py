"""Queue one reference refresh: current instruments, followed by ISIN profiles."""
import threading
from datetime import datetime
from fastapi import HTTPException

LOCK = threading.Lock()
STATE = {"status": "idle"}
JOB_KEY = 'reference_data_upstox'


def state():
    from app.services.data_collection_queue_service import get_data_collection_queue_summary
    queue = get_data_collection_queue_summary()
    active = queue.get('active_job') or {}
    pending = JOB_KEY in queue.get('jobs', []) or active.get('job_key') == JOB_KEY
    with LOCK:
        return {**STATE, 'pending': pending}


def run_reference_refresh(current_user):
    from app.services.data_collection.instrument_sync_service import sync_upstox_current_instruments_service
    from app.services.data_collection.company_fundamentals_service import sync_upstox_company_fundamentals_service
    from app.services.index_membership_sync import sync_nse_index_memberships
    with LOCK:
        STATE.clear()
        STATE.update(status='running', stage='instruments')
    try:
        instruments = sync_upstox_current_instruments_service(current_user)
        if instruments['status'] != 'success':
            with LOCK:
                STATE.update(status=instruments['status'], message=instruments['message'])
            return
        with LOCK:
            STATE.update(stage='indices', counts=instruments.get('reference_data', {}))
        indices = sync_nse_index_memberships()
        with LOCK:
            STATE.update(stage='profiles', indices=indices)
        try:
            profiles = sync_upstox_company_fundamentals_service(current_user, config={'endpoints': ['company_profile'], 'skip_existing': True, 'force_refresh': False}, clear_cancel_at_start=False)
            with LOCK:
                final_status = 'partial_success' if indices['status'] != 'success' and profiles['status'] == 'success' else profiles['status']
                STATE.update(status=final_status, message=profiles['message'], profiles=profiles['metrics'])
        except HTTPException as error:
            with LOCK:
                STATE.update(status='partial_success', message=f'Instruments synced; profiles unavailable: {error.detail}')
    except Exception:
        with LOCK:
            STATE.update(status='failed', message='Reference sync failed. Check the collection monitor.')
        raise
    finally:
        with LOCK:
            STATE['finished_at'] = datetime.now().isoformat()
