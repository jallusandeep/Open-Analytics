import json
import logging
import math
import random
import string
import uuid

from fastapi import HTTPException, status

from app.repositories.base_repository import db_connection
from app.repositories.user_repository import UserRepository
from app.security import hash_password

logger = logging.getLogger(__name__)

user_repo = UserRepository()

VALID_ROLES = ["user", "admin", "super_admin"]
LOGIN_ID_SUFFIX_LENGTH = 5


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


def serialize_user_row(row):
    return {
        "user_id": row[0],
        "login_id": row[1],
        "full_name": row[2],
        "email": row[3],
        "mobile_number": row[4],
        "role": row[5],
        "access_restrictions": row[6],
        "is_active": row[7],
        "created_at": str(row[8]),
        "updated_at": str(row[9]),
    }


def list_users_service(
    page: int,
    page_size: int,
    search: str,
    role: str,
    is_active,
):
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size

    where_clause, params = user_repo.build_list_filters(search, role, is_active)

    logger.info(
        "Listing users: page=%s page_size=%s search=%s role=%s",
        page,
        page_size,
        bool(search),
        role,
    )

    with db_connection() as conn:
        total_records = user_repo.count_users(conn, where_clause, params)
        rows = user_repo.list_users(conn, where_clause, params, page_size, offset)

    users = [serialize_user_row(row) for row in rows]
    total_pages = math.ceil(total_records / page_size) if total_records else 1

    return {
        "page": page,
        "page_size": page_size,
        "total_records": total_records,
        "total_pages": total_pages,
        "users": users,
    }


def create_user_service(request, current_user):
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role",
        )

    if current_user["role"] == "admin" and request.role in ["admin", "super_admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin can create only normal users",
        )

    clean_email = request.email.strip().lower()
    clean_mobile_number = request.mobile_number.strip() if request.mobile_number else None

    logger.info(
        "Creating user: email=%s role=%s by=%s",
        clean_email,
        request.role,
        current_user.get("user_id"),
    )

    with db_connection() as conn:
        if user_repo.find_duplicate_for_create(conn, clean_email, clean_mobile_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email or mobile number already exists",
            )

        user_id = str(uuid.uuid4())
        login_id = generate_unique_login_id(conn)
        password_hash = hash_password(request.password)

        access_restrictions = None
        if request.role == "user":
            access_restrictions = json.dumps(request.access_restrictions or [])

        user_repo.create_user(
            conn,
            user_id=user_id,
            login_id=login_id,
            full_name=request.full_name.strip(),
            email=clean_email,
            mobile_number=clean_mobile_number,
            password_hash=password_hash,
            role=request.role,
            access_restrictions=access_restrictions,
            is_active=True,
        )

        created_user = user_repo.get_admin_user_row(conn, user_id)

    logger.info("User created: user_id=%s login_id=%s", user_id, login_id)
    return serialize_user_row(created_user)


def update_user_service(user_id: str, request, current_user: dict):
    if request.role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid user role",
        )

    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot edit your own account",
        )

    clean_login_id = request.login_id.strip()
    clean_email = request.email.strip().lower()
    clean_mobile_number = request.mobile_number.strip() if request.mobile_number else None

    logger.info("Updating user: user_id=%s by=%s", user_id, current_user.get("user_id"))

    with db_connection() as conn:
        target_user = user_repo.find_target_user(conn, user_id)

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        target_role = target_user[1]

        if current_user["role"] == "admin" and target_role == "super_admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cannot edit super admin",
            )

        if current_user["role"] == "admin" and request.role in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cannot assign admin roles",
            )

        if user_repo.find_duplicate_for_update(
            conn, clean_email, clean_login_id, clean_mobile_number, user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email, Login ID, or mobile number already exists",
            )

        access_restrictions = None
        if request.role == "user":
            access_restrictions = json.dumps(request.access_restrictions or [])

        user_repo.update_user_admin(
            conn,
            user_id=user_id,
            login_id=clean_login_id,
            full_name=request.full_name.strip(),
            email=clean_email,
            mobile_number=clean_mobile_number,
            role=request.role,
            access_restrictions=access_restrictions,
            is_active=request.is_active,
        )

        updated_user = user_repo.get_admin_user_row(conn, user_id)

    logger.info("User updated: user_id=%s", user_id)
    return serialize_user_row(updated_user)


def delete_user_service(user_id: str, current_user: dict):
    if user_id == current_user["user_id"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    logger.info("Deleting user: user_id=%s by=%s", user_id, current_user.get("user_id"))

    with db_connection() as conn:
        target_user = user_repo.find_target_user(conn, user_id)

        if not target_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        target_role = target_user[1]

        if current_user["role"] == "admin" and target_role in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin cannot delete admin or super admin",
            )

        user_repo.soft_delete(conn, user_id)

    logger.info("User deleted: user_id=%s", user_id)

    return {
        "message": "User deleted successfully",
        "user_id": user_id,
    }
