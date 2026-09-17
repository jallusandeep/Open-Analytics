"""Download the public NSE Nifty 50 constituent reference snapshot."""
import requests
from pathlib import Path
url='https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv'
r=requests.get(url, headers={'User-Agent':'Mozilla/5.0'},timeout=30)
r.raise_for_status()
p=Path(__file__).resolve().parent / 'reference_samples' / 'nifty50_source.csv'
p.parent.mkdir(exist_ok=True)
p.write_bytes(r.content)
print(r.text)

url='https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'
r=requests.get(url, headers={'User-Agent':'Mozilla/5.0'},timeout=30)
r.raise_for_status()
p=p.parent / 'equity_source.csv'
p.write_bytes(r.content)
import csv,io,json
symbols={'RELIANCE','TCS','HDFCBANK','INFY','ICICIBANK','SBIN','ITC','HINDUNILVR','LT','BHARTIARTL'}
print(json.dumps([row for row in csv.DictReader(io.StringIO(r.text)) if row.get('SYMBOL') in symbols],indent=2))
