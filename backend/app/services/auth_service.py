import random
import string
import uuid

from fastapi import HTTPException, status

from app.database import get_connection
from app.security import hash_password, verify_password, create_access_token


LOGIN_ID_SUFFIX_LENGTH = 5


def normalize_mobile_number(value: str | None) -> str | None:
    if not value:
        return None

    clean_value = "".join(char for char in str(value).strip() if char.isdigit())

    return clean_value or None


def generate_candidate_login_id() -> str:
    first_five_digits = "".join(random.choices(string.digits, k=5))
    suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=LOGIN_ID_SUFFIX_LENGTH)
    )

    return f"{first_five_digits}{suffix}"


def generate_unique_login_id(conn) -> str:
    for _ in range(50):
        login_id = generate_candidate_login_id()

        existing = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE login_id = ?
            """,
            [login_id]
        ).fetchone()

        if not existing:
            return login_id

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate unique login ID"
    )


def get_user_profile_by_id(user_id: str):
    conn = get_connection()

    user = conn.execute(
        """
        SELECT
            user_id,
            login_id,
            full_name,
            email,
            mobile_number,
            role,
            access_restrictions,
            is_active,
            created_at
        FROM users
        WHERE user_id = ?
        """,
        [user_id]
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    (
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        role,
        access_restrictions,
        is_active,
        created_at
    ) = user

    return {
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name,
        "email": email,
        "mobile_number": mobile_number,
        "role": role,
        "access_restrictions": access_restrictions,
        "is_active": is_active,
        "created_at": str(created_at)
    }


def register_user(full_name: str, email: str, password: str):
    clean_email = email.strip().lower()

    conn = get_connection()

    existing_user = conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE LOWER(email) = ?
        """,
        [clean_email]
    ).fetchone()

    if existing_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_id = str(uuid.uuid4())
    login_id = generate_unique_login_id(conn)
    password_hash = hash_password(password)

    conn.execute(
        """
        INSERT INTO users (
            user_id,
            login_id,
            full_name,
            email,
            password_hash,
            role,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            user_id,
            login_id,
            full_name.strip(),
            clean_email,
            password_hash,
            "user",
            True
        ]
    )

    conn.close()

    access_token = create_access_token(
        data={
            "sub": user_id,
            "login_id": login_id,
            "email": clean_email,
            "role": "user"
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name.strip(),
        "email": clean_email,
        "role": "user"
    }


def login_user(login_identifier: str, password: str):
    clean_identifier = login_identifier.strip()
    clean_identifier_lower = clean_identifier.lower()
    clean_identifier_mobile = normalize_mobile_number(clean_identifier)

    conn = get_connection()

    user = conn.execute(
        """
        SELECT
            user_id,
            login_id,
            full_name,
            email,
            mobile_number,
            password_hash,
            role,
            is_active
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
            clean_identifier_mobile or clean_identifier
        ]
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login ID, mobile, email, or password"
        )

    (
        user_id,
        login_id,
        full_name,
        user_email,
        mobile_number,
        password_hash,
        role,
        is_active
    ) = user

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if not verify_password(password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login ID, mobile, email, or password"
        )

    access_token = create_access_token(
        data={
            "sub": user_id,
            "login_id": login_id,
            "email": user_email,
            "role": role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name,
        "email": user_email,
        "role": role
    }


def update_profile_service(
    user_id: str,
    full_name: str,
    email: str,
    mobile_number: str | None
):
    clean_full_name = full_name.strip()
    clean_email = email.strip().lower()
    clean_mobile_number = mobile_number.strip() if mobile_number else None

    if len(clean_full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 2 characters"
        )

    conn = get_connection()

    user = conn.execute(
        """
        SELECT user_id, is_active
        FROM users
        WHERE user_id = ?
        """,
        [user_id]
    ).fetchone()

    if not user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    _, is_active = user

    if not is_active:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    existing_email_user = conn.execute(
        """
        SELECT user_id
        FROM users
        WHERE LOWER(email) = ? AND user_id != ?
        """,
        [clean_email, user_id]
    ).fetchone()

    if existing_email_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    if clean_mobile_number:
        existing_mobile_user = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE mobile_number = ? AND user_id != ?
            """,
            [clean_mobile_number, user_id]
        ).fetchone()

        if existing_mobile_user:
            conn.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered"
            )

    conn.execute(
        """
        UPDATE users
        SET
            full_name = ?,
            email = ?,
            mobile_number = ?
        WHERE user_id = ?
        """,
        [clean_full_name, clean_email, clean_mobile_number, user_id]
    )

    conn.close()

    return {
        "status": "success",
        "message": "User details updated successfully",
        "user": get_user_profile_by_id(user_id)
    }


def change_password_service(
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_password: str
):
    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password"
        )

    conn = get_connection()

    user = conn.execute(
        """
        SELECT password_hash, is_active
        FROM users
        WHERE user_id = ?
        """,
        [user_id]
    ).fetchone()

    if not user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    password_hash, is_active = user

    if not is_active:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if not verify_password(current_password, password_hash):
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    new_password_hash = hash_password(new_password)

    conn.execute(
        """
        UPDATE users
        SET password_hash = ?
        WHERE user_id = ?
        """,
        [new_password_hash, user_id]
    )

    conn.close()

    return {
        "status": "success",
        "message": "Password changed successfully"
    }