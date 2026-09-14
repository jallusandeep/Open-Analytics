# Open Analytics — Step 1: Universe Definition

## Purpose

The **Universe Definition Engine** determines which securities are eligible to enter the Open Analytics quantitative research and trading pipeline.

A professional quant workflow should not begin by calculating indicators across every available instrument. It should first define a clean, explainable, historically correct, and tradable universe.

The universe layer must answer:

- Which securities exist?
- Which ones are actual common equities?
- Which exchange listing should represent a company?
- Which securities are currently active?
- How much valid history does each security have?
- Is the security sufficiently liquid?
- Is the security suitable for research, trading, or both?
- Which indices, sectors, industries, and market-cap groups does it belong to?
- Which datasets are available for it?
- Was the security eligible on a specific historical date?

The output of this engine becomes the input for all later calculation engines.

---

# 1. Universe Definition

## Core Principle

Do not build one hard-coded universe.

Open Analytics should support multiple reusable universes such as:

```text
ALL_EQUITY
NSE_EQUITY
BSE_EQUITY

LIQUID_EQUITY
HIGH_LIQUIDITY

NIFTY_50
NIFTY_100
NIFTY_200
NIFTY_500

FNO

LARGE_CAP
MID_CAP
SMALL_CAP

NEW_LISTINGS
```

A security may belong to more than one universe at the same time.

Example:

```text
RELIANCE

NSE_EQUITY      = true
NIFTY_50        = true
NIFTY_100       = true
NIFTY_500       = true
FNO             = true
LARGE_CAP       = true
LIQUID_EQUITY   = true
```

---

# 1.1 Master Security Universe

## Objective

Create the complete master list of all instruments known to Open Analytics before applying research or trading filters.

The master should preserve every instrument type because non-equity instruments may later be used by derivatives, index, ETF, fixed-income, or other engines.

## Core Identity Fields

```text
instrument_key
exchange
segment
symbol
trading_symbol
company_name
isin
instrument_type
lot_size
tick_size
listing_date
expiry
strike
option_type
active_status
```

Not every field applies to every instrument type.

## Initial Architecture

```text
MASTER_UNIVERSE
      ↓
EQUITY_UNIVERSE
      ↓
RESEARCH_CANDIDATE_UNIVERSE
      ↓
TRADING_UNIVERSE
```

### MASTER_UNIVERSE

Contains all known instruments.

### EQUITY_UNIVERSE

Contains securities classified as genuine equity instruments.

### RESEARCH_CANDIDATE_UNIVERSE

Contains equities that satisfy basic data and status requirements for quantitative research.

### TRADING_UNIVERSE

Contains securities that additionally satisfy liquidity and tradability requirements.

## Required Summary

The engine should calculate:

```text
Total instruments
Total equities
NSE equities
BSE equities
Unique ISINs
Cross-listed securities
Unknown instruments
Active equities
Inactive equities
```

---

# 1.2 Security Type and Instrument Filtering

## Objective

Ensure the main equity research universe contains actual company shares rather than unrelated financial instruments.

## Instrument Classification

Every instrument should be classified into a normalized security class.

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

## Main Equity Research Inclusion

Default equity candidates should generally satisfy:

```text
Common Equity
+
Valid exchange
+
Valid security identifier
+
Recognized instrument classification
```

Active/tradable filtering is handled separately.

## Recommended Fields

```text
instrument_key
isin
exchange
segment
instrument_type
security_class

is_equity
is_common_equity
is_research_candidate

exclusion_reason
```

## Do Not Delete Excluded Instruments

Instead of removing records:

```text
is_equity = false
is_research_candidate = false
exclusion_reason = "ETF"
```

This preserves the instrument for future specialized engines.

## REITs and InvITs

REITs and InvITs should preferably be classified separately rather than mixed into normal company-equity factor models because their accounting, distributions, leverage, and valuation behavior differ materially from ordinary operating companies.

---

# 1.3 Exchange and Cross-Listing Handling

## Objective

Prevent the same economic company from being treated as multiple independent companies merely because it trades on both NSE and BSE.

## Identity Model

Use separate company and trading identities.

```text
Company identity   → ISIN / company-level identifier
Trading identity   → instrument_key
Exchange identity  → NSE / BSE
```

