from .common import *  # noqa: F401,F403
from .upstox_api import *  # noqa: F401,F403


def format_upstox_access_token_request_response(response: dict) -> str:
    if not isinstance(response, dict):
        return "Upstox access token approval request triggered."

    status_text = safe_strip(response.get("status"))
    data = response.get("data") if isinstance(response.get("data"), dict) else {}
    authorization_expiry = safe_strip(data.get("authorization_expiry"))
    notifier_url = safe_strip(data.get("notifier_url"))

    message_parts = []

    if status_text:
        message_parts.append(f"status={status_text}")

    if authorization_expiry:
        expiry_date = parse_upstox_epoch_millis(authorization_expiry)
        expiry_label = (
            expiry_date.strftime("%d %b %Y, %I:%M %p IST")
            if expiry_date
            else authorization_expiry
        )
        message_parts.append(f"authorization_expiry={expiry_label}")

    if notifier_url:
        message_parts.append(f"notifier_url={notifier_url}")

    if not message_parts:
        return "Upstox access token approval request triggered."

    return "Upstox access token approval request triggered: " + "; ".join(message_parts)


def get_upstox_error_message(error) -> str:
    detail = getattr(error, "detail", None)

    if isinstance(detail, dict):
        message = safe_strip(detail.get("message"))
        error_code = safe_strip(detail.get("error_code"))

        if error_code and message:
            return f"{error_code}: {message}"

        if message:
            return message

        return str(detail)

    if detail:
        return str(detail)

    return str(error)


def format_upstox_access_token_request_error(message: str) -> str:
    clean_message = safe_strip(message)

    if "invalid notifier url" in clean_message.lower():
        return (
            f"{clean_message}. Configure the Upstox app's Notifier Webhook "
            "Endpoint to the production backend URL: "
            f"{get_upstox_notifier_webhook_url()}"
        )

    return clean_message


def record_upstox_access_token_request_result(
    conn,
    status_text: str,
    message: str,
    response: dict | None = None
):
    now_time = get_ist_now()
    clean_status = safe_strip(status_text) or "unknown"
    clean_message = safe_strip(message)

    set_app_metadata_value(
        conn,
        "upstox_access_token_request_last_attempted_at",
        now_time.strftime("%Y-%m-%d %H:%M:%S")
    )
    set_app_metadata_value(
        conn,
        "upstox_access_token_request_last_status",
        clean_status
    )

    if clean_message:
        set_app_metadata_value(
            conn,
            "upstox_access_token_request_last_message",
            clean_message[:1000]
        )

    if clean_status == "success":
        set_app_metadata_value(
            conn,
            "upstox_access_token_request_last_triggered_at",
            now_time.strftime("%Y-%m-%d %H:%M:%S")
        )

        if isinstance(response, dict):
            data = response.get("data") if isinstance(response.get("data"), dict) else {}
            notifier_url = safe_strip(data.get("notifier_url"))
            authorization_expiry = safe_strip(data.get("authorization_expiry"))

            if notifier_url:
                set_app_metadata_value(
                    conn,
                    "upstox_access_token_request_notifier_url",
                    notifier_url
                )

            if authorization_expiry:
                set_app_metadata_value(
                    conn,
                    "upstox_access_token_request_authorization_expiry",
                    authorization_expiry
                )


def trigger_upstox_access_token_request(conn, client_id: str, client_secret: str):
    try:
        response = upstox_access_token_request_post(
            client_id=client_id,
            client_secret=client_secret
        )
        message = format_upstox_access_token_request_response(response)
        record_upstox_access_token_request_result(
            conn=conn,
            status_text="success",
            message=message,
            response=response
        )
        return {
            "status": "success",
            "message": message,
            "response": response
        }

    except Exception as error:
        message = get_upstox_error_message(error)
        record_upstox_access_token_request_result(
            conn=conn,
            status_text="failed",
            message=message
        )
        raise


