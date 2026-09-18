"""Synchronize current NSE index constituents while retaining membership history."""
import csv
import io
import urllib.request
from datetime import date, timedelta

from app.database import get_connection
from app.services.security_reference import ensure_reference_schema, refresh_security_index_memberships, valid_isin


NSE_INDEX_SOURCES = (
    ("NIFTY_50", "Nifty 50", "ind_nifty50list.csv"),
    ("NIFTY_NEXT_50", "Nifty Next 50", "ind_niftynext50list.csv"),
    ("NIFTY_100", "Nifty 100", "ind_nifty100list.csv"),
    ("NIFTY_200", "Nifty 200", "ind_nifty200list.csv"),
    ("NIFTY_500", "Nifty 500", "ind_nifty500list.csv"),
)
NSE_ARCHIVE_ROOT = "https://nsearchives.nseindia.com/content/indices/"


def download_constituents(filename):
    request = urllib.request.Request(
        NSE_ARCHIVE_ROOT + filename,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "text/csv,*/*"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8-sig")


def parse_constituent_isins(content):
    rows = csv.DictReader(io.StringIO(content))
    return {
        isin for row in rows
        if (isin := valid_isin(row.get("ISIN Code") or row.get("ISIN") or row.get("isin")))
    }


def apply_index_snapshot(conn, index_code, index_name, isins, as_of_date=None):
    as_of_date = as_of_date or date.today()
    known = {
        row[0] for row in conn.execute(
            "SELECT isin FROM security_reference WHERE isin IN (SELECT UNNEST(?))", [sorted(isins)]
        ).fetchall()
    } if isins else set()
    current = {
        row[0] for row in conn.execute(
            """SELECT isin FROM security_index_membership
               WHERE index_code=? AND effective_from <= ?
                 AND (effective_to IS NULL OR effective_to >= ?)""",
            [index_code, as_of_date, as_of_date],
        ).fetchall()
    }
    added = known - current
    removed = current - known
    if added:
        company_names = dict(conn.execute(
            "SELECT isin, company_name FROM security_reference WHERE isin IN (SELECT UNNEST(?))", [sorted(added)]
        ).fetchall())
        conn.executemany(
            """INSERT INTO security_index_membership
               (isin, company_name, index_code, index_name, effective_from, effective_to, is_current)
               VALUES (?, ?, ?, ?, ?, NULL, TRUE)
               ON CONFLICT (isin, index_code, effective_from) DO UPDATE
               SET company_name=excluded.company_name, index_name=excluded.index_name, effective_to=NULL, is_current=TRUE""",
            [(isin, company_names.get(isin), index_code, index_name, as_of_date) for isin in sorted(added)],
        )
    if removed:
        # A correction to today's first snapshot should not create an invalid
        # interval whose end predates its start.
        conn.execute(
            "DELETE FROM security_index_membership WHERE index_code=? AND effective_from=? AND isin IN (SELECT UNNEST(?))",
            [index_code, as_of_date, sorted(removed)],
        )
        conn.execute(
            """UPDATE security_index_membership SET effective_to=?, is_current=FALSE
               WHERE index_code=? AND isin IN (SELECT UNNEST(?))
                 AND effective_from < ? AND (effective_to IS NULL OR effective_to >= ?)""",
            [as_of_date - timedelta(days=1), index_code, sorted(removed), as_of_date, as_of_date],
        )
    return {"received": len(isins), "matched": len(known), "added": len(added), "removed": len(removed)}


def sync_nse_index_memberships(as_of_date=None, downloader=download_constituents):
    conn = get_connection()
    results = {}
    try:
        ensure_reference_schema(conn)
        conn.execute("BEGIN TRANSACTION")
        for code, name, filename in NSE_INDEX_SOURCES:
            try:
                isins = parse_constituent_isins(downloader(filename))
                if not isins:
                    raise ValueError("source contained no valid ISINs")
                results[code] = {"status": "success", **apply_index_snapshot(conn, code, name, isins, as_of_date)}
            except Exception as error:
                # Do not close old memberships when this source could not be verified.
                results[code] = {"status": "failed", "message": str(error)}
        refresh_security_index_memberships(conn)
        conn.execute("COMMIT")
        successful = [item for item in results.values() if item["status"] == "success"]
        return {
            "status": "success" if len(successful) == len(results) else "partial_success" if successful else "failed",
            "sources": results,
            "memberships": sum(item.get("matched", 0) for item in successful),
            "added": sum(item.get("added", 0) for item in successful),
            "removed": sum(item.get("removed", 0) for item in successful),
        }
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
