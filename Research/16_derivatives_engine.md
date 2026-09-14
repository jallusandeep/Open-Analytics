# Open Analytics — Step 16: Derivatives Engine

## Purpose

The **Derivatives Engine** converts futures and options data into structured measures of positioning, implied expectations, leverage, volatility, hedging pressure, and market sentiment.

The engine should answer:

- Are futures trading at a premium or discount to spot?
- Is open interest rising or falling?
- Does price + OI suggest long buildup, short buildup, short covering, or long unwinding?
- Is rollover activity increasing?
- What is the market-implied volatility?
- Is implied volatility high or low relative to its own history?
- What is the volatility skew?
- What does the term structure look like?
- Are puts or calls dominating activity?
- What are the option Greeks?
- What is the expected move implied by options?
- Where is positioning concentrated by strike and expiry?
- Are index and stock derivatives confirming or contradicting cash-market signals?
- What risk and alpha features can be extracted without oversimplifying derivatives data?

Outputs feed directly into:

- Alpha / Signal Engine
- Market Regime Engine
- Risk Engine
- Institutional Flow Engine
- Event analysis
- Volatility strategies
- Hedging
- Portfolio construction
- Execution
- Machine learning features

---

# 16.1 Core Principle

Derivatives data is rich but easy to misinterpret.

Open Analytics should separate:

```text
Futures Pricing
Open Interest
Rollover
Implied Volatility
Skew
Term Structure
Option Activity
Greeks
Position Concentration
Expected Move
Participant Positioning
```

Do not reduce derivatives analysis to only:

```text
PCR
```

or:

```text
OI increase = bullish
```

Context is mandatory.

---

# 16.2 Required Inputs

Minimum futures inputs:

```text
instrument_key
underlying_key
date
expiry

spot_price
futures_price

open_interest
volume
```

Minimum options inputs:

```text
underlying_key
date
expiry
strike
option_type

spot_price
option_price
volume
open_interest
```

Preferred:

```text
bid
ask
last_price

implied_volatility
delta
gamma
theta
vega
rho

risk_free_rate
dividend_yield
time_to_expiry

participant-wise OI
```

---

# 16.3 Futures Basis

Basis:

```text
basis =
futures_price - spot_price
```

Store:

```text
futures_basis
```

---

# 16.4 Basis Percentage

```text
basis_pct =
(futures_price / spot_price) - 1
```

This makes basis comparable across instruments.

---

# 16.5 Annualized Basis

Conceptually:

```text
annualized_basis =
basis_pct × annualization_factor
```

A more precise implementation should use:

```text
days_to_expiry
```

Store:

```text
annualized_basis
```

---

# 16.6 Fair Value Basis

Theoretical futures fair value can depend on:

```text
spot
risk-free rate
dividend yield
time to expiry
```

Conceptually:

```text
F = S × exp((r - q) × T)
```

Store:

```text
theoretical_futures_price
fair_value_basis
basis_deviation
```

---

# 16.7 Futures Premium / Discount State

Possible:

```text
PREMIUM
FAIR
DISCOUNT
```

Store:

```text
basis_state
```

Thresholds should be configurable.

---

# 16.8 Open Interest

Store:

```text
open_interest
```

This represents outstanding derivative positions, not directional ownership by itself.

---

# 16.9 OI Change

Calculate:

```text
oi_change
oi_change_pct
```

Recommended:

```text
oi_change_1d
oi_change_5d
```

---

# 16.10 Price + OI State

Classic futures state matrix:

```text
Price ↑ + OI ↑
→ Long Buildup

Price ↓ + OI ↑
→ Short Buildup

Price ↑ + OI ↓
→ Short Covering

Price ↓ + OI ↓
→ Long Unwinding
```

Store:

```text
futures_position_state
```

Important:

This is a heuristic state, not direct proof of trader intent.

---

# 16.11 OI Intensity

Normalize OI:

```text
oi_percentile_252d
oi_z_60d
```

