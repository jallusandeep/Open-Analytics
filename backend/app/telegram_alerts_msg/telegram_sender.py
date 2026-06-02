from fastapi import HTTPException, status

from app.database import get_connection
from app.services.connection_service import (
    get_telegram_bot_token,
    get_user_telegram_connection_raw,
    safe_strip,
    send_telegram_message
)


def get_connected_user_telegram_chat_id(conn, user_id: str) -> str | None:
    row = get_user_telegram_connection_raw(conn, user_id)

    if not row:
        return None

    telegram_chat_id = safe_strip(row[2])
    connection_status = safe_strip(row[7])

    if connection_status != "connected" or not telegram_chat_id:
        return None

    return telegram_chat_id


def send_user_telegram_alert(user_id: str, message: str) -> bool:
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        telegram_chat_id = get_connected_user_telegram_chat_id(conn, user_id)

        if not telegram_chat_id:
            return False

        send_telegram_message(
            bot_token=bot_token,
            chat_id=telegram_chat_id,
            message=message
        )

        return True

    except HTTPException as error:
        if error.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ):
            return False

        raise

    finally:
        conn.close()