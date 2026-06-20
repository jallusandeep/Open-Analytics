export const emptySummary = {
  connection_status: "not_connected",
  total_current_instruments: 0,
  total_expired_instruments: 0,
  total_ohlcv_daily: 0,
  total_equity_news: 0,
  total_ipo_calendar: 0,
  total_ipo_gmp_scraper: 0,
  total_ipo_scraper: 0,
  total_company_fundamentals: 0,
  total_market_holidays: 0,
  total_sync_runs: 0,
  last_sync_at: "",
  last_duration_seconds: null,
  current_last_sync_at: "",
  current_duration_seconds: null,
  expired_last_sync_at: "",
  expired_duration_seconds: null,
  ohlcv_daily_last_sync_at: "",
  ohlcv_daily_duration_seconds: null,
  equity_news_last_sync_at: "",
  equity_news_duration_seconds: null,
  ipo_calendar_last_sync_at: "",
  ipo_calendar_duration_seconds: null,
  ipo_gmp_scraper_last_sync_at: "",
  ipo_gmp_scraper_duration_seconds: null,
  ipo_scraper_last_sync_at: "",
  ipo_scraper_duration_seconds: null,
  company_fundamentals_last_sync_at: "",
  company_fundamentals_duration_seconds: null,
  market_holidays_last_sync_at: "",
  market_holidays_duration_seconds: null,
  active_job: null,
  active_job_status: null,
  active_job_started_at: null,
  active_job_current_records: null,
  active_job_records_at_start: null,
  active_job_records_added: null,
  disk_space: {
    total_bytes: null,
    used_bytes: null,
    free_bytes: null,
    used_percent: null,
    free_percent: null
  },
  queued_jobs: {
    count: 0,
    jobs: []
  }
};

export const emptyPreviewData = {
  rows: [],
  page: 1,
  page_size: 500,
  total_pages: 1,
  total_records: 0
};

export const DATA_COLLECTION_PREVIEW_PAGE_SIZE = 500;

export const emptyScheduleForm = {
  schedule_id: "",
  job_type: "current_instruments",
  schedule_time: "",
  time_format: "24",
  schedule_frequency: "daily",
  is_active: true
};

export const emptyOhlcvForm = {
  sources: ["current"],
  candle_modes: ["historical"],
  intervals: ["day"],
  from_date: "",
  to_date: "",
  use_current_day: true,
  auto_date_range: true,
  skip_existing: true,
  respect_api_limits: true,
  retry_failed: true,
  instrument_scope: "all",
  instrument_limit: "",
  single_instrument_key: "",
  batch_size: "25",
  request_delay_ms: "500",
  batch_delay_seconds: "2",
  retry_count: "3"
};

export const viewOptions = [
  { key: "monitor", label: "Collection Monitor" },
  { key: "current_preview", label: "Current Instruments" },
  { key: "expired_preview", label: "Expired Instruments" },
  { key: "ohlcv", label: "OHLCV" },
  { key: "equity_news", label: "Equity News" },
  { key: "ipo_calendar", label: "IPO Calendar" },
  { key: "company_fundamentals", label: "Company Fundamentals" },
  { key: "market_calendar", label: "Market Calendar" }
];

export const timeFormatOptions = [
  { value: "24", label: "24 Hours" },
  { value: "12", label: "12 Hours" }
];

export const scheduleFrequencyOptions = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" }
];

export const timePeriodOptions = [
  { value: "AM", label: "AM" },
  { value: "PM", label: "PM" }
];

export const currentSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "bod_complete", label: "BOD Complete" }
];

export const expiredSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "expired_option_contract", label: "Expired Options" },
  { value: "expired_future_contract", label: "Expired Futures" }
];

export const segmentOptions = [
  { value: "all", label: "All Segments" },
  { value: "NSE_EQ", label: "NSE EQ" },
  { value: "BSE_EQ", label: "BSE EQ" },
  { value: "NSE_FO", label: "NSE FO" },
  { value: "BSE_FO", label: "BSE FO" },
  { value: "NSE_INDEX", label: "NSE Index" },
  { value: "BSE_INDEX", label: "BSE Index" },
  { value: "NCD_FO", label: "NCD FO" },
  { value: "BCD_FO", label: "BCD FO" }
];

export const instrumentTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "EQ", label: "EQ" },
  { value: "FUT", label: "FUT" },
  { value: "CE", label: "CE" },
  { value: "PE", label: "PE" },
  { value: "INDEX", label: "INDEX" }
];

