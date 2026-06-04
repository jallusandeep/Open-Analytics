from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.dependencies import require_admin_or_super_admin
from app.services.data_collection_service import (
    get_data_collection_runs_service,
    get_data_collection_summary_service,
    get_upstox_instruments_preview_service,
    request_cancel_active_sync_runs_service,
    sync_upstox_current_instruments_service
)
from app.services.data_collection_scheduler_service import (
    create_data_collection_schedule_service,
    delete_data_collection_schedule_service,
    get_data_collection_schedules_service,
    toggle_data_collection_schedule_service,
    update_data_collection_schedule_service
)


router = APIRouter(prefix="/data-collection", tags=["Data Collection"])


@router.get("/upstox/summary")
def get_upstox_data_collection_summary(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_data_collection_summary_service()
    }


@router.get("/upstox/runs")
def get_upstox_data_collection_runs(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_data_collection_runs_service()
    }


@router.get("/upstox/instruments")
def get_upstox_instruments_preview(
    search: str = Query(
        "",
        description="Search instrument key, symbol, name, segment, exchange, type, or underlying."
    ),
    source_type: str = Query("all", description="Filter by source type."),
    segment: str = Query("all", description="Filter by segment."),
    instrument_type: str = Query("all", description="Filter by instrument type."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_instruments_preview_service(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type,
            page=page,
            page_size=page_size
        )
    }


@router.post("/upstox/sync-current")
def sync_upstox_current_instruments(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_current_instruments_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Current Instruments collection started. Monitor will update while it runs."
    }


@router.post("/upstox/cancel")
def cancel_upstox_data_collection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return request_cancel_active_sync_runs_service()


@router.get("/upstox/schedules")
def get_upstox_data_collection_schedules(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_data_collection_schedules_service()
    }


@router.post("/upstox/schedules")
def create_upstox_data_collection_schedule(
    payload: dict,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return create_data_collection_schedule_service(payload, current_user)


@router.put("/upstox/schedules/{schedule_id}")
def update_upstox_data_collection_schedule(
    schedule_id: str,
    payload: dict,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return update_data_collection_schedule_service(
        schedule_id=schedule_id,
        payload=payload,
        current_user=current_user
    )


@router.post("/upstox/schedules/{schedule_id}/toggle")
def toggle_upstox_data_collection_schedule(
    schedule_id: str,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return toggle_data_collection_schedule_service(schedule_id, current_user)


@router.delete("/upstox/schedules/{schedule_id}")
def delete_upstox_data_collection_schedule(
    schedule_id: str,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return delete_data_collection_schedule_service(schedule_id, current_user)