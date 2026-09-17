# Security Reference

Mapped to Research/reference data.md, in its specified column order:

- security_reference: one row per valid ISIN. Company name and short name come from Upstox; listing counts, primary exchange (NSE preferred, BSE fallback), symbols, keys, and current derivative availability come from the current instrument snapshot.
- security_listing_reference: one row per instrument_key. Exchange identity, symbol, token, lot size and tick size come from Upstox; series is populated only when supplied, never inferred from EQ.
- security_index_membership: dated membership per ISIN/index/effective_from; overlapping inclusive periods are rejected. Current membership is calculated for the current date on reads.
- security_identifier_history: observed company-name/symbol changes plus uploaded ISIN/merger/demerger events. Observed change dates are explicitly observation dates, not authoritative corporate-action dates.

Refresh queues a full current-instrument download and then missing Upstox Company Profile requests by ISIN. The existing rate-limited collection service and credentials are reused. Profile sector is mapped as Upstox sector, not relabeled as NSE industry. No financial metrics are copied. Cached profiles are also mapped during instrument sync. Existing successful profiles are skipped; use the Company Fundamentals collector to force-refresh profiles when needed.

Only instrument_type EQ in NSE_EQ/BSE_EQ is included. ISINs require ISO format and valid Luhn checksum; conflicting source identities are skipped and counted. Missing listings are retained as NOT_IN_CURRENT_INSTRUMENTS, without inferring suspension/delisting. Unknown fields stay null. Uploaded enrichment survives sync through internal manual_fields metadata.

Legacy reference names are migrated once on creation of the new master; the legacy table remains intact. New Reference Data uses the four new tables.

API: /api/v1/reference-data/tables/{securities|listings|indices|identifiers}, with pagination/search/filters/sort; /download, /upload; POST /sync and GET /sync/status. All require admin or super-admin access.

Downloads: Data is read-only; Template + Data adds a flag column. Blank skips; A adds and skips existing keys; U updates supplied enrichment fields; D clears enrichment on securities/listings and removes dated membership/history rows. Source identity cannot be altered by upload. Dates use YYYY-MM-DD; booleans accept true/false, yes/no, 1/0. Uploads are atomic, with added/updated/cleared/skipped counts in the toast.

References: https://upstox.com/developer/api-documentation/instruments/ and https://upstox.com/developer/api-documentation/get-company-profile/
