import duckdb
from pathlib import Path


DB_PATH = Path(__file__).parent / "open_analytics.duckdb"

# Change this email if your login email is different
EMAIL = "sandeep@test.com"

print("DATABASE PATH:")
print(DB_PATH)

if not DB_PATH.exists():
    print("ERROR: DuckDB file not found.")
    raise SystemExit

conn = duckdb.connect(str(DB_PATH))

before_user = conn.execute(
    """
    SELECT login_id, full_name, email, role, is_active
    FROM users
    WHERE email = ?
    """,
    [EMAIL]
).fetchone()

print("\nBEFORE UPDATE:")
print(before_user)

if before_user is None:
    print("\nERROR: No user found with this email:")
    print(EMAIL)

    print("\nAvailable users:")
    users = conn.execute(
        """
        SELECT login_id, full_name, email, role, is_active
        FROM users
        ORDER BY created_at DESC
        """
    ).fetchall()

    for user in users:
        print(user)

    conn.close()
    raise SystemExit

conn.execute(
    """
    UPDATE users
    SET role = 'super_admin',
        updated_at = CURRENT_TIMESTAMP
    WHERE email = ?
    """,
    [EMAIL]
)

after_user = conn.execute(
    """
    SELECT login_id, full_name, email, role, is_active
    FROM users
    WHERE email = ?
    """,
    [EMAIL]
).fetchone()

conn.close()

print("\nAFTER UPDATE:")
print(after_user)

print("\nSUCCESS: User role updated.")