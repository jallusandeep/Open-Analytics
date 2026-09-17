def ensure_ai_schema(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS ai_connections (
            connection_id VARCHAR PRIMARY KEY,
            name VARCHAR NOT NULL,
            provider VARCHAR NOT NULL,
            model VARCHAR NOT NULL,
            encrypted_api_key VARCHAR NOT NULL,
            is_default BOOLEAN DEFAULT FALSE,
            connection_status VARCHAR DEFAULT 'saved',
            last_tested_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR
        )
    """)
