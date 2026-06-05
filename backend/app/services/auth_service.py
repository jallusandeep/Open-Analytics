import logging
import random
import string
import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException, status

from app.repositories.base_repository import db_connection
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.user_repository import UserRepository
from app.security import create_access_token, hash_password, verify_password
from app.telegram_alerts_msg.message_templates import (
    build_forgot_password_otp_message,
    build_password_changed_message,
    build_password_reset_success_message,
    build_profile_updated_message,
)
from app.telegram_alerts_msg.telegram_sender import send_user_telegram_alert

logger = logging.getLogger(__name__)

user_repo = UserRepository()
password_reset_repo = PasswordResetRepository()

LOGIN_ID_SUFFIX_LENGTH = 5
FORGOT_PASSWORD_OTP_MINUTES = 5
FORGOT_PASSWORD_OTP_LENGTH = 6


def generate_candidate_login_id() -> str:
    first_five_digits = "".join(random.choices(string.digits, k=5))
    suffix = "".join(
        random.choices(string.ascii_uppercase + string.digits, k=LOGIN_ID_SUFFIX_LENGTH)
    )
    return f"{first_five_digits}{suffix}"


def generate_unique_login_id(conn) -> str:
    for _ in range(50):
        login_id = generate_candidate_login_id()
        if not user_repo.login_id_exists(conn, login_id):
            return login_id

    logger.error("Failed to generate unique login ID after 50 attempts")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Unable to generate unique login ID",
    )


def generate_forgot_password_otp() -> str:
    return "".join(
        random.SystemRandom().choice(string.digits)
        for _ in range(FORGOT_PASSWORD_OTP_LENGTH)
    )


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
        is_active,
    ) = user

    return {
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name,
        "email": email,
        "mobile_number": mobile_number,
        "password_hash": password_hash,
        "role": role,
        "is_active": is_active,
    }


def profile_row_to_dict(user):
    if not user:
        return None

    (
        user_id,
        login_id,
        full_name,
        email,
        mobile_number,
        role,
        access_restrictions,
        is_active,
        created_at,
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
        "created_at": str(created_at),
    }


def get_user_profile_by_id(user_id: str):
    with db_connection() as conn:
        user = user_repo.get_profile_by_id(conn, user_id)

    if not user:
        logger.warning("User profile not found: user_id=%s", user_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return profile_row_to_dict(user)


def register_user(full_name: str, email: str, password: str):
    clean_email = email.strip().lower()
    logger.info("Registering user: email=%s", clean_email)

    with db_connection() as conn:
        if user_repo.find_by_email(conn, clean_email):
            logger.warning("Registration rejected, email already exists: %s", clean_email)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        user_id = str(uuid.uuid4())
        login_id = generate_unique_login_id(conn)
        password_hash = hash_password(password)

        user_repo.create_user(
            conn,
            user_id=user_id,
            login_id=login_id,
            full_name=full_name.strip(),
            email=clean_email,
            mobile_number=None,
            password_hash=password_hash,
            role="user",
            access_restrictions=None,
            is_active=True,
        )

    logger.info("User registered successfully: user_id=%s login_id=%s", user_id, login_id)

    access_token = create_access_token(
        data={
            "sub": user_id,
            "login_id": login_id,
            "email": clean_email,
            "role": "user",
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_id,
        "login_id": login_id,
        "full_name": full_name.strip(),
        "email": clean_email,
        "role": "user",
    }


def login_user(login_identifier: str, password: str):
    logger.info("Login attempt for identifier=%s", login_identifier.strip()[:3] + "***")

    with db_connection() as conn:
        user = user_repo.find_by_login_identifier(conn, login_identifier)

    if not user:
        logger.warning("Login failed: user not found")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login ID, mobile, email, or password",
        )

    user_data = user_row_to_dict(user)

    if not user_data["is_active"]:
        logger.warning("Login failed: inactive account user_id=%s", user_data["user_id"])
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
        )

    if not verify_password(password, user_data["password_hash"]):
        logger.warning("Login failed: invalid password user_id=%s", user_data["user_id"])
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login ID, mobile, email, or password",
        )

    logger.info("Login successful: user_id=%s role=%s", user_data["user_id"], user_data["role"])

    access_token = create_access_token(
        data={
            "sub": user_data["user_id"],
            "login_id": user_data["login_id"],
            "email": user_data["email"],
            "role": user_data["role"],
        }
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user_data["user_id"],
        "login_id": user_data["login_id"],
        "full_name": user_data["full_name"],
        "email": user_data["email"],
        "role": user_data["role"],
    }


