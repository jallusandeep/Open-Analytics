


1. **Universe Definition** — decide which stocks are eligible for research/trading: NSE equities, NIFTY 500, F&O stocks, liquidity limits, minimum history, exclusions.

2. **Data Quality & Validation** — verify OHLCV, missing dates, duplicates, bad prices, zero volume, stale instruments, IPO history, suspended/delisted stocks.

3. **Corporate Action Adjustment** — adjust historical prices/volume for splits, bonus, dividends, rights issues, mergers where relevant.

4. **Returns Engine** — calculate daily, weekly, monthly, multi-period, log, intraday, overnight, cumulative, benchmark-relative and sector-relative returns.

5. **Risk Engine** — volatility, downside volatility, drawdown, beta, correlation, covariance, VaR, CVaR and tail-risk metrics.

6. **Liquidity & Tradability Engine** — traded value, average volume, turnover, spread, liquidity score, price impact and whether the stock can realistically be traded.

7. **Trend Engine** — moving averages, slopes, breakout state, 52-week position, trend persistence and trend strength.

8. **Momentum Engine** — 1M/3M/6M/12M momentum, skip-month momentum, relative strength, acceleration and momentum ranking.

9. **Volume & Participation Engine** — relative volume, volume z-score, OBV, VWAP-related measures and price-volume confirmation.

10. **Cross-Sectional Ranking Engine** — compare every stock against the universe using percentile ranks, z-scores, sector ranks, winsorization and neutralization.

11. **Fundamental Engine** — profitability, balance-sheet quality, cash flow, growth, leverage, margins and earnings quality.

12. **Valuation Engine** — P/E, P/B, EV/EBITDA, FCF yield, earnings yield and valuation relative to history/sector.

13. **Factor Engine** — combine raw measurements into Momentum, Value, Quality, Growth, Low Volatility, Liquidity and other factor scores.

14. **News & Event Engine** — sentiment, event classification, relevance, novelty, earnings news, management changes, orders, regulation and other events.

15. **Institutional Flow Engine** — FII/DII flows, rolling flows, flow momentum, z-scores and market participation.

16. **Derivatives Engine** — futures basis, OI, rollover, options IV, IV rank, PCR, skew, Greeks and derivatives positioning.

17. **Market Breadth Engine** — advance/decline, stocks above moving averages, new highs/lows and participation across the whole market.

18. **Market Regime Engine** — identify bull/bear, high/low volatility, trending/ranging, liquidity and correlation regimes.

19. **Alpha / Signal Engine** — combine factors, market conditions and events into measurable long/short opportunity scores.

20. **Confidence Engine** — measure how reliable a signal is based on historical evidence, factor agreement, regime fit, data quality and model uncertainty.

21. **Portfolio Construction Engine** — choose stocks, weights, sector limits, factor exposure, diversification and capital allocation.

22. **Position Sizing & Risk Controls** — volatility sizing, max position, stop logic where appropriate, portfolio risk limits and exposure limits.

23. **Execution & Transaction Cost Engine** — spread, slippage, brokerage, taxes, fees, impact and expected implementation cost.

24. **Backtesting Engine** — simulate historical strategies correctly with lagged information, costs, rebalancing and survivorship-safe data.

25. **Performance Analytics** — CAGR, Sharpe, Sortino, Calmar, drawdown, turnover, hit rate, alpha, beta and other strategy statistics.

26. **Attribution Engine** — explain where returns came from: stock selection, sector, momentum, value, quality, market beta, costs, etc.

27. **ML Dataset Engine** — prepare features, targets, labels, lagging, normalization and train/validation/test datasets without leakage.

28. **Machine Learning / Forecasting** — regression, classification, ranking, tree models, boosting, deep learning or other predictive models only after the earlier layers are trustworthy.

29. **Stock Search / Screener Engine** — query all calculated metrics to find stocks meeting quantitative conditions.

30. **Final Research Decision Layer** — produce ranked candidates with **Alpha Score, Risk Score, Liquidity Score, Factor Scores, Confidence, expected return and explanation**.
