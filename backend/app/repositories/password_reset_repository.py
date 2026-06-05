class PasswordResetRepository:
    def invalidate_unused_tokens(self, conn, user_id: str):
        conn.execute(
            """
            UPDATE password_reset_tokens
            SET is_used = TRUE
            WHERE user_id = ?
              AND is_used = FALSE
            """,
            [user_id],
        )

    def create_token(
        self,
        conn,
        reset_id: str,
        user_id: str,
        otp: str,
        expires_at,
    ):
        conn.execute(
            """
            INSERT INTO password_reset_tokens (
                reset_id,
                user_id,
                reset_token,
                is_used,
                expires_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            [reset_id, user_id, otp, False, expires_at],
        )

    def find_valid_token(self, conn, user_id: str, otp: str):
        return conn.execute(
            """
            SELECT reset_id
            FROM password_reset_tokens
            WHERE user_id = ?
              AND reset_token = ?
              AND is_used = FALSE
              AND expires_at >= CURRENT_TIMESTAMP
            ORDER BY created_at DESC
            LIMIT 1
            """,
            [user_id, otp],
        ).fetchone()

    def mark_used(self, conn, reset_id: str):
        conn.execute(
            """
            UPDATE password_reset_tokens
            SET is_used = TRUE
            WHERE reset_id = ?
            """,
            [reset_id],
        )