Conceptually:

```text
COMPANY MASTER
      ↓
EXCHANGE LISTINGS
```

Example:

```text
Company / ISIN
  ├── NSE instrument_key
  └── BSE instrument_key
```

## Company-Level Fields

```text
isin
company_name
sector
industry
sub_industry

primary_symbol
primary_exchange
primary_instrument_key
```

## Listing-Level Fields

```text
instrument_key
isin
exchange
trading_symbol
segment

tick_size
lot_size

active_status
last_price

average_volume
average_traded_value
spread
data_quality
```

## Primary Listing Selection

Do not permanently assume NSE or BSE.

Choose the preferred listing using measurable trading quality.

Possible inputs:

```text
Average traded value
Average volume
Bid-ask spread
Active trading days
Market depth
Data completeness
```

Conceptually:

```text
Venue Score
=
Liquidity
+ Traded Value
- Spread
+ Data Quality
```

The best venue becomes:

```text
is_primary_listing = true
```

## Required Flags

```text
is_cross_listed
listing_count

has_nse_listing
has_bse_listing

primary_exchange
primary_instrument_key
```

## Important Separation

Company-level calculations:

```text
Fundamentals
Valuation
Quality
Growth
News
Corporate events
```

Venue-level calculations:

```text
Volume
Spread
Market depth
Slippage
Liquidity
Execution cost
```

Returns and price-based factors should generally use one consistent primary listing unless a strategy specifically studies venue differences.

---

# 1.4 Active and Tradable Status

## Objective

Determine whether a security merely exists in the database or is currently usable for research and/or trading.

Possible states include:

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

## Recommended Fields

```text
is_active
is_listed
is_tradable
is_suspended
is_delisted
is_stale

last_trade_date
days_since_last_trade

listing_status
data_status
trading_status

status_reason
```

## Important Principle

```text
ACTIVE != TRADABLE
```

A security may technically remain listed but trade very rarely.

Example:

```text
Stock A

active = true
last_trade_date = current session
traded_days_20d = 20
tradable = true
```

Compared with:

```text
Stock B

active = true
last_trade_date = 12 days ago
traded_days_20d = 3
tradable = false

reason = "Insufficient recent trading activity"
```

## Recommended Status Layers

Maintain three independent concepts:

```text
listing_status
data_status
trading_status
```

Example:

```text
listing_status = ACTIVE
data_status    = HEALTHY
trading_status = TRADABLE
```

or:

```text
listing_status = ACTIVE
data_status    = STALE
trading_status = NOT_TRADABLE
```

## Historical Securities Must Be Preserved

Do not remove delisted or inactive securities from historical databases.

Instead:

```text
current_research_eligible = false
historical_research_eligible = true
```

This is necessary to reduce survivorship bias in backtesting.

---

# 1.5 Trading History Requirement

## Objective

Determine which calculations each stock is eligible for based on available valid historical observations.

A newly listed company should not be excluded from all research simply because it lacks one year of history.

Eligibility should be calculation-specific.

## Required History Fields

```text
first_trade_date
last_trade_date

calendar_age_days
trading_history_days

valid_ohlcv_days
missing_ohlcv_days

trading_coverage_pct

max_missing_streak
recent_missing_days
historical_missing_days
```

## Horizon Eligibility Flags

```text
eligible_5d
eligible_21d
eligible_63d
eligible_126d
eligible_252d

eligible_1y
eligible_3y
eligible_5y

eligible_short_term_risk
eligible_long_term_risk

eligible_beta
eligible_factor_model
```

## Return History Requirements

A return over N sessions requires N+1 prices.

```text
5D return     → minimum 6 valid closes
21D return    → minimum 22 valid closes
63D return    → minimum 64 valid closes
126D return   → minimum 127 valid closes
252D return   → minimum 253 valid closes
```

## Rolling Statistics

Examples:

```text
20D volatility → minimum 20 valid daily returns
60D volatility → minimum 60 valid daily returns
252D beta      → sufficient overlapping stock and benchmark returns
```

## Data Coverage

Age alone is not enough.

Bad rule:

```text
listing_age > 1 year
```

Better rule:

```text
valid_history_days >= required_days
AND
coverage_pct >= minimum_coverage
```

Coverage:

```text
Coverage
=
Valid expected trading sessions
/
Expected trading sessions
```

Example:

```text
Expected sessions = 252
Valid candles     = 249

Coverage = 98.8%
```

## Missing Streaks

A stock can have high overall coverage but still contain a long uninterrupted missing section.

Therefore track:

```text
max_missing_streak
```

and potentially reject calculations when gaps are concentrated.

## IPO Handling

Do not globally exclude young listings.

Example:

```text
IPO age = 45 trading sessions

eligible_5d      = true
eligible_21d     = true
eligible_63d     = false
eligible_252d    = false
eligible_12m_mom = false
```

## Overlapping History

Relative calculations require matching dates.

For example, beta requires stock and benchmark returns on the same trading sessions.

Track:

```text
benchmark_overlap_days
sector_overlap_days
factor_overlap_days
```

Example:

```text
Stock history  = 400 observations
NIFTY overlap  = 247 observations

252D beta eligible = false
126D beta eligible = true
```

## Main Principle

Do not ask:

> Does this stock have enough history?

Ask:

> Does this stock have enough valid history for this specific calculation?

---

# 1.6 Liquidity Eligibility

## Objective

Determine whether a mathematically attractive security can realistically be traded.

Liquidity should be evaluated using multiple dimensions rather than volume alone.

## Core Metrics

```text
avg_volume_5d
avg_volume_20d
avg_volume_60d

avg_traded_value_5d
avg_traded_value_20d
avg_traded_value_60d

median_traded_value_20d
median_traded_value_60d

traded_days_20d
traded_days_60d

zero_volume_days_20d
zero_volume_days_60d

turnover
```

Where available, additionally include:

```text
bid_ask_spread
bid_ask_spread_pct

market_depth
top_book_depth
depth_imbalance

estimated_slippage
estimated_market_impact
```

## Traded Value

Volume should not be compared directly across stocks with very different prices.

Use traded value:

```text
traded_value = price × volume
```

Average Daily Traded Value is particularly useful for practical eligibility.

## Liquidity Eligibility

Do not initially hard-code one universal threshold.

Support configurable rules such as:

```text
minimum_avg_traded_value
minimum_active_trading_days
maximum_zero_volume_days
maximum_spread_pct
```

## Liquidity Score

Eventually create a normalized score from:

```text
Traded value
Volume
Spread
Trading frequency
Market depth
Market impact
```

Example output:

```text
liquidity_score = 0-100
liquidity_percentile = 0-100
liquidity_bucket = HIGH / MEDIUM / LOW
```

## Research vs Trading

An illiquid stock can still be useful for academic or factor research.

Therefore keep separate flags:

```text
research_eligible
trading_eligible
```

---

# 1.7 Price Eligibility

## Objective

Identify securities whose price characteristics make them unsuitable for certain live strategies.

Possible checks include:

```text
last_price
median_price_20d
minimum_price
maximum_price
penny_stock_flag
price_stale_flag
```

Do not permanently discard low-price stocks from the database.

Instead support configurable strategy-level restrictions.

Example:

```text
price_eligible = false
price_exclusion_reason = "Below configured minimum price"
```

This threshold should be strategy-dependent.

---

# 1.8 Market-Capitalization Classification

## Objective

Classify companies by economic size and allow market-cap-sensitive factor models.

Store actual numerical market cap whenever available.

## Recommended Fields

```text
market_cap
free_float_market_cap

market_cap_rank
free_float_market_cap_rank

market_cap_percentile

market_cap_bucket
```

Possible buckets:

```text
LARGE_CAP
MID_CAP
SMALL_CAP
MICRO_CAP
```

Do not rely exclusively on labels because classification rules may change.

Retain both:

```text
numerical market cap
classification
```

## Historical Market Cap

For backtesting, market cap should ideally be point-in-time:

```text
date
instrument / company
market_cap
free_float_market_cap
rank
bucket
```

Using today's market cap to classify historical stocks introduces look-ahead bias.

---

# 1.9 Index Membership

## Objective

Track membership in market and sector indices.

Possible memberships:

```text
NIFTY_50
NIFTY_NEXT_50
NIFTY_100
NIFTY_200
NIFTY_500

NIFTY_MIDCAP
NIFTY_SMALLCAP

BANK_NIFTY
NIFTY_IT
NIFTY_AUTO
NIFTY_PHARMA
NIFTY_METAL
NIFTY_FMCG
...
```

A stock can belong to multiple indices.

## Point-in-Time Membership

Store effective dates:

```text
instrument / company
index_code
effective_from
effective_to
```

This is essential for survivorship-safe historical research.

---

# 1.10 Sector and Industry Classification

## Objective

Provide consistent peer grouping for relative valuation, quality, momentum, risk, and sector-neutral factor construction.

Recommended hierarchy:

```text
sector
industry
sub_industry
```

Potential additional hierarchy:

```text
macro_sector
sector
industry
sub_industry
```

## Why It Matters

Later engines need to calculate:

```text
sector_return
industry_return

sector_relative_momentum
industry_relative_momentum

sector_percentile
industry_percentile

sector_neutral_value
sector_neutral_quality
sector_neutral_growth
```

Sector classification should therefore be stable and versioned when mappings change.

---

# 1.11 F&O Eligibility

## Objective

Identify stocks currently available in the derivatives segment.

Fields:

```text
fno_eligible
futures_available
options_available

fno_effective_from
fno_effective_to
```

## Why It Matters

F&O eligibility can be used for:

```text
Derivatives strategies
OI analysis
Option chain analysis
Futures basis
Shorting implementation
Liquidity segmentation
Institutional universe construction
```

Historical eligibility should also be preserved.

---

# 1.12 Corporate Event Flags

## Objective

Identify unusual corporate situations that can distort prices, returns, liquidity, or comparability.

Possible flags:

```text
recent_ipo
recent_split
recent_bonus
recent_dividend
recent_rights_issue

merger_event
demerger_event
buyback_event

delisting_event
symbol_change
isin_change

capital_restructuring
```

These events should normally trigger downstream handling rather than immediate permanent exclusion.

Example:

```text
recent_split = true
requires_price_adjustment = true
```

---

# 1.13 Data Availability Flags

## Objective

Tell downstream engines exactly which datasets exist for each security.

Recommended fields:

```text
has_ohlcv
has_adjusted_ohlcv

has_fundamentals
has_corporate_actions
has_news

has_futures
has_options
has_option_chain

has_market_depth
has_delivery_data

has_sector_mapping
has_index_membership
has_market_cap
```

## Dataset Quality

Availability should eventually include quality metadata.

Example:

```text
ohlcv_coverage_pct
fundamental_last_updated
news_last_updated
corporate_action_last_updated
```

Different strategies can then define their own data requirements.

Example:

```text
Momentum strategy:
requires OHLCV only

Quality strategy:
requires OHLCV + fundamentals

News strategy:
requires OHLCV + news

Options strategy:
requires spot + option chain + derivatives data
```

---

# 1.14 Universe Membership Engine

## Objective

Create reusable named universes from configurable rules.

A universe should not be stored only as a static list.

It should contain:

```text
universe_id
universe_name
description

rules
effective_from
effective_to

created_at
updated_at
```

Example:

```text
UNIVERSE_ID = LIQUID_NSE_500

Rules:

exchange = NSE
security_class = COMMON_EQUITY
active = true
history_252d = true
avg_traded_value_20d >= configured threshold
```

## Membership Record

```text
universe_id
instrument_key
membership_date

is_member
inclusion_reason
exclusion_reason
```

---

# 1.15 Historical Universe Snapshots

## Objective

Prevent survivorship bias and look-ahead bias.

This is one of the most important requirements for a professional quantitative platform.

Do not backtest 2018 using today's stock universe.

Historical membership should allow the engine to answer:

> Which securities were actually eligible on 15 June 2018?

## Recommended Model

```text
universe_id
instrument_key

effective_from
effective_to

inclusion_reason
exclusion_reason
```

or daily snapshots where required:

```text
date
universe_id
instrument_key
is_member
```

## Why This Matters

Companies may:

```text
IPO
Delist
Merge
Fail
Become illiquid
Enter an index
Leave an index
Enter F&O
Leave F&O
Move market-cap buckets
```

