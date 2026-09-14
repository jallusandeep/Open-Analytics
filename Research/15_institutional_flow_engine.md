# Open Analytics — Step 15: Institutional Flow Engine

## Purpose

The **Institutional Flow Engine** measures the direction, persistence, intensity, and market impact of institutional capital flows.

For the Indian market, this includes especially:

- FII / FPI cash-market activity
- DII cash-market activity
- Institutional derivatives positioning
- Stock-level delivery / block / bulk deal context
- Rolling net flows
- Flow momentum
- Flow z-scores
- Flow regimes
- Flow confirmation with market returns, breadth, and volatility

The engine should answer:

- Are foreign institutions net buying or selling?
- Are domestic institutions offsetting or reinforcing those flows?
- Is flow pressure increasing or fading?
- Are flows unusually large relative to history?
- Are institutions buying into strength or weakness?
- Are cash and derivatives flows aligned?
- Is a stock or sector receiving unusual institutional participation?
- Is the market in a persistent accumulation or distribution regime?
- How much explanatory power do flows have for forward returns?
- Are current flows supportive or hostile to the broader market regime?

Outputs feed directly into:

- Market Regime Engine
- Alpha / Signal Engine
- Breadth analysis
- Sector allocation
- Risk overlays
- Stock screening
- Event analysis
- Machine learning features

---

# 15.1 Core Principle

Institutional flow is not one number.

Open Analytics should distinguish:

```text
Gross Buying
Gross Selling
Net Flow
Flow Persistence
Flow Acceleration
Flow Surprise
Flow Z-Score
Cash vs Derivatives Flow
Foreign vs Domestic Flow
Sector Flow
Stock-Level Flow Proxy
Flow-Regime State
```

Do not assume:

```text
FII net buying = market must rise
```

Flow impact depends on:

```text
market regime
valuation
liquidity
breadth
derivatives positioning
counterparty flows
global context
```

---

# 15.2 Required Inputs

Minimum market-level inputs:

```text
date

fii_gross_buy
fii_gross_sell
fii_net

dii_gross_buy
dii_gross_sell
dii_net
```

Preferred:

```text
fii_cash
dii_cash

fii_index_futures_net
fii_stock_futures_net

fii_index_options_positioning
fii_stock_options_positioning

market_return
market_breadth
market_volume
india_vix
```

Optional stock-level / sector-level inputs:

```text
delivery_percentage
delivery_value

bulk_deals
block_deals

promoter transactions
institutional shareholding changes

mutual fund holdings
FPI holdings

sector fund flows
ETF flows
```

---

# 15.3 FII / FPI Cash Flow

Store:

```text
fii_gross_buy
fii_gross_sell
fii_net
```

Formula:

```text
fii_net =
fii_gross_buy - fii_gross_sell
```

Use one source definition consistently.

---

# 15.4 DII Cash Flow

Store:

```text
dii_gross_buy
dii_gross_sell
dii_net
```

Formula:

```text
dii_net =
dii_gross_buy - dii_gross_sell
```

---

# 15.5 Combined Institutional Flow

```text
institutional_net =
fii_net + dii_net
```

This indicates whether combined institutional activity is supportive or negative.

---

# 15.6 FII-DII Interaction State

Possible:

```text
FII_BUY_DII_BUY
FII_BUY_DII_SELL
FII_SELL_DII_BUY
FII_SELL_DII_SELL
MIXED_LOW_INTENSITY
```

Store:

```text
institutional_flow_state
```

---

# 15.7 Rolling Net Flow

Recommended:

```text
fii_net_5d
fii_net_20d
fii_net_60d

dii_net_5d
dii_net_20d
dii_net_60d

institutional_net_5d
institutional_net_20d
institutional_net_60d
```

These reveal persistence beyond one session.

---

# 15.8 Average Daily Flow

```text
avg_fii_net_5d
avg_fii_net_20d

avg_dii_net_5d
avg_dii_net_20d
```

---

# 15.9 Flow Momentum

Possible:

```text
fii_flow_momentum =
avg_fii_net_5d - avg_fii_net_20d
```

Store:

```text
fii_flow_momentum
dii_flow_momentum
institutional_flow_momentum
```

---

# 15.10 Flow Acceleration