def update_profile_service(
    user_id: str,
    full_name: str,
    email: str,
    mobile_number: str | None,
):
    clean_full_name = full_name.strip()
    clean_email = email.strip().lower()
    clean_mobile_number = mobile_number.strip() if mobile_number else None

    logger.info("Updating profile: user_id=%s", user_id)

    if len(clean_full_name) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 2 characters",
        )

    with db_connection() as conn:
        user = user_repo.get_active_status(conn, user_id)

        if not user:
            logger.warning("Profile update failed: user not found user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if not user[1]:
            logger.warning("Profile update failed: inactive user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if user_repo.find_by_email_excluding_user(conn, clean_email, user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        if clean_mobile_number and user_repo.find_by_mobile_excluding_user(
            conn, clean_mobile_number, user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mobile number already registered",
            )

        user_repo.update_profile(
            conn,
            user_id=user_id,
            full_name=clean_full_name,
            email=clean_email,
            mobile_number=clean_mobile_number,
        )

    updated_user = get_user_profile_by_id(user_id)
    logger.info("Profile updated successfully: user_id=%s", user_id)

    send_user_telegram_alert(
        user_id=user_id,
        message=build_profile_updated_message(updated_user),
    )

    return {
        "status": "success",
        "message": "User details updated successfully",
        "user": updated_user,
    }


def change_password_service(
    user_id: str,
    current_password: str,
    new_password: str,
    confirm_password: str,
):
    logger.info("Password change requested: user_id=%s", user_id)

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    if current_password == new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    with db_connection() as conn:
        user = user_repo.get_password_hash_and_active(conn, user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        password_hash, is_active = user

        if not is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive",
            )

        if not verify_password(current_password, password_hash):
            logger.warning("Password change failed: wrong current password user_id=%s", user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect",
            )

        user_repo.update_password(conn, user_id, hash_password(new_password))

    updated_user = get_user_profile_by_id(user_id)
    logger.info("Password changed successfully: user_id=%s", user_id)

    send_user_telegram_alert(
        user_id=user_id,
        message=build_password_changed_message(updated_user),
    )

    return {
        "status": "success",
        "message": "Password changed successfully",
    }


def request_forgot_password_otp_service(login_identifier: str):
    logger.info("Forgot password OTP requested")

    with db_connection() as conn:
        try:
            user = user_repo.find_by_login_identifier(conn, login_identifier)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            user_data = user_row_to_dict(user)

            if not user_data["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            otp = generate_forgot_password_otp()
            reset_id = str(uuid.uuid4())
            expires_at = datetime.now() + timedelta(minutes=FORGOT_PASSWORD_OTP_MINUTES)

            password_reset_repo.invalidate_unused_tokens(conn, user_data["user_id"])
            password_reset_repo.create_token(
                conn,
                reset_id=reset_id,
                user_id=user_data["user_id"],
                otp=otp,
                expires_at=expires_at,
            )
            conn.commit()

            telegram_sent = send_user_telegram_alert(
                user_id=user_data["user_id"],
                message=build_forgot_password_otp_message(user_data, otp),
            )

            if not telegram_sent:
                logger.warning(
                    "Forgot password OTP not sent: Telegram not connected user_id=%s",
                    user_data["user_id"],
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Telegram is not connected for this user. Please contact admin "
                        "or login and connect Telegram from Settings."
                    ),
                )

            logger.info("Forgot password OTP sent: user_id=%s", user_data["user_id"])

            return {
                "status": "success",
                "message": "OTP sent to your connected Telegram. OTP is valid for 5 minutes.",
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

            logger.exception("Unable to send forgot password OTP: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to send forgot password OTP: {e}",
            )


def reset_password_with_otp_service(
    login_identifier: str,
    otp: str,
    new_password: str,
    confirm_password: str,
):
    clean_otp = str(otp).strip()
    logger.info("Password reset with OTP requested")

    if new_password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match",
        )

    with db_connection() as conn:
        try:
            user = user_repo.find_by_login_identifier(conn, login_identifier)

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="User not found",
                )

            user_data = user_row_to_dict(user)

            if not user_data["is_active"]:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="User account is inactive",
                )

            reset_token = password_reset_repo.find_valid_token(
                conn, user_data["user_id"], clean_otp
            )

            if not reset_token:
                logger.warning(
                    "Password reset failed: invalid OTP user_id=%s",
                    user_data["user_id"],
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or expired OTP",
                )

            reset_id = reset_token[0]
            user_repo.update_password(
                conn, user_data["user_id"], hash_password(new_password)
            )
            password_reset_repo.mark_used(conn, reset_id)
            conn.commit()

            updated_user = get_user_profile_by_id(user_data["user_id"])
            logger.info("Password reset successful: user_id=%s", user_data["user_id"])

            send_user_telegram_alert(
                user_id=user_data["user_id"],
                message=build_password_reset_success_message(updated_user),
            )

            return {
                "status": "success",
                "message": "Password reset successfully",
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

            logger.exception("Unable to reset password: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Unable to reset password: {e}",
            )
