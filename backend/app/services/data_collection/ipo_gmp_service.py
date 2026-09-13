"""IPO Watch GMP scraping, status updates, and preview."""

from .common import *
from .news_ipo_service import ensure_upstox_news_ipo_tables


def normalize_ipo_gmp_value(value: Any) -> str:
    if value is None:
        return ""

    clean_value = str(value).strip()

    if clean_value.lower() in ("nan", "none", "null"):
        return ""

    return clean_value


def parse_ipo_gmp_date_range(value: Any, reference_date: Optional[date] = None) -> Optional[dict]:
    clean_value = normalize_ipo_gmp_value(value)

    if not clean_value:
        return None

    normalized = re.sub(r"\s+", " ", clean_value.replace("–", "-").replace("—", "-")).strip()
    reference_date = reference_date or date.today()
    current_year = reference_date.year

    def inferred_year(month: int) -> int:
        if reference_date.month >= 11 and month <= 2:
            return current_year + 1
        if reference_date.month <= 2 and month >= 11:
            return current_year - 1
        return current_year

    match = re.search(
        r"(?P<start_day>\d{1,2})\s*-\s*(?P<end_day>\d{1,2})\s+"
        r"(?P<month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            month = datetime.strptime(match.group("month")[:3], "%b").month
            year = int(match.group("year")) if match.group("year") else inferred_year(month)
            return {
                "start_date": date(year, month, int(match.group("start_day"))),
                "end_date": date(year, month, int(match.group("end_day")))
            }
        except Exception:
            return None

    match = re.search(
        r"(?P<start_day>\d{1,2})\s+"
        r"(?P<start_month>[A-Za-z]{3,9})\s*-\s*"
        r"(?P<end_day>\d{1,2})\s+"
        r"(?P<end_month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            start_month = datetime.strptime(match.group("start_month")[:3], "%b").month
            end_month = datetime.strptime(match.group("end_month")[:3], "%b").month
            start_year = int(match.group("year")) if match.group("year") else inferred_year(start_month)
            end_year = start_year + 1 if end_month < start_month else start_year
            return {
                "start_date": date(start_year, start_month, int(match.group("start_day"))),
                "end_date": date(end_year, end_month, int(match.group("end_day")))
            }
        except Exception:
            return None

    match = re.search(
        r"(?P<day>\d{1,2})\s+(?P<month>[A-Za-z]{3,9})(?:\s+(?P<year>\d{4}))?",
        normalized
    )

    if match:
        try:
            month = datetime.strptime(match.group("month")[:3], "%b").month
            year = int(match.group("year")) if match.group("year") else inferred_year(month)
            parsed_date = date(year, month, int(match.group("day")))
            return {
                "start_date": parsed_date,
                "end_date": parsed_date
            }
        except Exception:
            return None

    return None


def derive_ipo_gmp_status(ipo_date: Any, current_status: Any = None, reference_date: Optional[date] = None) -> str:
    status_value = normalize_ipo_gmp_value(current_status)
    parsed_range = parse_ipo_gmp_date_range(ipo_date, reference_date)

    if not parsed_range:
        return status_value

    today = date.today()

    if today < parsed_range["start_date"]:
        return "Upcoming"

    if parsed_range["start_date"] <= today <= parsed_range["end_date"]:
        return "Open"

    if today > parsed_range["end_date"]:
        return "Closed"

    return status_value


def parse_ipo_gmp_number(value: Any) -> Optional[float]:
    clean_value = normalize_ipo_gmp_value(value)

    if not clean_value:
        return None

    normalized_value = (
        clean_value
        .replace(",", "")
        .replace("₹", "")
        .replace("Rs.", "")
        .replace("Rs", "")
        .replace("INR", "")
        .strip()
    )
    matches = re.findall(r"-?\d+(?:\.\d+)?", normalized_value)

    if not matches:
        return None

    try:
        values = [float(match) for match in matches]
    except ValueError:
        return None

    return max(values) if values else None


def format_ipo_gmp_money(value: float) -> str:
    if value == int(value):
        return f"₹{int(value)}"

    return f"₹{value:.2f}"


def calculate_ipo_gmp_gain(ipo_gmp: Any, price_band: Any) -> Optional[str]:
    gmp_value = parse_ipo_gmp_number(ipo_gmp)
    price_band_value = parse_ipo_gmp_number(price_band)

    if gmp_value is None or price_band_value in (None, 0):
        return None

    estimated_listing = price_band_value + gmp_value
    gain_percent = (gmp_value / price_band_value) * 100

    return f"{format_ipo_gmp_money(estimated_listing)} ({gain_percent:.2f}%)"


def normalize_ipo_gmp_column_name(column: Any) -> str:
    if isinstance(column, tuple):
        column_parts = [
            str(part).strip()
            for part in column
            if str(part).strip()
            and not str(part).strip().lower().startswith("unnamed:")
        ]
        column_name = column_parts[-1] if column_parts else str(column).strip()
    else:
        column_name = str(column).strip()

    if column_name.rstrip("*").strip().lower() == "ipo gmp":
        return "IPO GMP"

    return column_name


def combine_ipo_gmp_tables(tables: List[Any]):
    matching_tables = []
    discovered_columns = []
    required_source_columns = {
        "IPO Name",
        "IPO GMP",
        "Price Band",
        "Date",
        "Status",
        "Last Updated"
    }

    for df in tables:
        normalized_table = df.copy()
        normalized_table.columns = [
            normalize_ipo_gmp_column_name(column)
            for column in normalized_table.columns
        ]

        if not normalized_table.empty:
            first_row_columns = [
                normalize_ipo_gmp_column_name(normalize_ipo_gmp_value(value))
                for value in normalized_table.iloc[0].tolist()
            ]

            if "IPO Name" in first_row_columns and "IPO GMP" in first_row_columns:
                normalized_table = normalized_table.iloc[1:].copy()
                normalized_table.columns = first_row_columns

        discovered_columns.append(list(normalized_table.columns))

        if not required_source_columns.issubset(set(normalized_table.columns)):
            continue

        if "Type" not in normalized_table.columns:
            normalized_table["Type"] = (
                "Mainboard" if not matching_tables else "SME"
            )

        matching_tables.append(normalized_table)

    if not matching_tables:
        raise ValueError(
            "Target IPO GMP tables were not found. "
            f"Discovered columns: {discovered_columns}"
        )

    return pd.concat(matching_tables, ignore_index=True)


def find_ipo_gmp_table_from_html(url: str):
    return combine_ipo_gmp_tables(pd.read_html(url))


def first_existing_path(paths: List[str]) -> Optional[str]:
    for path in paths:
        clean_path = safe_strip(path)

        if clean_path and Path(clean_path).exists():
            return clean_path

    return None


def find_ipo_gmp_table_with_selenium(url: str):
    import os
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.service import Service
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "pandas.read_html failed and Selenium is not installed. "
                "Install selenium and ChromeDriver support, or fix read_html dependencies."
            )
        )

    options = webdriver.ChromeOptions()

    chrome_binary = first_existing_path(
        [
            os.environ.get("CHROME_BIN"),
            "/usr/bin/chromium",
            "/usr/bin/google-chrome",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
        ]
    )

    if chrome_binary:
        options.binary_location = chrome_binary

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-background-networking")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--window-size=1920,1080")

    chromedriver_path = first_existing_path(
        [
            os.environ.get("CHROMEDRIVER_PATH"),
            "/usr/bin/chromedriver"
        ]
    )
    service = Service(executable_path=chromedriver_path) if chromedriver_path else Service()

    driver = None

    try:
        driver = webdriver.Chrome(
            service=service,
            options=options,
        )

        wait = WebDriverWait(driver, 25)

        driver.get(url)

        wait.until(
            EC.presence_of_all_elements_located(
                (By.TAG_NAME, "table")
            )
        )

        time.sleep(2)

        tables = driver.find_elements(By.TAG_NAME, "table")

        html_tables = []

        for table in tables:
            table_text = table.text.strip()

            if (
                "IPO Name" in table_text
                and "IPO GMP" in table_text
                and "Price Band" in table_text
                and "Last Updated" in table_text
            ):
                html_tables.append(table.get_attribute("outerHTML"))

        if not html_tables:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Target IPO GMP tables were not found with Selenium.",
            )

        parsed_tables = [
            pd.read_html(StringIO(html_table))[0]
            for html_table in html_tables
        ]

        return combine_ipo_gmp_tables(parsed_tables)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                f"Selenium failed using "
                f"Chrome='{chrome_binary or 'auto'}', "
                f"ChromeDriver='{chromedriver_path or 'Selenium Manager'}'. "
                f"Error: {exc}"
            ),
        )

    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass


def get_ipo_gmp_dataframe(url: str = IPO_GMP_SCRAPER_URL):
    try:
        return find_ipo_gmp_table_from_html(url)
    except Exception as error:
        print("IPO GMP read_html failed, trying Selenium fallback.")
        print(f"Reason: {error}")

    return find_ipo_gmp_table_with_selenium(url)


def normalize_ipo_gmp_dataframe(df):
    normalized_df = df.copy()
    normalized_df.columns = [
        normalize_ipo_gmp_column_name(column)
        for column in normalized_df.columns
    ]

    if (
        not set(IPO_GMP_SCRAPER_REQUIRED_COLUMNS).issubset(set(normalized_df.columns))
        and not normalized_df.empty
    ):
        first_row_values = [
            normalize_ipo_gmp_value(value)
            for value in normalized_df.iloc[0].tolist()
        ]

        if "IPO Name" in first_row_values and "IPO GMP" in first_row_values:
            normalized_df = normalized_df.iloc[1:].copy()
            normalized_df.columns = first_row_values

    normalized_df.columns = [
        normalize_ipo_gmp_column_name(column)
        for column in normalized_df.columns
    ]
    return normalized_df.reset_index(drop=True)


def normalize_ipo_gmp_record(row: dict, source_url: str) -> Optional[dict]:
    ipo_name = normalize_ipo_gmp_value(row.get("IPO Name"))

    if not ipo_name:
        return None

    raw_record = {
        key: normalize_ipo_gmp_value(value)
        for key, value in row.items()
    }

    return {
        "ipo_name": ipo_name,
        "ipo_gmp": normalize_ipo_gmp_value(row.get("IPO GMP")),
        "price_band": normalize_ipo_gmp_value(row.get("Price Band")),
        "ipo_date": normalize_ipo_gmp_value(row.get("Date")),
        "ipo_type": normalize_ipo_gmp_value(row.get("Type")),
        "ipo_status": derive_ipo_gmp_status(row.get("Date"), row.get("Status")),
        "last_updated": normalize_ipo_gmp_value(row.get("Last Updated")),
        "source_url": source_url,
        "raw_json": json_dumps_for_db(raw_record)
    }


