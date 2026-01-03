# Screener Scraping Flow Documentation

## Overview
The Screener scraper extracts company fundamentals, news, and corporate actions from Screener.in (or other configured sources) and stores them in a unified time-series database.

## 1. Symbol Source

### Where Symbols Come From
Symbols are retrieved from the **Symbols DuckDB database** (`symbols/symbols.duckdb`).

**Location:** `backend/app/services/screener_service.py` - `get_active_symbols()`

```python
def get_active_symbols(conn: duckdb.DuckDBPyConnection) -> List[Dict[str, str]]:
    """Get active symbols from Symbols database"""
    symbols_db_path = os.path.join(
        os.path.abspath(settings.DATA_DIR),
        "symbols",
        "symbols.duckdb"
    )
```

### Symbol Filtering Rules
**CRITICAL:** Only processes symbols where:
- `status = 'ACTIVE'`
- `instrument_type = 'EQ'` OR `instrument_type = 'CASH'`

**SQL Query:**
```sql
SELECT DISTINCT trading_symbol, exchange
FROM symbols_db.symbols
WHERE status = 'ACTIVE'
AND (instrument_type = 'EQ' OR instrument_type = 'CASH')
ORDER BY exchange, trading_symbol
```

**What Gets Excluded:**
- Derivatives (FUTURES, OPTIONS)
- Indices
- ETFs
- Inactive symbols
- Any non-cash instruments

## 2. Scraping Process Flow

### Step 1: Start Scraping
**Trigger:** User clicks "Start" button on a connection in `/admin/reference-data/screener/connections`

**API Endpoint:** `POST /api/v1/admin/screener/connections/{connection_id}/start`

**Location:** `backend/app/api/v1/screener.py` - `start_scraping()`

### Step 2: Background Processing
**Function:** `process_scraping_async()`

**Location:** `backend/app/api/v1/screener.py`

**Process:**
1. Creates a background thread
2. Gets database connection (with retry logic)
3. Retrieves active symbols using `get_active_symbols()`
4. Gets connection details (base_url, connection_type)
5. Loops through each symbol

### Step 3: Per-Symbol Scraping
**Function:** `scrape_symbol()`

**Location:** `backend/app/services/screener_service.py`

**For each symbol:**
1. **Check Stop Flag:** If user clicked "Stop", break loop
2. **Get Connection URL:** Uses `base_url` from connection, replaces `{symbol}` placeholder
3. **Scrape Fundamentals:** Calls `scrape_fundamentals()`
4. **Scrape News:** Calls `scrape_news()` (TODO - not implemented yet)
5. **Scrape Corporate Actions:** Calls `scrape_corporate_actions()` (TODO - not implemented yet)
6. **Insert Data:** Stores in unified `screener_data` table
7. **Update Progress:** Updates status cache for real-time UI updates

## 3. URL Construction

### Dynamic URL from Connection
The scraper uses the `base_url` stored in the `screener_connections` table.

**Default URL Pattern:**
```
https://www.screener.in/company/{symbol}/
```

**Example:**
- Symbol: `RELIANCE`
- URL: `https://www.screener.in/company/RELIANCE/`

**Custom URLs:**
- Users can configure custom URLs in the connection settings
- Must include `{symbol}` placeholder
- Example: `https://custom-site.com/stock/{symbol}/data`

**Code Location:** `backend/app/services/screener_service.py` - `scrape_fundamentals()`

```python
if base_url and base_url.strip():
    # Replace {symbol} placeholder with actual symbol
    url = base_url.strip().replace('{symbol}', symbol)
else:
    # Default fallback URL
    url = f"https://www.screener.in/company/{symbol}/"
```

## 4. Data Scraping Details

### Fundamentals Scraping
**Function:** `scrape_fundamentals()`

**What It Scrapes:**
- Market Cap (Cr)
- Current Price
- High / Low
- Stock P/E
- Book Value
- Dividend Yield %
- ROCE %
- ROE %
- Face Value

**How It Works:**
1. Fetches HTML from Screener.in URL
2. Parses text using regex patterns
3. Extracts numeric values
4. Stores as `SNAPSHOT` period type in `MARKET` statement group

**Data Storage:**
- **Entity Type:** `COMPANY`
- **Period Type:** `SNAPSHOT`
- **Period Key:** Current date (YYYY-MM-DD)
- **Statement Group:** `MARKET`
- **Source:** `screener.in`

### News Scraping
**Status:** TODO - Not implemented yet

**Planned Implementation:**
- URL: `https://www.screener.in/company/{symbol}/announcements/`
- Period Type: `EVENT`
- Statement Group: `NEWS`

### Corporate Actions Scraping
**Status:** TODO - Not implemented yet

**Planned Implementation:**
- Actions: Dividends, Bonus, Split, Buyback
- Period Type: `EVENT`
- Statement Group: `CORPORATE_ACTION`

## 5. Data Storage

### Database Structure
**Database:** DuckDB (`Company Fundamentals/screener.duckdb`)

**Main Table:** `screener_data`