Ignoring historical membership can materially inflate backtest results.

---

# 1.16 Research Eligibility vs Trading Eligibility

These should be separate concepts.

## Research Eligibility

Answers:

> Is this security appropriate for quantitative analysis?

Possible requirements:

```text
Valid security classification
Usable OHLCV
Sufficient history for requested metric
Acceptable data quality
```

## Trading Eligibility

Answers:

> Could this security realistically be used by this strategy today?

Possible requirements:

```text
Research eligible
Currently active
Recent trading
Adequate liquidity
Acceptable spread
Adequate market depth
Strategy capacity
No blocking status
```

Fields:

```text
research_eligible
trading_eligible

research_exclusion_reason
trading_exclusion_reason
```

---

# 1.17 Calculation-Specific Eligibility

Avoid one global eligibility flag for every calculation.

Example:

```text
eligible_return_5d
eligible_return_21d
eligible_return_252d

eligible_volatility_20d
eligible_volatility_60d

eligible_beta_252d
eligible_momentum_12_1

eligible_fundamental_factor
eligible_news_factor
eligible_derivatives_factor
```

This makes the system far more robust for IPOs and securities with partial datasets.

---

# 1.18 Exclusion Reason Framework

Every exclusion should be explainable.

Possible codes:

```text
NON_EQUITY
INVALID_SECURITY_TYPE
INVALID_IDENTIFIER

INACTIVE
SUSPENDED
DELISTED
STALE_PRICE

INSUFFICIENT_HISTORY
LOW_DATA_COVERAGE
LONG_DATA_GAP

LOW_VOLUME
LOW_TRADED_VALUE
HIGH_SPREAD
INSUFFICIENT_TRADING_DAYS

PRICE_BELOW_THRESHOLD

MISSING_FUNDAMENTALS
MISSING_CORPORATE_ACTION_DATA

DUPLICATE_LISTING
NON_PRIMARY_LISTING

MANUAL_EXCLUSION
```

Prefer storing both:

```text
exclusion_code
exclusion_detail
```

---

# 1.19 Suggested Final Universe Record

A complete universe/security eligibility record may ultimately contain:

```text
# IDENTITY

instrument_key
isin
symbol
trading_symbol
company_name

exchange
segment
security_class


# COMPANY / LISTING

company_id
is_cross_listed
listing_count

has_nse_listing
has_bse_listing

is_primary_listing
primary_exchange
primary_instrument_key


# STATUS

listing_status
data_status
trading_status

is_active
is_listed
is_tradable
is_suspended
is_delisted
is_stale

last_trade_date
days_since_last_trade


# HISTORY

listing_date
first_trade_date
last_trade_date

trading_history_days
valid_ohlcv_days
missing_ohlcv_days
coverage_pct
max_missing_streak


# HORIZON ELIGIBILITY

eligible_5d
eligible_21d
eligible_63d
eligible_126d
eligible_252d

eligible_1y
eligible_3y
eligible_5y


# LIQUIDITY

avg_volume_20d
avg_volume_60d

avg_traded_value_20d
avg_traded_value_60d

traded_days_20d
traded_days_60d

zero_volume_days_20d
zero_volume_days_60d

bid_ask_spread_pct
liquidity_score
liquidity_percentile


# PRICE

last_price
median_price_20d
price_eligible
penny_stock_flag


# COMPANY CLASSIFICATION

market_cap
free_float_market_cap
market_cap_rank
market_cap_bucket

sector
industry
sub_industry


# INDEX / DERIVATIVES

index_memberships

fno_eligible
futures_available
options_available


# DATA AVAILABILITY

has_ohlcv
has_adjusted_ohlcv

has_fundamentals
has_corporate_actions
has_news

has_futures
has_options
has_market_depth


# EVENTS

recent_ipo
recent_split
recent_bonus
recent_dividend
merger_event
demerger_event
delisting_event


# FINAL ELIGIBILITY

research_eligible
trading_eligible

research_exclusion_reason
trading_exclusion_reason

universe_memberships
```

---

# 1.20 Universe Engine Outputs

The Universe Engine should be able to answer queries such as:

```text
Give me all active NSE common equities.
```

```text
Give me all current F&O stocks.
```

