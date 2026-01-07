"""
Clean up blank and duplicate announcements from database

IMPORTANT: Only removes duplicates by announcement_id (TrueData's unique identifier)
Different companies can have the same headline, so we don't dedupe by headline
"""
import os
import sys
import duckdb
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.config import settings

def clean_announcements():
    """Remove blank entries and duplicates from announcements database"""
    data_dir = settings.DATA_DIR
    db_dir = os.path.join(data_dir, "Company Fundamentals")
    db_path = os.path.join(db_dir, "corporate_announcements.duckdb")
    
    if not os.path.exists(db_path):
        print(f"Database not found: {db_path}")
        return
    
    print(f"Connecting to database: {db_path}")
    conn = duckdb.connect(db_path)
    
    try:
        # Count before cleanup
        total_before = conn.execute("SELECT COUNT(*) FROM corporate_announcements").fetchone()[0]
        print(f"\nTotal announcements before cleanup: {total_before}")
        
        # Find blank entries
        blank_count = conn.execute("""
            SELECT COUNT(*) FROM corporate_announcements
            WHERE (headline IS NULL OR headline = '' OR headline = '-' OR headline = 'null' OR headline = 'None')
              AND (description IS NULL OR description = '' OR description = '-')
        """).fetchone()[0]
        print(f"Found {blank_count} blank entries")
        
        # Find duplicates by announcement_id ONLY
        # Different companies can have the same headline, so we ONLY dedupe by announcement_id
        id_dup_count = conn.execute("""
            SELECT COALESCE(SUM(cnt - 1), 0) FROM (
                SELECT COUNT(*) as cnt
                FROM corporate_announcements
                WHERE announcement_id IS NOT NULL AND announcement_id != ''
                GROUP BY announcement_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        print(f"Found {id_dup_count} duplicates by announcement_id")
        
        total_to_remove = blank_count + id_dup_count
        
        if total_to_remove == 0:
            print("\n[OK] No cleanup needed - database is clean!")
            
            # Show stats
            unique_ids = conn.execute("SELECT COUNT(DISTINCT announcement_id) FROM corporate_announcements").fetchone()[0]
            unique_headlines = conn.execute("SELECT COUNT(DISTINCT headline) FROM corporate_announcements WHERE headline IS NOT NULL").fetchone()[0]
            print(f"\nStats:")
            print(f"  Total announcements: {total_before}")
            print(f"  Unique announcement_ids: {unique_ids}")
            print(f"  Unique headlines: {unique_headlines}")
            print(f"  (Note: Same headline can appear for different companies - this is normal)")
            return
        
        print(f"\n[INFO] Starting cleanup...")
        
        # Step 1: Delete blank entries
        if blank_count > 0:
            print(f"Deleting blank entries...")
            conn.execute("""
                DELETE FROM corporate_announcements
                WHERE (headline IS NULL OR headline = '' OR headline = '-' OR headline = 'null' OR headline = 'None')
                  AND (description IS NULL OR description = '' OR description = '-')
            """)
            conn.commit()
            print(f"[OK] Deleted blank entries")
        
        # Step 2: Delete duplicates by announcement_id ONLY (keep first by rowid)
        if id_dup_count > 0:
            print(f"Removing duplicates by announcement_id...")
            conn.execute("""
                DELETE FROM corporate_announcements
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM corporate_announcements
                    GROUP BY announcement_id
                )
            """)
            conn.commit()
            print(f"[OK] Removed duplicates by announcement_id")
        
        # Count after cleanup
        total_after = conn.execute("SELECT COUNT(*) FROM corporate_announcements").fetchone()[0]
        removed = total_before - total_after
        
        # Verify no more duplicates by announcement_id
        remaining_dups = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT announcement_id, COUNT(*) as cnt
                FROM corporate_announcements
                WHERE announcement_id IS NOT NULL AND announcement_id != ''
                GROUP BY announcement_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Cleanup Complete:")
        print(f"  Before: {total_before} announcements")
        print(f"  After:  {total_after} announcements")
        print(f"  Removed: {removed} entries")
        print(f"  Remaining duplicates (by ID): {remaining_dups}")
        print(f"{'='*50}")
        
        if remaining_dups == 0:
            print("[OK] Database is now clean!")
        else:
            print(f"[WARNING] Still {remaining_dups} duplicate groups remaining")
        
    except Exception as e:
        print(f"[ERROR] Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    clean_announcements()