```text
flow_acceleration =
current_flow_momentum - prior_flow_momentum
```

Store:

```text
fii_flow_acceleration
dii_flow_acceleration
```

---

# 15.11 Flow Z-Score

```text
fii_flow_z_60d =
(fii_net - mean_fii_net_60d)
/
std_fii_net_60d
```

Also:

```text
dii_flow_z_60d
institutional_flow_z_60d
```

Recommended windows:

```text
20D
60D
252D
```

---

# 15.12 Flow Percentile

Historical percentile:

```text
fii_flow_percentile_252d
dii_flow_percentile_252d
```

Useful for identifying unusually large accumulation or selling.

---

# 15.13 Flow Regime

Possible states:

```text
STRONG_FOREIGN_ACCUMULATION
FOREIGN_ACCUMULATION
NEUTRAL
FOREIGN_DISTRIBUTION
STRONG_FOREIGN_DISTRIBUTION
```

Store:

```text
flow_regime
```

---

# 15.14 Persistent Flow Regime

Use:

```text
20D cumulative flow
positive-day count
flow z-score
```

Store:

```text
flow_regime_persistence
```

---

# 15.15 Positive / Negative Flow Day Ratio

```text
fii_positive_day_ratio_20d
fii_negative_day_ratio_20d

dii_positive_day_ratio_20d
dii_negative_day_ratio_20d
```

This distinguishes consistent activity from one extreme day.

---

# 15.16 Flow Volatility

```text
fii_flow_volatility_20d
dii_flow_volatility_20d
```

High variability can reduce confidence in the current regime.

---

# 15.17 Flow Surprise

Simple:

```text
flow_surprise =
current_flow - rolling_mean_flow
```

Normalized:

```text
flow_surprise_z
```

---

# 15.18 Market-Normalized Flow

Possible:

```text
fii_flow_pct_turnover
dii_flow_pct_turnover
institutional_flow_pct_turnover
```

This gives context to absolute rupee values.

---

# 15.19 Flow vs Market Return

Classify:

```text
market_up + fii_buying
market_up + fii_selling
market_down + fii_buying
market_down + fii_selling
```

Store:

```text
flow_price_state
```

---

# 15.20 Flow-Return Correlation

Rolling:

```text
fii_market_return_corr_20d
fii_market_return_corr_60d

dii_market_return_corr_20d
dii_market_return_corr_60d
```

---

# 15.21 Flow and Breadth

Store:

```text
flow_breadth_confirmation
```

Example:

```text
FII buying + strong breadth
```

differs from:

```text
FII buying + narrow index rally
```

---

# 15.22 Flow and Volatility

Possible states:

```text
fii selling + VIX rising
fii buying + VIX falling
```

Store:

```text
flow_volatility_state
```

---

# 15.23 Cash vs Futures Alignment

If derivatives data exists:

```text
fii_cash_net
fii_index_futures_net
fii_stock_futures_net
```

Classify:

```text
CASH_BUY_FUTURES_LONG
CASH_BUY_FUTURES_SHORT
CASH_SELL_FUTURES_LONG
CASH_SELL_FUTURES_SHORT
MIXED
```

Store:

```text
cash_futures_alignment
```

---

# 15.24 Index Futures Positioning

Store:

```text
fii_index_futures_long
fii_index_futures_short
fii_index_futures_net
```

Also:

```text
fii_index_futures_net_change
```

---

# 15.25 Stock Futures Positioning

Store:

```text
fii_stock_futures_long
fii_stock_futures_short
fii_stock_futures_net
fii_stock_futures_net_change
```

---

# 15.26 Options Positioning

Where reliable participant-wise data exists, track:

```text
index_call_long
index_call_short
index_put_long
index_put_short
```

Interpret cautiously because options positions can be hedges or spreads.

---

# 15.27 Participant-Wise Derivative Flow

Potential participant groups:

```text
FII
DII
PRO
CLIENT
```

Store:

```text
participant_flow_state
```

where source definitions are reliable.

---

# 15.28 Institutional Positioning Score

Possible components:

```text
cash flow
futures positioning
options context
```

Output:

```text
institutional_positioning_score
```

---

# 15.29 Sector-Level Flow

Where data exists:

```text
sector_fii_flow
sector_dii_flow
sector_mutual_fund_flow
```

