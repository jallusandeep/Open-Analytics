# Open Analytics — Step 12: Valuation Engine

## Purpose

The **Valuation Engine** measures how expensive or cheap a security is relative to its own fundamentals, history, peers, sector, industry, and growth profile.

This engine should answer:

- Is the stock expensive or cheap on earnings?
- Is it expensive or cheap on book value?
- How does enterprise value compare with operating earnings?
- What cash-flow yield does the stock offer?
- How does current valuation compare with its own history?
- How does it compare with sector and industry peers?
- Is the valuation justified by growth and quality?
- Is a low valuation caused by genuine cheapness or financial distress?
- Are the required fundamentals and prices point-in-time correct?
- Which valuation measures are economically meaningful for this company?

Valuation outputs feed directly into:

- Value factors
- Quality-at-a-reasonable-price models
- Alpha signals
- Stock screening
- Portfolio construction
- Fundamental research
- Machine learning features

---

# 12.1 Core Principle

Valuation is relative.

A raw P/E of:

```text
25x
```

does not tell enough by itself.

The engine should compare valuation against:

```text
Own history
Sector peers
Industry peers
Market
Growth
Quality
Profitability
Interest-rate environment
```

The same multiple can mean very different things for different companies.

---

# 12.2 Required Inputs

From market data:

```text
instrument_key
date

price
market_cap
free_float_market_cap
shares_outstanding
```

From Step 11:

```text
revenue_ttm
ebitda_ttm
ebit_ttm
net_income_ttm
eps_ttm

book_value
shareholders_equity

operating_cash_flow_ttm
free_cash_flow_ttm

total_debt
cash
net_debt

growth metrics
quality metrics
```

Optional:

```text
forward estimates
analyst consensus
dividends
enterprise value inputs
minority interest
preferred equity
```

---

# 12.3 Point-in-Time Requirement

Valuation must use:

```text
market price at date T
+
fundamental information publicly available at date T
```

Do not combine:

```text
historical price
+
future financial statement
```

That creates look-ahead bias.

---

# 12.4 Market Capitalization

Basic:

```text
market_cap =
price × shares_outstanding
```

Prefer point-in-time diluted share count where available.

Store:

```text
market_cap
```

---

# 12.5 Enterprise Value

Typical:

```text
enterprise_value =
market_cap
+ total_debt
+ preferred_equity
+ minority_interest
- cash
```

If some components are unavailable, document the simplified formula.

Store:

```text
enterprise_value
```

---

# 12.6 Price to Earnings

```text
pe_ttm =
price / eps_ttm
```

or equivalently:

```text
market_cap / net_income_ttm
```

Store:

```text
pe_ttm
```

Do not treat negative earnings as a normal positive P/E.

Use:

```text
pe_valid = false
```

when economically meaningless.

---

# 12.7 Forward P/E

If consensus estimates exist:

```text
forward_pe =
price / forward_eps
```

Possible:

```text
forward_pe_fy1
forward_pe_fy2
```

Estimate timestamp must be point-in-time.

---

# 12.8 Earnings Yield

Inverse of P/E:

```text
earnings_yield =
net_income_ttm / market_cap
```

or:

```text
eps_ttm / price
```

Store:

```text
earnings_yield
```

This is often easier to normalize and combine than P/E.

Higher is generally cheaper, subject to quality/distress checks.

---

# 12.9 Price to Book

```text
pb =
market_cap / shareholders_equity
```

or:

```text
price / book_value_per_share
```

Store:

```text
price_to_book
```

Most useful in sectors where book value is economically meaningful.

---

# 12.10 Book-to-Price

Inverse:

```text
book_to_price =
shareholders_equity / market_cap
```

This often behaves better in factor models because higher = cheaper.

---

# 12.11 Price to Sales

```text
price_to_sales =
market_cap / revenue_ttm
```

Store:

```text
price_to_sales
```

Useful when profits are weak or temporarily depressed.

---

# 12.12 Sales Yield

Inverse:

```text
sales_yield =
revenue_ttm / market_cap
```

---

# 12.13 EV to EBITDA

```text
ev_to_ebitda =
enterprise_value / ebitda_ttm
```

Store:

```text
ev_ebitda
```

Invalid or unstable when EBITDA <= 0.

---

# 12.14 EBITDA to EV

Inverse:

```text
ebitda_to_ev =
ebitda_ttm / enterprise_value
```

Useful for value-factor construction.

---

# 12.15 EV to EBIT

```text
ev_to_ebit =
enterprise_value / ebit_ttm
```