**Schema:**
```sql
CREATE TABLE screener_data (
    id INTEGER PRIMARY KEY,
    entity_type VARCHAR NOT NULL,           -- COMPANY, PEER, etc.
    parent_company_symbol VARCHAR,          -- For peer comparisons
    symbol VARCHAR NOT NULL,                 -- Trading symbol
    exchange VARCHAR NOT NULL,               -- NSE, BSE, etc.
    period_type VARCHAR NOT NULL,           -- ANNUAL, SNAPSHOT, EVENT
    period_key VARCHAR NOT NULL,            -- Date or period identifier
    statement_group VARCHAR NOT NULL,       -- MARKET, PROFIT_LOSS, etc.
    metric_name VARCHAR NOT NULL,           -- e.g., "Market Cap (Cr)"
    metric_value DOUBLE,                    -- Numeric value
    unit VARCHAR,                           -- ₹, %, etc.
    consolidated_flag VARCHAR DEFAULT 'CONSOLIDATED',
    source VARCHAR DEFAULT 'screener.in',
    captured_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    metadata TEXT
)
```

### Indexes
- `idx_symbol_period` - For queries by symbol and period
- `idx_statement_group` - For queries by statement group
- `idx_entity_type` - For peer comparison queries

## 6. Error Handling

### Stop Mechanism
- User can click "Stop" button during scraping
- Sets stop flag in `_stop_flags` dictionary
- Loop checks flag before/after each symbol
- Gracefully stops after current symbol completes

### Error Handling
- Individual symbol failures don't stop the entire job
- Errors are logged and collected
- Failed symbols are counted separately
- Job continues with remaining symbols

### Retry Logic
- Database connection retries 3 times with exponential backoff
- Individual symbol failures are logged but don't retry
- Network timeouts: 15 seconds per request

## 7. Progress Tracking

### Real-Time Status
**Cache:** `_scraping_status_cache` (in-memory dictionary)

**Status Fields:**
- `status`: PROCESSING, COMPLETED, FAILED, STOPPED
- `total_symbols`: Total symbols to process
- `symbols_processed`: How many processed so far
- `symbols_succeeded`: Successfully scraped
- `symbols_failed`: Failed to scrape
- `total_records_inserted`: Total data records saved
- `percentage`: Progress percentage
- `errors`: List of error messages (max 10)

**API Endpoint:** `GET /api/v1/admin/screener/scrape/status/{job_id}`

## 8. Connection Configuration

### Connection Types
1. **WEBSITE_SCRAPING** (Implemented)
   - Scrapes from web pages
   - Uses `base_url` with `{symbol}` placeholder
   - Default: Screener.in

2. **API_CONNECTION** (Not Implemented Yet)
   - Would connect to APIs
   - Would use authentication (Key/Token)
   - Configuration stored but execution not implemented

### Default Connection
- Created automatically on startup if none exists
- Name: "Screener.in Default"
- Type: WEBSITE_SCRAPING
- URL: `https://www.screener.in/company/{symbol}/`

## 9. Example Flow

### Complete Example: Scraping RELIANCE

1. **User Action:** Click "Start" on "Screener.in Default" connection

2. **Backend:**
   - Creates job_id: `screener_abc123...`
   - Starts background thread
   - Gets connection: `base_url = "https://www.screener.in/company/{symbol}/"`

3. **Get Symbols:**
   - Queries: `SELECT trading_symbol, exchange FROM symbols WHERE status='ACTIVE' AND instrument_type IN ('EQ','CASH')`
   - Returns: `[{"symbol": "RELIANCE", "exchange": "NSE"}, ...]`
   - Total: 5000 symbols (example)

4. **Process RELIANCE:**
   - URL: `https://www.screener.in/company/RELIANCE/`
   - Fetch HTML
   - Parse: Market Cap = ₹15,00,000 Cr, P/E = 25.5, etc.
   - Insert 9 records into `screener_data` table

5. **Continue:**
   - Process next symbol
   - Update progress: 1/5000 = 0.02%
   - Repeat for all symbols

6. **Complete:**
   - Status: COMPLETED
   - Records: 45,000 (9 metrics × 5000 symbols)
   - Update connection: status = "Completed", records_loaded = 45000

## 10. Current Limitations

### Not Implemented Yet:
- ❌ News scraping
- ❌ Corporate actions scraping
- ❌ Financial statements (Profit & Loss, Balance Sheet, Cash Flow)
- ❌ Ratios scraping
- ❌ Peer comparison scraping
- ❌ API connection execution

### Implemented:
- ✅ Fundamentals header data (Market Cap, P/E, etc.)
- ✅ Symbol filtering (CASH/EQ only)
- ✅ Dynamic URL from connections
- ✅ Stop mechanism
- ✅ Progress tracking
- ✅ Error handling
- ✅ Unified data storage

## 11. Files Involved

### Backend:
- `backend/app/services/screener_service.py` - Core scraping logic
- `backend/app/api/v1/screener.py` - API endpoints and background processing
- `backend/app/main.py` - Startup initialization

### Frontend:
- `frontend/app/(main)/admin/reference-data/screener/connections/page.tsx` - UI
- `frontend/lib/api.ts` - API client functions

### Database:
- `data/Company Fundamentals/screener.duckdb` - Screener data
- `data/symbols/symbols.duckdb` - Symbols source