def request_upstox_access_token_service(current_user):
    conn = get_connection()

    try:
        existing = get_upstox_connection_raw(conn)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox connection is not configured."
            )

        api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])

        if not api_key or not api_secret:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox API key and API secret are required."
            )

        try:
            result = trigger_upstox_access_token_request(
                conn=conn,
                client_id=api_key,
                client_secret=api_secret
            )
            conn.commit()

            return {
                "status": "success",
                "message": result.get("message") or "Upstox access token approval request triggered."
            }

        except HTTPException as error:
            detail = error.detail

            if isinstance(detail, dict):
                message = detail.get("message") or str(detail)
            else:
                message = str(detail)

            conn.commit()

            raise HTTPException(
                status_code=error.status_code,
                detail=format_upstox_access_token_request_error(message)
            )

        except Exception as error:
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=format_upstox_access_token_request_error(str(error))
            )

    finally:
        conn.close()


def record_upstox_notifier_webhook_event(
    conn,
    status_text: str,
    message: str,
    client_id: str = "",
    has_access_token: bool = False,
    message_type: str = "",
    expires_at: str = "",
    issued_at: str = ""
):
    now_time = get_ist_now().strftime("%Y-%m-%d %H:%M:%S")

    set_app_metadata_value(conn, "upstox_notifier_webhook_last_received_at", now_time)
    set_app_metadata_value(conn, "upstox_notifier_webhook_last_status", safe_strip(status_text) or "unknown")
    set_app_metadata_value(conn, "upstox_notifier_webhook_last_message", safe_strip(message)[:1000])
    set_app_metadata_value(conn, "upstox_notifier_webhook_last_client_id", mask_identifier(client_id))
    set_app_metadata_value(conn, "upstox_notifier_webhook_last_has_access_token", "true" if has_access_token else "false")

    if message_type:
        set_app_metadata_value(conn, "upstox_notifier_webhook_last_message_type", safe_strip(message_type))

    if expires_at:
        set_app_metadata_value(conn, "upstox_notifier_webhook_last_expires_at", safe_strip(expires_at))

    if issued_at:
        set_app_metadata_value(conn, "upstox_notifier_webhook_last_issued_at", safe_strip(issued_at))


