"""App grants stored as namespaced denies alongside existing access restrictions."""
import json

APPS = ("trading", "admin", "recom")


def restrictions_list(value):
    if isinstance(value, str):
        value = json.loads(value)
    return value if isinstance(value, list) else []


def allowed_apps(role, restrictions):
    denied = set(restrictions_list(restrictions))
    return [app for app in APPS if f"app:deny:{app}" not in denied and (app != "admin" or role in ("admin", "super_admin"))]


def serialize_app_access(restrictions, grants):
    values = [value for value in restrictions_list(restrictions) if not value.startswith("app:deny:")]
    values.extend(f"app:deny:{app}" for app in APPS if app not in grants)
    return json.dumps(values)