def get_ipo_gmp_record_hash(record: dict) -> str:
    comparable_record = {
        key: record.get(key) or ""
        for key in (
            "ipo_name",
            "ipo_gmp",
            "price_band",
            "ipo_date",
            "ipo_type",
            "ipo_status",
            "last_updated"
        )
    }

    payload = json.dumps(
        comparable_record,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":")
    )

    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def scrape_ipo_gmp_records(source_url: str = IPO_GMP_SCRAPER_URL) -> List[dict]:
    df = normalize_ipo_gmp_dataframe(get_ipo_gmp_dataframe(source_url))

    missing_columns = [
        column
        for column in IPO_GMP_SCRAPER_REQUIRED_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "IPO GMP scraper table is missing required columns: "
                + ", ".join(missing_columns)
            )
        )

    records = []

    for row in df.to_dict(orient="records"):
        record = normalize_ipo_gmp_record(row, source_url)

        if record:
            records.append(record)

    return list({
        record["ipo_name"].lower(): record
        for record in records
        if record.get("ipo_name")
    }.values())


def insert_ipo_gmp_scraper_records(
    conn,
    records: List[dict],
    source_sync_id: str
) -> int:
    rows = list({
        safe_strip(record.get("ipo_name")).lower(): record
        for record in records
        if safe_strip(record.get("ipo_name"))
    }.values())

    if not rows:
        return 0

    for row in rows:
        row["data_hash"] = get_ipo_gmp_record_hash(row)

    conn.executemany("""
        INSERT OR REPLACE INTO ipo_gmp_scraper (
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            source_sync_id,
            data_hash,
            scraped_at,
            updated_at
        )
        SELECT
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            TRY_CAST(? AS JSON),
            ?,
            ?,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP;
    """, [
        (
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            source_sync_id,
            row.get("data_hash")
        )
        for row in rows
    ])

    conn.executemany("""
        INSERT INTO ipo_gmp_scraper_snapshots (
            snapshot_id,
            source_sync_id,
            ipo_name,
            ipo_gmp,
            price_band,
            ipo_date,
            ipo_type,
            ipo_status,
            last_updated,
            source_url,
            raw_json,
            data_hash,
            scraped_at
        )
        SELECT
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            ?,
            TRY_CAST(? AS JSON),
            ?,
            CURRENT_TIMESTAMP;
    """, [
        (
            str(uuid.uuid4()),
            source_sync_id,
            row.get("ipo_name"),
            row.get("ipo_gmp"),
            row.get("price_band"),
            row.get("ipo_date"),
            row.get("ipo_type"),
            row.get("ipo_status"),
            row.get("last_updated"),
            row.get("source_url"),
            row.get("raw_json"),
            row.get("data_hash")
        )
        for row in rows
    ])

    return len(rows)


