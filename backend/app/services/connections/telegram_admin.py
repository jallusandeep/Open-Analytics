from .common import *  # noqa: F401,F403


def save_telegram_connection_service(request, current_user):
    bot_token = safe_strip(getattr(request, "bot_token", None))

    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is required."
        )

    bot_data = validate_telegram_bot_token(bot_token)
    clear_telegram_webhook(bot_token)
    bot_username = safe_strip(bot_data.get("username"))
    bot_label = bot_username or bot_data.get("first_name") or "Telegram bot"

    conn = get_connection()

    try:
        existing = get_telegram_connection_raw(conn)

        if existing:
            connection_id = existing[0]

            conn.execute("""
                UPDATE external_connections
                SET
                    api_key = ?,
                    api_secret = NULL,
                    redirect_url = ?,
                    analytical_token = NULL,
                    access_token = ?,
                    connection_status = 'connected',
                    record_status = 'S',
                    last_tested_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE connection_id = ?;
            """, [
                bot_token,
                bot_username,
                bot_token,
                current_user["user_id"],
                connection_id
            ])

        else:
            connection_id = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO external_connections (
                    connection_id,
                    provider,
                    api_key,
                    api_secret,
                    redirect_url,
                    analytical_token,
                    access_token,
                    connection_status,
                    record_status,
                    version_no,
                    last_tested_at,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
            """, [
                connection_id,
                TELEGRAM_PROVIDER,
                bot_token,
                None,
                bot_username,
                None,
                bot_token,
                "connected",
                "S",
                1,
                current_user["user_id"],
                current_user["user_id"]
            ])

        conn.commit()

        return {
            "status": "success",
            "message": (
                f"Telegram bot verified and saved successfully for {bot_label}. "
                "Users must link Telegram in their profile before notifications can be delivered."
            )
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
            detail=f"Unable to save Telegram connection: {e}"
        )

    finally:
        conn.close()


def test_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_info = get_telegram_bot_info(conn)
        clear_telegram_webhook(bot_info["bot_token"])

        return {
            "status": "connected",
            "message": (
                f"Telegram bot token verified successfully for @{bot_info['bot_username']}. "
                "This verifies the global bot only; each user must link Telegram to receive notifications."
            )
        }

    finally:
        conn.close()


def disconnect_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        existing = get_telegram_connection_raw(conn)

        if not existing or existing[8] == "disconnected":
            return {
                "status": "success",
                "message": "Telegram connection is already disconnected."
            }

        connection_id = existing[0]

        conn.execute("""
            UPDATE external_connections
            SET
                record_status = 'D',
                connection_status = 'disconnected',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [current_user["user_id"], connection_id])

        conn.commit()

        return {
            "status": "success",
            "message": "Telegram disconnected successfully."
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to disconnect Telegram: {e}"
        )

    finally:
        conn.close()