This helps identify unusually large positioning.

---

# 16.12 OI / Volume Ratio

```text
oi_volume_ratio =
open_interest / volume
```

Can help distinguish:

```text
existing position concentration
vs
high turnover
```

Use carefully.

---

# 16.13 Futures Volume

Store:

```text
futures_volume
```

Rolling:

```text
avg_futures_volume_20d
futures_volume_z_20d
```

---

# 16.14 Futures Liquidity

Possible:

```text
spread
depth
volume
OI
```

Create:

```text
futures_liquidity_score
```

---

# 16.15 Rollover

Near expiry, measure migration from current to next contract.

Possible:

```text
rollover_ratio =
next_month_OI
/
(current_month_OI + next_month_OI)
```

Store:

```text
rollover_ratio
```

---

# 16.16 Rollover Change

```text
rollover_change
```

Useful for expiry-week behavior.

---

# 16.17 Rollover Cost

Compare:

```text
next_month_futures
vs
near_month_futures
```

Store:

```text
rollover_cost
rollover_cost_pct
```

---

# 16.18 Futures Curve

For instruments with multiple expiries:

```text
near
next
far
```

Construct:

```text
futures_term_structure
```

Possible states:

```text
CONTANGO
FLAT
BACKWARDATION
```

---

# 16.19 Futures Curve Slope

```text
curve_slope =
far_contract_basis - near_contract_basis
```

Store:

```text
futures_curve_slope
```

---

# 16.20 Options Chain

For each underlying / expiry / strike:

```text
call_bid
call_ask
call_last
call_volume
call_oi

put_bid
put_ask
put_last
put_volume
put_oi
```

Maintain raw chain snapshots.

---

# 16.21 Moneyness

Classify each option:

```text
ITM
ATM
OTM
```

Better continuous metric:

```text
moneyness =
strike / spot
```

or log-moneyness.

Store:

```text
moneyness
```

---

# 16.22 Time to Expiry

Store:

```text
days_to_expiry
time_to_expiry_years
```

This is essential for IV and Greeks.

---

# 16.23 Implied Volatility

If IV is not provided, solve from option price using an option pricing model.

Store:

```text
implied_volatility
```

At minimum:

```text
call_iv
put_iv
```

---

# 16.24 ATM Implied Volatility

Identify ATM strike and compute:

```text
atm_iv
```

Possible aggregation:

```text
average(call_iv, put_iv)
```

around closest ATM strikes.

---

# 16.25 IV Percentile

Compare current IV to historical distribution.

```text
iv_percentile_252d
```

Recommended convention:

```text
100 = very high IV
0 = very low IV
```

---

# 16.26 IV Rank

Traditional form:

```text
iv_rank =
(current_iv - min_iv_lookback)
/
(max_iv_lookback - min_iv_lookback)
```

Store:

```text
iv_rank_252d
```

Note:

IV Rank and IV Percentile are not the same metric.

---

# 16.27 Realized vs Implied Volatility

Compare:

```text
atm_iv
vs
realized_volatility
```

Store:

```text
iv_rv_spread
```

Example:

```text
atm_iv = 30%
realized vol = 20%

iv_rv_spread = +10%
```

---

# 16.28 Volatility Risk Premium

Conceptually:

```text
VRP =
implied_volatility - realized_volatility
```

Store:

```text
volatility_risk_premium
```

Use consistent maturities.

---

# 16.29 IV Term Structure

Compare ATM IV across expiries.

Possible:

```text
iv_near
iv_next
iv_far
```

Store:

```text
iv_term_structure_slope
```

Possible states:

```text
NORMAL
FLAT
INVERTED
```

---

# 16.30 Volatility Skew

Compare IV across strikes.

Common:

```text
OTM put IV - ATM IV
```

Store:

```text
put_skew
```

Also:

```text
call_skew
```

---

# 16.31 Risk Reversal

Possible:

```text
25-delta call IV - 25-delta put IV
```

