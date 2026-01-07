"""
Clean up blank and duplicate announcements from database
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
        
        # Find blank entries (no headline and no description, or headline is just "-")
        blank_query = """
            SELECT announcement_id, headline, description 
            FROM corporate_announcements
            WHERE (headline IS NULL OR headline = '' OR headline = '-' OR headline = 'null' OR headline = 'None')
              AND (description IS NULL OR description = '' OR description = '-')
        """
        blanks = conn.execute(blank_query).fetchall()
        blank_count = len(blanks)
        print(f"Found {blank_count} blank entries")
        
        # Find duplicates (same announcement_id)
        duplicate_query = """
            SELECT announcement_id, COUNT(*) as cnt
            FROM corporate_announcements
            WHERE announcement_id IS NOT NULL AND announcement_id != ''
            GROUP BY announcement_id
            HAVING COUNT(*) > 1
        """
        duplicates = conn.execute(duplicate_query).fetchall()
        duplicate_count = sum(row[1] - 1 for row in duplicates)
        print(f"Found {len(duplicates)} announcement_ids with duplicates ({duplicate_count} extra copies)")
        
        # Find duplicates by headline + datetime (same content, different IDs)
        content_duplicate_query = """
            SELECT headline, announcement_datetime, COUNT(*) as cnt
            FROM corporate_announcements
            WHERE headline IS NOT NULL 
              AND headline != '' 
              AND headline != '-'
              AND announcement_datetime IS NOT NULL
            GROUP BY headline, announcement_datetime
            HAVING COUNT(*) > 1
        """
        content_duplicates = conn.execute(content_duplicate_query).fetchall()
        content_duplicate_count = sum(row[2] - 1 for row in content_duplicates)
        print(f"Found {len(content_duplicates)} content duplicates by headline+datetime ({content_duplicate_count} extra copies)")
        
        # Find TRUE duplicates (same headline + symbol)
        true_duplicate_query = """
            SELECT headline, COALESCE(symbol_nse, symbol_bse, symbol) as sym, COUNT(*) as cnt
            FROM corporate_announcements
            WHERE headline IS NOT NULL AND headline != '' AND headline != '-'
            GROUP BY headline, COALESCE(symbol_nse, symbol_bse, symbol)
            HAVING COUNT(*) > 1
        """
        true_duplicates = conn.execute(true_duplicate_query).fetchall()
        true_duplicate_count = sum(row[2] - 1 for row in true_duplicates)
        print(f"Found {len(true_duplicates)} true duplicates by headline+symbol ({true_duplicate_count} extra copies)")
        
        total_to_remove = blank_count + duplicate_count + content_duplicate_count + true_duplicate_count
        
        if total_to_remove == 0:
            print("\n[OK] No cleanup needed - database is clean!")
            return
        
        print(f"\n[INFO] Starting cleanup (estimated {total_to_remove} rows to remove)...")
        
        # Delete blank entries
        if blank_count > 0:
            print(f"\nDeleting {blank_count} blank entries...")
            conn.execute("""
                DELETE FROM corporate_announcements
                WHERE (headline IS NULL OR headline = '' OR headline = '-' OR headline = 'null' OR headline = 'None')
                  AND (description IS NULL OR description = '' OR description = '-')
            """)
            print(f"[OK] Deleted blank entries")
        
        # Delete duplicates by announcement_id (keep the one with earliest received_at)
        if duplicate_count > 0:
            print(f"\nRemoving duplicates by announcement_id...")
            conn.execute("""
                DELETE FROM corporate_announcements
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM corporate_announcements
                    WHERE announcement_id IS NOT NULL AND announcement_id != ''
                    GROUP BY announcement_id
                )
                AND announcement_id IS NOT NULL AND announcement_id != ''
            """)
            print(f"[OK] Removed duplicates by announcement_id")
        
        # Delete content duplicates by headline + datetime (keep earliest received_at)
        if content_duplicate_count > 0:
            print(f"\nRemoving duplicates by headline+datetime...")
            conn.execute("""
                DELETE FROM corporate_announcements
                WHERE rowid NOT IN (
                    SELECT MIN(rowid)
                    FROM corporate_announcements
                    WHERE headline IS NOT NULL 
                      AND headline != '' 
                      AND headline != '-'
                      AND announcement_datetime IS NOT NULL
                    GROUP BY headline, announcement_datetime
                )
                AND headline IS NOT NULL 
                AND headline != '' 
                AND headline != '-'
                AND announcement_datetime IS NOT NULL
            """)
            print(f"[OK] Removed duplicates by headline+datetime")
        
        # Delete TRUE duplicates by headline + symbol (keep earliest received_at)
        # This is the most important one - same headline AND same symbol = true duplicate
        print(f"\nRemoving true duplicates by headline+symbol...")
        conn.execute("""
            DELETE FROM corporate_announcements
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM corporate_announcements
                WHERE headline IS NOT NULL 
                  AND headline != '' 
                  AND headline != '-'
                GROUP BY headline, COALESCE(symbol_nse, symbol_bse, symbol)
            )
            AND headline IS NOT NULL 
            AND headline != '' 
            AND headline != '-'
        """)
        print(f"[OK] Removed true duplicates by headline+symbol")
        
        # Commit all changes
        conn.commit()
        
        # Count after cleanup
        total_after = conn.execute("SELECT COUNT(*) FROM corporate_announcements").fetchone()[0]
        removed = total_before - total_after
        
        # Verify no more duplicates
        remaining_dups = conn.execute("""
            SELECT COUNT(*) FROM (
                SELECT headline, COALESCE(symbol_nse, symbol_bse, symbol) as sym, COUNT(*) as cnt
                FROM corporate_announcements
                WHERE headline IS NOT NULL AND headline != '' AND headline != '-'
                GROUP BY headline, COALESCE(symbol_nse, symbol_bse, symbol)
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]
        
        print(f"\n{'='*50}")
        print(f"[SUMMARY] Cleanup Complete:")
        print(f"  Before: {total_before} announcements")
        print(f"  After:  {total_after} announcements")
        print(f"  Removed: {removed} entries")
        print(f"  Remaining duplicates: {remaining_dups}")
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