export const ohlcvSourceOptions = [
  { value: "current", label: "Current / Equity Instruments" },
  { value: "expired", label: "Expired Instruments" }
];

export const ohlcvModeOptions = [
  { value: "historical", label: "Historical" },
  { value: "intraday", label: "Intraday Current Day" }
];

export const ohlcvIntervalOptions = [
  { value: "1minute", label: "1 minute" },
  { value: "3minute", label: "3 minute" },
  { value: "5minute", label: "5 minute" },
  { value: "15minute", label: "15 minute" },
  { value: "30minute", label: "30 minute" },
  { value: "1hour", label: "1 hour" },
  { value: "day", label: "Day" },
  { value: "week", label: "Week" },
  { value: "month", label: "Month" }
];

export const marketHolidayTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "TRADING_HOLIDAY", label: "Trading Holiday" },
  { value: "SETTLEMENT_HOLIDAY", label: "Settlement Holiday" }
];

export const marketHolidayExchangeOptions = [
  { value: "all", label: "All Exchanges" },
  { value: "NSE", label: "NSE" },
  { value: "BSE", label: "BSE" },
  { value: "NFO", label: "NFO" },
  { value: "BFO", label: "BFO" },
  { value: "CDS", label: "CDS" },
  { value: "MCX", label: "MCX" }
];

export const marketHolidayTradingStatusOptions = [
  { value: "all", label: "All Status" },
  { value: "closed", label: "Closed" },
  { value: "open", label: "Partially Open" }
];

export const ipoCalendarSubTabOptions = [
  { value: "ipo", label: "IPO" },
  { value: "ipo_scraper", label: "IPO Scrapper" }
];

export const ipoStatusOptions = [
  { value: "all", label: "All Status" },
  { value: "upcoming", label: "Upcoming" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
  { value: "listed", label: "Listed" }
];

export const ipoIssueTypeOptions = [
  { value: "all", label: "All Issue Types" },
  { value: "regular", label: "Regular" },
  { value: "sme", label: "SME" }
];

export const ipoIndustryOptions = [
  { value: "all", label: "All Industries" }
];

export const companyFundamentalsEndpointOptions = [
  { value: "company_profile", label: "Company Profile" },
  { value: "balance_sheet", label: "Balance Sheet" },
  { value: "income_statement", label: "Income Statement" },
  { value: "cash_flow", label: "Cash Flow" },
  { value: "share_holdings", label: "Share Holdings" },
  { value: "key_ratios", label: "Key Ratios" },
  { value: "corporate_actions", label: "Corporate Actions" },
  { value: "competitors", label: "Competitors" }
];

export const companyFundamentalsStatementTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "consolidated", label: "Consolidated" },
  { value: "standalone", label: "Standalone" }
];

export const companyFundamentalsTimePeriodOptions = [
  { value: "all", label: "All Periods" },
  { value: "yearly", label: "Yearly" },
  { value: "quarterly", label: "Quarterly" }
];

export const dumpJobColumns = [
  { key: "source", label: "Source" },
  { key: "saved", label: "Saved" },
  { key: "updated", label: "Updated" },
  { key: "triggered_by", label: "Scheduled By" },
  { key: "time", label: "Time" },
  { key: "last_update_status", label: "Last Update Status" }
];

export const dumpJobGridTemplateColumns =
  "1.2fr 0.85fr 0.75fr 0.75fr 0.45fr 0.7fr 190px";

export const scheduleColumns = [
  { key: "schedule_time", label: "Time" },
  { key: "schedule_frequency", label: "Repeat" },
  { key: "next_run_at", label: "Next Run" },
  { key: "is_active", label: "Status" }
];

export const scheduleGridTemplateColumns = "0.9fr 0.8fr 1.35fr 0.7fr 112px";

export const previewColumns = [
  { key: "instrument_key", label: "Instrument Key" },
  { key: "trading_symbol", label: "Trading Symbol" },
  { key: "name", label: "Name" },
  { key: "segment", label: "Segment" },
  { key: "exchange", label: "Exchange" },
  { key: "instrument_type", label: "Type" },
  { key: "expiry", label: "Expiry" },
  { key: "strike_price", label: "Strike" },
  { key: "source_type", label: "Source" },
  { key: "synced_at", label: "Synced At" }
];

export const previewGridTemplateColumns =
  "280px 300px 300px 150px 150px 130px 150px 140px 190px 230px";

