import random
import string
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.database import get_connection
from app.security import hash_password, verify_password, create_access_token
from app.telegram_alerts_msg.message_templates import (
    build_forgot_password_otp_message,
    build_password_changed_message,
    build_password_reset_success_message,
    build_profile_updated_message
)
from app.telegram_alerts_msg.telegram_sender import send_user_telegram_alert


LOGIN_ID_PREFIX_LENGTH = 5
LOGIN_ID_SUFFIX_LENGTH = 5
LOGIN_ID_GENERATION_ATTEMPTS = 50
FORGOT_PASSWORD_OTP_MINUTES = 5
FORGOT_PASSWORD_OTP_LENGTH = 6


def normalize_mobile_number(value: str | None) -> str | None:
    if not value:
        return None

    clean_value = "".join(char for char in str(value).strip() if char.isdigit())

    return clean_value or None


def generate_candidate_login_id() -> str:
    prefix = "".join(random.choices(string.digits, k=LOGIN_ID_PREFIX_LENGTH))
    suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=LOGIN_ID_SUFFIX_LENGTH)
    )

    return f"{prefix}{suffix}"


def generate_unique_login_id(conn) -> str:
    for _ in range(LOGIN_ID_GENERATION_ATTEMPTS):
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


def generate_forgot_password_otp() -> str:
    return "".join(
        random.SystemRandom().choice(string.digits)
        for _ in range(FORGOT_PASSWORD_OTP_LENGTH)
    )


def create_user_session(conn, user_id: str, access_token: str):
    session_id = str(uuid.uuid4())

    conn.execute(
        """
        INSERT INTO user_sessions (
            session_id,
            user_id,
            access_token,
            is_active,
            created_at,
            last_seen_at,
            expires_at,
            logged_out_at
        )
        VALUES (?, ?, ?, TRUE, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, NULL, NULL)
        """,
        [
            session_id,
            user_id,
            access_token
        ]
    )

    return session_id


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
          AND COALESCE(record_status, 'S') != 'D'
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


def get_user_by_login_identifier(conn, login_identifier: str):
    clean_identifier = login_identifier.strip()
    clean_identifier_lower = clean_identifier.lower()
    clean_identifier_mobile = normalize_mobile_number(clean_identifier)

    return conn.execute(
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


def user_row_to_dict(user):
    if not user:
        return None

    (
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        password_hash,
        role,
        is_active
    ) = user

    return {
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name,
        "email": email,
        "mobile_number": mobile_number,
        "password_hash": password_hash,
        "role": role,
        "is_active": is_active
    }


def register_user(full_name: str, email: str, password: str):
    clean_email = email.strip().lower()

    conn = get_connection()

    try:
        existing_user = conn.execute(
            """
            SELECT user_id
            FROM users
            WHERE LOWER(email) = ?
              AND COALESCE(record_status, 'S') != 'D'
            """,
            [clean_email]
        ).fetchone()

        if existing_user:
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

        access_token = create_access_token(
            data={
                "sub": user_id,
                "login_id": login_id,
                "email": clean_email,
                "role": "user"
            }
        )

        create_user_session(
            conn=conn,
            user_id=user_id,
            access_token=access_token
        )

        conn.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_id,
            "login_id": login_id,
            "full_name": full_name.strip(),
            "email": clean_email,
            "role": "user"
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to register user: {e}"
        )

    finally:
        conn.close()


def login_user(login_identifier: str, password: str):
    conn = get_connection()

    try:
        user = get_user_by_login_identifier(conn, login_identifier)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login ID, mobile, email, or password"
            )

        user_data = user_row_to_dict(user)

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        if not verify_password(password, user_data["password_hash"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid login ID, mobile, email, or password"
            )

        access_token = create_access_token(
            data={
                "sub": user_data["user_id"],
                "login_id": user_data["login_id"],
                "email": user_data["email"],
                "role": user_data["role"]
            }
        )

        create_user_session(
            conn=conn,
            user_id=user_data["user_id"],
            access_token=access_token
        )

        conn.commit()

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user_id": user_data["user_id"],
            "login_id": user_data["login_id"],
            "full_name": user_data["full_name"],
            "email": user_data["email"],
            "role": user_data["role"]
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to login: {e}"
        )

    finally:
        conn.close()


