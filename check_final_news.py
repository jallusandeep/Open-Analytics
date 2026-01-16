import duckdb
import os

db_path = 'data/News/Final/final_news.duckdb'
if os.path.exists(db_path):
    try:
        # Open in read-only mode to avoid locking issues
        conn = duckdb.connect(db_path, read_only=True)
        print(f"Checking table final_news in {db_path}...")
        
        # Check columns
        cols = conn.execute("PRAGMA table_info('final_news')").fetchall()
        print("\nColumns:")
        for col in cols:
            print(f"- {col[1]} ({col[2]})")
            
        # Check sample data for URL
        rows = conn.execute("SELECT news_id, ticker, company_name, url FROM final_news LIMIT 10").fetchall()
        print("\nSample Data (First 10):")
        for row in rows:
            print(f"ID: {row[0]} | Ticker: {row[1]} | Co: {row[2]} | URL: {row[3]}")
            
        # Count items with and without URL
        total = conn.execute("SELECT COUNT(*) FROM final_news").fetchone()[0]
        with_url = conn.execute("SELECT COUNT(*) FROM final_news WHERE url IS NOT NULL AND url != ''").fetchone()[0]
        print(f"\nStats: Total={total}, With URL={with_url}")
        
    except Exception as e:
        print(f"Error checking DB: {e}")
else:
    print(f"DB not found at {db_path}")
