from datetime import datetime


APP_NAME = "Open Analytics"


def format_display_value(value):
    if value is None:
        return "--"

    clean_value = str(value).strip()

    if not clean_value:
        return "--"

    return clean_value


def get_current_timestamp_label():
    return datetime.now().strftime("%d-%b-%Y %I:%M %p")


def build_profile_updated_message(user: dict) -> str:
    full_name = format_display_value(user.get("full_name"))
    email = format_display_value(user.get("email"))
    mobile_number = format_display_value(user.get("mobile_number"))

    return (
        f"{APP_NAME} profile updated.\n\n"
        f"Name: {full_name}\n"
        f"Email: {email}\n"
        f"Mobile: {mobile_number}\n"
        f"Time: {get_current_timestamp_label()}\n\n"
        "If this was not done by you, please contact admin immediately."
    )


def build_user_account_updated_message(user: dict) -> str:
    full_name = format_display_value(user.get("full_name"))
    email = format_display_value(user.get("email"))
    mobile_number = format_display_value(user.get("mobile_number"))
    role = format_display_value(user.get("role")).replace("_", " ").title()
    status = "Active" if user.get("is_active") else "Inactive"

    return (
        f"{APP_NAME} user account updated.\n\n"
        f"Name: {full_name}\n"
        f"Email: {email}\n"
        f"Mobile: {mobile_number}\n"
        f"Role: {role}\n"
        f"Status: {status}\n"
        f"Time: {get_current_timestamp_label()}\n\n"
        "If this was not done by you, please contact admin immediately."
    )


def build_password_changed_message(user: dict) -> str:
    full_name = format_display_value(user.get("full_name"))
    email = format_display_value(user.get("email"))

    return (
        f"{APP_NAME} password changed.\n\n"
        f"User: {full_name}\n"
        f"Email: {email}\n"
        f"Time: {get_current_timestamp_label()}\n\n"
        "If this was not done by you, please contact admin immediately."
    )


def build_forgot_password_otp_message(user: dict, otp: str) -> str:
    full_name = format_display_value(user.get("full_name"))
    email = format_display_value(user.get("email"))

    return (
        f"{APP_NAME} password reset OTP.\n\n"
        f"User: {full_name}\n"
        f"Email: {email}\n"
        f"OTP: {otp}\n"
        "Valid for: 5 minutes\n\n"
        "Do not share this OTP with anyone."
    )


def build_password_reset_success_message(user: dict) -> str:
    full_name = format_display_value(user.get("full_name"))
    email = format_display_value(user.get("email"))

    return (
        f"{APP_NAME} password reset completed.\n\n"
        f"User: {full_name}\n"
        f"Email: {email}\n"
        f"Time: {get_current_timestamp_label()}\n\n"
        "If this was not done by you, please contact admin immediately."
    )


def build_telegram_connected_message() -> str:
    return f"{APP_NAME} Telegram connected successfully."


def build_telegram_test_message() -> str:
    return f"{APP_NAME} Telegram test message."


def build_upstox_token_saved_from_webhook_message(expiry_date) -> str:
    expiry_label = "--"

    if expiry_date:
        expiry_label = expiry_date.strftime("%d %b %Y, %I:%M %p")

    return (
        f"{APP_NAME} update\n\n"
        "Upstox access token was received from the Upstox notifier webhook "
        "and saved successfully.\n\n"
        f"Token expiry: {expiry_label} IST"
    )


def build_upstox_access_token_reminder_message(
    token_status_text: str,
    approval_text: str,
    auto_request_status: str,
    auto_request_message: str
) -> str:
    return (
        f"{APP_NAME} reminder\n\n"
        f"Upstox access token is {format_display_value(token_status_text)}.\n\n"
        f"{format_display_value(approval_text)}\n\n"
        f"Auto request status: {format_display_value(auto_request_status)}\n"
        f"Details: {format_display_value(auto_request_message)}\n\n"
        "This reminder repeats every 1 hour after 6:00 AM IST until a valid token is saved."
    )
