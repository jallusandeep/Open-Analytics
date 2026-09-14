Yes. Keep it much simpler. The UI should look like this.

```text
┌────┐
│  > │
├────┤
│ ⌂  │ Home
│ ◉  │ Stocks
│ ⌕  │ Research
│ ◫  │ Portfolio
│ ↻  │ Backtest
│ ◈  │ Market
├────┤
│ ⚙  │ Settings
└────┘
```

### Home

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ HOME                                                   As of 14 Sep 2026    │
├──────────────────────────────────────────────────────────────────────────────┤
│ Regime        Breadth       Risk         Flow         Opportunity            │
│ Bull/Low Vol  Broad 68%     Moderate     Mixed        High                   │
├──────────────────────────────────────────────────────────────────────────────┤
│ TOP PRIORITY SIGNALS                                                        │
│ Symbol    Decision     Change       Alpha   Conf   Risk   Action             │
│ REL       STRONG BUY   WATCH→BUY     94      88    Low    ENTER              │
│ HDFC      BUY          HOLD→BUY      89      84    Med    ADD                │
│ INFY      WATCH        NEW           77      69    Low    WATCH              │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ SIGNAL CHANGES                       │ IMPORTANT EVENTS                      │
│ REL  WATCH → BUY                     │ HDFC  Earnings                        │
│ SBIN BUY → HOLD                      │ INFY  Order announcement              │
├──────────────────────────────────────┼───────────────────────────────────────┤
│ MARKET BREADTH                       │ FACTOR LEADERSHIP                     │
│ Advancing      342                   │ Momentum   Strong                     │
│ Declining      143                   │ Quality    Strong                     │
│ Above SMA50     64%                  │ Value      Neutral                    │
├──────────────────────────────────────┼───────────────────────────────────────┤
│ SECTORS                              │ RISK MONITOR                          │
│ Financials Strong                    │ Volatility  11.8%                     │
│ IT         Strong                    │ Beta         0.92                     │
│ Metals     Weak                      │ Drawdown    -2.1%                     │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

### Stocks

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ RELIANCE INDUSTRIES LTD                                                     │
│ ₹2,984   +1.24%                                                             │
│                                                                            │
│ STRONG BUY   Score 82   Confidence 78   21D Alpha +4.6%   Risk MODERATE    │
│ Portfolio: 3.2% → 4.5%   Action: ADD                                      │
├──────────────────────────────────────────────────────────────────────────────┤
│ Overview | Technical | Fundamental | Events | Flow | Derivatives | Forecast │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ WHY POSITIVE                         │ KEY RISKS                             │
│ + Strong momentum                    │ - Expensive valuation                 │
│ + High quality                       │ - Volatility rising                   │
│ + Positive flow                      │ - Earnings soon                       │
├──────────────────────────────────────┼───────────────────────────────────────┤
│ PRICE / TREND                        │ SIGNAL MAP                            │
│ [Chart]                              │ Trend        STRONG                   │
│ SMA20 +5.2%                          │ Momentum     STRONG                   │
│ SMA50 +9.1%                          │ Quality      STRONG                   │
│ SMA200 +18.4%                        │ News         POSITIVE                 │
│                                     │ ML           POSITIVE                 │
├──────────────────────────────────────┼───────────────────────────────────────┤
│ FUNDAMENTALS                         │ VALUATION                             │
│ ROE       17.8%                      │ P/E      24.3x                        │
│ ROIC      15.9%                      │ FCF Yld   3.8%                        │
│ EPS YoY   15.2%                      │ Value %ile 52                         │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

### Research

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ RESEARCH                         Search...       Universe: NIFTY 500 ▼       │
├──────────────────────────────────────────────────────────────────────────────┤
│ High Alpha | High Confidence | Momentum | Quality | Value | Catalysts | ML  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Symbol  Decision  Alpha  Conf  Trend  Quality  Value  News  ML  Risk        │
│ REL     STR BUY    94     88    ↑↑      81       52    +    91  Med         │
│ HDFC    BUY        89     84    ↑       86       63    0    87  Low         │
│ INFY    WATCH      77     69    ↑       79       48    +    82  Low         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Portfolio

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ PORTFOLIO                                              Core Equity Strategy  │
├──────────────────────────────────────────────────────────────────────────────┤
│ Value      Day P&L    Return     Alpha     Vol      Beta     Drawdown         │
│ ₹XX        +₹XX       +14.8%     +5.3%     11.8%    0.92     -2.1%           │
├──────────────────────────────────────────────────────────────────────────────┤
│ ACTIONS                                                                     │
│ ENTER   REL      Target 4.5%      Strong Buy                               │
│ ADD     HDFC     +1.2%            Buy                                      │
│ HOLD    INFY     3.1%             Hold                                     │
│ TRIM    SBIN     -0.8%            Risk concentration                       │
│ EXIT    ABC      Full             Avoid                                    │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ ALLOCATION                           │ RISK                                  │
│ Financials 24% → 22%                 │ Portfolio Vol 11.8%                   │
│ IT         18% → 19%                 │ Beta          0.92                    │
│ Energy     11% → 14%                 │ Risk State    NORMAL                  │
├──────────────────────────────────────────────────────────────────────────────┤
│ POSITIONS                                                                    │
│ Symbol Weight Target P&L Alpha Conf Risk Decision Action                    │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Backtest

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ BACKTEST                                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Strategy: High Alpha + High Confidence                                      │
│ Universe: NIFTY 500   Rebalance: Weekly   Top 20                            │
├──────────────────────────────────────────────────────────────────────────────┤
│ CAGR       Sharpe      Max DD      Turnover      Excess Return               │
│ 18.2%      1.42        -12.4%      3.1x          +6.6%                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ [NAV vs Benchmark Chart]                                                     │
├──────────────────────────────────────────────────────────────────────────────┤
│ Yearly Returns | Regime | IC | Trades | Diagnostics                         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Market

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ MARKET                                                                       │
├──────────────────────────────────────────────────────────────────────────────┤
│ REGIME: BULL / LOW VOL       Confidence 82%       Stress 31                 │
├──────────────────────────────────────┬───────────────────────────────────────┤
│ BREADTH                              │ SECTORS                               │
│ Advancers 342                        │ Financials Strong                     │
│ Decliners 143                        │ IT         Strong                     │
│ > SMA50   64%                        │ Metals     Weak                       │
├──────────────────────────────────────┼───────────────────────────────────────┤
│ FLOW                                 │ DERIVATIVES                           │
│ FII   Negative                       │ PCR        1.08                       │
│ DII   Positive                       │ IV %ile     62                        │
│ Combined Mixed                       │ Futures    Neutral                    │
└──────────────────────────────────────┴───────────────────────────────────────┘
```

This is the UI shape I would use: **compact, dark, table-heavy, priority-first, with minimal cards and strong drill-downs.**