def refresh_ipo_gmp_statuses(conn):
    rows = conn.execute("""
        SELECT ipo_name, ipo_date, ipo_status, scraped_at
        FROM ipo_gmp_scraper;
    """).fetchall()

    updates = []

    for row in rows:
        scraped_at = row[3]
        reference_date = scraped_at.date() if isinstance(scraped_at, datetime) else None
        next_status = derive_ipo_gmp_status(row[1], row[2], reference_date)

        if next_status and next_status.lower() != normalize_ipo_gmp_value(row[2]).lower():
            updates.append((next_status, row[0]))

    if not updates:
        return 0

    conn.executemany("""
        UPDATE ipo_gmp_scraper
        SET ipo_status = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE ipo_name = ?;
    """, updates)

    return len(updates)


def sync_ipo_gmp_scraper_service(
    current_user: dict,
    config: Optional[dict] = None,
    clear_cancel_at_start: bool = True
):
    conn = get_connection()
    started_at = datetime.now()
    sync_id = None
    total_records = 0

    try:
        if clear_cancel_at_start:
            clear_cancel_signal()

        ensure_no_active_sync_run(conn)
        ensure_upstox_news_ipo_tables(conn)

        payload = config or {}
        source_url = safe_strip(payload.get("source_url")) or IPO_GMP_SCRAPER_URL

        sync_id = create_sync_run(
            conn,
            IPO_GMP_SCRAPER_SYNC_TYPE,
            "running",
            "IPO GMP scraper started.",
            current_user=current_user
        )

        check_sync_cancelled(conn, sync_id)

        records = scrape_ipo_gmp_records(source_url=source_url)

        check_sync_cancelled(conn, sync_id)

        conn.execute("BEGIN TRANSACTION")
        total_records = insert_ipo_gmp_scraper_records(
            conn,
            records,
            sync_id
        )
        refresh_ipo_gmp_statuses(conn)
        conn.execute("COMMIT")

        finish_sync_run(
            conn,
            sync_id,
            "success",
            "IPO GMP scraper completed successfully.",
            total_records,
            started_at
        )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "success",
            "message": "IPO GMP scraper completed successfully.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except SyncCancelled:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "cancelled",
                "IPO GMP scraper cancelled.",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        return {
            "status": "cancelled",
            "message": "IPO GMP scraper cancelled.",
            "total_records": total_records,
            "duration_seconds": duration_seconds(started_at)
        }

    except HTTPException as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"IPO GMP scraper failed: {error.detail}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise

    except Exception as error:
        try:
            conn.rollback()
        except Exception:
            pass

        if sync_id:
            finish_sync_run(
                conn,
                sync_id,
                "failed",
                f"IPO GMP scraper failed: {error}",
                total_records,
                started_at
            )

        if clear_cancel_at_start:
            clear_cancel_signal()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to run IPO GMP scraper: {error}"
        )

    finally:
        conn.close()