Store:

```text
ev_ebit
```

---

# 12.16 EBIT to EV

Inverse:

```text
ebit_to_ev =
ebit_ttm / enterprise_value
```

This is a common quality/value-style factor input.

---

# 12.17 EV to Sales

```text
ev_to_sales =
enterprise_value / revenue_ttm
```

Store:

```text
ev_sales
```

---

# 12.18 Free Cash Flow Yield

```text
fcf_yield =
free_cash_flow_ttm / market_cap
```

Store:

```text
fcf_yield
```

Higher positive values generally indicate cheaper cash-flow valuation.

---

# 12.19 Enterprise FCF Yield

Optional:

```text
enterprise_fcf_yield =
free_cash_flow_to_firm / enterprise_value
```

Requires consistent FCFF calculation.

---

# 12.20 Operating Cash Flow Yield

```text
ocf_yield =
operating_cash_flow_ttm / market_cap
```

Useful as a cash-based complement to earnings yield.

---

# 12.21 Dividend Yield

```text
dividend_yield =
dividends_per_share_ttm / price
```

Store:

```text
dividend_yield
```

Do not treat high dividend yield as automatically attractive.

Check:

```text
payout sustainability
cash flow
special dividends
```

---

# 12.22 Shareholder Yield

Potential broader measure:

```text
shareholder_yield =
dividend_yield
+
net_buyback_yield
-
dilution_yield
```

This is more advanced but useful later.

---

# 12.23 Net Payout Yield

Possible:

```text
net_payout_yield =
(dividends + net_buybacks)
/
market_cap
```

---

# 12.24 PEG Ratio

Basic:

```text
PEG =
P/E / expected_growth_rate
```

This is sensitive to growth assumptions.

Use only when growth denominator is positive and meaningful.

Store:

```text
peg
```

Do not rely on it as a primary value factor.

---

# 12.25 Growth-Adjusted Earnings Yield

Alternative concept:

```text
growth_adjusted_value =
earnings_yield + growth
```

or more robust research formulations.

This should be explicitly defined if used.

---

# 12.26 EV / Growth Metrics

Possible:

```text
ev_sales_to_growth
ev_ebitda_to_growth
```

Useful only with stable positive growth.

---

# 12.27 Historical Valuation Percentile

For each stock, compare current valuation to its own history.

Example:

```text
pe_historical_percentile_5y
```

Interpretation:

```text
20
→ current P/E is cheaper than roughly 80% of its own 5Y observations
```

Choose convention carefully.

Recommended user-facing value percentile:

```text
100 = cheapest / most attractive
0 = most expensive
```

---

# 12.28 Historical Valuation Z-Score

For each stock:

```text
pe_hist_z
pb_hist_z
ev_ebitda_hist_z
fcf_yield_hist_z
```

Use robust z-score where distributions are skewed.

---

# 12.29 Own-History Median Comparison

Store:

```text
pe_vs_5y_median
pb_vs_5y_median
ev_ebitda_vs_5y_median
```

Example:

```text
current PE = 24
5Y median PE = 32

PE discount to history ≈ 25%
```

---

# 12.30 Sector Valuation Percentile

Compare valuation within sector:

```text
sector_pe_percentile
sector_ev_ebitda_percentile
sector_fcf_yield_percentile
```

This is often more meaningful than broad-market comparison.

---

# 12.31 Industry Valuation Percentile

Likewise:

```text
industry_pe_percentile
industry_ev_ebitda_percentile
industry_fcf_yield_percentile
```

---

# 12.32 Market Valuation Percentile

Compare against full universe:

```text
market_value_percentile
```

Useful, but sector context must not be ignored.

---

# 12.33 Size-Peer Valuation

Compare companies of similar market cap.

Store:

```text
size_peer_value_percentile
```

This can reduce structural small-cap/large-cap valuation differences.

---

# 12.34 Sector-Neutral Valuation

Use Step 10 neutralization methods.

Examples:

```text
sector_neutral_earnings_yield_z
sector_neutral_fcf_yield_z
sector_neutral_book_to_price_z
```

---

# 12.35 Industry-Neutral Valuation

Similarly:

```text
industry_neutral_value_z
```

---

# 12.36 Composite Value Factor

Possible components:

```text
earnings_yield
book_to_price
ebit_to_ev
fcf_yield
sales_yield
```

Normalize first.

Conceptually:

```text
value_factor_score =
average(
    z(earnings_yield),
    z(book_to_price),
    z(ebit_to_ev),
    z(fcf_yield)
)
```