def handle_upstox_notifier_webhook_service(request):
    client_id = safe_strip(getattr(request, "client_id", None))
    access_token = normalize_upstox_token(getattr(request, "access_token", None))
    token_type = safe_strip(getattr(request, "token_type", None)) or "Bearer"
    message_type = safe_strip(getattr(request, "message_type", None))
    expires_at = safe_strip(getattr(request, "expires_at", None))
    issued_at = safe_strip(getattr(request, "issued_at", None))

    conn = get_connection()

    try:
        record_upstox_notifier_webhook_event(
            conn=conn,
            status_text="received",
            message="Upstox notifier webhook received.",
            client_id=client_id,
            has_access_token=bool(access_token),
            message_type=message_type,
            expires_at=expires_at,
            issued_at=issued_at
        )

        if message_type and message_type != "access_token":
            record_upstox_notifier_webhook_event(
                conn=conn,
                status_text="failed",
                message="Invalid Upstox notifier message type.",
                client_id=client_id,
                has_access_token=bool(access_token),
                message_type=message_type,
                expires_at=expires_at,
                issued_at=issued_at
            )
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid Upstox notifier message type."
            )

        if not client_id:
            record_upstox_notifier_webhook_event(
                conn=conn,
                status_text="failed",
                message="Upstox notifier client_id is required.",
                has_access_token=bool(access_token),
                message_type=message_type,
                expires_at=expires_at,
                issued_at=issued_at
            )
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox notifier client_id is required."
            )

        if not access_token:
            record_upstox_notifier_webhook_event(
                conn=conn,
                status_text="failed",
                message="Upstox notifier access_token is required.",
                client_id=client_id,
                has_access_token=False,
                message_type=message_type,
                expires_at=expires_at,
                issued_at=issued_at
            )
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox notifier access_token is required."
            )

        existing = get_upstox_connection_raw(conn)

        if not existing:
            record_upstox_notifier_webhook_event(
                conn=conn,
                status_text="failed",
                message="Upstox connection is not configured.",
                client_id=client_id,
                has_access_token=bool(access_token),
                message_type=message_type,
                expires_at=expires_at,
                issued_at=issued_at
            )
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Upstox connection is not configured."
            )

        connection_id = existing[0]
        saved_api_key = safe_strip(existing[2])
        api_secret = safe_strip(existing[3])
        redirect_url = safe_strip(existing[4])
        analytical_token = normalize_upstox_token(existing[5])

        if saved_api_key and saved_api_key != client_id:
            record_upstox_notifier_webhook_event(
                conn=conn,
                status_text="failed",
                message="Upstox notifier client_id does not match saved API key.",
                client_id=client_id,
                has_access_token=bool(access_token),
                message_type=message_type,
                expires_at=expires_at,
                issued_at=issued_at
            )
            conn.commit()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Upstox notifier client_id does not match saved API key."
            )

        expiry_date = parse_upstox_epoch_millis(expires_at)

        if not expiry_date:
            expiry_date = get_next_upstox_access_token_expiry(get_ist_now())

        issued_date = parse_upstox_epoch_millis(issued_at)
        token_updated_at = issued_date or get_ist_now()

        next_status = get_upstox_save_status(
            api_key=saved_api_key,
            api_secret=api_secret,
            redirect_url=redirect_url,
            analytical_token=analytical_token,
            access_token=access_token
        )

        conn.execute("""
            UPDATE external_connections
            SET
                access_token = ?,
                token_type = ?,
                access_token_expires_at = ?,
                token_updated_at = ?,
                connection_status = ?,
                record_status = 'S',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = 'upstox_notifier'
            WHERE connection_id = ?;
        """, [
            access_token,
            token_type,
            expiry_date.strftime("%Y-%m-%d %H:%M:%S"),
            token_updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            next_status,
            connection_id
        ])

        clear_upstox_expiry_notification_marker(conn)
        record_upstox_notifier_webhook_event(
            conn=conn,
            status_text="success",
            message="Upstox access token received from notifier and saved successfully.",
            client_id=client_id,
            has_access_token=True,
            message_type=message_type,
            expires_at=expires_at,
            issued_at=issued_at
        )

        try:
            bot_token = get_telegram_bot_token(conn)
            chat_ids = get_admin_super_admin_telegram_chat_ids(conn)
            notify_message = build_upstox_token_saved_from_webhook_message(
                expiry_date=expiry_date
            )

            for chat_id in chat_ids:
                try:
                    send_telegram_message(
                        bot_token=bot_token,
                        chat_id=chat_id,
                        message=notify_message
                    )
                except Exception as error:
                    print(f"Unable to send Upstox token saved Telegram alert: {error}")

        except Exception as notify_error:
            print(f"Unable to notify Telegram after Upstox webhook save: {notify_error}")

        conn.commit()

        return {
            "status": "success",
            "message": "Upstox access token received from notifier and saved successfully."
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to process Upstox notifier webhook: {e}"
        )

    finally:
        conn.close()


def ensure_app_metadata_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS app_metadata (
            key VARCHAR PRIMARY KEY,
            value VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)


def get_app_metadata_value(conn, key: str):
    ensure_app_metadata_table(conn)

    row = conn.execute("""
        SELECT value
        FROM app_metadata
        WHERE key = ?
        LIMIT 1;
    """, [key]).fetchone()

    return row[0] if row else None


def set_app_metadata_value(conn, key: str, value: str):
    ensure_app_metadata_table(conn)

    existing = conn.execute("""
        SELECT key
        FROM app_metadata
        WHERE key = ?
        LIMIT 1;
    """, [key]).fetchone()

    if existing:
        conn.execute("""
            UPDATE app_metadata
            SET value = ?, updated_at = CURRENT_TIMESTAMP
            WHERE key = ?;
        """, [value, key])
        return

    conn.execute("""
        INSERT INTO app_metadata (key, value, updated_at)
        VALUES (?, ?, CURRENT_TIMESTAMP);
    """, [key, value])


def is_upstox_reminder_window(now_time: datetime) -> bool:
    return (
        now_time.hour >= UPSTOX_REMINDER_START_HOUR
        and now_time.hour < UPSTOX_REMINDER_END_HOUR
    )


def should_send_upstox_reminder(conn, now_time: datetime) -> bool:
    last_sent_at = parse_db_datetime(
        get_app_metadata_value(
            conn,
            "upstox_access_token_reminder_last_sent_at"
        )
    )

    if not last_sent_at:
        return True

    return now_time - last_sent_at >= timedelta(
        minutes=UPSTOX_REMINDER_REPEAT_MINUTES
    )


