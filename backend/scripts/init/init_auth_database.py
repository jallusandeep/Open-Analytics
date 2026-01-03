#!/usr/bin/env python3
"""
Initialize the authentication database with tables and admin user.

This script creates all database tables and ensures a super_admin user exists.
Safe to run multiple times (idempotent).

Admin credentials can be provided via:
1. Command line arguments: --username, --email, --password
2. Environment variables: ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD
3. Interactive prompts (if running interactively)
"""
import sys
import os
import uuid
import getpass
import argparse

# Add backend directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(os.path.dirname(script_dir))
sys.path.insert(0, backend_dir)

from app.core.database import Base, get_db_router, get_connection_manager
from app.models.user import User
from app.models.access_request import AccessRequest
from app.models.feedback import Feedback
from app.models.feature_request import FeatureRequest
from app.models.connection import Connection
from app.models.audit_log import AuditLog
# Note: Symbol, SymbolUploadLog, ScheduledIngestion models have been removed.
# TransformationScript may be used for other purposes, but is not imported here.
# Import only auth-related models.
from app.core.security import get_password_hash
from app.core.config import settings


def get_admin_credentials(args=None):
    """Get admin credentials from args, environment variables, or prompt"""
    # Priority: command line args > environment variables > interactive prompt
    
    # Get username
    username = None
    if args and args.username:
        username = args.username
    elif os.environ.get("ADMIN_USERNAME"):
        username = os.environ.get("ADMIN_USERNAME")
    
    # Get email
    email = None
    if args and args.email:
        email = args.email
    elif os.environ.get("ADMIN_EMAIL"):
        email = os.environ.get("ADMIN_EMAIL")
    
    # Get password
    password = None
    if args and args.password:
        password = args.password
    elif os.environ.get("ADMIN_PASSWORD"):
        password = os.environ.get("ADMIN_PASSWORD")
    
    # Interactive prompts for missing values (only if running interactively)
    if sys.stdin.isatty():
        if not username:
            username = input("Enter admin username: ").strip()
        if not email:
            email = input("Enter admin email: ").strip()
        if not password:
            password = getpass.getpass("Enter admin password: ")
            password_confirm = getpass.getpass("Confirm admin password: ")
            if password != password_confirm:
                print("[ERROR] Passwords do not match!")
                return None, None, None
    
    # Validate
    if not username or not email or not password:
        print("[ERROR] Admin credentials required. Provide via:")
        print("  - Command line: --username <user> --email <email> --password <pass>")
        print("  - Environment: ADMIN_USERNAME, ADMIN_EMAIL, ADMIN_PASSWORD")
        print("  - Interactive prompts (when running in terminal)")
        return None, None, None
    
    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long")
        return None, None, None
    
    return username, email, password