Store:

```text
risk_reversal_25d
```

Requires reliable delta-based chain mapping.

---

# 16.32 Butterfly

Possible:

```text
0.5 × (call25_iv + put25_iv) - atm_iv
```

Store:

```text
butterfly_25d
```

Advanced but useful for smile shape.

---

# 16.33 Volatility Smile

Maintain:

```text
strike
moneyness
IV
```

across chain.

Research outputs may include:

```text
smile_curvature
```

---

# 16.34 Put-Call Ratio by OI

```text
pcr_oi =
put_oi / call_oi
```

Store:

```text
pcr_oi
```

---

# 16.35 Put-Call Ratio by Volume

```text
pcr_volume =
put_volume / call_volume
```

Store:

```text
pcr_volume
```

---

# 16.36 PCR Percentile

Normalize:

```text
pcr_oi_percentile
pcr_volume_percentile
```

Do not interpret a single absolute threshold universally.

---

# 16.37 Strike-Level OI Concentration

Identify strikes with high OI.

Store:

```text
max_call_oi_strike
max_put_oi_strike
```

Also:

```text
top_call_oi_strikes
top_put_oi_strikes
```

---

# 16.38 OI Change by Strike

Store:

```text
call_oi_change
put_oi_change
```

This can reveal where new positions are accumulating.

---

# 16.39 Max Pain

Possible calculation:

```text
max_pain_strike
```

This is a descriptive metric, not a guaranteed settlement target.

Use cautiously.

---

# 16.40 Expected Move

A common approximation from ATM straddle:

```text
expected_move =
ATM call price + ATM put price
```

Percentage:

```text
expected_move_pct =
expected_move / spot
```

Can also derive from IV:

```text
expected_move ≈ spot × IV × sqrt(T)
```

Store both if available:

```text
straddle_expected_move
iv_expected_move
```

---

# 16.41 ATM Straddle

Store:

```text
atm_call_price
atm_put_price
atm_straddle_price
```

Useful for event-volatility analysis.

---

# 16.42 ATM Strangle

Optional:

```text
atm_strangle_price
```

based on selected OTM strikes.

---

# 16.43 Option Greeks

Store per contract:

```text
delta
gamma
theta
vega
rho
```

---

# 16.44 Delta

Measures first-order price sensitivity.

Store:

```text
delta
```

---

# 16.45 Gamma

Measures change in delta.

Store:

```text
gamma
```

High gamma near expiry can create fast directional sensitivity.

---

# 16.46 Theta

Measures time decay.

Store:

```text
theta
```

---

# 16.47 Vega

Measures volatility sensitivity.

Store:

```text
vega
```

---

# 16.48 Rho

Measures rate sensitivity.

Usually smaller importance in short-dated equity options, but retain.

---

# 16.49 Greeks Quality

If Greeks are computed internally, store:

```text
pricing_model
risk_free_rate
dividend_yield
calculation_timestamp
```

---

# 16.50 Delta-Adjusted Exposure

Possible:

```text
delta_exposure =
OI × lot_size × delta
```

Store:

```text
delta_exposure
```

---

# 16.51 Gamma Exposure

Possible:

```text
gamma_exposure =
OI × lot_size × gamma × spot-related scaling
```

Store:

```text
gamma_exposure
```

Precise convention must be standardized.

---

# 16.52 Aggregate GEX

Aggregate by:

```text
strike
expiry
underlying
```

Store:

```text
aggregate_gamma_exposure
```

Interpret cautiously because dealer position sign is not directly observable from OI alone.

---

# 16.53 Delta Exposure by Strike

Store:

```text
strike_delta_exposure
```

This can help characterize directional sensitivity distribution.

---

# 16.54 Option OI Concentration

Possible:

```text
oi_concentration_index
```

A high concentration at few strikes may matter around expiry.

---

# 16.55 Expiry Concentration

Measure proportion of total OI in near expiry.

```text
near_expiry_oi_share
```