def logout_user_service(user_id: str):
    conn = get_connection()

    try:
        conn.execute(
            """
            UPDATE user_sessions
            SET
                is_active = FALSE,
                logged_out_at = CURRENT_TIMESTAMP,
                last_seen_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND COALESCE(is_active, TRUE) = TRUE
            """,
            [user_id]
        )

        conn.commit()

        return {
            "status": "success",
            "message": "Logged out successfully"
        }

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to logout: {e}"
        )

    finally:
        conn.close()


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
          AND COALESCE(record_status, 'S') != 'D'
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
        WHERE LOWER(email) = ?
          AND user_id != ?
          AND COALESCE(record_status, 'S') != 'D'
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
            WHERE mobile_number = ?
              AND user_id != ?
              AND COALESCE(record_status, 'S') != 'D'
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
            mobile_number = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = ?
        WHERE user_id = ?
        """,
        [clean_full_name, clean_email, clean_mobile_number, user_id, user_id]
    )

    conn.close()

    updated_user = get_user_profile_by_id(user_id)

    send_user_telegram_alert(
        user_id=user_id,
        message=build_profile_updated_message(updated_user)
    )

    return {
        "status": "success",
        "message": "User details updated successfully",
        "user": updated_user
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
          AND COALESCE(record_status, 'S') != 'D'
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
        SET
            password_hash = ?,
            updated_at = CURRENT_TIMESTAMP,
            updated_by = ?
        WHERE user_id = ?
        """,
        [new_password_hash, user_id, user_id]
    )

    conn.close()

    updated_user = get_user_profile_by_id(user_id)

    send_user_telegram_alert(
        user_id=user_id,
        message=build_password_changed_message(updated_user)
    )

    return {
        "status": "success",
        "message": "Password changed successfully"
    }


def request_forgot_password_otp_service(login_identifier: str):
    conn = get_connection()

    try:
        user = get_user_by_login_identifier(conn, login_identifier)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user_data = user_row_to_dict(user)

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        otp = generate_forgot_password_otp()
        reset_id = str(uuid.uuid4())
        expires_at = datetime.now() + timedelta(minutes=FORGOT_PASSWORD_OTP_MINUTES)

        conn.execute(
            """
            UPDATE password_reset_tokens
            SET is_used = TRUE
            WHERE user_id = ?
              AND is_used = FALSE
            """,
            [user_data["user_id"]]
        )

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
            [
                reset_id,
                user_data["user_id"],
                otp,
                False,
                expires_at
            ]
        )

        conn.commit()

        telegram_sent = send_user_telegram_alert(
            user_id=user_data["user_id"],
            message=build_forgot_password_otp_message(user_data, otp)
        )

        if not telegram_sent:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Telegram is not connected for this user. Please contact admin or login and connect Telegram from Settings."
            )

        return {
            "status": "success",
            "message": "OTP sent to your connected Telegram. OTP is valid for 5 minutes."
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to send forgot password OTP: {e}"
        )

    finally:
        conn.close()


def reset_password_with_otp_service(
    login_identifier: str,
    otp: str,
    new_password: str,
    confirm_password: str
):
    clean_otp = str(otp).strip()

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match"
        )

    conn = get_connection()

    try:
        user = get_user_by_login_identifier(conn, login_identifier)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user_data = user_row_to_dict(user)

        if not user_data["is_active"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        reset_token = conn.execute(
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
            [
                user_data["user_id"],
                clean_otp
            ]
        ).fetchone()

        if not reset_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired OTP"
            )

        reset_id = reset_token[0]
        new_password_hash = hash_password(new_password)

        conn.execute(
            """
            UPDATE users
            SET
                password_hash = ?,
                updated_at = CURRENT_TIMESTAMP,
                updated_by = ?
            WHERE user_id = ?
            """,
            [
                new_password_hash,
                user_data["user_id"],
                user_data["user_id"]
            ]
        )

        conn.execute(
            """
            UPDATE password_reset_tokens
            SET is_used = TRUE
            WHERE reset_id = ?
            """,
            [reset_id]
        )

        conn.commit()

        updated_user = get_user_profile_by_id(user_data["user_id"])

        send_user_telegram_alert(
            user_id=user_data["user_id"],
            message=build_password_reset_success_message(updated_user)
        )

        return {
            "status": "success",
            "message": "Password reset successfully"
        }

    except HTTPException:
        try:
            conn.rollback()
        except Exception:
            pass
        raise

    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to reset password: {e}"
        )

    finally:
        conn.close()