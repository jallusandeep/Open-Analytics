USER_TELEGRAM_COLUMNS = """
    telegram_connection_id,
    user_id,
    telegram_chat_id,
    telegram_username,
    telegram_first_name,
    telegram_last_name,
    link_token,
    connection_status,
    updated_at
"""


class UserTelegramRepository:
    def get_by_user_id(self, conn, user_id: str):
        return conn.execute(f"""
            SELECT {USER_TELEGRAM_COLUMNS}
            FROM user_telegram_connections
            WHERE user_id = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [user_id]).fetchone()

    def reset_pending_link(
        self,
        conn,
        telegram_connection_id: str,
        link_token: str,
        user_id: str,
    ):
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
        """, [link_token, user_id, telegram_connection_id])

    def insert_pending(
        self,
        conn,
        telegram_connection_id: str,
        user_id: str,
        link_token: str,
    ):
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
            user_id,
        ])

    def connect_user(
        self,
        conn,
        telegram_connection_id: str,
        telegram_chat_id: str,
        telegram_username,
        telegram_first_name,
        telegram_last_name,
        user_id: str,
    ):
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
            telegram_chat_id,
            telegram_username,
            telegram_first_name,
            telegram_last_name,
            user_id,
            telegram_connection_id,
        ])