```text
Give me all NIFTY 500 stocks with at least 252 valid sessions.
```

```text
Give me all liquid NSE stocks with at least three years of usable history.
```

```text
Give me all IPOs listed within the last 180 days.
```

```text
Give me securities eligible for 12-1 momentum.
```

```text
Give me stocks suitable for a strategy requiring ₹50 crore minimum average daily traded value.
```

```text
Give me the exact eligible universe as of 2019-01-02.
```

---

# 1.21 Universe Engine Processing Flow

Recommended processing order:

```text
RAW INSTRUMENT MASTER
        ↓
SECURITY CLASSIFICATION
        ↓
COMPANY / ISIN MAPPING
        ↓
EXCHANGE LISTING RESOLUTION
        ↓
ACTIVE / TRADABLE STATUS
        ↓
HISTORICAL DATA COVERAGE
        ↓
LIQUIDITY CALCULATION
        ↓
PRICE ELIGIBILITY
        ↓
MARKET-CAP CLASSIFICATION
        ↓
SECTOR / INDUSTRY CLASSIFICATION
        ↓
INDEX MEMBERSHIP
        ↓
F&O ELIGIBILITY
        ↓
CORPORATE EVENT FLAGS
        ↓
DATA AVAILABILITY
        ↓
RESEARCH ELIGIBILITY
        ↓
TRADING ELIGIBILITY
        ↓
NAMED UNIVERSE MEMBERSHIP
        ↓
HISTORICAL UNIVERSE SNAPSHOT
```

---

# 1.22 Important Quant Rules

## Rule 1 — Never Delete Historical Failures

Delisted, failed, merged, or inactive companies must remain available historically.

Otherwise backtests suffer from survivorship bias.

---

## Rule 2 — Do Not Use Today's Universe for Historical Tests

Membership must be point-in-time.

---

## Rule 3 — Separate Company from Listing

One company can trade through multiple exchange instruments.

Company-level factors and exchange-level execution metrics should not be confused.

---

## Rule 4 — Do Not Use One Eligibility Flag

Different calculations require different amounts and types of data.

---

## Rule 5 — Research Eligibility Is Not Trading Eligibility

A stock can be statistically interesting but practically untradable.

---

## Rule 6 — Preserve Raw Data

Universe classifications and exclusions should never destroy original instrument records.

---

## Rule 7 — Every Exclusion Must Be Explainable

The engine should always answer:

> Why is this stock not in the universe?

---

## Rule 8 — Thresholds Should Be Configurable

Examples:

```text
minimum price
minimum history
minimum data coverage
minimum average traded value
maximum spread
minimum active sessions
```

Different strategies will need different thresholds.

---

# 1.23 Final Purpose of Step 1

After Step 1, Open Analytics should have a clean point-in-time function conceptually equivalent to:

```text
get_universe(
    universe_id,
    as_of_date,
    strategy_requirements
)
```

which returns only the securities valid for that calculation or strategy on that date.

For example:

```text
get_universe(
    universe_id="NIFTY_500",
    as_of_date="2026-09-14",
    strategy_requirements={
        "history_days": 253,
        "min_liquidity": "MEDIUM",
        "require_fundamentals": True
    }
)
```

The result becomes the input to:

```text
Step 2 — Data Quality & Validation
```

and later:

```text
Returns
Risk
Momentum
Factors
Signals
Portfolio Construction
Backtesting
```

---

# Step 1 Completion Criteria

Universe Definition is complete when Open Analytics can reliably answer:

1. What instruments exist?
2. Which are actual common equities?
3. Which listings correspond to the same company?
4. Which listing should be used as the primary market listing?
5. Is the security currently active?
6. Is it currently tradable?
7. How much valid history exists?
8. Is liquidity sufficient?
9. What is its market-cap classification?
10. Which sector and industry does it belong to?
11. Which indices does it belong to?
12. Is it F&O eligible?
13. Which datasets are available?
14. Is it research eligible?
15. Is it trading eligible?
16. Why was it excluded?
17. Which named universes does it belong to?
18. Was it eligible on any requested historical date?

Once all eighteen questions can be answered consistently, **Step 1 — Universe Definition** is ready to support the rest of the Open Analytics quant pipeline.
