# Open Analytics — Step 11: Fundamental Engine

## Purpose

The **Fundamental Engine** converts reported company financial statements and related accounting data into standardized measures of business quality, profitability, growth, financial strength, efficiency, cash generation, and earnings quality.

This engine should answer:

- Is the company profitable?
- Is profitability improving or deteriorating?
- Is revenue growing?
- Are earnings growing?
- Is growth backed by cash flow?
- Is leverage increasing or decreasing?
- Can the company comfortably service debt?
- Is capital being used efficiently?
- Are margins expanding or shrinking?
- Are reported earnings high quality?
- Is the company financially stable?
- How do these metrics compare with sector and industry peers?
- Were these values actually known at the historical research date?

Fundamental outputs feed directly into:

- Quality factors
- Growth factors
- Value factors
- Alpha models
- Risk models
- Stock screening
- Portfolio construction
- Machine learning features

---

# 11.1 Core Principle

Fundamental analysis must be **point-in-time**.

Do not use:

```text
latest financial data today
```

to evaluate what a quant strategy could have known historically.

For every financial period, Open Analytics should distinguish:

```text
period_end_date
reporting_date
announcement_date
filing_date
data_available_date
```

The value only becomes usable when it was actually publicly available.

---

# 11.2 Required Input Data

Minimum statement data:

```text
revenue
operating_expenses
ebitda
ebit
profit_before_tax
tax_expense
net_income
eps
```

Balance sheet:

```text
cash
total_assets
current_assets
current_liabilities
inventory
receivables
total_debt
short_term_debt
long_term_debt
shareholders_equity
```

Cash flow:

```text
operating_cash_flow
capital_expenditure
investing_cash_flow
financing_cash_flow
free_cash_flow
```

Preferred additional data:

```text
interest_expense
depreciation_amortization
shares_outstanding
book_value
retained_earnings
working_capital
goodwill
intangibles
minority_interest
```

---

# 11.3 Period Types

Support:

```text
QUARTERLY
TTM
ANNUAL
```

Optional:

```text
SEMI_ANNUAL
```

Each metric should state which period basis it uses.

---

# 11.4 TTM Construction

Trailing Twelve Months:

```text
TTM =
sum(last 4 reported quarters)
```

for flow variables such as:

```text
revenue
EBITDA
EBIT
net income
operating cash flow
capex
free cash flow
```

Balance-sheet values are usually point-in-time, not summed.

---

# 11.5 Revenue Growth

Calculate:

```text
revenue_growth_yoy
revenue_growth_qoq
revenue_cagr_3y
revenue_cagr_5y
```

YoY:

```text
revenue_current_period / revenue_same_period_last_year - 1
```

QoQ:

```text
revenue_current_quarter / revenue_previous_quarter - 1
```

---

# 11.6 EBITDA Growth

Recommended:

```text
ebitda_growth_yoy
ebitda_growth_qoq
ebitda_cagr_3y
ebitda_cagr_5y
```

---

# 11.7 EBIT Growth

Recommended:

```text
ebit_growth_yoy
ebit_growth_qoq
```

---

# 11.8 Net Income Growth

Recommended:

```text
net_income_growth_yoy
net_income_growth_qoq
net_income_cagr_3y
net_income_cagr_5y
```

Handle sign changes carefully.

Growth from negative to positive earnings should not be treated naively as an ordinary percentage growth rate.

---

# 11.9 EPS Growth

Recommended:

```text
eps_growth_yoy
eps_growth_qoq
eps_cagr_3y
eps_cagr_5y
```

Use split-adjusted EPS where appropriate.

---

# 11.10 Free Cash Flow Growth

Recommended:

```text
fcf_growth_yoy
fcf_cagr_3y
fcf_cagr_5y
```

Again, sign changes need robust handling.

---

# 11.11 Gross Margin

Where gross profit is available:

```text
gross_margin =
gross_profit / revenue
```

Store:

```text
gross_margin
gross_margin_change_yoy
gross_margin_3y_avg
```

---

# 11.12 EBITDA Margin

```text
ebitda_margin =
ebitda / revenue
```

Store:

```text
ebitda_margin
ebitda_margin_change_yoy
ebitda_margin_3y_avg
```

---

# 11.13 EBIT Margin

```text
ebit_margin =
ebit / revenue
```

---

# 11.14 Net Margin

```text
net_margin =
net_income / revenue
```

Store:

```text
net_margin
net_margin_change_yoy
```

---

# 11.15 Margin Expansion

Useful derived metrics:

```text
gross_margin_delta
ebitda_margin_delta
ebit_margin_delta
net_margin_delta
```

Positive values indicate expansion.

---

# 11.16 Return on Equity

```text
ROE =
net_income / average_shareholders_equity
```

Use average beginning/end equity where possible.

Store:

```text
roe_ttm
roe_3y_avg
roe_5y_avg
```

---

# 11.17 Return on Assets

```text
ROA =
net_income / average_total_assets
```

Store:

```text
roa_ttm
```

---

# 11.18 Return on Capital Employed

A common form:

```text
ROCE =
EBIT / capital_employed
```

Capital employed may be defined as:

```text
total_assets - current_liabilities
```

or:

```text
equity + debt - cash
```

Open Analytics must choose one platform-wide definition and document it.

Store:

```text
roce_ttm
roce_3y_avg
```

---

# 11.19 Return on Invested Capital

Conceptually:

```text
ROIC =
NOPAT / invested_capital
```

where:

```text
NOPAT =
EBIT × (1 - effective_tax_rate)
```

Store:

```text
roic_ttm
roic_3y_avg
```

This is a key quality metric.

---

# 11.20 Asset Turnover

```text
asset_turnover =
revenue / average_total_assets
```

Useful for operating efficiency.

---

# 11.21 Inventory Turnover

Where applicable:

```text
inventory_turnover =
COGS / average_inventory
```

Sector relevance varies.

---

# 11.22 Receivables Turnover

```text
receivables_turnover =
revenue / average_receivables
```

---

# 11.23 Working Capital Efficiency

Possible measures:

```text
working_capital_turnover
cash_conversion_cycle
days_sales_outstanding
days_inventory_outstanding
days_payables_outstanding
```

These are valuable where source data is sufficient.

---

# 11.24 Debt to Equity

```text
debt_to_equity =
total_debt / shareholders_equity
```

Store:

```text
debt_to_equity
```

Handle negative equity explicitly.

---

# 11.25 Debt to Assets

```text
debt_to_assets =
total_debt / total_assets
```

---

# 11.26 Net Debt

```text
net_debt =
total_debt - cash
```

---

# 11.27 Net Debt to EBITDA

```text
net_debt_to_ebitda =
net_debt / EBITDA
```

Do not treat as valid when EBITDA <= 0 without explicit special handling.

---

# 11.28 Interest Coverage

```text
interest_coverage =
EBIT / interest_expense
```

or optionally EBITDA-based.

Store definition metadata.

---

# 11.29 Current Ratio

```text
current_ratio =
current_assets / current_liabilities
```

---

# 11.30 Quick Ratio

```text
quick_ratio =
(current_assets - inventory)
/
current_liabilities
```

---

# 11.31 Cash Ratio

```text
cash_ratio =
cash / current_liabilities
```

---

# 11.32 Operating Cash Flow

Store:

```text
operating_cash_flow_ttm
```

and compare with net income.

---

# 11.33 Free Cash Flow

Preferred basic definition:

```text
free_cash_flow =
operating_cash_flow - capital_expenditure
```

Store:

```text
fcf_ttm
fcf_margin
```

where:

```text
fcf_margin =
free_cash_flow / revenue
```

---

# 11.34 Cash Conversion

```text
cash_conversion_ratio =
operating_cash_flow / net_income
```

Useful for earnings quality.

---

# 11.35 FCF Conversion

```text
fcf_conversion =
free_cash_flow / net_income
```

Interpret carefully when net income is negative or near zero.

---

# 11.36 Accruals

A basic accrual measure can compare accounting earnings to cash flow.

Conceptually:

```text
accruals =
net_income - operating_cash_flow
```

Normalize by:

```text
average assets
```

Store:

```text
accrual_ratio
```

Lower accruals can indicate better earnings quality in many contexts.

---

# 11.37 Earnings Quality

Possible components:

```text
cash conversion
FCF conversion
accrual ratio
earnings stability
margin stability
receivables growth
inventory growth
```

Output later:

```text
earnings_quality_score
```

---

# 11.38 Earnings Stability

Calculate historical variability:

```text
eps_volatility_3y
net_income_volatility_3y
margin_volatility_3y
```

Stable profitability can support a quality factor.

---

# 11.39 Revenue Stability

```text
revenue_growth_volatility
```

or:

```text
revenue_std / mean_revenue
```

where appropriate.

---

# 11.40 Margin Stability

Recommended:

```text
gross_margin_volatility_3y
ebitda_margin_volatility_3y
net_margin_volatility_3y
```

---

# 11.41 Profitability Trend

Track whether profitability is improving.

Possible:

```text
roe_change_yoy
roic_change_yoy
roce_change_yoy
```

Store:

```text
profitability_trend
```

Possible states:

```text
IMPROVING
STABLE
DETERIORATING
```

---

# 11.42 Margin Trend

Similarly:

```text
margin_trend
```

based on:

```text
gross margin
EBITDA margin
net margin
```

---

# 11.43 Leverage Trend

Track:

```text
debt_change_yoy
net_debt_change_yoy
debt_to_equity_change
net_debt_to_ebitda_change
```

Output:

```text
leverage_trend
```

---

# 11.44 Cash Flow Trend

Track:

```text
operating_cash_flow_growth
fcf_growth
cash_conversion_change
```

Output:

```text
cash_flow_trend
```

---

# 11.45 Capital Efficiency Trend

Track changes in:

```text
ROIC
ROCE
asset turnover
```

Output:

```text
capital_efficiency_trend
```

---

# 11.46 Fundamental Acceleration

Growth itself can accelerate or decelerate.

Examples:

```text
revenue_growth_acceleration
eps_growth_acceleration
margin_acceleration
```

Concept:

```text
latest growth rate - previous growth rate
```

---

# 11.47 Earnings Surprise

If analyst consensus exists:

```text
eps_surprise =
(actual_eps - expected_eps)
/
abs(expected_eps)
```

Similarly:

```text
revenue_surprise
ebitda_surprise
margin_surprise
```

Keep actual and expected values separately.

---

# 11.48 Estimate Revisions

If consensus estimates exist:

```text
eps_revision_1m
eps_revision_3m

revenue_revision_1m
target_price_revision
```

Also:

```text
upgrade_count
downgrade_count
```

Estimate revisions can become a separate factor.

---

# 11.49 Guidance Change

Where management guidance can be structured:

```text
guidance_revision
```

Possible states:

```text
RAISED
MAINTAINED
LOWERED
WITHDRAWN
```

This is optional and source-dependent.

---

# 11.50 Piotroski-Style Inputs

Potential fundamental quality signals:

```text
positive net income
positive operating cash flow
improving ROA
cash flow > net income
declining leverage
improving current ratio
no excessive dilution
improving gross margin
improving asset turnover
```

Open Analytics may later calculate:

```text
piotroski_like_score
```

Do not label as exact Piotroski F-Score unless methodology matches the published definition exactly.

---

# 11.51 Altman-Style Distress Inputs

Potential later financial distress metrics can include:

```text
working capital / assets
retained earnings / assets
EBIT / assets
market value equity / liabilities
sales / assets
```

Only calculate a named Altman Z-score if the chosen formula is valid for the relevant company type.

---

# 11.52 Beneish-Style Earnings Manipulation Inputs

Advanced forensic metrics may later include:

```text
DSRI
GMI
AQI
SGI
DEPI
SGAI
LVGI
TATA
```

This is advanced and requires high-quality statement mapping.

Not needed for first production.

---

# 11.53 Share Dilution

Track:

```text
shares_outstanding
shares_growth_yoy
```

Possible:

```text
dilution_rate
```

Frequent dilution can reduce per-share compounding even when company-level profit grows.

---