---

# 16.56 Option Volume Surprise

```text
option_volume_z
```

for calls, puts, and total chain.

---

# 16.57 Call/Put Volume Imbalance

```text
option_volume_imbalance =
call_volume - put_volume
```

or normalized:

```text
(call_volume - put_volume)
/
(call_volume + put_volume)
```

Store:

```text
option_volume_imbalance
```

---

# 16.58 Call/Put OI Imbalance

Similarly:

```text
option_oi_imbalance
```

---

# 16.59 Intraday Chain Change

If intraday snapshots exist:

```text
IV change
OI change
volume change
skew change
```

This supports intraday derivatives analytics.

---

# 16.60 Event IV

Before earnings or major events, IV may rise.

Store:

```text
pre_event_iv
post_event_iv
iv_crush
```

Useful for event-driven options analysis.

---

# 16.61 IV Crush

```text
iv_crush =
pre_event_iv - post_event_iv
```

Store:

```text
iv_crush_pct
```

---

# 16.62 Futures-Options Confirmation

Possible state:

```text
futures long buildup
+
call-side IV expansion
```

or other combinations.

Store:

```text
derivatives_confirmation_state
```

Avoid simplistic bullish/bearish labels.

---

# 16.63 Spot-Futures Divergence

Example:

```text
spot rising
basis weakening
```

Store:

```text
spot_futures_divergence
```

---

# 16.64 OI-Price Divergence

Possible:

```text
price rises while OI falls
```

which maps to short covering rather than fresh long buildup.

Store:

```text
oi_price_state
```

---

# 16.65 Derivatives Sentiment Score

Possible components:

```text
basis
OI state
PCR
skew
IV percentile
futures positioning
```

Output:

```text
derivatives_sentiment_score
```

This must remain explainable.

---

# 16.66 Derivatives Risk Score

Separate:

```text
derivatives_risk_score
```

Possible inputs:

```text
extreme IV
skew
near-expiry concentration
gamma exposure
liquidity
spread
```

---

# 16.67 Volatility Regime Score

Possible:

```text
volatility_regime_score
```

using:

```text
IV percentile
RV
IV-RV spread
term structure
skew
```

This can later feed Market Regime Engine.

---

# 16.68 Futures Positioning Score

Potential:

```text
futures_positioning_score
```

from:

```text
basis
OI change
rollover
participant positioning
```

---

# 16.69 Option Positioning Score

Potential:

```text
options_positioning_score
```

from:

```text
PCR
skew
OI concentration
IV term structure
volume imbalance
```

---

# 16.70 Composite Derivatives Score

Potential:

```text
derivatives_score
```

combining:

```text
futures positioning
options positioning
volatility regime
```

Weights must be researched.

---

# 16.71 Derivatives Confidence

Possible:

```text
derivatives_confidence
```

Inputs:

```text
chain completeness
quote freshness
OI completeness
spread quality
model quality
participant data availability
```

---

# 16.72 Derivatives Quality Status

Possible:

```text
VALID
PARTIAL_CHAIN
STALE_QUOTES
MISSING_IV
MISSING_GREEKS
LOW_LIQUIDITY
EXPIRY_EDGE_CASE
INVALID
```

---

# 16.73 Futures Daily Record

Recommended:

```text
date
underlying_key
expiry

spot_price
futures_price

basis
basis_pct
annualized_basis

theoretical_futures_price
basis_deviation

open_interest
oi_change
oi_change_pct

futures_volume
futures_volume_z

futures_position_state

rollover_ratio
rollover_cost

futures_curve_slope

futures_positioning_score

derivatives_quality_status
```

---

# 16.74 Option Contract Record

```text
date
underlying_key
expiry
strike
option_type

bid
ask
last_price

volume
open_interest

implied_volatility

delta
gamma
theta
vega
rho

moneyness
days_to_expiry

quality_status
```

---

# 16.75 Underlying-Level Option Summary