def should_trigger_upstox_access_token_request(conn, now_time: datetime) -> bool:
    last_triggered_at = parse_db_datetime(
        get_app_metadata_value(
            conn,
            "upstox_access_token_request_last_triggered_at"
        )
    )

    if not last_triggered_at:
        return True

    return now_time - last_triggered_at >= timedelta(
        minutes=UPSTOX_REMINDER_REPEAT_MINUTES
    )


def build_upstox_access_token_approval_reminder_message(
    reason: str,
    previous_status: str,
    current_status: str,
    request_triggered: bool,
    request_message: str = ""
) -> str:
    approval_text = (
        "A semi-automated Upstox access token request has been triggered. "
        "Please approve it in the Upstox app/web before the request expires."
        if request_triggered
        else
        "Backend could not trigger the semi-automated Upstox access token request. "
        "Please open Open Analytics > Connections and generate the Upstox access token."
    )

    return (
        "🔔 Upstox access token approval required\n\n"
        f"Reason: {reason}\n"
        f"Previous status: {previous_status or '--'}\n"
        f"Current status: {current_status or '--'}\n\n"
        f"{approval_text}\n\n"
        f"Details: {request_message or '--'}"
    )


def maybe_request_upstox_access_token_and_send_reminder(
    conn,
    reason: str,
    previous_status: str,
    current_status: str
):
    now_time = get_ist_now()

    if not is_upstox_reminder_window(now_time):
        return {
            "status": "skipped",
            "message": "Outside Upstox reminder window."
        }

    existing = get_upstox_connection_raw(conn)

    if not existing:
        return {
            "status": "skipped",
            "message": "Upstox connection is not configured."
        }

    api_key = safe_strip(existing[2])
    api_secret = safe_strip(existing[3])

    if not api_key or not api_secret:
        return {
            "status": "skipped",
            "message": "Upstox API key and API secret are required."
        }

    request_triggered = False
    request_message = ""

    if should_trigger_upstox_access_token_request(conn, now_time):
        try:
            request_result = trigger_upstox_access_token_request(
                conn=conn,
                client_id=api_key,
                client_secret=api_secret
            )
            request_triggered = True
            request_message = request_result.get("message") or ""

        except Exception as error:
            request_message = format_upstox_access_token_request_error(
                get_upstox_error_message(error)
            )
            print(f"Unable to trigger Upstox access token request: {request_message}")

    if not should_send_upstox_reminder(conn, now_time):
        conn.commit()

        return {
            "status": "skipped",
            "message": "Upstox reminder was already sent recently."
        }

    try:
        bot_token = get_telegram_bot_token(conn)
        chat_ids = get_admin_super_admin_telegram_chat_ids(conn)

        reminder_message = build_upstox_access_token_approval_reminder_message(
            reason=reason,
            previous_status=previous_status,
            current_status=current_status,
            request_triggered=request_triggered,
            request_message=request_message
        )

        for chat_id in chat_ids:
            try:
                send_telegram_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=reminder_message
                )
            except Exception as error:
                print(f"Unable to send Upstox approval reminder Telegram alert: {error}")

        set_app_metadata_value(
            conn,
            "upstox_access_token_reminder_last_sent_at",
            now_time.strftime("%Y-%m-%d %H:%M:%S")
        )

        conn.commit()

        return {
            "status": "success",
            "message": (
                "Upstox token request triggered and Telegram reminder sent."
                if request_triggered
                else "Telegram reminder sent."
            )
        }

    except Exception as error:
        print(f"Unable to send Upstox access token reminder: {error}")

        try:
            conn.commit()
        except Exception:
            pass

        return {
            "status": "failed",
            "message": str(error)
        }


def clear_upstox_expiry_notification_marker(conn):
    ensure_app_metadata_table(conn)

    conn.execute("""
        DELETE FROM app_metadata
        WHERE key IN (
            'upstox_analytics_token_expiry_notified_date',
            'upstox_analytics_token_expiry_notified_expiry',
            'upstox_analytical_token_reminder_last_sent_at',
            'upstox_access_token_reminder_last_sent_at',
            'upstox_access_token_request_last_triggered_at',
            'upstox_access_token_request_last_attempted_at',
            'upstox_access_token_request_last_status',
            'upstox_access_token_request_last_message',
            'upstox_access_token_request_notifier_url',
            'upstox_access_token_request_authorization_expiry'
        );
    """)