# 11.54 Buybacks

Track:

```text
share_count_reduction
buyback_flag
```

Can support capital-allocation analysis.

---

# 11.55 Dividend Coverage

Where relevant:

```text
dividend_payout_ratio
dividend_coverage
```

These belong partly to valuation/shareholder-return analysis.

---

# 11.56 Capital Expenditure Intensity

```text
capex_to_sales =
capex / revenue
```

and:

```text
capex_to_ocf
```

Useful for capital-intensive businesses.

---

# 11.57 R&D Intensity

Where available:

```text
rd_to_sales
```

Especially useful for technology/pharma sectors.

---

# 11.58 SG&A Intensity

```text
sga_to_sales
```

Can help analyze operating leverage.

---

# 11.59 Operating Leverage

Potential measure:

```text
change in EBIT
/
change in revenue
```

or regression-based sensitivity.

Use carefully because short samples are unstable.

---

# 11.60 Financial Sector Handling

Banks, NBFCs, and insurers require different metrics.

Do not blindly apply industrial-company metrics such as:

```text
net debt / EBITDA
current ratio
```

to banks.

Financial-sector-specific metrics may include:

```text
net interest margin
gross NPA
net NPA
provision coverage
capital adequacy
credit growth
deposit growth
CASA ratio
ROA
ROE
cost-to-income
```

Open Analytics should support sector-specific metric templates.

---

# 11.61 Banking Metrics

Potential:

```text
nim
gross_npa
net_npa
provision_coverage
capital_adequacy_ratio
cet1_ratio
loan_growth
deposit_growth
casa_ratio
cost_income_ratio
```

Source-dependent.

---

# 11.62 Insurance Metrics

Potential:

```text
gross_written_premium_growth
embedded_value_growth
value_of_new_business
vnb_margin
solvency_ratio
combined_ratio
```

Use only if high-quality data exists.

---

# 11.63 Asset Management Metrics

Potential:

```text
AUM growth
fee yield
operating margin
net inflow
```

Sector-specific engine extensions can be added later.

---

# 11.64 Sector-Specific Metric Registry

Create metadata:

```text
metric_name
applicable_sector
formula
period_basis
direction
minimum_history
```

This prevents nonsensical ratios from being calculated for incompatible sectors.

---

# 11.65 Restatements

Financial statements may be restated.

Store both:

```text
original_reported_value
restated_value
```

and:

```text
restatement_date
```

For point-in-time backtests, use the version known at that date.

---

# 11.66 Filing Lag

The fundamental period may end before data is publicly available.

Example:

```text
quarter_end = 2025-06-30
results_announced = 2025-08-05
```

The data must not enter the model before:

```text
2025-08-05
```

or the validated availability timestamp.

---

# 11.67 Fundamental Age

Calculate:

```text
days_since_latest_report
```

and:

```text
fundamental_staleness_flag
```

A metric from a very old filing may need lower confidence.

---

# 11.68 Duplicate Period Handling

Detect:

```text
duplicate company
duplicate fiscal period
duplicate filing
```

Keep source/version lineage.

---

# 11.69 Fiscal Year Differences

Companies may use different fiscal calendars.

Do not assume all fiscal quarters map identically.

Store:

```text
fiscal_year
fiscal_quarter
period_start
period_end
```

---

# 11.70 Currency Normalization

If multi-currency data appears, store:

```text
reported_currency
normalized_currency
fx_rate_used
```

For India-focused equities this may be less frequent but should remain explicit.

---

# 11.71 Per-Share Normalization

Possible:

```text
revenue_per_share
book_value_per_share
fcf_per_share
```

Use point-in-time share count and adjust for splits.

---

# 11.72 Book Value Per Share

```text
book_value_per_share =
shareholders_equity / shares_outstanding
```

Useful later for valuation.

---

# 11.73 Free Cash Flow Per Share

```text
fcf_per_share =
free_cash_flow / diluted_shares
```

---

# 11.74 Fundamental Cross-Sectional Ranking

Use Step 10 to calculate:

```text
roe_percentile
roic_percentile
revenue_growth_percentile
eps_growth_percentile
fcf_margin_percentile
debt_quality_percentile
```

