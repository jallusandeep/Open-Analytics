# Open Analytics — Reference Data Design

## Purpose

The **Reference Data** module is the canonical security master for Open Analytics.

Its purpose is to maintain stable, explainable, normalized information about each security and each exchange listing without mixing in time-series calculations such as returns, momentum, risk, OHLCV, valuation ratios, or liquidity calculations.

The core identity should be based on **ISIN** at the security/company level, while exchange-specific tradable identities should remain separate through `instrument_key`.

---

# 1. Reference Data UI Structure

Recommended tabs:

```text
Reference Data
│
├── Securities
├── Classification
├── Listings
├── Index Membership
├── F&O
├── Status
└── Identifier History
```

The default tab should be:

```text
Securities
```

---

# 2. Securities Tab

## Purpose

This is the main security-level reference table.

One row should represent one security identity, preferably one unique ISIN.

## Recommended Columns

```text
isin
company_name
short_name
security_class
instrument_type
primary_symbol
primary_exchange
listing_status
is_active
```

## UI Table

```text
ISIN
Company Name
Security Class
Instrument Type
Primary Symbol
Primary Exchange
Listing Status
Active
```

## Example

```text
INE002A01018
Reliance Industries Limited
COMMON_EQUITY
EQ
RELIANCE
NSE
ACTIVE
true
```

## Important Rule

Do not make exchange-specific fields the primary identity of this table.

Fields such as:

```text
trading_symbol
exchange
segment
instrument_key
exchange_token
lot_size
tick_size
```

belong in the **Listings** tab.

---

# 3. Classification Tab

## Purpose

Maintain normalized company/security classification data.

This becomes the foundation for:

```text
sector analysis
industry analysis
peer comparison
sector-relative momentum
industry-relative momentum
sector-neutral factors
market-cap grouping
```

## Recommended Columns

```text
isin
company_name

macro_sector
sector
industry
basic_industry

market_cap_bucket

classification_source
source_updated_at
record_updated_at
```

## UI Table

```text
ISIN
Company Name
Macro Sector
Sector
Industry
Basic Industry
Market Cap Bucket
Classification Source
Last Updated
```

## Example

```text
INE002A01018
Reliance Industries Limited
Energy
Oil, Gas & Consumable Fuels
Petroleum Products
Refineries & Marketing
LARGE_CAP
NSE
2026-09-16
```

---

# 4. Listings Tab

## Purpose

Maintain exchange-specific instrument records.

One ISIN can have multiple exchange listings.

Example:

```text
Reliance Industries
    ├── NSE listing
    └── BSE listing
```

## Recommended Columns

```text
instrument_key
isin

exchange
segment

symbol
trading_symbol
exchange_token

instrument_type
series

lot_size
tick_size

is_primary_listing
is_active

listing_status
```

## UI Table

```text
Instrument Key
ISIN
Exchange
Segment
Trading Symbol
Exchange Token
Instrument Type
Series
Lot Size
Tick Size
Primary Listing
Active
```

## Example — NSE

```text
instrument_key      = NSE_EQ|INE002A01018
isin                = INE002A01018
exchange            = NSE
segment             = NSE_EQ
trading_symbol      = RELIANCE
instrument_type     = EQ
series              = EQ
lot_size            = 1
tick_size           = 0.05
is_primary_listing  = true
is_active           = true
```

## Example — BSE

```text
instrument_key      = BSE_EQ|INE002A01018
isin                = INE002A01018
exchange            = BSE
segment             = BSE_EQ
trading_symbol      = 500325
instrument_type     = EQ
is_primary_listing  = false
is_active           = true
```

---

# 5. Index Membership Tab

## Purpose

Track all index memberships for a security.

A stock may belong to multiple indices at the same time.

Example:

```text
NIFTY_50
NIFTY_100
NIFTY_500
NIFTY_ENERGY
```

Do not create permanent boolean columns such as:

```text
is_nifty_50
is_nifty_100
is_nifty_500
```

Index membership changes over time and should remain historical.

## Recommended Columns

```text
isin
company_name

index_code
index_name

effective_from
effective_to

is_current

source
source_updated_at
```

## UI Table

```text
ISIN
Company Name
Index Code
Index Name
Effective From
Effective To
Current
Source
```

## Example

```text
INE002A01018 | Reliance Industries | NIFTY_50  | Nifty 50  | 2024-01-01 | NULL | true
INE002A01018 | Reliance Industries | NIFTY_100 | Nifty 100 | 2024-01-01 | NULL | true
INE002A01018 | Reliance Industries | NIFTY_500 | Nifty 500 | 2024-01-01 | NULL | true
```

