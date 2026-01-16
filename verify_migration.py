import logging
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.telegram_extractor.db import ensure_schema
from app.services.shared_db import get_shared_db

logging.basicConfig(level=logging.INFO)

print("Running ensure_schema for telegram_extractor...")
ensure_schema()

db = get_shared_db()
cols = db.run_raw_query("DESCRIBE telegram_raw", fetch='all')
print("\nColumns in telegram_raw:")
for col in cols:
    print(f"- {col[0]}")

found = any(col[0] == 'source_url' for col in cols)
if found:
    print("\nSUCCESS: source_url column found!")
else:
    print("\nFAILURE: source_url column MISSING!")