def init_auth_database(admin_username=None, admin_email=None, admin_password=None):
    """Initialize authentication database with tables and admin user"""
    print("Initializing authentication database...")
    
    # Ensure DATA_DIR is set and valid
    # Priority: environment variable > settings.DATA_DIR > default
    data_dir = os.environ.get("DATA_DIR")
    if not data_dir or data_dir.strip() == '':
        # Fallback to settings or default
        data_dir = settings.DATA_DIR if settings.DATA_DIR and settings.DATA_DIR.strip() else "/app/data"
        # If it's the hardcoded Windows path, use Docker default instead
        if "C:/Users" in data_dir or "C:\\Users" in data_dir:
            data_dir = "/app/data"
            print(f"[INFO] Detected Windows path in settings, using Docker default: {data_dir}")
    
    # Normalize path (handle both absolute and relative paths)
    if not os.path.isabs(data_dir):
        # If relative, make it absolute relative to backend directory
        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        data_dir = os.path.abspath(os.path.join(backend_dir, data_dir))
    
    print(f"[INFO] Using DATA_DIR: {data_dir}")
    
    router = get_db_router(data_dir)
    auth_client = router.get_auth_db()
    
    if not auth_client:
        print("[ERROR] Failed to connect to authentication database")
        return False
    
    # Ensure client is connected
    if not auth_client.is_connected:
        if not auth_client.connect():
            print("[ERROR] Failed to connect to authentication database")
            return False
    
    # Create all tables using the client's engine
    if hasattr(auth_client, 'engine') and auth_client.engine:
        engine = auth_client.engine
    else:
        # Fallback: create engine from connection config
        from sqlalchemy import create_engine
        # Use the same data_dir we validated earlier (already set above)
        
        manager = get_connection_manager(data_dir)
        conn_id = manager.active_connections.get("auth")
        if conn_id:
            conn_config = manager.connections.get(conn_id, {}).get("config", {})
            db_path = conn_config.get("path", os.path.join(data_dir, "auth", "sqlite", "auth.db"))
        else:
            db_path = os.path.join(data_dir, "auth", "sqlite", "auth.db")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created")
    
    db = auth_client.get_session()
    try:
        # Check if any super_admin user exists
        all_users = db.query(User).all()
        super_admins = [u for u in all_users if u.role and u.role.lower() == "super_admin"]
        
        if not super_admins:
            # No super admin exists - we need credentials to create one
            if not admin_username or not admin_email or not admin_password:
                print("[WARNING] No super_admin user exists and no credentials provided.")
                print("          Run this script with credentials to create an admin user:")
                print("          python init_auth_database.py --username <user> --email <email> --password <pass>")
                return True  # Tables created successfully, just no admin user
            
            # Check if the user already exists (by username or email)
            existing_user = db.query(User).filter(
                (User.username == admin_username) | (User.email == admin_email)
            ).first()
            
            if existing_user:
                # User exists, just ensure they're a super_admin
                print(f"[INFO] User '{admin_username}' already exists, ensuring super_admin role...")
                existing_user.role = "super_admin"
                existing_user.is_active = True
                if not existing_user.user_id or existing_user.user_id == '':
                    existing_user.user_id = str(uuid.uuid4())
                db.commit()
                print(f"[OK] Updated existing user to super_admin")
                print(f"  Username: {existing_user.username}")
                print(f"  Email: {existing_user.email}")
            else:
                # Create new admin user with provided credentials
                admin = User(
                    user_id=str(uuid.uuid4()),
                    username=admin_username,
                    email=admin_email,
                    mobile="",
                    hashed_password=get_password_hash(admin_password),
                    role="super_admin",
                    is_active=True,
                )
                db.add(admin)
                db.commit()
                print("[OK] Admin user created")
                print(f"  User ID: {admin.user_id}")
                print(f"  Username: {admin_username}")
                print(f"  Email: {admin_email}")
                print("  Role: super_admin")
                print("  Status: ACTIVE")
        else:
            # Super admins already exist - don't create new ones, just ensure they're active
            print(f"[OK] Found {len(super_admins)} existing super_admin user(s). Using existing users.")
            print("[INFO] Skipping creation of new admin user from docker-compose.yml")
            print("[INFO] Existing super_admin users:")
            for super_user in super_admins:
                print(f"  - {super_user.username} ({super_user.email})")
            
            # Only update the docker-compose admin user if it exists and needs updating
            if admin_username:
                existing_admin = db.query(User).filter(User.username == admin_username).first()
                if existing_admin:
                    # Ensure this user is also a super_admin if it exists
                    was_updated = False
                    if not existing_admin.user_id or existing_admin.user_id == '':
                        existing_admin.user_id = str(uuid.uuid4())
                        was_updated = True
                        print(f"[OK] Generated user_id for existing admin: {existing_admin.user_id}")
                    
                    if not existing_admin.is_active:
                        existing_admin.is_active = True
                        was_updated = True
                        print("[OK] Admin user activated")
                    
                    if existing_admin.role and existing_admin.role.lower() != "super_admin":
                        existing_admin.role = "super_admin"
                        was_updated = True
                        print("[OK] Admin user promoted to super_admin")
                    
                    if was_updated:
                        db.commit()
                        print("[OK] Admin user updated")
                    else:
                        print(f"[OK] Admin user '{admin_username}' already exists and is active")
        
        # Ensure ALL super_admin users are active (critical) - case-insensitive
        all_users = db.query(User).all()
        super_admins = [u for u in all_users if u.role and u.role.lower() == "super_admin"]
        super_admin_updated = False
        for super_user in super_admins:
            # Normalize role
            if super_user.role.lower() != "super_admin":
                super_user.role = "super_admin"
                super_admin_updated = True
                print(f"[OK] Normalized role for {super_user.username} to super_admin")
            if not super_user.is_active:
                super_user.is_active = True
                super_admin_updated = True
                print(f"[OK] Activated super_admin user: {super_user.username}")
        
        if super_admin_updated:
            db.commit()
            print("[OK] All super_admin users are now active and protected")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
        return False
    finally:
        db.close()

def main():
    """Main entry point with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Initialize authentication database with tables and admin user",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for credentials)
  python init_auth_database.py

  # With command line arguments
  python init_auth_database.py --username admin --email admin@example.com --password MySecurePass123

  # Using environment variables
  ADMIN_USERNAME=admin ADMIN_EMAIL=admin@example.com ADMIN_PASSWORD=MySecurePass123 python init_auth_database.py
        """
    )
    parser.add_argument("--username", "-u", help="Admin username")
    parser.add_argument("--email", "-e", help="Admin email address")
    parser.add_argument("--password", "-p", help="Admin password (min 8 characters)")
    
    args = parser.parse_args()
    
    # Get credentials
    username, email, password = get_admin_credentials(args)
    
    # Initialize database
    success = init_auth_database(
        admin_username=username,
        admin_email=email,
        admin_password=password
    )
    
    if success:
        print("[OK] Authentication database initialization complete")
    else:
        print("[ERROR] Authentication database initialization failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

