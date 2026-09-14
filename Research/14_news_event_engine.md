# Open Analytics — Step 14: News & Event Engine

## Purpose

The **News & Event Engine** converts unstructured market news, company announcements, filings, exchange disclosures, and external events into structured, time-aware quantitative features.

The engine should answer:

- What happened?
- Which company/security does the event affect?
- When did the information become public?
- Is the event positive, negative, or neutral?
- How important is the event?
- Is it new information or a duplicate/rewrite?
- Is it company-specific, sector-wide, or market-wide?
- Is the event confirmed by a reliable source?
- How quickly should the signal decay?
- Did price already react before the article timestamp?
- Does the event materially change expected earnings, cash flow, risk, or valuation?
- Is there a measurable post-event drift or reversal?
- How does current news flow compare with the stock's historical norm?

The outputs feed directly into:

- Alpha / Signal Engine
- Event-driven strategies
- Earnings strategies
- Risk controls
- Regime detection
- Stock screening
- Machine learning features
- Event attribution

---

# 14.1 Core Principle

News is not just sentiment.

The engine should separate:

```text
Entity
Timestamp
Event Type
Sentiment
Relevance
Novelty
Severity
Surprise
Source Quality
Confirmation
Decay
Market Reaction
```

A positive article with low novelty may have less value than a neutral but highly material regulatory filing.

---

# 14.2 Required Input Data

Minimum:

```text
article_id
source
published_at
headline
body_or_summary
url_or_source_reference
```

Preferred:

```text
author
source_type
exchange_announcement_flag
filing_flag
language
region

related_symbols
related_isins
company_names
sector
industry

raw_timestamp
ingestion_timestamp
```

Optional:

```text
social media
broker research
earnings transcript
management commentary
conference call
regulatory filing
exchange circular
```

---

# 14.3 Point-in-Time Rule

Use:

```text
public_available_at
```

not:

```text
database_ingested_at
```

for research/backtesting.

The information becomes usable only when it was publicly available.

Store:

```text
published_at
first_seen_at
public_available_at
ingested_at
```

---

# 14.4 Timezone Normalization

Normalize all timestamps to a standard timezone.

Recommended storage:

```text
UTC
```

Display may convert to:

```text
Asia/Kolkata
```

Store source timezone where needed.

---

# 14.5 News Source Types

Classify:

```text
EXCHANGE_ANNOUNCEMENT
REGULATORY_FILING
COMPANY_PRESS_RELEASE
NEWS_WIRE
FINANCIAL_MEDIA
GENERAL_MEDIA
BROKER_RESEARCH
TRANSCRIPT
SOCIAL_MEDIA
OTHER
```

Source type affects confidence.

---

# 14.6 Source Quality Score

Possible inputs:

```text
official source
historical reliability
direct vs secondary reporting
timestamp quality
duplicate history
retraction rate
```

Output:

```text
source_quality_score
```

Recommended:

```text
0 to 100
```

---

# 14.7 Entity Resolution

Map each article/event to one or more securities.

Use:

```text
company_name
symbol
ISIN
instrument_key
aliases
subsidiaries
brands
management names
```

Output:

```text
resolved_company_id
resolved_instrument_keys
entity_confidence
```

---

# 14.8 Multi-Entity News

One article may affect:

```text
multiple companies
sector
index
commodity
macro market
```

Store separate entity-event links.

Example:

```text
article_id
entity_id
relevance_score
```

---

# 14.9 Entity Relevance Score

Not every mentioned company is equally important.

Possible:

```text
0 to 100
```

Inputs:

```text
headline mention
first paragraph prominence
mention frequency
event role
named target/acquirer
```

---

# 14.10 Event Taxonomy

Recommended high-level event classes:

```text
EARNINGS
GUIDANCE
ORDER_WIN
ORDER_LOSS
CONTRACT
M_AND_A
STAKE_SALE
FUND_RAISE
BUYBACK
DIVIDEND
SPLIT
BONUS
RIGHTS_ISSUE
MANAGEMENT_CHANGE
BOARD_CHANGE
REGULATORY
LEGAL
FRAUD
GOVERNANCE
CREDIT_RATING
DEBT
DEFAULT
PRODUCT_LAUNCH
CAPACITY_EXPANSION
CAPEX
PLANT_SHUTDOWN
LABOUR
CYBERSECURITY
ACCIDENT
ESG
MACRO
SECTOR
ANALYST_ACTION
INSIDER_ACTIVITY
OTHER
```

---

# 14.11 Event Subtypes

Example under EARNINGS:

```text
REVENUE_BEAT
REVENUE_MISS
EPS_BEAT
EPS_MISS
MARGIN_EXPANSION
MARGIN_COMPRESSION
GUIDANCE_RAISED
GUIDANCE_CUT
```

Detailed taxonomy improves modeling.

---

# 14.12 Event Materiality

Estimate economic importance.

Possible:

```text
materiality_score
```

Inputs:

```text
event type
deal value
order value
revenue impact
earnings impact
legal exposure
management importance
balance-sheet impact
```

---

# 14.13 Sentiment

Store at least:

```text
sentiment_score
```

Possible range:

```text
-1 to +1
```

or:

```text
0 to 100
```

Prefer one internal standard.

---

# 14.14 Sentiment Labels

Possible:

```text
VERY_NEGATIVE
NEGATIVE
NEUTRAL
POSITIVE
VERY_POSITIVE
```

Keep continuous score as primary.

---

# 14.15 Event-Specific Sentiment

Generic language sentiment is not enough.

Example:

```text
"Company cuts costs by closing loss-making unit"
```

may contain negative words but be economically positive.

Use event-aware interpretation where possible.

---

# 14.16 Relevance-Weighted Sentiment

Possible:

```text
weighted_sentiment =
sentiment × relevance
```

This reduces impact from incidental mentions.

---

# 14.17 Materiality-Weighted Sentiment

Possible:

```text
materiality_weighted_sentiment =
sentiment × materiality
```

---

# 14.18 Novelty

News value decreases if it repeats known information.

Calculate:

```text
novelty_score
```

Inputs:

```text
headline similarity
body similarity
same-event clustering
time since first article
```

---

# 14.19 Duplicate Detection

Identify:

```text
exact duplicate
syndicated copy
rewritten duplicate
same-event follow-up
```

Store:

```text
duplicate_flag
duplicate_group_id
```

---

# 14.20 First-Source Detection

For an event cluster:

```text
first_publication_timestamp
first_source
```

Later rewrites should not be treated as new independent alpha events.

---

# 14.21 Event Clustering

Cluster articles into one event.

Example:

```text
event_cluster_id
```

One earnings result may generate hundreds of articles.

The factor should avoid counting all as separate events.

---

# 14.22 Confirmation Count

Track:

```text
independent_source_count
```

Useful to distinguish rumor from confirmed event.

---

# 14.23 Rumor Flag

Possible:

```text
rumor_flag
```

Inputs:

```text
source type
language
confirmation
company denial/confirmation
```

Rumor events should usually receive lower confidence.

---

# 14.24 Official Confirmation

Track:

```text
official_confirmation_flag
official_confirmation_timestamp
```

Official exchange/company disclosure can materially increase confidence.

---

# 14.25 Event Surprise

For events with expected values:

```text
surprise =
actual - expected
```

Examples:

```text
EPS surprise
revenue surprise
order-value surprise
guidance surprise
```

Normalize where appropriate.

---

# 14.26 Earnings Surprise

Recommended:

```text
eps_surprise_pct
revenue_surprise_pct
ebitda_surprise_pct
margin_surprise
```

Point-in-time analyst expectations are required.

---

# 14.27 Guidance Surprise

Possible:

```text
guidance_delta
guidance_surprise_score
```

Compare:

```text
new guidance
vs
prior guidance / consensus
```

---

# 14.28 Order-Win Materiality

For contract wins:

```text
order_value / annual_revenue
```

Store:

```text
order_to_revenue_ratio
```

This is more meaningful than order size alone.

---

# 14.29 Fund-Raise Materiality

Possible:

```text
fund_raise_value / market_cap
```

and:

```text
dilution_estimate
```

---

# 14.30 M&A Materiality

Possible:

```text
deal_value / market_cap
```

plus:

```text
acquirer_or_target
cash_or_stock
control_change_flag
```

---

# 14.31 Credit Event Severity

Examples:

```text
upgrade
downgrade
default
watch negative
watch positive
```

Store:

```text
credit_event_score
```

---

# 14.32 Management Change Severity

Differentiate:

```text
routine board appointment
CEO resignation
CFO resignation
promoter exit
auditor resignation
```

Potential:

```text
management_event_severity
```

---

# 14.33 Governance Risk Event

Possible:

```text
auditor resignation
fraud allegation
regulatory investigation
related-party concern
promoter pledge issue
```

Store:

```text
governance_risk_score
```

---

# 14.34 Legal / Regulatory Severity

Possible:

```text
fine
license issue
ban
court judgment
regulatory approval
regulatory rejection
```

Store:

```text
regulatory_event_score
```

---

# 14.35 Event Decay

News impact usually decays with time.

Possible:

```text
decayed_event_score =
initial_score × exp(-lambda × time_since_event)
```

Different event types should have different decay speeds.

Examples:

```text
rumor → fast decay
earnings → slower decay
fraud/regulatory → potentially long decay
```

---

# 14.36 Half-Life by Event Type

Metadata:

```text
event_type
default_half_life
```

Example:

```text
ANALYST_ACTION      3 days
EARNINGS           10 days
REGULATORY         20 days
GOVERNANCE         30 days
```

These are research parameters, not fixed universal truths.

---

# 14.37 News Velocity

Measure count of relevant events/articles:

```text
news_count_1h
news_count_24h
news_count_7d
```

Use event clusters, not raw duplicate article counts where possible.

---

# 14.38 News Volume Z-Score

```text
news_volume_z
```

Compare current event activity to historical baseline.

---

# 14.39 Positive / Negative News Counts

Store:

```text
positive_news_count_24h
negative_news_count_24h

positive_news_count_7d
negative_news_count_7d
```

Again, cluster duplicates.

---

# 14.40 Net News Sentiment

Possible:

```text
net_news_sentiment =
weighted positive sentiment
-
weighted negative sentiment
```

---

# 14.41 News Sentiment 24H / 7D

Recommended:

```text
news_sentiment_24h
news_sentiment_7d
news_sentiment_30d
```

Weight by:

```text
relevance
materiality
novelty
source quality
decay
```

---

# 14.42 News Momentum

Measure whether sentiment is improving.

Example:

```text
news_sentiment_change =
sentiment_24h - sentiment_prior_7d_baseline
```

Store:

```text
news_momentum_score
```

---

# 14.43 News Reversal

Possible when:

```text
recent sentiment strongly positive
but latest high-materiality event negative
```

Store:

```text
news_reversal_flag
```

---

# 14.44 Event Intensity

Possible:

```text
event_intensity =
frequency × materiality × novelty
```

Store:

```text
event_intensity_score
```

---

# 14.45 Price Reaction

For every event, calculate post-event returns:

```text
event_return_5m
event_return_30m
event_return_1h
event_return_1d
event_return_5d
event_return_21d
```

depending on available price frequency.

---

# 14.46 Abnormal Return

Compare stock reaction with benchmark/sector.

```text
abnormal_return =
stock_return - expected/benchmark_return
```

Store:

```text
event_abnormal_return_1d
event_abnormal_return_5d
```

---

# 14.47 Pre-Event Return

Measure potential anticipation/leakage:

```text
pre_event_return_1d
pre_event_return_5d
```

Large pre-event moves can indicate information was partially priced before publication.

---

# 14.48 Event Drift

Track post-event continuation:

```text
post_event_drift_5d
post_event_drift_21d
post_event_drift_63d
```

Especially useful for earnings surprise research.

---

# 14.49 Event Reversal

Possible:

```text
initial reaction positive
subsequent 5D return negative
```

Store:

```text
event_reversal_flag
```

---

# 14.50 Volume Reaction

Use Step 9:

```text
event_rvol
event_volume_z
```

A material news event with no participation response differs from one with extreme volume.

---

# 14.51 Volatility Reaction

Use Step 5:

```text
event_volatility_change
```

---

# 14.52 Gap Reaction

Use Step 4:

```text
event_overnight_gap
```

Useful for after-hours or pre-market announcements.

---

# 14.53 Event Confirmation by Market

Possible composite:

```text
market_confirmation_score
```

Inputs:

```text
abnormal return
RVOL
spread/depth change
volatility change
```

---

# 14.54 News Factor Score

Potential components:

```text
sentiment
materiality
novelty
relevance
source quality
decay
market confirmation
```

Conceptually:

```text
news_factor_score
```

---

# 14.55 Event Risk Score

Separate from alpha-oriented news score.

Possible inputs:

```text
governance
legal
regulatory
credit
management
operational disruption
```

Output:

```text
event_risk_score
```

---

# 14.56 Positive Catalyst Score

Possible:

```text
positive_catalyst_score
```

Examples:

```text
earnings beat
guidance raise
large order win
regulatory approval
buyback
rating upgrade
```

---

# 14.57 Negative Catalyst Score

Possible:

```text
negative_catalyst_score
```

Examples:

```text
earnings miss
guidance cut
fraud allegation
default
regulatory ban
auditor resignation
```

---

# 14.58 Event Confidence

Possible:

```text
event_confidence
```

Inputs:

```text
source quality
entity confidence
official confirmation
independent source count
novelty
data completeness
```

---

# 14.59 Headline vs Body Sentiment

Store separately if useful:

```text
headline_sentiment
body_sentiment
```

Headline alone can be misleading.

---

# 14.60 Language Handling

Support source language metadata.

If translation is used, store:

```text
original_language
translation_used
translation_quality
```

---

# 14.61 Sector News

Some events affect entire sectors.

Example:

```text
government policy
commodity shock
regulation
tariff
```

Store:

```text
sector_event_flag
affected_sector
```

---

# 14.62 Macro News

Possible:

```text
RBI decision
inflation
GDP
currency
crude oil
global rates
```

Macro events belong partly in market regime, but entity mapping can connect them to affected industries.

---

# 14.63 Commodity Linkage

For relevant sectors:

```text
crude
steel
aluminium
gold
natural gas
```

Store:

```text
commodity_event_link
```

---

# 14.64 Supply Chain Events

Potential:

```text
supplier disruption
customer loss
raw-material shock
logistics disruption
```

Useful where entity graph exists.

---

# 14.65 Parent / Subsidiary Mapping

News may mention:

```text
subsidiary
parent company
joint venture
promoter entity
```

Maintain relationship graph to propagate relevance carefully.

---

# 14.66 Management Entity Mapping

Track key people:

```text
CEO
CFO
Chairperson
Promoter
Auditor
```

This helps resolve management news.

---

# 14.67 Historical Event Store

Recommended record:

```text
event_id
event_cluster_id

published_at
public_available_at

source
source_type
source_quality_score

event_type
event_subtype

sentiment_score
relevance_score
materiality_score
novelty_score

event_confidence

company_id
instrument_key
sector_id

duplicate_flag
official_confirmation_flag

event_text_reference
```

---

# 14.68 Per-Stock Daily News Feature Record

```text
instrument_key
date

news_count_24h
news_count_7d

positive_news_count_24h
negative_news_count_24h

news_sentiment_24h
news_sentiment_7d

news_momentum_score

event_intensity_score

positive_catalyst_score
negative_catalyst_score

event_risk_score
news_factor_score

news_quality_status
```

---

# 14.69 Event-Level Reaction Record

```text
event_id
instrument_key

pre_event_return_1d
pre_event_return_5d

event_return_1d
event_return_5d
event_return_21d

event_abnormal_return_1d
event_abnormal_return_5d

event_rvol
event_volatility_change

event_reversal_flag
```

---

# 14.70 News Quality Status

Possible:

```text
VALID
LOW_SOURCE_QUALITY
LOW_ENTITY_CONFIDENCE
DUPLICATE
LOW_NOVELTY
MISSING_TIMESTAMP
UNCONFIRMED_RUMOR
STALE_EVENT
INVALID
```

---

# 14.71 Missing Timestamp Handling

If exact publish time is unknown:

```text
event_intraday_eligible = false
```

but daily event research may still be possible if date is known.

---

# 14.72 Duplicate Handling Rule

Do not sum 50 syndicated copies as 50 independent signals.

Cluster them into one event and use:

```text
source_count
confirmation_count
```

as separate features.

---

# 14.73 Rumor vs Confirmed Event

Keep:

```text
rumor_score
confirmation_status
```

separate from sentiment.

---

# 14.74 Point-in-Time Backtesting

At timestamp T, only use events with:

```text
public_available_at <= T
```

No later corrected article or updated summary should leak backward.

---

# 14.75 Retractions and Corrections

Store:

```text
retracted_flag
correction_flag
correction_timestamp
```

Historical models should reflect what was known before correction.

---

# 14.76 Source Revisions

Some articles update after publication.

Store versions when possible:

```text
article_version
version_timestamp
```

---

# 14.77 Event Taxonomy Versioning

Taxonomy may evolve.

Store:

```text
event_taxonomy_version
```

for reproducibility.

---

# 14.78 Model Versioning

If NLP/LLM models are used for classification:

```text
classifier_version
sentiment_model_version
entity_model_version
```

Store model versions with outputs.

---

# 14.79 Manual Review Flag

High-severity events may require:

```text
manual_review_required
```

Examples:

```text
fraud
default
regulatory ban
merger
delisting
```

---

# 14.80 Event Exclusion Rules

Possible exclusions:

```text
duplicate
irrelevant mention
low entity confidence
very low source quality
stale repost
```

Do not permanently delete them; retain audit trail.

---

# 14.81 Initial Production Event Types

Start with economically material classes:

```text
EARNINGS
GUIDANCE
ORDER_WIN
M_AND_A
FUND_RAISE
BUYBACK
DIVIDEND
MANAGEMENT_CHANGE
REGULATORY
LEGAL
FRAUD
CREDIT_RATING
DEFAULT
PRODUCT_LAUNCH
CAPACITY_EXPANSION
```

