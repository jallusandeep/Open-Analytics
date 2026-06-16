import threading

from fastapi import APIRouter, Depends, Query

from app.dependencies import require_admin_or_super_admin
from app.services.data_collection_service import (
    get_data_collection_runs_service,
    get_data_collection_summary_service,
    get_ipo_gmp_scraper_preview_service,
    get_upstox_company_fundamentals_options_service,
    get_upstox_company_fundamentals_preview_service,
    get_upstox_equity_news_preview_service,
    get_upstox_expired_instruments_preview_service,
    get_upstox_instruments_preview_service,
    get_upstox_ipo_calendar_preview_service,
    get_upstox_market_holidays_preview_service,
    get_upstox_ohlcv_options_service,
    get_upstox_ohlcv_preview_service,
    request_cancel_active_sync_runs_service,
    save_upstox_ohlcv_options_service,
    sync_ipo_gmp_scraper_service,
    sync_upstox_company_fundamentals_service,
    sync_upstox_current_instruments_service,
    sync_upstox_equity_news_service,
    sync_upstox_expired_instruments_service,
    sync_upstox_ipo_calendar_service,
    sync_upstox_market_holidays_service,
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
PREVIEW_PAGE_SIZE_DEFAULT = 500


def start_detached_collection_job(target, **kwargs):
    def run_job():
        try:
            target(**kwargs)
        except Exception as error:
            import traceback

            print(f"Detached data collection job failed: {error}")
            traceback.print_exc()

    worker = threading.Thread(target=run_job, daemon=True)
    worker.start()


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
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
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
        description="Search expired instrument key, symbol, name, segment, exchange, type, or underlying."
    ),
    source_type: str = Query("all", description="Filter by source type."),
    segment: str = Query("all", description="Filter by segment."),
    instrument_type: str = Query("all", description="Filter by instrument type."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
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


@router.get("/upstox/market-holidays")
def get_upstox_market_holidays_preview(
    search: str = Query(
        "",
        description="Search holiday date, description, holiday type, or exchange."
    ),
    holiday_type: str = Query("all", description="Filter by holiday type."),
    exchange: str = Query("all", description="Filter by exchange."),
    trading_status: str = Query("all", description="Filter by open or closed trading status."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_market_holidays_preview_service(
            search=search,
            holiday_type=holiday_type,
            exchange=exchange,
            trading_status=trading_status,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/calendar/preview")
def get_upstox_calendar_preview(
    search: str = Query(
        "",
        description="Search holiday date, description, holiday type, or exchange."
    ),
    holiday_type: str = Query("all", description="Filter by holiday type."),
    exchange: str = Query("all", description="Filter by exchange."),
    trading_status: str = Query("all", description="Filter by open or closed trading status."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_market_holidays_preview_service(
            search=search,
            holiday_type=holiday_type,
            exchange=exchange,
            trading_status=trading_status,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/equity-news/preview")
def get_upstox_equity_news_preview(
    search: str = Query(
        "",
        description="Search instrument key, symbol, company name, headline, summary, source, or article link."
    ),
    segment: str = Query("all", description="Filter by segment."),
    source: str = Query("all", description="Filter by news source."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_equity_news_preview_service(
            search=search,
            segment=segment,
            source=source,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/news/preview")
def get_upstox_news_preview_legacy(
    search: str = Query(
        "",
        description="Search instrument key, symbol, company name, headline, summary, source, or article link."
    ),
    segment: str = Query("all", description="Filter by segment."),
    source: str = Query("all", description="Filter by news source."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_equity_news_preview_service(
            search=search,
            segment=segment,
            source=source,
            page=page,
            page_size=page_size
        )
    }


@router.post("/upstox/equity-news/run")
def sync_upstox_equity_news(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_equity_news_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "Equity News collection started. Monitor will update while it runs."
    }


@router.post("/upstox/news/run")
def sync_upstox_news_legacy(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_equity_news_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "Equity News collection started. Monitor will update while it runs."
    }


@router.get("/upstox/ipo-calendar/preview")
def get_upstox_ipo_calendar_preview(
    search: str = Query(
        "",
        description="Search IPO id, symbol, name, ISIN, status, issue type, industry, or registrar."
    ),
    ipo_status: str = Query("all", description="Filter by IPO status."),
    issue_type: str = Query("all", description="Filter by issue type."),
    industry: str = Query("all", description="Accepted from frontend; industry filtering is handled by search/service when available."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ipo_calendar_preview_service(
            search=search,
            ipo_status=ipo_status,
            issue_type=issue_type,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/ipos/preview")
def get_upstox_ipos_preview_legacy(
    search: str = Query(
        "",
        description="Search IPO id, symbol, name, ISIN, status, issue type, industry, or registrar."
    ),
    ipo_status: str = Query("all", description="Filter by IPO status."),
    issue_type: str = Query("all", description="Filter by issue type."),
    industry: str = Query("all", description="Accepted from frontend; industry filtering is handled by search/service when available."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ipo_calendar_preview_service(
            search=search,
            ipo_status=ipo_status,
            issue_type=issue_type,
            page=page,
            page_size=page_size
        )
    }


@router.post("/upstox/ipo-calendar/run")
def sync_upstox_ipo_calendar(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_ipo_calendar_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "IPO Calendar collection started. Monitor will update while it runs."
    }


@router.post("/upstox/ipos/run")
def sync_upstox_ipos_legacy(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_ipo_calendar_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "IPO Calendar collection started. Monitor will update while it runs."
    }


@router.get("/upstox/ipo-scraper/preview")
def get_ipo_gmp_scraper_preview(
    search: str = Query(
        "",
        description="Search IPO name, GMP, price band, date, type, status, or last updated."
    ),
    ipo_status: str = Query("all", description="Filter by IPO scraper status."),
    ipo_type: str = Query("all", description="Filter by IPO scraper type."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_ipo_gmp_scraper_preview_service(
            search=search,
            ipo_status=ipo_status,
            ipo_type=ipo_type,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/ipo-gmp-scraper/preview")
def get_ipo_gmp_scraper_preview_legacy(
    search: str = Query(
        "",
        description="Search IPO name, GMP, price band, date, type, status, or last updated."
    ),
    ipo_status: str = Query("all", description="Filter by IPO scraper status."),
    ipo_type: str = Query("all", description="Filter by IPO scraper type."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_ipo_gmp_scraper_preview_service(
            search=search,
            ipo_status=ipo_status,
            ipo_type=ipo_type,
            page=page,
            page_size=page_size
        )
    }


@router.post("/upstox/ipo-scraper/run")
def sync_ipo_gmp_scraper(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_ipo_gmp_scraper_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "IPO Scrapper collection started. Monitor will update while it runs."
    }


@router.post("/upstox/ipo-gmp-scraper/run")
def sync_ipo_gmp_scraper_legacy(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_ipo_gmp_scraper_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "IPO Scrapper collection started. Monitor will update while it runs."
    }


@router.get("/upstox/ohlcv-preview")
def get_upstox_ohlcv_preview_legacy(
    search: str = Query(
        "",
        description="Search instrument key, symbol, source, mode, interval, exchange, or segment."
    ),
    source: str = Query("all", description="Filter by OHLCV source."),
    mode: str = Query("all", description="Filter by OHLCV mode."),
    interval: str = Query("all", description="Filter by OHLCV interval."),
    segment: str = Query("all", description="Filter by segment."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ohlcv_preview_service(
            search=search,
            source=source,
            mode=mode,
            interval=interval,
            segment=segment,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/ohlcv/preview")
def get_upstox_ohlcv_preview(
    search: str = Query(
        "",
        description="Search instrument key, symbol, source, mode, interval, exchange, or segment."
    ),
    source: str = Query("all", description="Filter by OHLCV source."),
    mode: str = Query("all", description="Filter by OHLCV mode."),
    interval: str = Query("all", description="Filter by OHLCV interval."),
    segment: str = Query("all", description="Filter by segment."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ohlcv_preview_service(
            search=search,
            source=source,
            mode=mode,
            interval=interval,
            segment=segment,
            page=page,
            page_size=page_size
        )
    }


@router.get("/upstox/ohlcv-options")
def get_upstox_ohlcv_options_legacy(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ohlcv_options_service()
    }


@router.get("/upstox/ohlcv/options")
def get_upstox_ohlcv_options(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_ohlcv_options_service()
    }


@router.put("/upstox/ohlcv-options")
def save_upstox_ohlcv_options_legacy(
    payload: dict,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return save_upstox_ohlcv_options_service(payload, current_user)


@router.post("/upstox/ohlcv/options")
def save_upstox_ohlcv_options(
    payload: dict,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return save_upstox_ohlcv_options_service(payload, current_user)


@router.put("/upstox/ohlcv/options")
def update_upstox_ohlcv_options(
    payload: dict,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return save_upstox_ohlcv_options_service(payload, current_user)


@router.get("/upstox/company-fundamentals/options")
def get_upstox_company_fundamentals_options(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_company_fundamentals_options_service()
    }


@router.get("/upstox/company-fundamentals/preview")
def get_upstox_company_fundamentals_preview(
    search: str = Query(
        "",
        description="Search ISIN, symbol, company name, endpoint, sector, action type, or particular."
    ),
    endpoint: str = Query("all", description="Filter by Company Fundamentals endpoint/tab."),
    statement_type: str = Query("all", description="Filter by statement type."),
    time_period: str = Query("all", description="Filter by yearly or quarterly."),
    segment: str = Query("all", description="Filter by segment."),
    page: int = Query(1, ge=1),
    page_size: int = Query(PREVIEW_PAGE_SIZE_DEFAULT, ge=10, le=2000),
    current_user: dict = Depends(require_admin_or_super_admin)
):
    return {
        "status": "success",
        "data": get_upstox_company_fundamentals_preview_service(
            search=search,
            endpoint=endpoint,
            statement_type=statement_type,
            time_period=time_period,
            segment=segment,
            page=page,
            page_size=page_size
        )
    }


@router.post("/upstox/company-fundamentals/run")
def sync_upstox_company_fundamentals(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_company_fundamentals_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "Company Fundamentals collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-company-fundamentals")
def sync_upstox_company_fundamentals_legacy(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_company_fundamentals_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "Company Fundamentals collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-current")
def sync_upstox_current_instruments(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_current_instruments_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Current Instruments collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-expired")
def sync_upstox_expired_instruments(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_expired_instruments_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "Expired Instruments collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-market-holidays")
def sync_upstox_market_holidays_legacy(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_market_holidays_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Market Holidays calendar collection started. Monitor will update while it runs."
    }


@router.post("/upstox/market-holidays/run")
def sync_upstox_market_holidays(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_market_holidays_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Market Holidays calendar collection started. Monitor will update while it runs."
    }


@router.post("/upstox/calendar/run")
def sync_upstox_calendar(
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_market_holidays_service,
        current_user=current_user
    )

    return {
        "status": "started",
        "message": "Market Holidays calendar collection started. Monitor will update while it runs."
    }


@router.post("/upstox/sync-ohlcv")
def sync_upstox_ohlcv_daily_legacy(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_ohlcv_daily_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "OHLCV collection started using selected options. Monitor will update while it runs."
    }


@router.post("/upstox/ohlcv/run")
def sync_upstox_ohlcv_daily(
    payload: dict | None = None,
    current_user: dict = Depends(require_admin_or_super_admin)
):
    start_detached_collection_job(
        sync_upstox_ohlcv_daily_service,
        current_user=current_user,
        config=payload or {}
    )

    return {
        "status": "started",
        "message": "OHLCV collection started using selected options. Monitor will update while it runs."
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
