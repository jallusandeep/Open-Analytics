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