```text
date
underlying_key
expiry

spot_price

atm_strike
atm_iv

iv_rank_252d
iv_percentile_252d

pcr_oi
pcr_volume

put_skew
call_skew
risk_reversal_25d

max_call_oi_strike
max_put_oi_strike
max_pain_strike

atm_straddle_price
expected_move
expected_move_pct

aggregate_gamma_exposure

options_positioning_score
derivatives_risk_score
```

---

# 16.76 Initial Production Futures Metrics

Recommended first version:

```text
spot_price
futures_price

basis
basis_pct
annualized_basis

open_interest
oi_change
oi_change_pct

futures_volume

futures_position_state

rollover_ratio
rollover_cost

futures_positioning_score
```

---

# 16.77 Initial Production Options Metrics

Recommended:

```text
atm_iv
iv_percentile_252d
iv_rank_252d

pcr_oi
pcr_volume

put_skew

max_call_oi_strike
max_put_oi_strike

atm_straddle_price
expected_move_pct

delta
gamma
theta
vega

options_positioning_score
derivatives_risk_score
```

Then expand into:

```text
term structure
risk reversals
gamma exposure
intraday chain dynamics
```

---

# 16.78 Derivatives Engine Processing Flow

Recommended:

```text
RAW FUTURES / OPTIONS DATA
        ↓
CONTRACT / EXPIRY MAPPING
        ↓
QUOTE / OI VALIDATION
        ↓
SPOT ALIGNMENT
        ↓
FUTURES BASIS
        ↓
OI CHANGE
        ↓
PRICE + OI STATE
        ↓
ROLLOVER / CURVE
        ↓
OPTIONS CHAIN NORMALIZATION
        ↓
IV CALCULATION
        ↓
IV RANK / PERCENTILE
        ↓
SKEW / TERM STRUCTURE
        ↓
PCR / OI CONCENTRATION
        ↓
EXPECTED MOVE
        ↓
GREEKS
        ↓
EXPOSURE AGGREGATION
        ↓
FUTURES / OPTIONS SCORES
        ↓
DERIVATIVES RISK / SENTIMENT
        ↓
QUALITY / CONFIDENCE
```

---

# 16.79 Point-in-Time Rule

At timestamp T, use only:

```text
quotes known at T
OI published/known at T
spot known at T
risk-free rate known at T
dividend assumptions known at T
```

No future chain values.

---

# 16.80 Expiry Mapping

Every contract needs:

```text
expiry_date
contract_month
days_to_expiry
```

Near-expiry handling must be explicit.

---

# 16.81 Contract Roll Handling

Continuous futures series must not simply splice raw prices.

Possible:

```text
back-adjusted futures
ratio-adjusted futures
unadjusted front-month series
```

Store methodology.

---

# 16.82 Corporate Actions

Stock derivatives may be adjusted around:

```text
splits
bonus
rights
mergers
```

Contract multipliers / strikes can change.

Maintain exchange adjustment history.

---

# 16.83 Missing Chain Data

Do not interpret absent strikes as zero OI or zero volume.

Use:

```text
null
```

and:

```text
chain_completeness_score
```

---

# 16.84 Stale Quotes

Track:

```text
quote_timestamp
quote_age
stale_quote_flag
```

IV/Greeks from stale quotes may be invalid.

---

# 16.85 Wide Spreads

When:

```text
bid-ask spread is too wide
```

mid-price IV becomes unreliable.

Use quality flags.

---

# 16.86 Zero Bid Options

Very far OTM options may have:

```text
bid = 0
```

Treat with caution for IV/skew calculations.

---

# 16.87 Illiquid Strikes

Exclude or downweight strikes with:

```text
very low OI
very low volume
wide spread
stale quote
```

when estimating smile/skew.

---

# 16.88 IV Model Assumptions

If computing IV internally, store:

```text
pricing_model
risk_free_rate
dividend_yield
spot_or_forward_input
```

For index vs stock options, assumptions may differ.

