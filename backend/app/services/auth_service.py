import uuid
from fastapi import HTTPException, status

from app.database import get_connection
from app.security import hash_password, verify_password, create_access_token


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
    conn = get_connection()

    existing_user = conn.execute(
        "SELECT user_id FROM users WHERE email = ?",
        [email]
    ).fetchone()

    if existing_user:
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    user_id = str(uuid.uuid4())
    password_hash = hash_password(password)

    conn.execute(
        """
        INSERT INTO users (
            user_id,
            full_name,
            email,
            password_hash,
            role,
            is_active
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [user_id, full_name, email, password_hash, "user", True]
    )

    conn.close()

    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": email,
            "role": "user"
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "full_name": full_name,
        "email": email,
        "role": "user"
    }


def login_user(email: str, password: str):
    conn = get_connection()

    user = conn.execute(
        """
        SELECT user_id, full_name, email, password_hash, role, is_active
        FROM users
        WHERE email = ?
        """,
        [email]
    ).fetchone()

    conn.close()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    user_id, full_name, user_email, password_hash, role, is_active = user

    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    if not verify_password(password, password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    access_token = create_access_token(
        data={
            "sub": user_id,
            "email": user_email,
            "role": role
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
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