Prefer sector/industry-aware comparison where economically appropriate.

---

# 11.75 Sector-Neutral Fundamental Metrics

Examples:

```text
sector_neutral_roe
sector_neutral_roic
sector_neutral_growth
sector_neutral_margin
```

This reduces structural sector bias.

---

# 11.76 Fundamental Quality Score

Possible components:

```text
ROIC
ROE
FCF margin
cash conversion
low leverage
margin stability
earnings stability
```

Output:

```text
fundamental_quality_score
```

Weights should be researched and versioned.

---

# 11.77 Growth Score

Possible inputs:

```text
revenue growth
EBITDA growth
EPS growth
FCF growth
growth acceleration
```

Output:

```text
fundamental_growth_score
```

---

# 11.78 Financial Strength Score

Possible inputs:

```text
low leverage
interest coverage
current ratio
cash ratio
positive FCF
debt trend
```

Output:

```text
financial_strength_score
```

---

# 11.79 Earnings Quality Score

Possible inputs:

```text
cash conversion
accrual ratio
FCF conversion
margin stability
earnings stability
```

Output:

```text
earnings_quality_score
```

---

# 11.80 Composite Fundamental Score

Eventually:

```text
fundamental_score
```

from:

```text
quality
growth
financial strength
earnings quality
```

Do not mix valuation here; valuation belongs in Step 12.

---

# 11.81 Recommended Fundamental Record

A point-in-time fundamental record could include:

```text
company_id
instrument_key

period_end_date
announcement_date
data_available_date

period_type


# INCOME STATEMENT

revenue
ebitda
ebit
net_income
eps


# BALANCE SHEET

cash
total_assets
current_assets
current_liabilities

total_debt
net_debt
shareholders_equity


# CASH FLOW

operating_cash_flow
capex
free_cash_flow


# GROWTH

revenue_growth_yoy
revenue_growth_qoq

ebitda_growth_yoy
net_income_growth_yoy
eps_growth_yoy
fcf_growth_yoy

revenue_cagr_3y
eps_cagr_3y
fcf_cagr_3y


# MARGINS

gross_margin
ebitda_margin
ebit_margin
net_margin

gross_margin_delta
ebitda_margin_delta
net_margin_delta


# PROFITABILITY

roe_ttm
roa_ttm
roce_ttm
roic_ttm

asset_turnover


# LEVERAGE

debt_to_equity
debt_to_assets
net_debt_to_ebitda
interest_coverage


# LIQUIDITY / BALANCE SHEET

current_ratio
quick_ratio
cash_ratio


# CASH QUALITY

fcf_margin
cash_conversion_ratio
fcf_conversion
accrual_ratio


# STABILITY

eps_volatility_3y
margin_volatility_3y
revenue_growth_volatility


# TRENDS

profitability_trend
margin_trend
leverage_trend
cash_flow_trend
capital_efficiency_trend


# RANKING

roe_percentile
roic_percentile
growth_percentile
financial_strength_percentile

sector_roe_percentile
sector_growth_percentile


# SCORES

fundamental_quality_score
fundamental_growth_score
financial_strength_score
earnings_quality_score
fundamental_score


# QUALITY

fundamental_valid
fundamental_quality_status
fundamental_staleness_flag
fundamental_invalid_reason
```

---

# 11.82 Initial Production Metrics

The first production version should prioritize robust metrics available from standard statements.

Recommended:

```text
revenue_ttm
ebitda_ttm
ebit_ttm
net_income_ttm
eps_ttm

revenue_growth_yoy
ebitda_growth_yoy
net_income_growth_yoy
eps_growth_yoy

revenue_cagr_3y
eps_cagr_3y

ebitda_margin
ebit_margin
net_margin

roe_ttm
roa_ttm
roce_ttm
roic_ttm

debt_to_equity
net_debt
net_debt_to_ebitda
interest_coverage

current_ratio

operating_cash_flow_ttm
free_cash_flow_ttm
fcf_margin

cash_conversion_ratio
accrual_ratio

profitability_trend
margin_trend
leverage_trend
cash_flow_trend

fundamental_quality_score
fundamental_growth_score
financial_strength_score

fundamental_quality_status
```