def get_ipo_gmp_scraper_preview_service(
    search: str = "",
    ipo_status: str = "all",
    ipo_type: str = "all",
    page: int = 1,
    page_size: int = 50
):
    conn = get_connection()

    try:
        ensure_upstox_news_ipo_tables(conn)
        refresh_ipo_gmp_statuses(conn)

        current_page = normalize_page(page)
        current_page_size = normalize_page_size(page_size)
        offset = (current_page - 1) * current_page_size
        where_clauses = []
        params = []

        if search:
            search_value = f"%{search.strip().lower()}%"
            where_clauses.append("""
                (
                    LOWER(COALESCE(ipo_name, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_gmp, '')) LIKE ?
                    OR LOWER(COALESCE(price_band, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_date, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_type, '')) LIKE ?
                    OR LOWER(COALESCE(ipo_status, '')) LIKE ?
                    OR LOWER(COALESCE(last_updated, '')) LIKE ?
                )
            """)
            params.extend([search_value] * 7)

        if ipo_status != "all":
            where_clauses.append("LOWER(COALESCE(ipo_status, '')) = ?")
            params.append(ipo_status.lower())

        if ipo_type != "all":
            where_clauses.append("LOWER(COALESCE(ipo_type, '')) = ?")
            params.append(ipo_type.lower())

        where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""

        total_records = conn.execute(f"""
            SELECT COUNT(*)
            FROM ipo_gmp_scraper
            {where_sql};
        """, params).fetchone()[0]

        rows = conn.execute(f"""
            SELECT
                ipo_name,
                ipo_gmp,
                price_band,
                ipo_date,
                ipo_type,
                ipo_status,
                last_updated,
                source_url,
                scraped_at,
                updated_at
            FROM ipo_gmp_scraper
            {where_sql}
            ORDER BY updated_at DESC, ipo_name
            LIMIT ?
            OFFSET ?;
        """, params + [current_page_size, offset]).fetchall()

        total_pages = max(
            1,
            int((total_records + current_page_size - 1) / current_page_size)
        )

        return {
            "rows": [
                {
                    "ipo_name": row[0],
                    "ipo_gmp": row[1],
                    "price_band": row[2],
                    "gain": calculate_ipo_gmp_gain(row[1], row[2]),
                    "ipo_date": row[3],
                    "ipo_type": row[4],
                    "ipo_status": row[5],
                    "last_updated": row[6],
                    "source_url": row[7],
                    "scraped_at": str(row[8]) if row[8] else None,
                    "updated_at": str(row[9]) if row[9] else None
                }
                for row in rows
            ],
            "page": current_page,
            "page_size": current_page_size,
            "total_pages": total_pages,
            "total_records": total_records
        }

    finally:
        conn.close()
