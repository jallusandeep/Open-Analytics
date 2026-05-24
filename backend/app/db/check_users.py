import duckdb
from pathlib import Path


DB_PATH = Path(__file__).parent / "open_analytics.duckdb"

print("DATABASE PATH:")
print(DB_PATH)

if not DB_PATH.exists():
    print("ERROR: DuckDB file not found.")
    raise SystemExit

conn = duckdb.connect(str(DB_PATH))

users = conn.execute(
    """
    SELECT
        user_id,
        login_id,
        full_name,
        email,
        role,
        is_active
    FROM users
    ORDER BY created_at DESC
    """
).fetchall()

print("\nUSERS FOUND:")
for user in users:
    print(user)

conn.close()