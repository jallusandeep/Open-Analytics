"""Schema creation for one part of the existing DuckDB database."""


def ensure_ipo_scraper_schema(conn, safe_execute):
    # -----------------------------
    # IPO Watch GMP scraper
    # Stores IPO grey market premium scraper data from IPO Watch.
    # Source:
    #   https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/
    # Only required UI columns are stored separately.
    # -----------------------------
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_gmp_scraper (
            ipo_name VARCHAR PRIMARY KEY,
            ipo_gmp VARCHAR,
            price_band VARCHAR,
            ipo_date VARCHAR,
            ipo_type VARCHAR,
            ipo_status VARCHAR,
            last_updated VARCHAR,
            source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
            raw_json JSON,
            source_sync_id VARCHAR,
            data_hash VARCHAR,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_gmp VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN price_band VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_date VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN ipo_status VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN last_updated VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN data_hash VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS ipo_gmp_scraper_snapshots (
            snapshot_id VARCHAR PRIMARY KEY,
            source_sync_id VARCHAR NOT NULL,
            ipo_name VARCHAR NOT NULL,
            ipo_gmp VARCHAR,
            price_band VARCHAR,
            ipo_date VARCHAR,
            ipo_type VARCHAR,
            ipo_status VARCHAR,
            last_updated VARCHAR,
            source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/',
            raw_json JSON,
            data_hash VARCHAR,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN snapshot_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_sync_id VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_name VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_gmp VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN price_band VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_date VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_type VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN ipo_status VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN last_updated VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN source_url VARCHAR DEFAULT 'https://ipowatch.in/ipo-grey-market-premium-latest-ipo-gmp/';")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN raw_json JSON;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN data_hash VARCHAR;")
    safe_execute(conn, "ALTER TABLE ipo_gmp_scraper_snapshots ADD COLUMN scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;")

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_status
        ON ipo_gmp_scraper (ipo_status);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_updated
        ON ipo_gmp_scraper (updated_at);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_ipo_name
        ON ipo_gmp_scraper_snapshots (ipo_name);
    """)

    safe_execute(conn, """
        CREATE INDEX IF NOT EXISTS idx_ipo_gmp_scraper_snapshots_sync
        ON ipo_gmp_scraper_snapshots (source_sync_id);
    """)
