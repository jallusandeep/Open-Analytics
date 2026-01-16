import logging
import os
from typing import Optional
from .config import SCORING_DB_PATH, SCORING_TABLE, AI_DB_PATH, AI_TABLE, FINAL_TABLE
from app.services.shared_db import get_shared_db
from app.core.websocket_manager import manager

logger = logging.getLogger(__name__)

def get_db():
    return get_shared_db()

def ensure_schema():
    """Ensure news_ai and ai_queue tables exist and handle migrations."""
    db = get_db()
    try:
        # Main Enriched Table
        query_ai = f"""
        CREATE TABLE IF NOT EXISTS {AI_TABLE} (
            news_id BIGINT PRIMARY KEY,
            received_date TIMESTAMP,
            category_code TEXT,
            sub_type_code TEXT,
            company_name TEXT,
            ticker TEXT,
            exchange TEXT,
            country_code TEXT,
            headline TEXT,
            summary TEXT,
            sentiment TEXT,
            language_code TEXT,
            url TEXT,
            impact_score INTEGER DEFAULT 0,
            latency_ms INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ai_model TEXT,
            ai_config_id INTEGER
        );
        """
        db.run_ai_query(query_ai)

        # Queue Table for state management
        query_queue = """
        CREATE TABLE IF NOT EXISTS ai_queue (
            news_id BIGINT PRIMARY KEY,
            status TEXT DEFAULT 'PENDING',
            retries INTEGER DEFAULT 0,
            error_log TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.run_ai_query(query_queue)
        
        # Final Table for curated data
        query_final = f"""
        CREATE TABLE IF NOT EXISTS {FINAL_TABLE} (
            news_id BIGINT PRIMARY KEY,
            received_date TIMESTAMP,
            headline TEXT,
            summary TEXT,
            company_name TEXT,
            ticker TEXT,
            exchange TEXT,
            country_code TEXT,
            sentiment TEXT,
            url TEXT,
            impact_score INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.run_final_query(query_final)
        
        # System Settings Table
        query_settings = """
        CREATE TABLE IF NOT EXISTS system_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        db.run_final_query(query_settings)
        
        # Initialize default news_sync status if not exists
        db.run_final_query("INSERT OR IGNORE INTO system_settings (key, value) VALUES ('news_sync_enabled', 'true')")

        # Migration: Check for missing columns in news_ai
        cols = db.run_ai_query(f"PRAGMA table_info({AI_TABLE})", fetch='all')
        existing_cols = [c[1] for c in cols]
        
        if 'impact_score' not in existing_cols:
            logger.info("Adding impact_score column to news_ai")
            db.run_ai_query(f"ALTER TABLE {AI_TABLE} ADD COLUMN impact_score INTEGER DEFAULT 0")
            
        if 'latency_ms' not in existing_cols:
            logger.info("Adding latency_ms column to news_ai")
            db.run_ai_query(f"ALTER TABLE {AI_TABLE} ADD COLUMN latency_ms INTEGER DEFAULT 0")

    except Exception as e:
        logger.error(f"AI Schema Error during migration: {e}")
        raise

def sync_queue():
    """Sync missing scores from news_scoring to ai_queue."""
    db = get_db()
    try:
        # 1. Get IDs already in news_ai or ai_queue to avoid duplicates
        existing_ids = db.run_ai_query(f"SELECT news_id FROM {AI_TABLE} UNION SELECT news_id FROM ai_queue", fetch='all')
        existing_ids_list = [row[0] for row in existing_ids]

        where_clause = ""
        if existing_ids_list:
            ids_str = ",".join(map(str, existing_ids_list))
            where_clause = f"WHERE score_id NOT IN ({ids_str})"

        # 2. Fetch new scores from scoring DB
        scoring_query = f"SELECT score_id FROM {SCORING_TABLE} {where_clause} ORDER BY scored_at ASC LIMIT 100"
        new_scores = db.run_scoring_query(scoring_query, fetch='all')

        if new_scores:
            for row in new_scores:
                db.run_ai_query("INSERT OR IGNORE INTO ai_queue (news_id) VALUES (?)", [row[0]])
            logger.info(f"Synced {len(new_scores)} items to AI queue.")
    except Exception as e:
        logger.error(f"Error syncing AI queue: {e}")

def get_eligible_news(limit=1):
    """
    Fetch news from ai_queue that are PENDING.
    Marks them as PROCESSING immediately.
    """
    db = get_db()
    sync_queue()
    
    try:
        # 1. Fetch next PENDING item
        query = "SELECT news_id FROM ai_queue WHERE status = 'PENDING' ORDER BY created_at ASC LIMIT ?"
        pending_items = db.run_ai_query(query, [limit], fetch='all')
        
        if not pending_items:
            return []

        results = []
        for (news_id,) in pending_items:
            # Mark as PROCESSING
            db.run_ai_query("UPDATE ai_queue SET status = 'PROCESSING', updated_at = CURRENT_TIMESTAMP WHERE news_id = ?", [news_id])
            
            # Get the text from raw DB
            # We need raw_id from scoring_db first
            scoring_row = db.run_scoring_query(f"SELECT raw_id FROM {SCORING_TABLE} WHERE score_id = ?", [news_id], fetch='one')
            if not scoring_row:
                continue
            
            raw_id = scoring_row[0]
            raw_row = db.run_raw_query("SELECT combined_text, received_at, source_url FROM telegram_raw WHERE raw_id = ?", [raw_id], fetch='one')
            
            if raw_row:
                results.append((news_id, raw_row[1], raw_row[0], raw_row[2]))
            
        return results
        
    except Exception as e:
        if "does not exist" in str(e).lower():
            return []
        logger.error(f"Error fetching eligible news from queue: {e}")
        return []

def mark_failed(news_id, error_msg):
    """Mark a news item as failed in the queue."""
    db = get_db()
    try:
        db.run_ai_query("""
            UPDATE ai_queue 
            SET status = 'FAILED', 
                retries = retries + 1,
                error_log = ?,
                updated_at = CURRENT_TIMESTAMP 
            WHERE news_id = ?
        """, [error_msg, news_id])
    except Exception as e:
        logger.error(f"Failed to mark news {news_id} as failed: {e}")

def insert_enriched_news(news_id, received_date, ai_data, ai_model, ai_config_id, latency_ms=0, original_url=None):
    """Save AI enriched news to DB and mark queue as COMPLETED."""
    db = get_db()
    try:
        query = f"""
        INSERT INTO {AI_TABLE} (
            news_id, received_date, category_code, sub_type_code, company_name,
            ticker, exchange, country_code, headline, summary, sentiment,
            language_code, url, ai_model, ai_config_id, impact_score, latency_ms
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        impact_score = ai_data.get('impact_score', 0)
        # Handle cases where impact_score might be a string
        try:
            impact_score = int(impact_score)
        except:
            impact_score = 0

        # Use original URL if available, otherwise get from AI data
        url = original_url if original_url else ai_data.get('url', '')

        db.run_ai_query(query, [
            news_id,
            received_date,
            ai_data.get('category_code', ''),
            ai_data.get('sub_type_code', ''),
            ai_data.get('company_name', ''),
            ai_data.get('ticker', ''),
            ai_data.get('exchange', ''),
            ai_data.get('country_code', ''),
            ai_data.get('headline', ''),
            ai_data.get('summary', ''),
            ai_data.get('sentiment', ''),
            ai_data.get('language_code', ''),
            url,
            ai_model,
            ai_config_id,
            impact_score,
            latency_ms
        ])
        
        # Mark as COMPLETED
        db.run_ai_query("UPDATE ai_queue SET status = 'COMPLETED', updated_at = CURRENT_TIMESTAMP WHERE news_id = ?", [news_id])
        
        # 3. Sync to Final Database
        try:
            final_query = f"""
            INSERT INTO {FINAL_TABLE} (
                news_id, received_date, headline, summary, company_name,
                ticker, exchange, country_code, sentiment, url, impact_score
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """
            db.run_final_query(final_query, [
                news_id,
                received_date,
                ai_data.get('headline', ''),
                ai_data.get('summary', ''),
                ai_data.get('company_name', ''),
                ai_data.get('ticker', ''),
                ai_data.get('exchange', ''),
                ai_data.get('country_code', ''),
                ai_data.get('sentiment', ''),
                url,
                impact_score
            ])
            logger.info(f"Successfully synced news {news_id} to final database.")
            
            # 4. Broadcast to frontend
            try:
                broadcast_data = {
                    "news_id": news_id,
                    "received_date": received_date.isoformat() if hasattr(received_date, 'isoformat') else str(received_date),
                    "headline": ai_data.get('headline', ''),
                    "summary": ai_data.get('summary', ''),
                    "company_name": ai_data.get('company_name', ''),
                    "ticker": ai_data.get('ticker', ''),
                    "exchange": ai_data.get('exchange', ''),
                    "country_code": ai_data.get('country_code', ''),
                    "sentiment": ai_data.get('sentiment', ''),
                    "url": url,
                    "impact_score": impact_score
                }
                manager.broadcast_news_sync(broadcast_data)
            except Exception as broadcast_err:
                logger.warning(f"Failed to broadcast news {news_id}: {broadcast_err}")
                
        except Exception as final_err:
            logger.error(f"Failed to sync news {news_id} to final database: {final_err}")
            # We don't raise here to avoid failing the main process if only the sync fails
        
    except Exception as e:
        logger.error(f"Failed to insert enriched news {news_id}: {e}")
        # Mark as FAILED in queue
        mark_failed(news_id, str(e))
        raise

def get_recent_enrichments(limit=50):
    """Fetch recent AI enriched news formatted for the frontend table."""
    try:
        ensure_schema()
    except:
        pass

    db = get_db()
    try:
        query = f"""
            SELECT 
                news_id, created_at, headline, category_code, sentiment, 
                impact_score, ai_model, latency_ms, summary, url
            FROM {AI_TABLE}
            ORDER BY created_at DESC
            LIMIT ?
        """
        rows = db.run_ai_query(query, [limit], fetch='all')
        
        result = []
        for row in rows:
            result.append({
                "final_id": row[0],
                "processed_at": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else None,
                "headline": row[2],
                "category": row[3],
                "sentiment": row[4],
                "impact_score": row[5],
                "ai_model": row[6],
                "latency": row[7],
                "summary": row[8],
                "url": row[9]
            })
        return result
    except Exception as e:
        logger.error(f"Error fetching recent enrichments: {e}")
        return []

def get_final_news(limit=20, offset=0, search: Optional[str] = None):
    """Fetch AI-enriched news from final database with pagination and fuzzy search."""
    db = get_shared_db()
    try:
        where_clause = ""
        params = []
        
        if search and search.strip():
            tokens = search.strip().split()
            where_parts = []
            for token in tokens:
                pattern = f"%{token}%"
                # Substring match (ILIKE) + Fuzzy match (jaro_winkler) for better relevance
                where_parts.append("""
                    (headline ILIKE ? 
                    OR summary ILIKE ? 
                    OR ticker ILIKE ? 
                    OR company_name ILIKE ?
                    OR jaro_winkler_similarity(lower(ticker), lower(?)) > 0.8
                    OR jaro_winkler_similarity(lower(company_name), lower(?)) > 0.8)
                """)
                params.extend([pattern, pattern, pattern, pattern, token.lower(), token.lower()])
            where_clause = "WHERE " + " AND ".join(where_parts)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM {FINAL_TABLE} {where_clause}"
        total_count = db.run_final_query(count_query, params, fetch='one')[0]
        
        # Get paginated data
        data_params = params + [limit, offset]
        query = f"""
            SELECT 
                news_id, received_date, headline, summary, company_name,
                ticker, exchange, country_code, sentiment, url, impact_score, created_at
            FROM {FINAL_TABLE}
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = db.run_final_query(query, data_params, fetch='all')
        
        result = []
        for row in rows:
            result.append({
                "news_id": row[0],
                "received_date": row[1].strftime("%Y-%m-%d %H:%M:%S") if row[1] else None,
                "headline": row[2],
                "summary": row[3],
                "company_name": row[4],
                "ticker": row[5],
                "exchange": row[6],
                "country_code": row[7],
                "sentiment": row[8],
                "url": row[9],
                "impact_score": row[10],
                "created_at": row[11].strftime("%Y-%m-%d %H:%M:%S") if row[11] else None
            })
        return result, total_count
    except Exception as e:
        logger.error(f"Error fetching final news with pagination: {e}")
        return [], 0
def get_system_setting(key, default=None):
    """Retrieve a system setting."""
    db = get_db()
    try:
        res = db.run_final_query("SELECT value FROM system_settings WHERE key = ?", [key], fetch='one')
        return res[0] if res else default
    except Exception as e:
        logger.error(f"Error getting setting {key}: {e}")
        return default

def set_system_setting(key, value):
    """Update a system setting."""
    db = get_db()
    try:
        db.run_final_query(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            [key, str(value).lower()]
        )
        return True
    except Exception as e:
        logger.error(f"Error setting {key}: {e}")
        return False
