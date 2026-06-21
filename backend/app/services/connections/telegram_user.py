from .common import *  # noqa: F401,F403


def telegram_user_connection_to_response(row):
    if not row:
        return {
            "status": "success",
            "message": "Telegram is not connected.",
            "connection_status": "not_connected",
            "telegram_username": None,
            "telegram_first_name": None,
            "telegram_last_name": None,
            "updated_at": None
        }

    (
        telegram_connection_id,
        user_id,
        telegram_chat_id,
        telegram_username,
        telegram_first_name,
        telegram_last_name,
        link_token,
        connection_status,
        updated_at
    ) = row

    return {
        "status": "success",
        "message": "Telegram connection status loaded.",
        "connection_status": connection_status or "pending",
        "telegram_username": telegram_username,
        "telegram_first_name": telegram_first_name,
        "telegram_last_name": telegram_last_name,
        "updated_at": str(updated_at) if updated_at else None
    }


def get_my_telegram_connection_status_service(current_user):
    conn = get_connection()

    try:
        row = get_user_telegram_connection_raw(conn, current_user["user_id"])
        return telegram_user_connection_to_response(row)

    finally:
        conn.close()


def start_my_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_info = get_telegram_bot_info(conn)
        user_id = current_user["user_id"]

        existing = get_user_telegram_connection_raw(conn, user_id)

        if existing:
            telegram_connection_id = existing[0]
            link_token = str(uuid.uuid4())

            conn.execute("""
                UPDATE user_telegram_connections
                SET
                    telegram_chat_id = NULL,
                    telegram_username = NULL,
                    telegram_first_name = NULL,
                    telegram_last_name = NULL,
                    link_token = ?,
                    connection_status = 'pending',
                    record_status = 'S',
                    updated_at = CURRENT_TIMESTAMP,
                    updated_by = ?
                WHERE telegram_connection_id = ?;
            """, [
                link_token,
                user_id,
                telegram_connection_id
            ])

        else:
            telegram_connection_id = str(uuid.uuid4())
            link_token = str(uuid.uuid4())

            conn.execute("""
                INSERT INTO user_telegram_connections (
                    telegram_connection_id,
                    user_id,
                    telegram_chat_id,
                    telegram_username,
                    telegram_first_name,
                    telegram_last_name,
                    link_token,
                    connection_status,
                    record_status,
                    version_no,
                    created_by,
                    updated_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, [
                telegram_connection_id,
                user_id,
                None,
                None,
                None,
                None,
                link_token,
                "pending",
                "S",
                1,
                user_id,
                user_id
            ])

        conn.commit()

        telegram_url = f"https://t.me/{bot_info['bot_username']}?start={link_token}"

        return {
            "status": "success",
            "message": "Telegram link generated. Open it, tap Start, then click Verify Telegram.",
            "telegram_url": telegram_url,
            "bot_username": bot_info["bot_username"],
            "connection_status": "pending"
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
            detail=f"Unable to start Telegram connection: {e}"
        )

    finally:
        conn.close()


def get_message_from_telegram_update(update):
    if not isinstance(update, dict):
        return None

    message = (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )

    if isinstance(message, dict):
        return message

    return None


def find_telegram_start_for_token(updates_response, link_token: str):
    updates = updates_response.get("result")

    if not isinstance(updates, list) or not updates:
        return None

    token_text = safe_strip(link_token)

    for update in reversed(updates):
        message = get_message_from_telegram_update(update)

        if not message:
            continue

        text = safe_strip(message.get("text"))

        if not text:
            continue

        if text == f"/start {token_text}" or text.endswith(f" {token_text}"):
            chat = message.get("chat") or {}
            from_user = message.get("from") or {}

            if not isinstance(chat, dict) or chat.get("id") is None:
                continue

            return {
                "telegram_chat_id": str(chat.get("id")),
                "telegram_username": from_user.get("username") or chat.get("username"),
                "telegram_first_name": from_user.get("first_name") or chat.get("first_name"),
                "telegram_last_name": from_user.get("last_name") or chat.get("last_name")
            }

    return None


def verify_my_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        user_id = current_user["user_id"]

        existing = get_user_telegram_connection_raw(conn, user_id)

        if not existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Click Connect Telegram first to generate your Telegram link."
            )

        telegram_connection_id = existing[0]
        link_token = safe_strip(existing[6])

        if not link_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram link token is missing. Click Connect Telegram again."
            )

        updates_response = get_telegram_updates(bot_token)
        matched = find_telegram_start_for_token(updates_response, link_token)

        if not matched:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Telegram start message was not found. Open the generated Telegram link, "
                    "tap Start, then click Verify Telegram again."
                )
            )

        conn.execute("""
            UPDATE user_telegram_connections
            SET
                telegram_chat_id = ?,
                telegram_username = ?,
                telegram_first_name = ?,
                telegram_last_name = ?,
                connection_status = 'connected',
                record_status = 'S',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE telegram_connection_id = ?;
        """, [
            matched["telegram_chat_id"],
            matched["telegram_username"],
            matched["telegram_first_name"],
            matched["telegram_last_name"],
            user_id,
            telegram_connection_id
        ])

        conn.commit()

        send_telegram_message(
            bot_token=bot_token,
            chat_id=matched["telegram_chat_id"],
            message=build_telegram_connected_message()
        )

        row = get_user_telegram_connection_raw(conn, user_id)
        response = telegram_user_connection_to_response(row)
        response["message"] = "Telegram connected successfully."

        return response

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
            detail=f"Unable to verify Telegram connection: {e}"
        )

    finally:
        conn.close()


def test_my_telegram_connection_service(current_user):
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        user_id = current_user["user_id"]

        row = get_user_telegram_connection_raw(conn, user_id)

        if not row:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not connected. Click Connect Telegram first."
            )

        telegram_chat_id = safe_strip(row[2])
        connection_status = safe_strip(row[7])

        if connection_status != "connected" or not telegram_chat_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not verified yet. Click Verify Telegram first."
            )

        send_telegram_message(
            bot_token=bot_token,
            chat_id=telegram_chat_id,
            message=build_telegram_test_message()
        )

        return {
            "status": "success",
            "message": "Telegram test message sent successfully."
        }

    finally:
        conn.close()