export const ohlcvPreviewColumns = [
  { key: "instrument_key", label: "Instrument Key" },
  { key: "trading_symbol", label: "Trading Symbol" },
  { key: "source", label: "Source" },
  { key: "mode", label: "Mode" },
  { key: "interval_label", label: "Interval" },
  { key: "timestamp", label: "Timestamp" },
  { key: "date", label: "Date" },
  { key: "open", label: "Open" },
  { key: "high", label: "High" },
  { key: "low", label: "Low" },
  { key: "close", label: "Close" },
  { key: "volume", label: "Volume" },
  { key: "open_interest", label: "Open Interest" },
  { key: "exchange", label: "Exchange" },
  { key: "segment", label: "Segment" },
  { key: "instrument_type", label: "Type" },
  { key: "expiry", label: "Expiry" },
  { key: "ingested_at", label: "Ingested At" }
];

export const ohlcvPreviewGridTemplateColumns =
  "280px 260px 130px 140px 140px 230px 130px 120px 120px 120px 120px 140px 150px 130px 130px 130px 130px 230px";

export const marketHolidayPreviewColumns = [
  { key: "holiday_date", label: "Holiday Date" },
  { key: "description", label: "Description" },
  { key: "holiday_type", label: "Holiday Type" },
  { key: "is_trading_day", label: "Trading Status" },
  { key: "closed_exchanges", label: "Closed Exchanges" },
  { key: "open_exchanges", label: "Open Exchanges" },
  { key: "source_provider", label: "Source" },
  { key: "synced_at", label: "Synced At" },
  { key: "updated_at", label: "Updated At" }
];

export const marketHolidayPreviewGridTemplateColumns =
  "150px 320px 190px 170px 320px 360px 130px 230px 230px";

export const equityNewsPreviewColumns = [
  { key: "instrument_key", label: "Instrument Key" },
  { key: "trading_symbol", label: "Trading Symbol" },
  { key: "company_name", label: "Company" },
  { key: "segment", label: "Segment" },
  { key: "heading", label: "Heading" },
  { key: "summary", label: "Summary" },
  { key: "source", label: "Source" },
  { key: "published_at", label: "Published At" },
  { key: "article_link", label: "Article Link" },
  { key: "ingested_at", label: "Ingested At" }
];

export const equityNewsPreviewGridTemplateColumns =
  "280px 190px 300px 130px 420px 520px 180px 230px 360px 230px";

export const ipoCalendarPreviewColumns = [
  { key: "ipo_id", label: "IPO ID" },
  { key: "symbol", label: "Symbol" },
  { key: "name", label: "Name" },
  { key: "status", label: "Status" },
  { key: "issue_type", label: "Issue Type" },
  { key: "isin", label: "ISIN" },
  { key: "issue_size", label: "Issue Size" },
  { key: "industry", label: "Industry" },
  { key: "minimum_price", label: "Min Price" },
  { key: "maximum_price", label: "Max Price" },
  { key: "bidding_start_date", label: "Start Date" },
  { key: "bidding_end_date", label: "End Date" },
  { key: "total_subscription", label: "Subscription" },
  { key: "synced_at", label: "Synced At" }
];

export const ipoCalendarPreviewGridTemplateColumns =
  "240px 160px 320px 130px 140px 170px 150px 260px 130px 130px 140px 140px 150px 230px";

export const ipoScraperPreviewColumns = [
  { key: "ipo_name", label: "IPO Name" },
  { key: "ipo_gmp", label: "IPO GMP" },
  { key: "price_band", label: "Price Band" },
  { key: "gain", label: "Gain" },
  { key: "ipo_date", label: "Date" },
  { key: "ipo_type", label: "Type" },
  { key: "ipo_status", label: "Status" },
  { key: "last_updated", label: "Last Updated" },
  { key: "scraped_at", label: "Scraped At" },
  { key: "updated_at", label: "Updated At" }
];

export const ipoScraperPreviewGridTemplateColumns =
  "320px 150px 180px 180px 180px 150px 160px 210px 230px 230px";