Weights should be researched and versioned.

---

# 12.37 Valuation Validity Rules

A valuation ratio should only be used when economically meaningful.

Examples:

```text
P/E invalid when earnings <= 0
EV/EBITDA invalid when EBITDA <= 0
P/B problematic when equity <= 0
FCF yield can be negative and still valid
```

Store:

```text
valuation_metric_valid
valuation_invalid_reason
```

---

# 12.38 Distress Trap Handling

A very low multiple can indicate:

```text
distress
cyclical peak earnings
governance concerns
structural decline
high leverage
temporary accounting effects
```

Therefore value scores should later be combined with:

```text
quality
balance sheet strength
earnings trend
cash flow
```

This helps reduce value traps.

---

# 12.39 Cyclical Earnings Normalization

For cyclical sectors, current earnings may be unusually high or low.

Possible future measures:

```text
normalized_earnings
mid_cycle_earnings
5y_average_earnings
```

Then:

```text
normalized_pe
normalized_ev_ebitda
```

This is advanced and sector-specific.

---

# 12.40 Negative Earnings Handling

Do not calculate nonsensical negative P/E rankings.

Possible approach:

```text
pe_ttm = null
earnings_yield = negative valid value
```

Earnings yield may remain informative in some models.

---

# 12.41 Negative Book Value

If:

```text
shareholders_equity <= 0
```

then:

```text
P/B = invalid
```

Flag explicitly.

---

# 12.42 Negative Enterprise Value

Possible for cash-rich companies.

Handle carefully.

Store:

```text
enterprise_value
ev_negative_flag
```

Some EV ratios become unusual or invalid.

---

# 12.43 FCF Negative but Improving

Negative FCF should not be hidden.

Store:

```text
fcf_yield
fcf_trend
```

A negative but rapidly improving FCF profile may differ from persistent cash burn.

---

# 12.44 Valuation Trend

Track:

```text
pe_change_1m
pe_change_3m
pe_change_1y

ev_ebitda_change
fcf_yield_change
```

This shows re-rating or de-rating.

---

# 12.45 Multiple Expansion / Compression

Separate price movement from fundamental change.

Conceptually:

```text
price_return
≈
earnings_growth
+
multiple_change
```

Estimate:

```text
multiple_expansion
multiple_compression
```

Useful for attribution.

---

# 12.46 Earnings Growth vs P/E Change

Example decomposition:

```text
Stock return strong
EPS growth strong
P/E flat
```

versus:

```text
Stock return strong
EPS flat
P/E expanded sharply
```

The second is more valuation-driven.

---

# 12.47 Re-Rating Score

Possible:

```text
rerating_score
```

based on:

```text
valuation multiple expansion
relative price performance
fundamental changes
```

This is a later feature.

---

# 12.48 Quality-Adjusted Value

A cheap high-quality stock may deserve a different score than a cheap low-quality stock.

Possible composite:

```text
quality_adjusted_value =
value_score + quality_score
```

or interaction terms.

Do not implement arbitrary weights without research.

---

# 12.49 Growth-Adjusted Value

Similarly:

```text
growth_adjusted_value
```

using:

```text
value
growth
profitability
```

This can form QARP-style models.

---

# 12.50 Value + Momentum Interaction

A cheap stock with deteriorating momentum differs from a cheap stock with improving momentum.

Potential later feature:

```text
value_momentum_combination
```

---

# 12.51 Value + Risk Interaction

Cheapness caused by distress may show:

```text
high leverage
high volatility
deep drawdown
```

Potential:

```text
risk_adjusted_value_score
```

---

# 12.52 Valuation Breadth

At universe level, calculate:

```text
median PE
median PB
median EV/EBITDA
median earnings yield
median FCF yield
```

By:

```text
market
sector
industry
size bucket
```

Useful for market regime and relative valuation context.

---

# 12.53 Valuation Dispersion

Store:

```text
valuation_std
valuation_mad
p10
p50
p90
```

High dispersion can indicate differentiated opportunity.

---

# 12.54 Historical Market Valuation

Track broad market:

```text
market_median_pe_history
market_value_percentile
```

This can later feed market regime models.

---

# 12.55 Interest Rate Context

Valuation often interacts with rates.

Potential future context:

```text
earnings_yield_minus_risk_free_rate
```

or:

```text
equity_yield_spread
```

Do not hard-code one rate permanently.

---

# 12.56 Earnings Yield Spread

Example:

```text
earnings_yield_spread =
earnings_yield - risk_free_rate
```

Useful as a rough relative attractiveness measure.

---

# 12.57 FCF Yield Spread

Similarly:

```text
fcf_yield_spread =
fcf_yield - risk_free_rate
```

---

# 12.58 Forward Valuation

If analyst estimates exist:

```text
forward_pe
forward_ev_ebitda
forward_fcf_yield
```

Each estimate must have:

```text
estimate_date
data_available_date
```

to remain point-in-time.

---

# 12.59 Estimate Dispersion

A forward multiple built on uncertain consensus should expose uncertainty.

Possible:

```text
eps_estimate_dispersion
```

High dispersion means forward valuation is less reliable.

---

# 12.60 Sector-Specific Valuation

Different sectors need different preferred metrics.

Examples:

## Banks / Financials

Commonly useful:

```text
P/B
P/E
ROE
ROA
```

Enterprise-value metrics may be less meaningful.

## Capital-Intensive Industrials

Useful:

```text
EV/EBITDA
EV/EBIT
FCF yield
```

## High-Growth Software

Potential:

```text
EV/Sales
FCF yield
growth-adjusted valuation
```

## Commodity/Cyclical

May require:

```text
mid-cycle earnings
normalized EBITDA
```

Use a metric registry by sector.

---

# 12.61 Valuation Metric Registry

Recommended metadata:

```text
metric_name
applicable_sector
formula

direction
validity_rule

preferred_peer_group

winsorization_method
normalization_method

version
```

---

# 12.62 Valuation Quality Status

Possible:

```text
VALID
NEGATIVE_EARNINGS
NEGATIVE_EQUITY
NEGATIVE_EBITDA
STALE_FUNDAMENTALS
INSUFFICIENT_HISTORY
FORWARD_ESTIMATE_STALE
MISSING_ENTERPRISE_VALUE_INPUT
```

Store:

```text
valuation_quality_status
```

---

# 12.63 Fundamental Staleness Protection

Valuation uses market price daily but fundamentals update quarterly.

Track:

```text
days_since_fundamental_update
```

and:

```text
valuation_staleness_flag
```

This does not necessarily invalidate valuation, but it should reduce confidence when data becomes unusually stale.

---

# 12.64 Corporate Action Handling

Price and shares outstanding must be adjusted consistently around:

```text
splits
bonus issues
rights issues
buybacks
issuance
```

Otherwise market cap and per-share ratios can be wrong.

---

# 12.65 Point-in-Time Shares Outstanding

Use historical share count.

Do not use today's shares outstanding for old dates.

---

# 12.66 Survivorship Bias Protection

Historical value ranks must include securities eligible at the time even if they later:

```text
failed
delisted
merged
became distressed
```

Otherwise value backtests will be biased.

---

# 12.67 Look-Ahead Protection

At date T:

```text
valuation
```

may only use:

```text
price known at T
fundamentals known at T
estimates known at T
shares known at T
sector mapping known at T
```

---

# 12.68 Recommended Daily Valuation Record

A daily valuation record could include:

```text
instrument_key
date


# MARKET VALUE

price
shares_outstanding
market_cap

enterprise_value


# EARNINGS VALUATION

pe_ttm
forward_pe_fy1

earnings_yield


# BOOK VALUE

price_to_book
book_to_price


# SALES

price_to_sales
sales_yield

ev_sales


# OPERATING EARNINGS

ev_ebitda
ebitda_to_ev

ev_ebit
ebit_to_ev


# CASH FLOW

fcf_yield
ocf_yield

dividend_yield
shareholder_yield


# GROWTH ADJUSTMENT

peg
growth_adjusted_value


# OWN HISTORY

pe_hist_percentile_5y
pb_hist_percentile_5y
ev_ebitda_hist_percentile_5y
fcf_yield_hist_percentile_5y

pe_vs_5y_median
pb_vs_5y_median


# PEER RANKS

market_value_percentile

sector_value_percentile
industry_value_percentile
size_peer_value_percentile


# NEUTRALIZED

sector_neutral_value_z
industry_neutral_value_z
size_neutral_value_z


# INTERACTIONS

quality_adjusted_value
growth_adjusted_value
risk_adjusted_value


# FINAL

value_factor_score
value_percentile
valuation_state


# QUALITY

pe_valid
pb_valid
ev_ebitda_valid
fcf_yield_valid

valuation_quality_status
valuation_staleness_flag
valuation_invalid_reason
```

---

# 12.69 Initial Production Metrics