Outputs:

```text
sector_flow_score
sector_flow_rank
sector_flow_percentile
```

---

# 15.30 Sector Rotation

Track relative flow by sector.

Example:

```text
Banking flow percentile
IT flow percentile
Metal flow percentile
```

This can support sector rotation models.

---

# 15.31 Stock-Level Institutional Flow

Direct daily stock-level institutional flow may not always be available.

Use only reliable sources.

Potential direct inputs:

```text
bulk deals
block deals
institutional ownership changes
mutual fund holdings
FPI holdings
```

---

# 15.32 Delivery as a Proxy

Delivery can be used only as a weak participation proxy.

Store:

```text
delivery_pct
delivery_value
delivery_z
```

Do not label delivery as institutional buying.

---

# 15.33 Bulk Deal Analysis

Fields:

```text
buyer
seller
quantity
price
value
entity_type
```

Map known institutional entities where possible.

---

# 15.34 Block Deal Analysis

Store:

```text
block_deal_buy_value
block_deal_sell_value
block_deal_net_value
```

---

# 15.35 Institutional Ownership Change

From periodic holdings:

```text
fpi_holding_pct
mf_holding_pct
insurance_holding_pct
```

Calculate:

```text
fpi_holding_change_qoq
mf_holding_change_qoq
insurance_holding_change_qoq
```

---

# 15.36 Promoter Context

Separate:

```text
promoter_holding_change
promoter_pledge_change
```

This is useful context but should not be mixed directly with FII/DII flow.

---

# 15.37 ETF / Fund Flow

Where available:

```text
ETF inflow
ETF outflow
mutual fund equity inflow
SIP flow
```

These support broader domestic-flow analysis.

---

# 15.38 Flow Concentration

Possible:

```text
sector_flow_concentration
```

High concentration may indicate narrow institutional leadership.

---

# 15.39 Flow Breadth

Possible:

```text
positive_flow_sector_count
negative_flow_sector_count
flow_breadth_score
```

---

# 15.40 Flow Persistence Score

Possible components:

```text
rolling net flow
positive-day ratio
flow momentum
flow z-score
```

Output:

```text
flow_persistence_score
```

---

# 15.41 Foreign Flow Score

Output:

```text
foreign_flow_score
```

Potential inputs:

```text
fii_net_20d
fii_flow_z
fii_flow_momentum
cash-futures alignment
```

---

# 15.42 Domestic Flow Score

Output:

```text
domestic_flow_score
```

Potential inputs:

```text
dii_net_20d
dii_flow_z
dii_flow_momentum
```

---

# 15.43 Institutional Flow Score

Composite:

```text
institutional_flow_score
```

Potential inputs:

```text
foreign flow
domestic flow
persistence
breadth
derivatives alignment
```

Weights should be researched.

---

# 15.44 Stock-Level Flow Score

Where sufficient stock-specific evidence exists:

```text
stock_flow_score
```

Potential inputs:

```text
institutional deals
ownership changes
delivery behavior
volume confirmation
```

Proxy-based scores should carry lower confidence.

---

# 15.45 Flow Confidence

Possible inputs:

```text
source quality
data completeness
direct vs proxy data
persistence
cross-market confirmation
```

Output:

```text
flow_confidence
```

---

# 15.46 Flow Quality Status

Possible:

```text
VALID
PARTIAL
PROXY_ONLY
STALE
MISSING_DERIVATIVES
LOW_CONFIDENCE
INVALID
```

---

# 15.47 Market-Level Daily Flow Record

Recommended:

```text
date


# CASH

fii_gross_buy
fii_gross_sell
fii_net

dii_gross_buy
dii_gross_sell
dii_net

institutional_net


# ROLLING

fii_net_5d
fii_net_20d
fii_net_60d

dii_net_5d
dii_net_20d
dii_net_60d


# MOMENTUM

fii_flow_momentum
dii_flow_momentum

fii_flow_acceleration
dii_flow_acceleration


# NORMALIZATION

fii_flow_z_60d
dii_flow_z_60d

fii_flow_percentile_252d
dii_flow_percentile_252d


# STATE

institutional_flow_state
flow_price_state
flow_breadth_confirmation
flow_volatility_state

flow_regime
flow_regime_persistence


# DERIVATIVES

fii_index_futures_net
fii_stock_futures_net

fii_index_futures_net_change
fii_stock_futures_net_change

cash_futures_alignment


# FINAL

foreign_flow_score
domestic_flow_score
institutional_flow_score
flow_confidence

flow_quality_status
```