export const companyFundamentalsColumnGroups = {
  company_profile: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "sector", label: "Sector" },
      { key: "sector_market_cap_inr_formatted", label: "Market Cap INR" },
      { key: "sector_market_cap_usd_formatted", label: "Market Cap USD" },
      { key: "item_count", label: "Profile Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 230px 180px 180px 140px 140px 230px",
    minWidth: "min-w-[1780px]",
    rightAlignedKeys: [
      "sector_market_cap_inr_formatted",
      "sector_market_cap_usd_formatted",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  balance_sheet: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "statement_type", label: "Statement Type" },
      { key: "time_period", label: "Period Type" },
      { key: "latest_period", label: "Latest Period" },
      { key: "period_count", label: "Periods" },
      { key: "latest_total_asset", label: "Total Asset" },
      { key: "latest_total_liability", label: "Total Liability" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 170px 150px 150px 110px 160px 170px 110px 140px 230px",
    minWidth: "min-w-[2070px]",
    rightAlignedKeys: [
      "statement_type",
      "time_period",
      "latest_period",
      "period_count",
      "latest_total_asset",
      "latest_total_liability",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  income_statement: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "statement_type", label: "Statement Type" },
      { key: "time_period", label: "Period Type" },
      { key: "latest_period", label: "Latest Period" },
      { key: "period_count", label: "Periods" },
      { key: "latest_revenue", label: "Revenue" },
      { key: "latest_operating_profit", label: "Operating Profit" },
      { key: "latest_net_profit", label: "Net Profit" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 170px 150px 150px 110px 150px 180px 160px 110px 140px 230px",
    minWidth: "min-w-[2230px]",
    rightAlignedKeys: [
      "statement_type",
      "time_period",
      "latest_period",
      "period_count",
      "latest_revenue",
      "latest_operating_profit",
      "latest_net_profit",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  cash_flow: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "statement_type", label: "Statement Type" },
      { key: "time_period", label: "Period Type" },
      { key: "latest_period", label: "Latest Period" },
      { key: "period_count", label: "Periods" },
      { key: "latest_operating_cash_flow", label: "Operating CF" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 170px 150px 150px 110px 170px 110px 140px 230px",
    minWidth: "min-w-[1810px]",
    rightAlignedKeys: [
      "statement_type",
      "time_period",
      "latest_period",
      "period_count",
      "latest_operating_cash_flow",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  share_holdings: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "statement_type", label: "Statement Type" },
      { key: "time_period", label: "Period Type" },
      { key: "latest_period", label: "Latest Period" },
      { key: "period_count", label: "Periods" },
      { key: "latest_promoter_holding_pct", label: "Promoters %" },
      { key: "latest_fii_holding_pct", label: "FII %" },
      { key: "latest_dii_holding_pct", label: "DII %" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 170px 150px 150px 110px 140px 110px 110px 110px 140px 230px",
    minWidth: "min-w-[2100px]",
    rightAlignedKeys: [
      "statement_type",
      "time_period",
      "latest_period",
      "period_count",
      "latest_promoter_holding_pct",
      "latest_fii_holding_pct",
      "latest_dii_holding_pct",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  key_ratios: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "latest_period", label: "Latest Period" },
      { key: "pe_ratio_company", label: "P/E" },
      { key: "pb_ratio_company", label: "P/B" },
      { key: "roe_company", label: "ROE" },
      { key: "roce_company", label: "ROCE" },
      { key: "item_count", label: "Ratios" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns:
      "170px 190px 320px 150px 110px 110px 110px 110px 110px 140px 230px",
    minWidth: "min-w-[1650px]",
    rightAlignedKeys: [
      "latest_period",
      "pe_ratio_company",
      "pb_ratio_company",
      "roe_company",
      "roce_company",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  corporate_actions: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "latest_period", label: "Latest Action" },
      { key: "corporate_action_count", label: "Actions" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns: "170px 190px 320px 170px 130px 110px 140px 230px",
    minWidth: "min-w-[1460px]",
    rightAlignedKeys: [
      "latest_period",
      "corporate_action_count",
      "item_count",
      "api_status",
      "synced_at"
    ]
  },
  competitors: {
    columns: [
      { key: "isin", label: "ISIN" },
      { key: "trading_symbol", label: "Trading Symbol" },
      { key: "company_name", label: "Company" },
      { key: "sector", label: "Sector" },
      { key: "competitor_count", label: "Competitors" },
      { key: "item_count", label: "Items" },
      { key: "api_status", label: "API Status" },
      { key: "synced_at", label: "Synced At" }
    ],
    gridTemplateColumns: "170px 190px 320px 230px 140px 110px 140px 230px",
    minWidth: "min-w-[1530px]",
    rightAlignedKeys: [
      "competitor_count",
      "item_count",
      "api_status",
      "synced_at"
    ]
  }
};

export const defaultCompanyFundamentalsColumnGroup =
  companyFundamentalsColumnGroups.company_profile;
