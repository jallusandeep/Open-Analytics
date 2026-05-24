import uuid
from fastapi import HTTPException, status
from app.database import get_connection
from app.security import hash_password, verify_password, create_access_token


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