Then expand into sector-specific and forensic metrics.

---

# 11.83 Fundamental Engine Processing Flow

Recommended:

```text
RAW FINANCIAL STATEMENTS
        ↓
IDENTITY / PERIOD MAPPING
        ↓
POINT-IN-TIME AVAILABILITY
        ↓
RESTATEMENT VERSIONING
        ↓
TTM CONSTRUCTION
        ↓
GROWTH METRICS
        ↓
MARGINS
        ↓
PROFITABILITY
        ↓
CAPITAL EFFICIENCY
        ↓
LEVERAGE
        ↓
BALANCE-SHEET STRENGTH
        ↓
CASH FLOW
        ↓
EARNINGS QUALITY
        ↓
STABILITY
        ↓
FUNDAMENTAL TRENDS
        ↓
SECTOR-SPECIFIC METRICS
        ↓
CROSS-SECTIONAL RANKING
        ↓
FUNDAMENTAL SCORES
        ↓
QUALITY FLAGS
```

---

# 11.84 Important Quant Rules

## Rule 1 — Fundamentals Must Be Point-in-Time

Never use a filing before its public availability date.

---

## Rule 2 — Restatements Need Versioning

Historical backtests should use the version known at the time.

---

## Rule 3 — TTM and Annual Data Are Different

Do not mix periods without explicit labeling.

---

## Rule 4 — Sign Changes Need Special Handling

Percentage growth from negative to positive values can be meaningless.

---

## Rule 5 — Sector Context Matters

Banks and industrial companies should not use identical metric sets.

---

## Rule 6 — Cash Flow Matters

Reported earnings without cash support may be lower quality.

---

## Rule 7 — Capital Efficiency Matters

High growth with poor ROIC can destroy value.

---

## Rule 8 — Preserve Raw Accounting Values

Derived ratios should never replace source statements.

---

## Rule 9 — Missing Is Not Zero

Do not treat unavailable financial data as zero.

---

## Rule 10 — Staleness Matters

Old fundamentals should carry lower confidence.

---

## Rule 11 — Use Cross-Sectional Ranking Carefully

Many fundamental metrics should be compared within sector or industry.

---

## Rule 12 — Do Not Mix Valuation Into Quality

Valuation belongs in the next engine.

---

# 11.85 Completion Criteria

Step 11 is complete when Open Analytics can answer:

1. What are the company’s latest point-in-time revenue and earnings?
2. Is revenue growing?
3. Are EBITDA and EPS growing?
4. Are margins expanding or contracting?
5. What are ROE, ROA, ROCE, and ROIC?
6. Is capital efficiency improving?
7. How leveraged is the company?
8. Can it cover its interest expense?
9. Is liquidity/balance-sheet strength adequate?
10. Is operating cash flow supporting reported earnings?
11. Is free cash flow positive and improving?
12. Are accruals unusually high?
13. Are earnings and margins stable?
14. Is leverage rising or falling?
15. How do profitability and growth compare with sector peers?
16. What are the company’s quality, growth, financial-strength, and earnings-quality scores?
17. Was every metric actually available at the historical research date?
18. Are any values stale, restated, missing, or invalid?
19. Are sector-specific formulas being used where needed?
20. Can the exact historical fundamental state be reproduced?

Once these are reliable, the Fundamental Engine is ready to feed:

```text
Step 12 — Valuation Engine
```

---

# Step 11 Final Output

The Fundamental Engine transforms:

```text
Point-in-Time Financial Statements
```

into:

```text
Revenue and Earnings Growth
Margins
ROE / ROA / ROCE / ROIC
Capital Efficiency
Leverage
Balance-Sheet Strength
Cash Flow
Free Cash Flow
Cash Conversion
Accruals
Earnings Quality
Financial Stability
Fundamental Trends
Sector-Specific Metrics
Fundamental Rankings
Quality / Growth / Strength Scores
Fundamental Quality Flags
```

This becomes the business-quality and operating-performance layer for Open Analytics.
