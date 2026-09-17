"""Fill ten existing securities from reviewed public NSE sources, retaining Upstox identity."""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / 'backend'))
from app.database import get_connection
from app.services.security_reference import valid_isin
from app.api.v1.security_reference_routes import convert

SYMBOLS = ['RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'SBIN', 'ITC', 'HINDUNILVR', 'LT', 'BHARTIARTL']
# Basic industries verified in NSE quote pages or exchange-hosted filings.
# Parent classifications mapped using the explicitly versioned NSE taxonomy.
CLASSIFICATION = {
 'RELIANCE': ('Energy', 'Oil, Gas & Consumable Fuels', 'Petroleum Products', 'Refineries & Marketing'),
 'TCS': ('Information Technology', 'Information Technology', 'IT - Software', 'Computers - Software & Consulting'),
 'HDFCBANK': ('Financial Services', 'Financial Services', 'Banks', 'Private Sector Bank'),
 'INFY': ('Information Technology', 'Information Technology', 'IT - Software', 'Computers - Software & Consulting'),
 'ICICIBANK': ('Financial Services', 'Financial Services', 'Banks', 'Private Sector Bank'),
 'SBIN': ('Financial Services', 'Financial Services', 'Banks', 'Public Sector Bank'),
 'ITC': ('Fast Moving Consumer Goods', 'Fast Moving Consumer Goods', 'Diversified FMCG', 'Diversified FMCG'),
 'HINDUNILVR': ('Fast Moving Consumer Goods', 'Fast Moving Consumer Goods', 'Diversified FMCG', 'Diversified FMCG'),
 'LT': ('Industrials', 'Construction', 'Construction', 'Civil Construction'),
 'BHARTIARTL': ('Telecommunication', 'Telecommunication', 'Telecom - Services', 'Telecom - Cellular & Fixed line services')
}
SHORT = {'RELIANCE':'Reliance Industries','TCS':'TCS','HDFCBANK':'HDFC Bank','INFY':'Infosys','ICICIBANK':'ICICI Bank','SBIN':'State Bank of India','ITC':'ITC','HINDUNILVR':'Hindustan Unilever','LT':'Larsen & Toubro','BHARTIARTL':'Bharti Airtel'}
with (ROOT / 'reference_samples' / 'equity_source.csv').open(encoding='utf-8-sig', newline='') as file:
    equity = {row['SYMBOL']: {key.strip(): value.strip() for key, value in row.items()} for row in csv.DictReader(file)}
with (ROOT / 'reference_samples' / 'nifty50_source.csv').open(encoding='utf-8-sig', newline='') as file:
    constituents = {row['Symbol']: row for row in csv.DictReader(file)}
fields = ['isin', 'company_name', 'short_name', 'security_class', 'macro_sector', 'sector', 'industry', 'basic_industry', 'listing_date', 'face_value', 'classification_source']
rows = []
for symbol in SYMBOLS:
    raw = equity[symbol]
    isin = valid_isin(raw['ISIN NUMBER'])
    assert isin and constituents[symbol]['ISIN Code'] == isin and raw['SERIES'] == 'EQ', symbol
    macro, sector, industry, basic = CLASSIFICATION[symbol]
    rows.append(dict(isin=isin, company_name=raw['NAME OF COMPANY'], short_name=SHORT[symbol], security_class='COMMON_EQUITY', macro_sector=macro, sector=sector, industry=industry, basic_industry=basic, listing_date=datetime.strptime(raw['DATE OF LISTING'], '%d-%b-%Y').date(), face_value=float(raw['FACE VALUE']), classification_source='NSE equity master + NSE indices taxonomy (March 2022)'))
output = ROOT / 'reference_samples' / 'ten_equities_upload.csv'
with output.open('w', encoding='utf-8-sig', newline='') as file:
    writer = csv.DictWriter(file, fieldnames=fields + ['flag'])
    writer.writeheader()
    writer.writerows(dict(row, flag='U') for row in rows)
conn = get_connection()
try:
    snapshot = []
    for row in rows:
        result = conn.execute('SELECT * FROM security_reference WHERE isin=?', [row['isin']])
        keys = [column[0] for column in result.description]
        data = result.fetchone()
        if not data:
            raise ValueError('Missing current security: ' + row['isin'])
        snapshot.append(dict(zip(keys, data)))
    # Snapshot is immutable across reruns so the original values remain reviewable.
    backup = ROOT / 'reference_samples' / 'before_fill.json'
    if not backup.exists():
        backup.write_text(json.dumps(snapshot, default=str, indent=2), encoding='utf-8')
    conn.execute('BEGIN TRANSACTION')
    changed = 0
    for row, old in zip(rows, snapshot):
        changed_fields = [field for field in fields if field != 'isin' and old.get(field) != row[field]]
        if not changed_fields:
            continue
        manual = sorted(set(json.loads(old.get('manual_fields') or '[]')) | set(fields) - {'isin'})
        assignment = ', '.join(field + '=?' for field in changed_fields)
        conn.execute('UPDATE security_reference SET ' + assignment + ', manual_fields=?, record_updated_at=CURRENT_TIMESTAMP WHERE isin=?', [row[field] for field in changed_fields] + [json.dumps(manual), row['isin']])
        changed += 1
    conn.commit()
    print(json.dumps({'updated': changed, 'matched': len(rows), 'symbols': SYMBOLS, 'upload': str(output)}))
finally:
    conn.close()