---

# 16.89 American vs European Exercise

Use the correct pricing model for contract exercise style.

Do not assume one model universally.

---

# 16.90 Research Diagnostics

Test:

```text
basis vs forward returns
OI state vs forward returns
IV percentile vs realized volatility
skew vs downside returns
PCR vs future direction
term structure vs volatility regime
```

---

# 16.91 Derivatives Information Coefficient

For cross-sectional stock derivatives:

```text
rank_IC(
    derivatives_score_t,
    forward_return_t+h
)
```

---

# 16.92 Volatility Forecast Testing

For IV-related models:

```text
forecast error =
future realized volatility - implied volatility
```

Track by horizon.

---

# 16.93 Event Testing

Around:

```text
earnings
RBI policy
budget
elections
major corporate announcements
```

test:

```text
pre-event IV
post-event IV
expected move
actual move
```

---

# 16.94 Important Quant Rules

## Rule 1 — OI Does Not Reveal Direction by Itself

Use price + OI context.

## Rule 2 — PCR Is Not a Standalone Signal

Normalize and combine with skew/IV/context.

## Rule 3 — IV Rank and IV Percentile Are Different

Store both correctly.

## Rule 4 — Options Positions Can Be Hedges

Avoid simplistic bullish/bearish interpretations.

## Rule 5 — Use Liquidity Filters

Illiquid strikes produce bad IV/skew estimates.

## Rule 6 — Greeks Depend on Model Inputs

Store assumptions.

## Rule 7 — Expiry Effects Matter

Near-expiry data behaves differently.

## Rule 8 — Corporate Actions Can Alter Contracts

Maintain adjustment history.

## Rule 9 — Spot/Futures/Options Must Be Time-Aligned

Do not combine mismatched timestamps.

## Rule 10 — Keep Raw Chain Data

Derived summaries must remain auditable.

## Rule 11 — Point-in-Time Handling Is Mandatory

No future chain/OI values in historical backtests.

## Rule 12 — Derivatives Score Must Be Decomposable

Keep basis, OI, IV, skew, and PCR components visible.

---

# 16.95 Completion Criteria

Step 16 is complete when Open Analytics can answer:

1. What is the futures basis?
2. Is futures trading at premium or discount?
3. What is the annualized basis?
4. Is OI rising or falling?
5. Does price + OI imply long buildup, short buildup, short covering, or long unwinding?
6. What is the rollover ratio?
7. What is the futures curve state?
8. What is ATM implied volatility?
9. What is IV percentile?
10. What is IV rank?
11. How does IV compare with realized volatility?
12. What is the volatility risk premium?
13. What is the IV term structure?
14. What is the put skew?
15. What are PCR OI and PCR volume?
16. Where is call/put OI concentrated?
17. What is the expected move?
18. What are Delta, Gamma, Theta, and Vega?
19. What is aggregate derivatives positioning?
20. What is the derivatives sentiment score?
21. What is the derivatives risk score?
22. Are quotes and chain data sufficiently liquid and fresh?
23. Were all calculations point-in-time correct?
24. Can the exact historical derivatives state be reproduced?

Once these are reliable, the Derivatives Engine is ready to feed:

```text
Step 17 — Market Breadth Engine
```

---

# Step 16 Final Output

The Derivatives Engine transforms:

```text
Spot
+
Futures
+
Option Chain
+
Open Interest
+
Volatility Inputs
```

into:

```text
Futures Basis
Annualized Basis
OI Change
Price/OI States
Rollover
Futures Curve
ATM IV
IV Rank
IV Percentile
IV-RV Spread
Volatility Risk Premium
Skew
Term Structure
PCR
OI Concentration
Expected Move
Greeks
Delta/Gamma Exposure
Futures Positioning Score
Options Positioning Score
Derivatives Sentiment
Derivatives Risk
Derivatives Quality Flags
```

This becomes the leveraged-positioning and implied-expectations layer for Open Analytics.
