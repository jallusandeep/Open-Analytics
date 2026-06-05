from typing import Any, Optional


class UserRepository:
    PROFILE_COLUMNS = """
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        role,
        access_restrictions,
        is_active,
        created_at
    """

    AUTH_COLUMNS = """
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        password_hash,
        role,
        is_active
    """

    ADMIN_LIST_COLUMNS = """
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        role,
        CAST(access_restrictions AS VARCHAR),
        is_active,
        created_at,
        updated_at
    """

    @staticmethod
    def normalize_mobile_number(value: str | None) -> str | None:
        if not value:
            return None

        clean_value = "".join(char for char in str(value).strip() if char.isdigit())
        return clean_value or None

    def get_profile_by_id(self, conn, user_id: str):
        return conn.execute(
            f"""
            SELECT {self.PROFILE_COLUMNS}
            FROM users
            WHERE user_id = ?
            """,
            [user_id],
        ).fetchone()

    def find_by_login_identifier(self, conn, login_identifier: str):
        clean_identifier = login_identifier.strip()
        clean_identifier_lower = clean_identifier.lower()
        clean_identifier_mobile = self.normalize_mobile_number(clean_identifier)

        return conn.execute(
            f"""
            SELECT {self.AUTH_COLUMNS}
            FROM users
            WHERE COALESCE(record_status, 'S') != 'D'
              AND (
                LOWER(COALESCE(login_id, '')) = ?
                OR LOWER(COALESCE(email, '')) = ?
                OR COALESCE(mobile_number, '') = ?
                OR REPLACE(REPLACE(REPLACE(REPLACE(COALESCE(mobile_number, ''), ' ', ''), '-', ''), '+', ''), '(', '') = ?
              )
            """,
            [
                clean_identifier_lower,
                clean_identifier_lower,
                clean_identifier,
                clean_identifier_mobile or clean_identifier,
            ],
        ).fetchone()

    def login_id_exists(self, conn, login_id: str) -> bool:
        row = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE login_id = ?
            """,
            [login_id],
        ).fetchone()
        return bool(row)

    def find_by_email(self, conn, email: str):
        return conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE LOWER(email) = ?
            """,
            [email.strip().lower()],
        ).fetchone()

    def find_by_email_excluding_user(self, conn, email: str, user_id: str):
        return conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE LOWER(email) = ? AND user_id != ?
            """,
            [email.strip().lower(), user_id],
        ).fetchone()

    def find_by_mobile_excluding_user(self, conn, mobile_number: str, user_id: str):
        return conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE mobile_number = ? AND user_id != ?
            """,
            [mobile_number, user_id],
        ).fetchone()

    def get_active_status(self, conn, user_id: str):
        return conn.execute(
            """
            SELECT user_id, is_active
            FROM users
            WHERE user_id = ?
            """,
            [user_id],
        ).fetchone()

    def get_password_hash_and_active(self, conn, user_id: str):
        return conn.execute(
            """
            SELECT password_hash, is_active
            FROM users
            WHERE user_id = ?
            """,
            [user_id],
        ).fetchone()

    def create_user(
        self,
        conn,
        user_id: str,
        login_id: str,
        full_name: str,
        email: str,
        mobile_number: Optional[str],
        password_hash: str,
        role: str,
        access_restrictions: Optional[str],
        is_active: bool = True,
    ):
        conn.execute(
            """
            INSERT INTO users (
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                password_hash,
                role,
                access_restrictions,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                user_id,
                login_id,
                full_name,
                email,
                mobile_number,
                password_hash,
                role,
                access_restrictions,
                is_active,
            ],
        )

    def update_profile(
        self,
        conn,
        user_id: str,
        full_name: str,
        email: str,
        mobile_number: Optional[str],
    ):
        conn.execute(
            """
            UPDATE users
            SET
                full_name = ?,
                email = ?,
                mobile_number = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE user_id = ?
            """,
            [full_name, email, mobile_number, user_id, user_id],
        )

    def update_password(self, conn, user_id: str, password_hash: str):
        conn.execute(
            """
            UPDATE users
            SET
                password_hash = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE user_id = ?
            """,
            [password_hash, user_id, user_id],
        )

    def find_target_user(self, conn, user_id: str):
        return conn.execute(
            """
            SELECT user_id, role
            FROM users
            WHERE user_id = ?
              AND COALESCE(record_status, 'S') != 'D'
            """,
            [user_id],
        ).fetchone()

    def find_duplicate_for_update(
        self,
        conn,
        email: str,
        login_id: str,
        mobile_number: Optional[str],
        user_id: str,
    ):
        return conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE (
                LOWER(email) = ?
                OR login_id = ?
                OR (
                    ? IS NOT NULL
                    AND mobile_number = ?
                )
            )
            AND user_id != ?
            """,
            [email, login_id, mobile_number, mobile_number, user_id],
        ).fetchone()

    def find_duplicate_for_create(
        self,
        conn,
        email: str,
        mobile_number: Optional[str],
    ):
        return conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE LOWER(email) = ?
               OR (
                    ? IS NOT NULL
                    AND mobile_number = ?
               )
            """,
            [email, mobile_number, mobile_number],
        ).fetchone()

    def update_user_admin(
        self,
        conn,
        user_id: str,
        login_id: str,
        full_name: str,
        email: str,
        mobile_number: Optional[str],
        role: str,
        access_restrictions: Optional[str],
        is_active: bool,
    ):
        conn.execute(
            """
            UPDATE users
            SET
                login_id = ?,
                full_name = ?,
                email = ?,
                mobile_number = ?,
                role = ?,
                access_restrictions = ?,
                is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            [
                login_id,
                full_name,
                email,
                mobile_number,
                role,
                access_restrictions,
                is_active,
                user_id,
            ],
        )

    def get_admin_user_row(self, conn, user_id: str):
        return conn.execute(
            f"""
            SELECT {self.ADMIN_LIST_COLUMNS}
            FROM users
            WHERE user_id = ?
            """,
            [user_id],
        ).fetchone()

    def soft_delete(self, conn, user_id: str):
        conn.execute(
            """
            UPDATE users
            SET
                is_active = FALSE,
                record_status = 'D',
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            [user_id],
        )

    def count_users(self, conn, where_clause: str, params: list) -> int:
        return conn.execute(
            f"SELECT COUNT(*) FROM users {where_clause}",
            params,
        ).fetchone()[0]

    def list_users(
        self,
        conn,
        where_clause: str,
        params: list,
        page_size: int,
        offset: int,
    ):
        return conn.execute(
            f"""
            SELECT {self.ADMIN_LIST_COLUMNS}
            FROM users
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ?
            OFFSET ?
            """,
            params + [page_size, offset],
        ).fetchall()

    @staticmethod
    def build_list_filters(
        search: str,
        role: str,
        is_active: Any,
    ) -> tuple[list[str], list]:
        filters = ["COALESCE(record_status, 'S') != 'D'"]
        params: list = []

        if search:
            search_value = f"%{search.lower()}%"
            filters.append("""
                (
                    lower(coalesce(login_id, '')) LIKE ?
                    OR lower(coalesce(email, '')) LIKE ?
                    OR lower(coalesce(full_name, '')) LIKE ?
                    OR lower(coalesce(mobile_number, '')) LIKE ?
                    OR lower(coalesce(role, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 5)

        if role and role != "all":
            filters.append("role = ?")
            params.append(role)

        if is_active is not None:
            filters.append("is_active = ?")
            params.append(is_active)

        where_clause = "WHERE " + " AND ".join(filters)
        return where_clause, params
