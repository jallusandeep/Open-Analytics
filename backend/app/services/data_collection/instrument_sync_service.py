# backend\app\services\data_collection\instrument_sync_service.py
# Split from backend\app\services\data_collection_service.py
# Keep this module imported through app.services.data_collection or the compatibility wrapper.

from .common import *

def sync_upstox_current_instruments_service(
    current_user: dict,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    local_file = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_current_instruments",
            "running",
            "Current instrument dump started.",
            current_user=current_user
        )

        local_file = download_upstox_master_gz_file_once()

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")

        total_records = import_current_instruments_from_local_file(
            conn=conn,
            sync_id=sync_id,
            local_file=local_file
        )

        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Current instruments downloaded and imported successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Current instruments downloaded and imported successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Current instrument dump cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Current instrument dump cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                "Current instrument dump failed.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Current instrument dump failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump current instruments: {error}"
        )

    finally:
        delete_downloaded_master_file(local_file)
        conn.close()


def sync_upstox_expired_instruments_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    expired_download = {
        "records": [],
        "group_statuses": [],
        "skipped_groups": 0
    }
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)

        access_token = get_saved_upstox_access_token(conn)

        sync_id = create_sync_run(
            conn,
            "upstox_expired_instruments",
            "running",
            "Expired instrument SDK download started.",
            current_user=current_user
        )

        expired_download = download_expired_instruments_with_sdk(
            conn=conn,
            sync_id=sync_id,
            access_token=access_token,
            config=config,
            heartbeat_callback=lambda: check_sync_cancelled(conn, sync_id)
        )

        was_cancelled = bool(expired_download.get("cancelled"))

        if not was_cancelled:
            check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")

        total_records = int(expired_download.get("persisted_records") or 0)

        total_records += import_expired_instruments_records(
            conn=conn,
            sync_id=sync_id,
            records=expired_download.get("records", []),
            group_statuses=expired_download.get("group_statuses", []),
            underlying_statuses=expired_download.get("underlying_statuses", []),
            allow_cancelled_import=was_cancelled
        )

        conn.execute("COMMIT")

        if was_cancelled:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Expired instrument SDK download cancelled. Completed records were saved.",
                total_records,
                started_at
            )

            if clear_cancel_at_start:
                clear_cancel_signal()

            return {
                "status": "cancelled",
                "message": "Expired instrument SDK download cancelled. Completed records were saved.",
                "total_records": total_records,
                "duration_seconds": duration_seconds(started_at)
            }

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "Expired instruments downloaded through Upstox SDK and imported successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "Expired instruments downloaded through Upstox SDK and imported successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "Expired instrument SDK download cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "Expired instrument SDK download cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        error_message = error.detail

        if isinstance(error_message, dict):
            error_message = error_message.get("message") or str(error_message)

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Expired instrument SDK download failed: {error_message}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "failed",
            "message": str(error_message),
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"Expired instrument SDK download failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to dump expired instruments through Upstox SDK: {error}"
        )

    finally:
        conn.close()