---

# 15.48 Sector-Level Flow Record

```text
date
sector_id

sector_flow
sector_flow_5d
sector_flow_20d

sector_flow_z
sector_flow_rank
sector_flow_percentile

sector_flow_score
```

---

# 15.49 Stock-Level Flow Record

Where reliable data exists:

```text
date
instrument_key

institutional_buy_value
institutional_sell_value
institutional_net_value

bulk_deal_net
block_deal_net

fpi_holding_change
mf_holding_change

delivery_pct
delivery_z

stock_flow_score
stock_flow_confidence
flow_quality_status
```

---

# 15.50 Initial Production Metrics

Start with reliable market-level data:

```text
fii_gross_buy
fii_gross_sell
fii_net

dii_gross_buy
dii_gross_sell
dii_net

institutional_net

fii_net_5d
fii_net_20d
fii_net_60d

dii_net_5d
dii_net_20d
dii_net_60d

fii_flow_momentum
dii_flow_momentum

fii_flow_z_60d
dii_flow_z_60d

fii_flow_percentile_252d
dii_flow_percentile_252d

institutional_flow_state
flow_price_state

foreign_flow_score
domestic_flow_score
institutional_flow_score

flow_quality_status
```

Then extend into:

```text
futures positioning
sector flows
stock ownership changes
block/bulk deal mapping
ETF/fund flows
```

---

# 15.51 Institutional Flow Engine Processing Flow

Recommended:

```text
RAW INSTITUTIONAL FLOW DATA
        ↓
SOURCE / DATE VALIDATION
        ↓
FII / DII CASH FLOW
        ↓
ROLLING CUMULATIVE FLOW
        ↓
FLOW MOMENTUM
        ↓
FLOW Z-SCORES / PERCENTILES
        ↓
FII-DII INTERACTION STATE
        ↓
MARKET RETURN CONFIRMATION
        ↓
BREADTH / VOLATILITY CONFIRMATION
        ↓
DERIVATIVES POSITIONING
        ↓
CASH-FUTURES ALIGNMENT
        ↓
SECTOR FLOW
        ↓
STOCK-LEVEL FLOW PROXIES
        ↓
COMPOSITE FLOW SCORES
        ↓
QUALITY / CONFIDENCE
```

---

# 15.52 Point-in-Time Rule

At date T, only use flow data publicly available by T.

Store:

```text
source_date
published_at
data_available_at
ingested_at
```

Do not use later revisions in earlier backtest timestamps unless explicitly versioned.

---

# 15.53 Revision Handling

If flow data is revised:

```text
original_value
revised_value
revision_timestamp
```

Historical research should use the version known at the time.

---

# 15.54 Missing Data

Do not treat missing flow as zero.

Use:

```text
flow_value = null
flow_valid = false
```

Possible reasons:

```text
SOURCE_MISSING
HOLIDAY
PUBLICATION_DELAY
DATA_ERROR
```

---

# 15.55 Holiday Handling

No trading session should not create artificial flow observations.

Use the exchange calendar.

---

# 15.56 Unit Normalization

Store consistent units.

Recommended:

```text
INR
```

Display can convert to:

```text
₹ crore
```

---

# 15.57 Source Consistency

Do not mix differently defined FII/FPI flow series without mapping.

Each source should specify:

```text
scope
market segment
gross/net definition
publication timing
```

---

# 15.58 Data Lineage

Every value should retain:

```text
source_name
source_reference
source_timestamp
```

for auditability.

---

# 15.59 Market-Level vs Stock-Level Use

Market-level flow should mainly feed:

```text
market regime
sector allocation
signal conditioning
risk overlays
```

Stock-level flow requires direct data or clearly labeled proxies.

---

# 15.60 Flow and Momentum Interaction

Potential:

```text
strong momentum
+
positive institutional flow regime
```

Store later:

```text
flow_momentum_confirmation
```

---

# 15.61 Flow and Value Interaction

