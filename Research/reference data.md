For your case, keep it simple. Start from the **Upstox current instruments list**, take every unique **ISIN**, and build a clean reference-data master around that ISIN.

Your own universe document already says the company/security identity should be based on **ISIN**, while exchange trading identity should remain separate through `instrument_key`. 

I would maintain it in this exact structure:

| Group          | Column                   | Example                     |
| -------------- | ------------------------ | --------------------------- |
| Identity       | `isin`                   | INE002A01018                |
| Identity       | `company_name`           | Reliance Industries Limited |
| Identity       | `short_name`             | Reliance Industries         |
| Identity       | `security_class`         | COMMON_EQUITY               |
| Identity       | `instrument_type`        | EQ                          |
| Classification | `macro_sector`           | Commodities                 |
| Classification | `sector`                 | Oil, Gas & Consumable Fuels |
| Classification | `industry`               | Petroleum Products          |
| Classification | `basic_industry`         | Refineries & Marketing      |
| Classification | `market_cap_bucket`      | LARGE_CAP                   |
| Listing        | `has_nse_listing`        | true                        |
| Listing        | `has_bse_listing`        | true                        |
| Listing        | `is_cross_listed`        | true                        |
| Listing        | `listing_count`          | 2                           |
| Listing        | `primary_exchange`       | NSE                         |
| Listing        | `primary_symbol`         | RELIANCE                    |
| Listing        | `primary_instrument_key` | NSE_EQ|INE002A01018         |
| Status         | `listing_status`         | ACTIVE                      |
| Status         | `is_active`              | true                        |
| Status         | `is_listed`              | true                        |
| Status         | `is_suspended`           | false                       |
| Status         | `is_delisted`            | false                       |
| Other          | `listing_date`           | date                        |
| Other          | `face_value`             | 10                          |
| Derivatives    | `fno_eligible`           | true                        |
| Derivatives    | `futures_available`      | true                        |
| Derivatives    | `options_available`      | true                        |
| Source         | `classification_source`  | NSE                         |
| Source         | `instrument_source`      | Upstox                      |
| Source         | `source_updated_at`      | timestamp                   |
| Source         | `record_updated_at`      | timestamp                   |

So your main table can be:

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

Then keep the **Upstox exchange-specific rows separately**. Your document already recommends separating company-level fields from listing-level fields. 

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
```

Example for Reliance:

```text
ISIN: INE002A01018

Company Reference
-----------------
Company       : Reliance Industries Limited
Sector        : Oil, Gas & Consumable Fuels
Industry      : Petroleum Products
Basic Industry: Refineries & Marketing
Market Cap    : LARGE_CAP
F&O           : Yes
Primary       : NSE
```

And:

```text
Listings
--------

NSE
instrument_key : NSE_EQ|INE002A01018
segment        : NSE_EQ
symbol         : RELIANCE
primary        : true

BSE
instrument_key : BSE_EQ|INE002A01018
segment        : BSE_EQ
symbol         : 500325
primary        : false
```

For **indices**, do not add columns like `nifty_50`, `nifty_100`, `nifty_500` into the main table. One company can belong to many indices and membership changes over time. Your document explicitly calls for point-in-time membership. 

Maintain a third table:

```text
security_index_membership
-------------------------
isin
index_code
index_name
effective_from
effective_to
is_current
```

Example:

```text
INE002A01018 | NIFTY_50     | 2024-01-01 | NULL | true
INE002A01018 | NIFTY_100    | 2024-01-01 | NULL | true
INE002A01018 | NIFTY_500    | 2024-01-01 | NULL | true
INE002A01018 | NIFTY_ENERGY | 2024-01-01 | NULL | true
```

And finally maintain historical identifier changes separately:

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
```

This is useful for:

```text
SYMBOL CHANGE
COMPANY NAME CHANGE
ISIN CHANGE
MERGER
DEMERGER
```

So for Open Analytics, I would maintain only these **4 reference tables**:

```text
1. security_reference
   One row per ISIN

2. security_listing_reference
   One row per exchange instrument

3. security_index_membership
   Multiple indices per ISIN

4. security_identifier_history
   Symbol/name/ISIN changes
```

That is enough to start properly. Do not mix prices, volume, P/E, EPS, returns, momentum, risk, or other calculations into reference data.