Recommended first production set:

```text
market_cap
enterprise_value

pe_ttm
earnings_yield

price_to_book
book_to_price

price_to_sales
sales_yield

ev_ebitda
ebitda_to_ev

ev_ebit
ebit_to_ev

fcf_yield
ocf_yield

dividend_yield

pe_hist_percentile_5y
pb_hist_percentile_5y
ev_ebitda_hist_percentile_5y

sector_value_percentile
industry_value_percentile

sector_neutral_value_z

value_factor_score
value_percentile

valuation_quality_status
```

Then expand into:

```text
forward valuation
growth-adjusted value
quality-adjusted value
shareholder yield
cyclical normalization
```

---

# 12.70 Valuation Engine Processing Flow

Recommended:

```text
POINT-IN-TIME MARKET PRICE
        ↓
POINT-IN-TIME FUNDAMENTALS
        ↓
POINT-IN-TIME SHARE COUNT
        ↓
MARKET CAP
        ↓
ENTERPRISE VALUE
        ↓
EARNINGS / BOOK / SALES MULTIPLES
        ↓
EV MULTIPLES
        ↓
CASH-FLOW YIELDS
        ↓
DIVIDEND / SHAREHOLDER YIELD
        ↓
HISTORICAL VALUATION COMPARISON
        ↓
SECTOR / INDUSTRY COMPARISON
        ↓
NEUTRALIZATION
        ↓
GROWTH / QUALITY CONTEXT
        ↓
VALUE FACTOR SCORE
        ↓
QUALITY FLAGS
```

---

# 12.71 Important Quant Rules

## Rule 1 — Valuation Must Be Point-in-Time

Never combine historical prices with future fundamentals.

---

## Rule 2 — Cheap Is Relative

Use history, sector, industry, and peer context.

---

## Rule 3 — Inverse Yields Are Often Better Factor Inputs

Examples:

```text
earnings yield
book-to-price
EBIT/EV
FCF yield
```

because higher can consistently mean cheaper.

---

## Rule 4 — Invalid Multiples Must Stay Invalid

Negative earnings should not produce misleading P/E ranks.

---

## Rule 5 — Sector Context Is Essential

Banks, software, industrials, and commodity companies need different primary valuation measures.

---

## Rule 6 — Cheap Can Mean Distressed

Combine value later with quality, leverage, cash flow, and momentum.

---

## Rule 7 — Preserve Raw Inputs

Never replace market cap, earnings, or cash flow with ratios only.

---

## Rule 8 — Use Historical Share Count

Per-share and market-cap metrics must reflect the actual period.

---

## Rule 9 — Historical Percentiles Must Be Point-in-Time

Do not use future valuation history to score old dates.

---

## Rule 10 — Value Score Must Be Explainable

Keep component yields, peer ranks, and history percentiles visible.

---

# 12.72 Completion Criteria

Step 12 is complete when Open Analytics can answer:

1. What is the stock's current market cap?
2. What is its enterprise value?
3. What are P/E, P/B, P/S, EV/EBITDA, and EV/EBIT?
4. What are earnings yield, book-to-price, EBIT/EV, and FCF yield?
5. Is the stock cheap or expensive relative to its own history?
6. How does valuation compare with sector peers?
7. How does it compare with industry peers?
8. How does valuation compare with similar-size companies?
9. Which valuation metrics are valid for this sector?
10. Is a low multiple caused by negative or deteriorating fundamentals?
11. Is valuation improving because fundamentals improved or because price fell?
12. Is there multiple expansion or compression?
13. How does valuation interact with growth and quality?
14. Are point-in-time shares and fundamentals being used?
15. Are forward estimates current and historically correct?
16. What is the final value-factor score and percentile?
17. Why is any valuation metric unavailable or invalid?

Once these are reliable, the Valuation Engine is ready to feed:

```text
Step 13 — Factor Engine
```

---

# Step 12 Final Output

The Valuation Engine transforms:

```text
Market Price
+
Point-in-Time Fundamentals
+
Share Count
+
Peer Context
```

into:

```text
P/E
P/B
P/S
EV/EBITDA
EV/EBIT
Earnings Yield
Book-to-Price
EBIT/EV
FCF Yield
Dividend Yield
Historical Valuation Percentiles
Sector/Industry Relative Valuation
Neutralized Value Metrics
Growth/Quality-Aware Valuation
Composite Value Factor
Valuation Quality Flags
```

This becomes the price-versus-fundamental-value layer for Open Analytics.
