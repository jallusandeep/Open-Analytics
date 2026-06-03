from fastapi import APIRouter, BackgroundTasks, Depends, Query

from app.dependencies import require_admin_or_super_admin
from app.services.data_collection_service import (
    get_corporate_actions_preview_service,
    get_data_collection_runs_service,
    get_data_collection_summary_service,
    get_equity_news_preview_service,
    get_fii_dii_activity_preview_service,
    get_fundamentals_preview_service,
    get_ohlcv_daily_preview_service,
    get_upstox_equity_instruments_preview_service,
    get_upstox_expired_instruments_preview_service,
    get_upstox_instruments_preview_service,
    request_cancel_active_sync_runs_service,
    sync_upstox_all_instruments_service,
    sync_upstox_corporate_actions_service,
    sync_upstox_current_instruments_service,
    sync_upstox_equity_instruments_service,
    sync_upstox_equity_news_service,
    sync_upstox_expired_instruments_service,
    sync_upstox_fii_dii_activity_service,
    sync_upstox_fundamentals_service,
    sync_upstox_ohlcv_daily_service
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


@router.get("/upstox/expired-instruments")
def get_upstox_expired_instruments_preview(
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
        "data": get_upstox_expired_instruments_preview_service(
            search=search,
            source_type=source_type,
            segment=segment,
            instrument_type=instrument_type,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/equity-instruments")
def get_upstox_equity_instruments_preview(
    search: str = Query(
        "",
        description="Search equity instrument key, symbol, name, ISIN, segment, exchange, or security type."
    ),
    security_type: str = Query("all", description="Filter by security type."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_equity_instruments_preview_service(
            search=search,
            security_type=security_type,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/ohlcv-daily")
def get_upstox_ohlcv_daily_preview(
    search: str = Query(
        "",
        description="Search OHLCV by instrument key or trading symbol."
    ),
    from_date: str = Query("", description="Filter OHLCV from date YYYY-MM-DD."),
    to_date: str = Query("", description="Filter OHLCV to date YYYY-MM-DD."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_ohlcv_daily_preview_service(
            search=search,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/equity-news")
def get_upstox_equity_news_preview(
    search: str = Query(
        "",
        description="Search news by instrument key, symbol, title, summary, source, or URL."
    ),
    source: str = Query("all", description="Filter by news source."),
    from_date: str = Query("", description="Filter news from date YYYY-MM-DD."),
    to_date: str = Query("", description="Filter news to date YYYY-MM-DD."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_equity_news_preview_service(
            search=search,
            source=source,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/fundamentals")
def get_upstox_fundamentals_preview(
    search: str = Query(
        "",
        description="Search fundamentals by instrument key, ISIN, symbol, or period."
    ),
    period_type: str = Query("all", description="Filter by period type."),
    from_date: str = Query("", description="Filter fundamentals from report date YYYY-MM-DD."),
    to_date: str = Query("", description="Filter fundamentals to report date YYYY-MM-DD."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_fundamentals_preview_service(
            search=search,
            period_type=period_type,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/corporate-actions")
def get_upstox_corporate_actions_preview(
    search: str = Query(
        "",
        description="Search corporate actions by instrument key, ISIN, symbol, action, or remarks."
    ),
    action_type: str = Query("all", description="Filter by action type."),
    from_date: str = Query("", description="Filter corporate actions from ex-date YYYY-MM-DD."),
    to_date: str = Query("", description="Filter corporate actions to ex-date YYYY-MM-DD."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_corporate_actions_preview_service(
            search=search,
            action_type=action_type,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/fii-dii-activity")
def get_upstox_fii_dii_activity_preview(
    category: str = Query("all", description="Filter by FII or DII."),
    from_date: str = Query("", description="Filter activity from date YYYY-MM-DD."),
    to_date: str = Query("", description="Filter activity to date YYYY-MM-DD."),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=200),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_fii_dii_activity_preview_service(
            category=category,
            from_date=from_date,
            to_date=to_date,
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


@router.post("/upstox/sync-all")
def sync_upstox_all_instruments(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_all_instruments_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "All configured Upstox data collection jobs started. Monitor will update while they run."
    }


@router.post("/upstox/cancel")
def cancel_upstox_data_collection(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return request_cancel_active_sync_runs_service()


@router.post("/upstox/sync-expired-default")
def sync_upstox_expired_instruments(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_expired_instruments_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Expired Instruments collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-equity")
def sync_upstox_equity_instruments(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_equity_instruments_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Equity Instruments collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-ohlcv-daily")
def sync_upstox_ohlcv_daily(
    background_tasks: BackgroundTasks,
    target_date: str = Query(
        "",
        description="Optional target date in YYYY-MM-DD format. Defaults to today."
    ),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_ohlcv_daily_service,
        current_user=current_user,
        target_date=target_date or None
    )

    return {
        "status": "started",
        "message": "Equity OHLCV collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-equity-news")
def sync_upstox_equity_news(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_equity_news_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Equity News collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-fundamentals")
def sync_upstox_fundamentals(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_fundamentals_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Fundamentals collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-corporate-actions")
def sync_upstox_corporate_actions(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_corporate_actions_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Corporate Actions collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-fii-dii-activity")
def sync_upstox_fii_dii_activity(
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    background_tasks.add_task(
        sync_upstox_fii_dii_activity_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "FII/DII Activity collection started. Monitor will update while it runs."
    }


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