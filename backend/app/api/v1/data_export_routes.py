from app.services.instrument_expiry import archive_expired_instruments
import csv
from datetime import date
from io import BytesIO, StringIO
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from fastapi.responses import Response
from openpyxl import Workbook

from app.database import get_connection
from app.dependencies import require_admin_or_super_admin

router = APIRouter(prefix="/data/export", tags=["Data"], dependencies=[Depends(require_admin_or_super_admin)])
DATASETS = {
    "monitor": ("upstox_sync_runs", "started_at"),
    "current_preview": ("upstox_instruments", "expiry"),
    "expired_preview": ("upstox_expired_instruments", "expiry"),
    "ohlcv": ("upstox_ohlcv_candles", "candle_date"),
    "equity_news": ("equity_news", "published_at"),
    "ipo_calendar": ("upstox_ipo_list", "bidding_start_date"),
    "ipo_scraper": ("ipo_gmp_scraper", "scraped_at"),
    "company_fundamentals": ("upstox_company_fundamentals", "report_date"),
    "market_calendar": ("upstox_market_holidays", "holiday_date"),
}
MAX_ROWS = 100_000


def dataset_schema(conn, dataset):
    if dataset not in DATASETS:
        raise HTTPException(400, "Unknown dataset")
    table, preferred_date = DATASETS[dataset]
    columns = conn.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name=? ORDER BY ordinal_position", [table]).fetchall()
    if not columns:
        raise HTTPException(404, "Dataset is not available")
    dates = [name for name, kind in columns if kind == "DATE" or kind.startswith("TIMESTAMP")]
    return table, dates, preferred_date if preferred_date in dates else dates[0] if dates else None


@router.get("/{dataset}/options")
def export_options(dataset: str):
    conn = get_connection()
    try:
        _, dates, default_date = dataset_schema(conn, dataset)
        return {"date_columns": dates, "default_date_column": default_date, "max_rows": MAX_ROWS}
    finally:
        conn.close()


@router.get("/{dataset}")
def download_dataset(dataset: str, format: Literal["csv", "xlsx"] = "csv", start_date: date | None = None,
                     end_date: date | None = None, date_column: str | None = None, endpoint: str | None = None):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(400, "Start date must be before end date")
    conn = get_connection()
    try:
        table, dates, default_date = dataset_schema(conn, dataset)
        if dataset in {"current_preview", "expired_preview"}:
            archive_expired_instruments(conn)
        selected_date = date_column or default_date
        if date_column and date_column not in dates:
            raise HTTPException(400, "Invalid date column")
        clauses, params = [], []
        if (start_date or end_date) and not selected_date:
            raise HTTPException(400, "This dataset has no date range")
        for value, operator in [(start_date, ">="), (end_date, "<=")]:
            if value:
                clauses.append(f'CAST("{selected_date}" AS DATE) {operator} ?')
                params.append(value)
        if dataset == "company_fundamentals" and endpoint:
            clauses.append("endpoint = ?")
            params.append(endpoint)
        where = " WHERE " + " AND ".join(clauses) if clauses else ""
        cursor = conn.execute(f'SELECT * FROM "{table}"{where} LIMIT {MAX_ROWS + 1}', params)
        headers = [column[0] for column in cursor.description]
        rows = cursor.fetchall()
        if len(rows) > MAX_ROWS:
            raise HTTPException(413, "Export exceeds 100,000 rows. Select a narrower date range.")
    finally:
        conn.close()
    return format_export(dataset, format, headers, rows)


def format_export(dataset, format, headers, rows):
    if format == "csv":
        output = StringIO(newline="")
        writer = csv.writer(output)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(["'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for value in row])
        content = output.getvalue().encode("utf-8-sig")
        media_type = "text/csv"
    else:
        workbook = Workbook(write_only=True)
        sheet = workbook.create_sheet("Data")
        sheet.append(headers)
        from openpyxl.cell import WriteOnlyCell
        for row in rows:
            cells = []
            for value in row:
                if isinstance(value, str):
                    cell = WriteOnlyCell(sheet, value=value)
                    cell.data_type = "s"
                    cells.append(cell)
                else:
                    cells.append(value)
            sheet.append(cells)
        output = BytesIO()
        workbook.save(output)
        content = output.getvalue()
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    return Response(content, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{dataset}.{format}"'})


class FilteredExport(BaseModel):
    headers: list[str] = Field(min_length=1, max_length=100)
    rows: list[list[str | int | float | bool | None]] = Field(max_length=MAX_ROWS)


@router.post("/{dataset}/filtered")
def download_filtered_dataset(dataset: str, payload: FilteredExport, format: Literal["csv", "xlsx"] = "csv"):
    if dataset not in DATASETS:
        raise HTTPException(400, "Unknown dataset")
    if any(len(row) != len(payload.headers) for row in payload.rows):
        raise HTTPException(400, "Row width must match export headers")
    return format_export(dataset, format, payload.headers, payload.rows)
