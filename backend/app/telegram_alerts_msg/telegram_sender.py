import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import HTTPException, status

from app.database import get_connection


TELEGRAM_BASE_URL = "https://api.telegram.org"
TELEGRAM_PROVIDER = "telegram"
REQUEST_TIMEOUT_SECONDS = 30


def safe_strip(value):
    return value.strip() if isinstance(value, str) else ""


def get_telegram_connection_raw(conn):
    return conn.execute("""
        SELECT
            connection_id,
            provider,
            api_key,
            api_secret,
            redirect_url,
            analytical_token,
            access_token,
            access_token_expires_at,
            connection_status,
            last_tested_at,
            created_at,
            updated_at
        FROM external_connections
        WHERE provider = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [TELEGRAM_PROVIDER]).fetchone()


def telegram_api_request(bot_token: str, method_name: str, payload=None, query_params=None):
    clean_bot_token = safe_strip(bot_token)

    if not clean_bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is required."
        )

    query_string = ""

    if query_params:
        query_string = "?" + urllib.parse.urlencode(query_params)

    url = f"{TELEGRAM_BASE_URL}/bot{clean_bot_token}/{method_name}{query_string}"
    data = None
    headers = {
        "Accept": "application/json",
        "User-Agent": "OpenAnalytics/1.0"
    }

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        method="POST" if payload is not None else "GET",
        headers=headers
    )

    try:
        with urllib.request.urlopen(
            request,
            timeout=REQUEST_TIMEOUT_SECONDS
        ) as response:
            content = response.read().decode("utf-8")

            if not content:
                return {}

            result = json.loads(content)

            if not result.get("ok", False):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=result.get("description") or "Telegram API request failed."
                )

            return result

    except urllib.error.HTTPError as error:
        error_body = error.read().decode("utf-8", errors="ignore")

        try:
            payload = json.loads(error_body)
            message = payload.get("description") or str(payload)
        except Exception:
            message = error_body or str(error)

        raise HTTPException(
            status_code=error.code,
            detail=f"Telegram API error: {message}"
        )

    except urllib.error.URLError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to reach Telegram API: {error}"
        )

    except json.JSONDecodeError:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Invalid JSON response received from Telegram API."
        )


def validate_telegram_bot_token(bot_token: str):
    bot_response = telegram_api_request(
        bot_token=bot_token,
        method_name="getMe"
    )

    bot_data = bot_response.get("result") or {}

    if not bot_data.get("id"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token could not be verified."
        )

    return bot_data


def get_telegram_bot_token(conn):
    existing = get_telegram_connection_raw(conn)

    if not existing or existing[8] == "disconnected":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Telegram bot is not configured by admin."
        )

    bot_token = safe_strip(existing[6] or existing[2])

    if not bot_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot token is missing."
        )

    return bot_token


def get_telegram_bot_info(conn):
    bot_token = get_telegram_bot_token(conn)
    bot_data = validate_telegram_bot_token(bot_token)

    bot_username = safe_strip(bot_data.get("username"))
    bot_name = safe_strip(bot_data.get("first_name")) or "Telegram bot"

    if not bot_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Telegram bot username is missing. Please check the bot in BotFather."
        )

    return {
        "bot_token": bot_token,
        "bot_username": bot_username,
        "bot_name": bot_name
    }


def clear_telegram_webhook(bot_token: str):
    telegram_api_request(
        bot_token=bot_token,
        method_name="deleteWebhook",
        query_params={
            "drop_pending_updates": "false"
        }
    )


def get_telegram_updates(bot_token: str):
    return telegram_api_request(
        bot_token=bot_token,
        method_name="getUpdates",
        query_params={
            "limit": 100,
            "timeout": 2,
            "allowed_updates": json.dumps([
                "message",
                "edited_message",
                "channel_post",
                "edited_channel_post"
            ])
        }
    )


def send_telegram_message(bot_token: str, chat_id: str, message: str):
    return telegram_api_request(
        bot_token=bot_token,
        method_name="sendMessage",
        payload={
            "chat_id": chat_id,
            "text": message
        }
    )


def get_admin_super_admin_telegram_chat_ids(conn):
    rows = conn.execute("""
        SELECT DISTINCT utc.telegram_chat_id
        FROM user_telegram_connections utc
        INNER JOIN users u
            ON u.user_id = utc.user_id
        WHERE utc.record_status = 'S'
          AND utc.connection_status = 'connected'
          AND utc.telegram_chat_id IS NOT NULL
          AND TRIM(utc.telegram_chat_id) <> ''
          AND u.record_status = 'S'
          AND u.is_active = TRUE
          AND u.role IN ('admin', 'super_admin');
    """).fetchall()

    return [row[0] for row in rows if row and row[0]]


def get_user_telegram_connection_raw(conn, user_id: str):
    return conn.execute("""
        SELECT
            telegram_connection_id,
            user_id,
            telegram_chat_id,
            telegram_username,
            telegram_first_name,
            telegram_last_name,
            link_token,
            connection_status,
            updated_at
        FROM user_telegram_connections
        WHERE user_id = ?
          AND record_status = 'S'
        LIMIT 1;
    """, [user_id]).fetchone()


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


def send_admin_super_admin_telegram_alert(message: str) -> int:
    conn = get_connection()

    try:
        bot_token = get_telegram_bot_token(conn)
        chat_ids = get_admin_super_admin_telegram_chat_ids(conn)

        sent_count = 0

        for chat_id in chat_ids:
            try:
                send_telegram_message(
                    bot_token=bot_token,
                    chat_id=chat_id,
                    message=message
                )
                sent_count += 1
            except Exception as error:
                print(f"Unable to send admin/super admin Telegram alert: {error}")

        return sent_count

    except HTTPException as error:
        if error.status_code in (
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND
        ):
            return 0

        raise

    finally:
        conn.close()