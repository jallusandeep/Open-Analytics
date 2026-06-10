class AppMetadataRepository:
    def ensure_table(self, conn):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS app_metadata (
                key VARCHAR PRIMARY KEY,
                value VARCHAR,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

    def get_value(self, conn, key: str):
        self.ensure_table(conn)

        row = conn.execute("""
            SELECT value
            FROM app_metadata
            WHERE key = ?
            LIMIT 1;
        """, [key]).fetchone()

        return row[0] if row else None

    def set_value(self, conn, key: str, value: str):
        self.ensure_table(conn)

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

    def clear_upstox_expiry_notification_markers(self, conn):
        self.ensure_table(conn)

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

    def list_all(self, conn):
        return conn.execute("""
            SELECT key, value, updated_at
            FROM app_metadata
            ORDER BY key;
        """).fetchall()