---

# 6. F&O Tab

## Purpose

Track whether a company/security participates in the derivatives segment.

## Recommended Columns

```text
isin
company_name

fno_eligible
futures_available
options_available

effective_from
effective_to

is_current

source
source_updated_at
```

## UI Table

```text
ISIN
Company Name
F&O Eligible
Futures Available
Options Available
Effective From
Effective To
Current
```

## Example

```text
INE002A01018
Reliance Industries Limited
true
true
true
2025-01-01
NULL
true
```

---

# 7. Status Tab

## Purpose

Track current and historical listing/security status.

`ACTIVE` should not be treated as equivalent to `TRADABLE`.

## Recommended Columns

```text
isin
company_name

listing_status

is_active
is_listed
is_suspended
is_delisted

last_trade_date

status_reason

effective_from
effective_to

source_updated_at
record_updated_at
```

## Possible Status Values

```text
ACTIVE
SUSPENDED
DELISTED
INACTIVE
STALE
MERGED
CEASED_TRADING
RECENTLY_LISTED
UNKNOWN
```

## UI Table

```text
ISIN
Company Name
Listing Status
Active
Listed
Suspended
Delisted
Last Trade Date
Status Reason
Last Updated
```

---

# 8. Identifier History Tab

## Purpose

Preserve historical identifier changes.

Do not overwrite previous identifiers without history.

## Recommended Columns

```text
isin
company_name

identifier_type

old_value
new_value

effective_from
effective_to

change_reason

source
record_updated_at
```

## Supported Identifier Types

```text
SYMBOL
TRADING_SYMBOL
COMPANY_NAME
ISIN
EXCHANGE_CODE
```

## Typical Change Reasons

```text
SYMBOL_CHANGE
COMPANY_NAME_CHANGE
ISIN_CHANGE
MERGER
DEMERGER
RESTRUCTURING
EXCHANGE_CHANGE
```

## UI Table

```text
ISIN
Company Name
Identifier Type
Old Value
New Value
Effective From
Effective To
Change Reason
```

---

# 9. Core Reference Tables

Open Analytics should maintain these four core database structures first.

## 9.1 security_reference

One row per ISIN.

```text
security_reference
------------------

isin

company_name
short_name

security_class
instrument_type

macro_sector
sector
industry
basic_industry

market_cap_bucket

has_nse_listing
has_bse_listing
is_cross_listed
listing_count

primary_exchange
primary_symbol
primary_instrument_key

listing_status
is_active
is_listed
is_suspended
is_delisted

listing_date
face_value

fno_eligible
futures_available
options_available

classification_source
instrument_source

source_updated_at
record_updated_at
```

---

## 9.2 security_listing_reference

One row per exchange-specific listing.

```text
security_listing_reference
--------------------------

instrument_key
isin

exchange
segment

symbol
trading_symbol
exchange_token

instrument_type
series

lot_size
tick_size

listing_status

is_active
is_primary_listing

source_updated_at
record_updated_at
```

---

## 9.3 security_index_membership

Multiple rows per ISIN are allowed.

```text
security_index_membership
-------------------------

isin

index_code
index_name

effective_from
effective_to

is_current

source
source_updated_at
record_updated_at
```

---

## 9.4 security_identifier_history

Stores historical identifier changes.

```text
security_identifier_history
---------------------------

isin

identifier_type

old_value
new_value

effective_from
effective_to

change_reason

source
record_updated_at
```

---

# 10. Recommended Additional Reference Table

For long-term architecture, F&O membership should also be historical instead of only current flags.

## security_fno_membership

```text
security_fno_membership
-----------------------

isin

fno_eligible
futures_available
options_available

effective_from
effective_to

is_current

source
source_updated_at
record_updated_at
```

The current values can still be denormalized into `security_reference` for faster UI access.

---

# 11. Security Class Values

Normalize every instrument into one of these values:

```text
COMMON_EQUITY
ETF
INDEX
FUTURE
OPTION
BOND
DEBENTURE
MUTUAL_FUND
PREFERENCE_SHARE
WARRANT
RIGHTS_ENTITLEMENT
REIT
INVIT
STRUCTURED_PRODUCT
OTHER
UNKNOWN
```

For the normal equity research universe:

```text
security_class = COMMON_EQUITY
```

should be the main inclusion class.

---

# 12. Main Reference Data Screen

Recommended default layout:

```text
REFERENCE DATA

[ Securities ] [ Classification ] [ Listings ] [ Index Membership ]
[ F&O ] [ Status ] [ Identifier History ]


Search ISIN, company, symbol...

┌──────────────┬──────────────────────┬────────────────┬────────────┬──────────────┬──────────────┬────────┬────────┐
│ ISIN         │ COMPANY NAME         │ SECURITY CLASS │ TYPE       │ SYMBOL       │ PRIMARY EXCH │ STATUS │ ACTIVE │
├──────────────┼──────────────────────┼────────────────┼────────────┼──────────────┼──────────────┼────────┼────────┤
│ INE002A01018 │ Reliance Industries  │ Common Equity  │ EQ         │ RELIANCE     │ NSE          │ Active │ Yes    │
│ INE040A01034 │ HDFC Bank            │ Common Equity  │ EQ         │ HDFCBANK     │ NSE          │ Active │ Yes    │
│ INE009A01021 │ Infosys              │ Common Equity  │ EQ         │ INFY         │ NSE          │ Active │ Yes    │
└──────────────┴──────────────────────┴────────────────┴────────────┴──────────────┴──────────────┴────────┴────────┘
```

---

# 13. Current Screen Changes

Current table:

```text
ISIN
Trading Symbol
Name
Exchange
Segment
```

Recommended main Securities table:

```text
ISIN
Company Name
Security Class
Instrument Type
Primary Symbol
Primary Exchange
Listing Status
Active
```

Move these to the **Listings** tab:

```text
Trading Symbol
Exchange
Segment
Instrument Key
Exchange Token
Series
Lot Size
Tick Size
Primary Listing
```

---

# 14. Reference Data vs Calculated Data

Do not mix calculated quantitative data into Reference Data.

## Keep in Reference Data

```text
ISIN
company name
security class
instrument type
exchange listing
sector
industry
basic industry
market-cap bucket
index membership
F&O membership
listing status
identifier history
listing date
face value
```

## Keep Outside Reference Data

```text
OHLCV
returns
momentum
volatility
beta
drawdown
volume calculations
average traded value
liquidity score
P/E
P/B
EPS
ROE
ROCE
factor scores
signals
predictions
portfolio weights
```

Those belong to later data, analytics, factor, signal, and portfolio engines.

---

# 15. Identity Rules

## Rule 1 — ISIN is the security identity

Use:

```text
isin
```

as the main reference key wherever possible.

---

## Rule 2 — instrument_key is the listing identity

Use:

```text
instrument_key
```

for exchange-specific tradable instruments.

---

## Rule 3 — One ISIN can have multiple listings

Example:

```text
INE002A01018
    ├── NSE_EQ|INE002A01018
    └── BSE_EQ|INE002A01018
```

---

## Rule 4 — Primary listing is not the company identity

Primary listing should only identify the preferred market venue.

Example:

```text
primary_exchange       = NSE
primary_symbol         = RELIANCE
primary_instrument_key = NSE_EQ|INE002A01018
```

---

## Rule 5 — Never delete historical identifiers

If a company changes:

```text
symbol
company name
ISIN
exchange identifier
```

preserve the previous value in `security_identifier_history`.

---

# 16. Source Metadata

Every reference dataset should preserve source metadata.

Recommended fields:

```text
source
source_record_id
source_updated_at
record_updated_at
```

Example sources:

```text
Upstox
NSE
BSE
Nifty Indices
manual
other approved source
```

This allows Open Analytics to explain where each reference value came from.

---

# 17. Recommended First Implementation Order

Build the Reference Data module in this order:

```text
1. security_reference

2. security_listing_reference

3. Classification tab

4. security_index_membership

5. security_fno_membership

6. Status handling

7. security_identifier_history
```

This gives the system a strong ISIN-based master before adding the later quantitative engines.

---

# 18. Final Reference Data Structure

```text
                         ISIN
                          │
                          ▼
                  SECURITY REFERENCE
                          │
          ┌───────────────┼────────────────┐
          │               │                │
          ▼               ▼                ▼
      LISTINGS      CLASSIFICATION      STATUS
          │
          ├───────────────┐
          │               │
          ▼               ▼
   INDEX MEMBERSHIP    F&O MEMBERSHIP
          │
          ▼
 IDENTIFIER HISTORY
```

The main idea is:

```text
SECURITY / COMPANY LEVEL
        ↓
       ISIN
        ↓
REFERENCE MASTER
        ↓
EXCHANGE LISTINGS
        ↓
MEMBERSHIPS / CLASSIFICATIONS / STATUS HISTORY
```

This keeps the reference layer clean, normalized, historically maintainable, and ready for the later Open Analytics universe, calculation, factor, signal, and backtesting engines.
