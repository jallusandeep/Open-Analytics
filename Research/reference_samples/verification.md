# Ten verified equity samples

Filled in the local Reference Data master on 16 September 2026. Refresh the Reference Data page to see them.

Company names, ISIN, NSE listing date and face value were verified against the downloaded [NSE equity master](https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv). ISIN and sector were cross-checked against the [NSE Nifty 50 constituents](https://nsearchives.nseindia.com/content/indices/ind_nifty50list.csv). Source CSV snapshots are in this folder.

The four classification levels are explicitly mapped using the [NSE industry classification structure, March 2022](https://nsearchives.nseindia.com/web/sites/default/files/inline-files/NSE%20Indices_Industry%20Classification%20Structure-2022-03.pdf). This is a versioned taxonomy mapping, not a claim that a new 2026 taxonomy was downloaded. The NSE sample in the research document places Reliance in Commodities; the official taxonomy places Refineries & Marketing in Energy, which is used here.

Short names are display labels chosen for readability. COMMON_EQUITY is the application's normalized class for these regular EQ equity samples. Listing dates are NSE listing dates, not company incorporation dates or earliest listing across exchanges. Upstox keys, symbols, exchange identity and derived listing/derivative fields were preserved. Market-cap buckets and unsupported suspension/delisting fields were not guessed. No historical index-entry or corporate-action dates were invented.

| Symbol | ISIN | Sector | Industry | Basic industry | NSE listing date | Face value (INR) | Verify basic industry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| BHARTIARTL | INE397D01024 | Telecommunication | Telecom - Services | Telecom - Cellular & Fixed line services | 2002-02-15 | 5.0 | [Source](https://nsearchives.nseindia.com/corporate/GEECEEVC12345_13032026192108_COV_Bharti_Airtel_signed.pdf) |
| HDFCBANK | INE040A01034 | Financial Services | Banks | Private Sector Bank | 1995-11-08 | 1.0 | [Source](https://www.nseindia.com/get-quote/equity/HDFCBANK/HDFC-Bank-Limited) |
| HINDUNILVR | INE030A01027 | Fast Moving Consumer Goods | Diversified FMCG | Diversified FMCG | 1995-07-06 | 1.0 | [Source](https://nsearchives.nseindia.com/corporate/HDFCAMC_09052026151018_Monthly_Portfolios_for_April_2026.pdf) |
| ICICIBANK | INE090A01021 | Financial Services | Banks | Private Sector Bank | 1997-09-17 | 2.0 | [Source](https://www.nseindia.com/get-quotes/equity?symbol=ICICIBANK) |
| INFY | INE009A01021 | Information Technology | IT - Software | Computers - Software & Consulting | 1995-02-08 | 5.0 | [Source](https://www.nseindia.com/get-quote/equity/INFY/Infosys-Limited) |
| ITC | INE154A01025 | Fast Moving Consumer Goods | Diversified FMCG | Diversified FMCG | 1995-08-23 | 1.0 | [Source](https://www.nseindia.com/get-quote/equity/ITC/ITC-Limited) |
| LT | INE018A01030 | Construction | Construction | Civil Construction | 2004-06-23 | 2.0 | [Source](https://www.nseindia.com/get-quote/equity/LT/Larsen-%26-Toubro-Limited) |
| RELIANCE | INE002A01018 | Oil, Gas & Consumable Fuels | Petroleum Products | Refineries & Marketing | 1995-11-29 | 10.0 | [Source](https://www.nseindia.com/get-quote/equity/RELIANCE/Reliance-Industries-Limited) |
| SBIN | INE062A01020 | Financial Services | Banks | Public Sector Bank | 1995-03-01 | 1.0 | [Source](https://www.nseindia.com/get-quote/equity/SBIN/State-Bank-of-India) |
| TCS | INE467B01029 | Information Technology | IT - Software | Computers - Software & Consulting | 2004-08-25 | 1.0 | [Source](https://www.nseindia.com/get-quotes/equity?symbol=TCS) |

`ten_equities_upload.csv` contains only enrichment fields with U flags and is compatible with the Securities upload. `ten_equities_data.csv` contains all master columns for review. `before_fill.json` retains the ten original rows. Sync will retain this enrichment through manual_fields.