Potential:

```text
value_flow_confirmation
```

for undervalued stocks receiving persistent institutional support.

---

# 15.62 Flow and Risk Interaction

Persistent foreign selling with rising volatility can increase market risk.

Possible:

```text
flow_risk_overlay
```

---

# 15.63 Flow Regime and Portfolio Exposure

Later portfolio logic may use flow regime as a risk overlay.

Example concept:

```text
strong foreign distribution + high volatility
→ lower allowed gross exposure
```

This must be backtested before production use.

---

# 15.64 Research Diagnostics

Test:

```text
correlation with future market returns
correlation with future sector returns
regime-conditioned returns
turning-point behavior
persistence
decay
```

---

# 15.65 Flow Information Coefficient

For stock/sector-level scores:

```text
rank_IC(
    flow_score_t,
    forward_return_t+h
)
```

---

# 15.66 Market-Level Predictive Tests

Examples:

```text
future NIFTY return after extreme FII flow z-score
future volatility after extreme selling
future breadth after persistent accumulation
```

---

# 15.67 Regime-Conditional Testing

Test under:

```text
bull market
bear market
high VIX
low VIX
strong breadth
weak breadth
```

Flow effects may be regime-dependent.

---

# 15.68 Important Quant Rules

## Rule 1 — FII/DII Flow Is Context, Not a Standalone Buy/Sell Signal

Large flows may be hedged or offset elsewhere.

## Rule 2 — Separate Cash and Derivatives

They carry different information.

## Rule 3 — Net Flow Alone Is Not Enough

Use persistence, z-score, and context.

## Rule 4 — Do Not Label Delivery as Institutional Flow

Delivery is only a proxy unless institution identity is known.

## Rule 5 — Point-in-Time Publication Matters

Use when the data became available.

## Rule 6 — Preserve Gross Buy and Gross Sell

Do not store only net flow.

## Rule 7 — Normalize Large Numbers

Use turnover or historical distribution for context.

## Rule 8 — Sector and Stock Flow Require Reliable Mapping

Do not infer detailed institutional activity from weak data.

## Rule 9 — Derivatives Positioning Can Be Hedged

Avoid simplistic directional interpretation.

## Rule 10 — Flow Regimes Must Be Backtested

Do not assume persistent buying always predicts positive returns.

## Rule 11 — Missing Is Not Zero

Publication gaps must remain explicit.

## Rule 12 — Keep Market-Level and Stock-Level Flow Separate

They answer different questions.

---

# 15.69 Completion Criteria

Step 15 is complete when Open Analytics can answer:

1. What were FII gross buys and sells?
2. What was FII net flow?
3. What were DII gross buys and sells?
4. What was DII net flow?
5. What are the 5D, 20D, and 60D cumulative flows?
6. Are foreign flows accelerating or weakening?
7. Are domestic institutions offsetting foreign selling?
8. How unusual are current flows versus history?
9. What is the current foreign-flow percentile/z-score?
10. Is the market in an accumulation or distribution flow regime?
11. Are flows confirmed by market returns?
12. Are flows confirmed by market breadth?
13. Are flows aligned with volatility conditions?
14. Are cash and futures positions aligned?
15. Which sectors are receiving relatively stronger flows?
16. Is stock-level institutional evidence direct or proxy-based?
17. What are the foreign, domestic, and combined flow scores?
18. What is the confidence/quality of those scores?
19. Was the data actually available at the historical timestamp?
20. Can the exact historical flow state be reproduced?

Once these are reliable, the Institutional Flow Engine is ready to feed:

```text
Step 16 — Derivatives Engine
```

---

# Step 15 Final Output

The Institutional Flow Engine transforms:

```text
FII / FPI Data
+
DII Data
+
Derivatives Positioning
+
Sector / Stock Flow Evidence
```

into:

```text
Net Institutional Flow
Rolling Flow
Flow Momentum
Flow Acceleration
Flow Z-Scores
Flow Percentiles
FII-DII Interaction States
Flow Regimes
Cash-Futures Alignment
Sector Flow Rankings
Stock-Level Flow Proxies
Institutional Flow Scores
Flow Confidence
Flow Quality Flags
```

This becomes the institutional-capital-flow layer for Open Analytics.
