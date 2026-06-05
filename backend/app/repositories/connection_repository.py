UPSTOX_PROVIDER = "upstox"
TELEGRAM_PROVIDER = "telegram"

CONNECTION_COLUMNS = """
    connection_id,
    provider,
    api_key,
    api_secret,
    redirect_url,
    access_token,
    access_token_expires_at,
    connection_status,
    last_tested_at,
    created_at,
    updated_at
"""


class ConnectionRepository:
    def list_active(self, conn):
        return conn.execute(f"""
            SELECT {CONNECTION_COLUMNS}
            FROM external_connections
            WHERE record_status = 'S'
            ORDER BY provider;
        """).fetchall()

    def get_by_provider(self, conn, provider: str):
        return conn.execute(f"""
            SELECT {CONNECTION_COLUMNS}
            FROM external_connections
            WHERE provider = ?
              AND record_status = 'S'
            LIMIT 1;
        """, [provider]).fetchone()

    def get_upstox(self, conn):
        return self.get_by_provider(conn, UPSTOX_PROVIDER)

    def get_telegram(self, conn):
        return self.get_by_provider(conn, TELEGRAM_PROVIDER)

    def update_upstox_token(
        self,
        conn,
        connection_id: str,
        access_token: str,
        access_token_expires_at: str,
        updated_by: str,
    ):
        conn.execute("""
            UPDATE external_connections
            SET
                api_key = NULL,
                api_secret = NULL,
                redirect_url = NULL,
                access_token = ?,
                access_token_expires_at = ?,
                token_updated_at = CURRENT_TIMESTAMP,
                connection_status = 'connected',
                record_status = 'S',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [
            access_token,
            access_token_expires_at,
            updated_by,
            connection_id,
        ])

    def insert_upstox(
        self,
        conn,
        connection_id: str,
        access_token: str,
        access_token_expires_at: str,
        created_by: str,
    ):
        conn.execute("""
            INSERT INTO external_connections (
                connection_id,
                provider,
                api_key,
                api_secret,
                redirect_url,
                access_token,
                access_token_expires_at,
                token_updated_at,
                connection_status,
                record_status,
                version_no,
                last_tested_at,
                created_by,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
        """, [
            connection_id,
            UPSTOX_PROVIDER,
            None,
            None,
            None,
            access_token,
            access_token_expires_at,
            "connected",
            "S",
            1,
            created_by,
            created_by,
        ])

    def update_test_status(
        self,
        conn,
        connection_id: str,
        connection_status: str,
        updated_by: str,
    ):
        conn.execute("""
            UPDATE external_connections
            SET
                connection_status = ?,
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [connection_status, updated_by, connection_id])

    def disconnect(self, conn, connection_id: str, updated_by: str):
        conn.execute("""
            UPDATE external_connections
            SET
                record_status = 'D',
                connection_status = 'disconnected',
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [updated_by, connection_id])

    def update_telegram(
        self,
        conn,
        connection_id: str,
        bot_token: str,
        bot_username: str,
        updated_by: str,
    ):
        conn.execute("""
            UPDATE external_connections
            SET
                api_key = ?,
                api_secret = NULL,
                redirect_url = ?,
                access_token = ?,
                connection_status = 'connected',
                record_status = 'S',
                last_tested_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE connection_id = ?;
        """, [bot_token, bot_username, bot_token, updated_by, connection_id])

    def insert_telegram(
        self,
        conn,
        connection_id: str,
        bot_token: str,
        bot_username: str,
        created_by: str,
    ):
        conn.execute("""
            INSERT INTO external_connections (
                connection_id,
                provider,
                api_key,
                api_secret,
                redirect_url,
                access_token,
                connection_status,
                record_status,
                version_no,
                last_tested_at,
                created_by,
                updated_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?);
        """, [
            connection_id,
            TELEGRAM_PROVIDER,
            bot_token,
            None,
            bot_username,
            bot_token,
            "connected",
            "S",
            1,
            created_by,
            created_by,
        ])

    def get_admin_super_admin_telegram_chat_ids(self, conn):
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