---

# 14.82 Initial Production Metrics

Recommended first production set:

```text
event_type
event_subtype

sentiment_score
relevance_score
materiality_score
novelty_score
source_quality_score
event_confidence

news_count_24h
news_count_7d

positive_news_count_24h
negative_news_count_24h

news_sentiment_24h
news_sentiment_7d

event_intensity_score

positive_catalyst_score
negative_catalyst_score
event_risk_score

news_factor_score

event_abnormal_return_1d
event_abnormal_return_5d

event_rvol

news_quality_status
```

Then expand into:

```text
intraday reaction
transcripts
analyst revisions
social sources
relationship propagation
```

---

# 14.83 News & Event Engine Processing Flow

Recommended:

```text
RAW NEWS / FILINGS / ANNOUNCEMENTS
        ↓
TIMESTAMP NORMALIZATION
        ↓
SOURCE CLASSIFICATION
        ↓
ENTITY RESOLUTION
        ↓
DUPLICATE / EVENT CLUSTERING
        ↓
EVENT CLASSIFICATION
        ↓
SENTIMENT
        ↓
RELEVANCE
        ↓
MATERIALITY
        ↓
NOVELTY
        ↓
CONFIRMATION / SOURCE QUALITY
        ↓
EVENT SURPRISE
        ↓
DECAY MODEL
        ↓
DAILY NEWS AGGREGATION
        ↓
PRICE / VOLUME / VOLATILITY REACTION
        ↓
NEWS FACTOR SCORE
        ↓
EVENT RISK SCORE
        ↓
QUALITY FLAGS
```

---

# 14.84 Important Quant Rules

## Rule 1 — News Is More Than Sentiment

Event type, novelty, materiality, and timing matter.

---

## Rule 2 — First Publication Matters

Do not count later rewrites as fresh independent alpha.

---

## Rule 3 — Use Public Availability Time

Ingestion time is not the correct backtest timestamp.

---

## Rule 4 — Duplicate Clustering Is Mandatory

Syndication can otherwise massively overstate news intensity.

---

## Rule 5 — Official Sources Deserve Higher Confidence

But official does not automatically mean positive or negative.

---

## Rule 6 — Sentiment Must Be Entity-Specific

A positive article about a competitor can be negative for the mapped stock.

---

## Rule 7 — Materiality Matters

A tiny order win and a transformative acquisition should not receive equal weight.

---

## Rule 8 — Event Decay Must Be Type-Specific

Different information persists for different lengths of time.

---

## Rule 9 — Keep Alpha and Risk Separate

Positive catalyst score and event-risk score are different concepts.

---

## Rule 10 — Do Not Leak Revisions Backward

Corrections, retractions, and updated articles must remain time-versioned.

---

## Rule 11 — Market Reaction Is Context, Not Ground Truth

A price move can confirm or reject interpretation, but market reaction itself can be noisy.

---

## Rule 12 — Keep the Audit Trail

Every structured event should trace back to the raw source.

---

# 14.85 Completion Criteria

Step 14 is complete when Open Analytics can answer:

1. What event occurred?
2. Which company/security does it affect?
3. When did the information become public?
4. What is the event type and subtype?
5. What is the sentiment?
6. How relevant is it to the stock?
7. How material is it economically?
8. Is the information genuinely new?
9. Is it duplicated or syndicated?
10. Is the event officially confirmed?
11. How reliable is the source?
12. How confident is the entity/event mapping?
13. Is there measurable surprise versus expectations?
14. How should the event decay over time?
15. What is the 24H and 7D news sentiment?
16. Is news flow accelerating?
17. Is there a positive or negative catalyst?
18. Is there a governance/regulatory/event risk?
19. How did price react?
20. How did volume react?
21. Was the stock already moving before publication?
22. Is there post-event drift or reversal?
23. What is the final news factor score?
24. Can the exact historical news state be reproduced without look-ahead?

Once these are reliable, the News & Event Engine is ready to feed:

```text
Step 15 — Institutional Flow Engine
```

---

# Step 14 Final Output

The News & Event Engine transforms:

```text
News
+
Exchange Announcements
+
Filings
+
Company Disclosures
+
External Events
```

into:

```text
Entity-Mapped Events
Event Types
Sentiment
Relevance
Materiality
Novelty
Source Quality
Confirmation
Surprise
Decay
News Velocity
Catalyst Scores
Event Risk Scores
Post-Event Reactions
News Factor Scores
News Quality Flags
```

This becomes the unstructured-information and event-driven layer for Open Analytics.
