import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  Edit3,
  HardDrive,
  Play,
  Power,
  RefreshCcw,
  Trash2,
  X,
  XCircle
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Tooltip from "../../components/common/Tooltip";
import Modal from "../../components/common/Modal";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaCheckboxControlStyles,
  oaFormTextStyles,
  oaPillStyles,
  oaTabStyles
} from "../../components/common/uiStyles";
import {
  cancelUpstoxDataCollection,
  createUpstoxDataCollectionSchedule,
  deleteUpstoxDataCollectionSchedule,
  getUpstoxDataCollectionRuns,
  getUpstoxDataCollectionSchedules,
  getIpoGmpScraperPreview,
  getUpstoxDataCollectionSummary,
  getUpstoxEquityNewsPreview,
  getUpstoxExpiredInstrumentsPreview,
  getUpstoxInstrumentsPreview,
  getUpstoxIpoCalendarPreview,
  getUpstoxMarketHolidaysPreview,
  getUpstoxOhlcvOptions,
  getUpstoxOhlcvPreview,
  getUpstoxCompanyFundamentalsPreview,
  saveUpstoxOhlcvOptions,
  syncIpoGmpScraper,
  syncUpstoxCompanyFundamentals,
  syncUpstoxCurrentInstruments,
  syncUpstoxEquityNews,
  syncUpstoxExpiredInstruments,
  syncUpstoxIpoCalendar,
  syncUpstoxMarketHolidays,
  syncUpstoxOhlcvDaily,
  toggleUpstoxDataCollectionSchedule,
  updateUpstoxDataCollectionSchedule
} from "../../api/dataCollectionApi";
import DatePicker from "../../components/common/DatePicker";

const emptySummary = {
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

const emptyPreviewData = {
  rows: [],
  page: 1,
  page_size: 500,
  total_pages: 1,
  total_records: 0
};

const DATA_COLLECTION_PREVIEW_PAGE_SIZE = 500;

const emptyScheduleForm = {
  schedule_id: "",
  job_type: "current_instruments",
  schedule_time: "",
  time_format: "24",
  schedule_frequency: "daily",
  is_active: true
};

const emptyOhlcvForm = {
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

const viewOptions = [
  { key: "monitor", label: "Collection Monitor" },
  { key: "current_preview", label: "Current Instruments" },
  { key: "expired_preview", label: "Expired Instruments" },
  { key: "ohlcv", label: "OHLCV" },
  { key: "equity_news", label: "Equity News" },
  { key: "ipo_calendar", label: "IPO Calendar" },
  { key: "company_fundamentals", label: "Company Fundamentals" },
  { key: "market_calendar", label: "Market Calendar" }
];

const timeFormatOptions = [
  { value: "24", label: "24 Hours" },
  { value: "12", label: "12 Hours" }
];

const scheduleFrequencyOptions = [
  { value: "daily", label: "Daily" },
  { value: "weekly", label: "Weekly" },
  { value: "monthly", label: "Monthly" }
];

const timePeriodOptions = [
  { value: "AM", label: "AM" },
  { value: "PM", label: "PM" }
];

const currentSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "bod_complete", label: "BOD Complete" }
];

const expiredSourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "expired_option_contract", label: "Expired Options" },
  { value: "expired_future_contract", label: "Expired Futures" }
];

const segmentOptions = [
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

const instrumentTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "EQ", label: "EQ" },
  { value: "FUT", label: "FUT" },
  { value: "CE", label: "CE" },
  { value: "PE", label: "PE" },
  { value: "INDEX", label: "INDEX" }
];

const ohlcvSourceOptions = [
  { value: "current", label: "Current / Equity Instruments" },
  { value: "expired", label: "Expired Instruments" }
];

const ohlcvModeOptions = [
  { value: "historical", label: "Historical" },
  { value: "intraday", label: "Intraday Current Day" }
];

const ohlcvIntervalOptions = [
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

const marketHolidayTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "TRADING_HOLIDAY", label: "Trading Holiday" },
  { value: "SETTLEMENT_HOLIDAY", label: "Settlement Holiday" }
];

const marketHolidayExchangeOptions = [
  { value: "all", label: "All Exchanges" },
  { value: "NSE", label: "NSE" },
  { value: "BSE", label: "BSE" },
  { value: "NFO", label: "NFO" },
  { value: "BFO", label: "BFO" },
  { value: "CDS", label: "CDS" },
  { value: "MCX", label: "MCX" }
];

const marketHolidayTradingStatusOptions = [
  { value: "all", label: "All Status" },
  { value: "closed", label: "Closed" },
  { value: "open", label: "Partially Open" }
];

const ipoCalendarSubTabOptions = [
  { value: "ipo", label: "IPO" },
  { value: "ipo_scraper", label: "IPO Scrapper" }
];

const ipoStatusOptions = [
  { value: "all", label: "All Status" },
  { value: "upcoming", label: "Upcoming" },
  { value: "open", label: "Open" },
  { value: "closed", label: "Closed" },
  { value: "listed", label: "Listed" }
];

const ipoIssueTypeOptions = [
  { value: "all", label: "All Issue Types" },
  { value: "regular", label: "Regular" },
  { value: "sme", label: "SME" }
];

const ipoIndustryOptions = [
  { value: "all", label: "All Industries" }
];

const companyFundamentalsEndpointOptions = [
  { value: "company_profile", label: "Company Profile" },
  { value: "balance_sheet", label: "Balance Sheet" },
  { value: "income_statement", label: "Income Statement" },
  { value: "cash_flow", label: "Cash Flow" },
  { value: "share_holdings", label: "Share Holdings" },
  { value: "key_ratios", label: "Key Ratios" },
  { value: "corporate_actions", label: "Corporate Actions" },
  { value: "competitors", label: "Competitors" }
];

const companyFundamentalsStatementTypeOptions = [
  { value: "all", label: "All Types" },
  { value: "consolidated", label: "Consolidated" },
  { value: "standalone", label: "Standalone" }
];

const companyFundamentalsTimePeriodOptions = [
  { value: "all", label: "All Periods" },
  { value: "yearly", label: "Yearly" },
  { value: "quarterly", label: "Quarterly" }
];

const dumpJobColumns = [
  { key: "source", label: "Source" },
  { key: "saved", label: "Saved" },
  { key: "updated", label: "Updated" },
  { key: "triggered_by", label: "Scheduled By" },
  { key: "time", label: "Time" },
  { key: "last_update_status", label: "Last Update Status" }
];

const dumpJobGridTemplateColumns =
  "1.2fr 0.85fr 0.75fr 0.75fr 0.45fr 0.7fr 190px";

const scheduleColumns = [
  { key: "schedule_time", label: "Time" },
  { key: "schedule_frequency", label: "Repeat" },
  { key: "next_run_at", label: "Next Run" },
  { key: "is_active", label: "Status" }
];

const scheduleGridTemplateColumns = "0.9fr 0.8fr 1.35fr 0.7fr 112px";

const previewColumns = [
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

const previewGridTemplateColumns =
  "280px 300px 300px 150px 150px 130px 150px 140px 190px 230px";

const ohlcvPreviewColumns = [
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

const ohlcvPreviewGridTemplateColumns =
  "280px 260px 130px 140px 140px 230px 130px 120px 120px 120px 120px 140px 150px 130px 130px 130px 130px 230px";

const marketHolidayPreviewColumns = [
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

const marketHolidayPreviewGridTemplateColumns =
  "150px 320px 190px 170px 320px 360px 130px 230px 230px";

const equityNewsPreviewColumns = [
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

const equityNewsPreviewGridTemplateColumns =
  "280px 190px 300px 130px 420px 520px 180px 230px 360px 230px";

const ipoCalendarPreviewColumns = [
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

const ipoCalendarPreviewGridTemplateColumns =
  "240px 160px 320px 130px 140px 170px 150px 260px 130px 130px 140px 140px 150px 230px";

const ipoScraperPreviewColumns = [
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

const ipoScraperPreviewGridTemplateColumns =
  "320px 150px 180px 180px 180px 150px 160px 210px 230px 230px";

const companyFundamentalsColumnGroups = {
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

const defaultCompanyFundamentalsColumnGroup =
  companyFundamentalsColumnGroups.company_profile;

function getStoredCurrentUser() {
  try {
    const savedUser =
      localStorage.getItem("open_analytics_current_user") ||
      localStorage.getItem("open_analytics_user");

    if (!savedUser) {
      return null;
    }

    return JSON.parse(savedUser);
  } catch {
    return null;
  }
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }

  return Number(value).toLocaleString("en-IN");
}

function formatCompactNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }

  const numericValue = Number(value);
  const absoluteValue = Math.abs(numericValue);

  if (absoluteValue >= 1000000) {
    return `${Number((numericValue / 1000000).toFixed(1)).toLocaleString(
      "en-IN"
    )}M`;
  }

  if (absoluteValue >= 1000) {
    return `${Number((numericValue / 1000).toFixed(1)).toLocaleString(
      "en-IN"
    )}K`;
  }

  return formatNumber(numericValue);
}

function formatBytes(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  const numericValue = Number(value);

  if (!Number.isFinite(numericValue) || numericValue < 0) {
    return "--";
  }

  const units = ["B", "KB", "MB", "GB", "TB", "PB"];
  let unitIndex = 0;
  let nextValue = numericValue;

  while (nextValue >= 1024 && unitIndex < units.length - 1) {
    nextValue /= 1024;
    unitIndex += 1;
  }

  const precision = nextValue >= 100 || unitIndex === 0 ? 0 : 1;
  return `${nextValue.toFixed(precision)} ${units[unitIndex]}`;
}

function formatDuration(seconds) {
  if (seconds === null || seconds === undefined || seconds === "") {
    return "--";
  }

  const totalSeconds = Math.max(0, Math.round(Number(seconds)));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;

  if (minutes <= 0) {
    return `${remainingSeconds}s`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

function formatDateTime(value) {
  if (!value) {
    return "--";
  }

  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return String(value).replace(/:\d{2}(\.\d+)?$/, "");
  }

  return date.toLocaleString("en-IN", {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: true
  });
}

function normalizeCellValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

function getFilterValues(rows, key, getValue) {
  const valueMap = new Map();

  rows.forEach((row) => {
    const value = normalizeCellValue(getValue(row, key));
    valueMap.set(value, (valueMap.get(value) || 0) + 1);
  });

  return Array.from(valueMap.entries())
    .map(([value, count]) => ({
      label: value,
      value,
      count
    }))
    .sort((a, b) => a.label.localeCompare(b.label));
}

function applyColumnFilters(rows, columnFilters, getValue) {
  return rows.filter((row) => {
    return Object.entries(columnFilters).every(([key, selectedValues]) => {
      if (!selectedValues || selectedValues.length === 0) {
        return true;
      }

      const value = normalizeCellValue(getValue(row, key));
      return selectedValues.includes(value);
    });
  });
}

function applySort(rows, sortConfig, getValue) {
  if (!sortConfig.key || !sortConfig.direction) {
    return rows;
  }

  return [...rows].sort((firstRow, secondRow) => {
    const firstValue = normalizeCellValue(
      getValue(firstRow, sortConfig.key)
    ).toLowerCase();

    const secondValue = normalizeCellValue(
      getValue(secondRow, sortConfig.key)
    ).toLowerCase();

    if (firstValue < secondValue) {
      return sortConfig.direction === "asc" ? -1 : 1;
    }

    if (firstValue > secondValue) {
      return sortConfig.direction === "asc" ? 1 : -1;
    }

    return 0;
  });
}

function getDumpJobColumnValue(row, key) {
  if (key === "source") {
    return row.title;
  }

  if (key === "saved") {
    return formatNumber(row.records);
  }

  if (key === "updated") {
    return formatDateTime(row.lastSyncedAt);
  }

  if (key === "triggered_by") {
    return row.triggerSource === "system" ? "System" : row.triggeredBy || "Manual";
  }

  if (key === "time") {
    return formatDuration(row.duration);
  }

  if (key === "last_update_status") {
    return getStatusLabel(row.lastStatus);
  }

  return row[key];
}

function getPreviewColumnValue(row, key) {
  if (key === "synced_at") {
    return formatDateTime(row.synced_at);
  }

  if (key === "source_type") {
    return getSyncTypeLabel(row.source_type);
  }

  return row[key];
}

function parseMaybeJsonArray(value) {
  if (Array.isArray(value)) {
    return value;
  }

  if (value === null || value === undefined || value === "") {
    return [];
  }

  if (typeof value === "string") {
    try {
      const parsedValue = JSON.parse(value);

      if (Array.isArray(parsedValue)) {
        return parsedValue;
      }
    } catch {
      return value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);
    }
  }

  return [];
}

function formatOhlcvList(value) {
  const values = parseMaybeJsonArray(value);

  if (values.length === 0) {
    return "--";
  }

  return values
    .map((item) => getSyncTypeLabel(item))
    .join(", ");
}

function formatPrice(value) {
  if (
    value === null ||
    value === undefined ||
    value === "" ||
    Number.isNaN(Number(value))
  ) {
    return "--";
  }

  return Number(value).toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 4
  });
}

function getOhlcvColumnValue(row, key) {
  if (key === "timestamp" || key === "ingested_at") {
    return formatDateTime(row[key]);
  }

  if (key === "source" || key === "mode") {
    return getSyncTypeLabel(row[key]);
  }

  if (key === "open" || key === "high" || key === "low" || key === "close") {
    return formatPrice(row[key]);
  }

  if (key === "volume" || key === "open_interest") {
    return formatNumber(row[key] || 0);
  }

  return row[key];
}

function formatJsonListCell(value, displayKey = "exchange") {
  const values = parseMaybeJsonArray(value);

  if (values.length === 0) {
    return "--";
  }

  return values
    .map((item) => {
      if (item && typeof item === "object") {
        const exchange = item[displayKey] || item.exchange || item.segment || "";
        const startTime = item.start_time || item.startTime || "";
        const endTime = item.end_time || item.endTime || "";

        if (exchange && startTime && endTime) {
          return `${exchange} ${startTime}-${endTime}`;
        }

        return exchange || JSON.stringify(item);
      }

      return String(item);
    })
    .filter(Boolean)
    .join(", ");
}

function getMarketHolidayColumnValue(row, key) {
  if (key === "synced_at" || key === "updated_at") {
    return formatDateTime(row[key]);
  }

  if (key === "holiday_type") {
    return getSyncTypeLabel(row[key]);
  }

  if (key === "is_trading_day") {
    return row.is_trading_day ? "Partially Open" : "Closed";
  }

  if (key === "closed_exchanges" || key === "open_exchanges") {
    return formatJsonListCell(row[key]);
  }

  return row[key];
}

function getEquityNewsColumnValue(row, key) {
  if (key === "published_at" || key === "ingested_at" || key === "synced_at") {
    return formatDateTime(row[key]);
  }

  if (key === "article_link") {
    return row.article_link || row.url || row.link;
  }

  if (key === "heading") {
    return row.heading || row.title;
  }

  return row[key];
}

function getIpoCalendarColumnValue(row, key) {
  if (key === "synced_at" || key === "updated_at") {
    return formatDateTime(row[key]);
  }

  if (key === "status" || key === "issue_type") {
    return getSyncTypeLabel(row[key]);
  }

  if (
    key === "issue_size" ||
    key === "minimum_price" ||
    key === "maximum_price" ||
    key === "total_subscription"
  ) {
    return formatPrice(row[key]);
  }

  return row[key];
}

function getIpoScraperColumnValue(row, key) {
  if (key === "scraped_at" || key === "updated_at") {
    return formatDateTime(row[key]);
  }

  if (key === "ipo_type" || key === "ipo_status") {
    return getSyncTypeLabel(row[key]);
  }

  return row[key];
}

function getCompanyFundamentalsColumnValue(row, key) {
  if (key === "synced_at" || key === "updated_at") {
    return formatDateTime(row[key]);
  }

  if (key === "endpoint_label") {
    return row.endpoint_label || getSyncTypeLabel(row.endpoint);
  }

  if (key === "statement_type" || key === "time_period" || key === "api_status") {
    return getSyncTypeLabel(row[key]);
  }

  if (
    key === "latest_revenue" ||
    key === "latest_operating_profit" ||
    key === "latest_net_profit" ||
    key === "latest_total_asset" ||
    key === "latest_total_liability" ||
    key === "latest_operating_cash_flow" ||
    key === "pe_ratio_company" ||
    key === "pb_ratio_company" ||
    key === "roe_company" ||
    key === "roce_company"
  ) {
    return formatPrice(row[key]);
  }

  if (
    key === "period_count" ||
    key === "item_count" ||
    key === "corporate_action_count" ||
    key === "competitor_count"
  ) {
    return formatNumber(row[key] || 0);
  }

  return row[key];
}

function getElapsedSecondsFromDate(value) {
  if (!value) {
    return 0;
  }

  const startedAt = new Date(value);

  if (Number.isNaN(startedAt.getTime())) {
    return 0;
  }

  return Math.max(0, Math.floor((Date.now() - startedAt.getTime()) / 1000));
}

function isRequestCancelled(error) {
  return (
    error?.name === "CanceledError" ||
    error?.code === "ERR_CANCELED" ||
    error?.message === "canceled"
  );
}

function getApiErrorMessage(error, fallbackMessage) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => item?.msg || item?.message)
      .filter(Boolean)
      .join(", ");
  }

  if (detail?.message) {
    return detail.message;
  }

  if (error?.response?.status) {
    return `${fallbackMessage} (HTTP ${error.response.status})`;
  }

  if (error?.code === "ERR_NETWORK" || error?.message === "Network Error") {
    return `${fallbackMessage} Backend is not reachable. Check that the backend is running on port 8000 and that the request URL is correct.`;
  }

  if (error?.code === "ECONNABORTED") {
    return `${fallbackMessage} Request timed out. Please refresh after a few seconds.`;
  }

  return error?.message || fallbackMessage;
}

function getSyncTypeLabel(value) {
  const labels = {
    upstox_current_instruments: "Current Instruments",
    upstox_expired_instruments: "Expired Instruments",
    upstox_ohlcv_daily: "OHLCV",
    upstox_market_holidays: "Market Calendar",
    upstox_equity_news: "Equity News",
    upstox_ipo_calendar: "IPO Calendar",
    ipo_gmp_scraper: "IPO Scrapper",
    upstox_company_fundamentals: "Company Fundamentals",
    current_instruments: "Current Instruments",
    expired_instruments: "Expired Instruments",
    ohlcv_daily: "OHLCV",
    market_holidays: "Market Calendar",
    equity_news: "Equity News",
    ipo_calendar: "IPO Calendar",
    ipo_scraper: "IPO Scrapper",
    company_fundamentals: "Company Fundamentals",
    bod_complete: "BOD Complete",
    expired_option_contract: "Expired Options",
    expired_future_contract: "Expired Futures",
    current: "Current",
    expired: "Expired",
    historical: "Historical",
    intraday: "Intraday",
    TRADING_HOLIDAY: "Trading Holiday",
    SETTLEMENT_HOLIDAY: "Settlement Holiday",
    upcoming: "Upcoming",
    UPCOMING: "Upcoming",
    open: "Open",
    OPEN: "Open",
    closed: "Closed",
    CLOSED: "Closed",
    listed: "Listed",
    LISTED: "Listed",
    regular: "Regular",
    REGULAR: "Regular",
    sme: "SME",
    SME: "SME",
    company_profile: "Company Profile",
    balance_sheet: "Balance Sheet",
    income_statement: "Income Statement",
    cash_flow: "Cash Flow",
    share_holdings: "Share Holdings",
    key_ratios: "Key Ratios",
    corporate_actions: "Corporate Actions",
    competitors: "Competitors",
    consolidated: "Consolidated",
    standalone: "Standalone",
    yearly: "Yearly",
    quarterly: "Quarterly",
    upstox: "Upstox",
    "1minute": "1 Min",
    "3minute": "3 Min",
    "5minute": "5 Min",
    "15minute": "15 Min",
    "30minute": "30 Min",
    "1hour": "1 Hour",
    day: "Day",
    week: "Week",
    month: "Month"
  };

  return labels[value] || value || "--";
}

function getQueuedDumpJobId(jobName) {
  const names = {
    upstox_current_instruments: "current",
    upstox_expired_instruments: "expired",
    upstox_ohlcv_daily: "ohlcv",
    upstox_market_holidays: "market_calendar",
    upstox_equity_news: "equity_news",
    upstox_ipo_calendar: "ipo_calendar",
    ipo_gmp_scraper: "ipo_scraper",
    upstox_company_fundamentals: "company_fundamentals",
    sync_upstox_current_instruments_service: "current",
    sync_upstox_expired_instruments_service: "expired",
    sync_upstox_ohlcv_daily_service: "ohlcv",
    sync_upstox_market_holidays_service: "market_calendar",
    sync_upstox_equity_news_service: "equity_news",
    sync_upstox_ipo_calendar_service: "ipo_calendar",
    sync_ipo_gmp_scraper_service: "ipo_scraper",
    sync_upstox_company_fundamentals_service: "company_fundamentals",
    "scheduled:current_instruments": "current",
    "scheduled:expired_instruments": "expired",
    "scheduled:ohlcv_daily": "ohlcv",
    "scheduled:market_holidays": "market_calendar",
    "scheduled:equity_news": "equity_news",
    "scheduled:ipo_calendar": "ipo_calendar",
    "scheduled:ipo_scraper": "ipo_scraper",
    "scheduled:company_fundamentals": "company_fundamentals"
  };

  return names[jobName] || null;
}

function getStatusClass(status) {
  if (status === "success" || status === "connected" || status === "active" || status === "open") {
    return "border-emerald-500/40 bg-emerald-950/50 text-emerald-200";
  }

  if (status === "queued" || status === "upcoming" || status === "partial_success") {
    return "border-amber-500/40 bg-amber-950/50 text-amber-200";
  }

  if (status === "running" || status === "cancel_requested") {
    return "border-cyan-500/40 bg-cyan-950/50 text-cyan-200";
  }

  if (status === "failed" || status === "cancelled" || status === "inactive" || status === "closed") {
    return "border-red-500/40 bg-red-950/50 text-red-200";
  }

  if (status === "saved" || status === "listed") {
    return "border-sky-500/40 bg-sky-950/50 text-sky-200";
  }

  return "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function getStatusLabel(status) {
  if (status === "success") return "Success";
  if (status === "partial_success") return "Partial Success";
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "cancel_requested") return "Cancelling";
  if (status === "cancelled") return "Cancelled";
  if (status === "failed") return "Failed";
  if (status === "active") return "Active";
  if (status === "inactive") return "Inactive";
  if (status === "upcoming") return "Upcoming";
  if (status === "open") return "Open";
  if (status === "closed") return "Closed";
  if (status === "listed") return "Listed";

  return status || "Idle";
}

function getLatestRunByTypes(runs, syncTypes = []) {
  return runs.find((run) => syncTypes.includes(run.sync_type)) || null;
}

function isPreviewView(activeView) {
  return activeView === "current_preview" || activeView === "expired_preview";
}

function getPreviewMode(activeView) {
  if (activeView === "expired_preview") {
    return "expired";
  }

  return "current";
}

function getPaginationItems(currentPage, totalPages) {
  const pages = [];
  const safeTotalPages = Math.max(1, Number(totalPages) || 1);
  const safeCurrentPage = Math.min(
    Math.max(1, Number(currentPage) || 1),
    safeTotalPages
  );

  if (safeTotalPages <= 7) {
    for (let page = 1; page <= safeTotalPages; page += 1) {
      pages.push(page);
    }

    return pages;
  }

  pages.push(1);

  if (safeCurrentPage > 4) {
    pages.push("left-ellipsis");
  }

  const startPage = Math.max(2, safeCurrentPage - 1);
  const endPage = Math.min(safeTotalPages - 1, safeCurrentPage + 1);

  for (let page = startPage; page <= endPage; page += 1) {
    pages.push(page);
  }

  if (safeCurrentPage < safeTotalPages - 3) {
    pages.push("right-ellipsis");
  }

  pages.push(safeTotalPages);

  return pages;
}

function formatScheduleTime(schedule) {
  if (!schedule) {
    return "--";
  }

  if (schedule.time_format === "12") {
    return schedule.schedule_label || schedule.schedule_time || "--";
  }

  return schedule.schedule_time || "--";
}

function formatScheduleFrequency(scheduleFrequency) {
  const option = scheduleFrequencyOptions.find(
    (item) => item.value === String(scheduleFrequency || "").toLowerCase()
  );

  return option?.label || "Daily";
}

function getScheduleTimeParts(scheduleTime) {
  const match = String(scheduleTime || "").match(/^(\d{1,2}):(\d{2})$/);

  if (!match) {
    return {
      hour12: "",
      minute: "",
      period: "AM"
    };
  }

  const hour24 = Math.min(23, Math.max(0, Number(match[1])));
  const minute = Math.min(59, Math.max(0, Number(match[2])));
  const period = hour24 >= 12 ? "PM" : "AM";
  const hour12 = hour24 % 12 || 12;

  return {
    hour12: String(hour12),
    minute: String(minute).padStart(2, "0"),
    period
  };
}

function buildScheduleTimeFrom12Hour(hourValue, minuteValue, periodValue) {
  if (hourValue === "" || hourValue === null || hourValue === undefined) {
    return "";
  }

  const hour12 = Math.min(12, Math.max(1, Number(hourValue) || 1));
  const minute = Math.min(59, Math.max(0, Number(minuteValue) || 0));
  const period = periodValue === "PM" ? "PM" : "AM";
  let hour24 = hour12 % 12;

  if (period === "PM") {
    hour24 += 12;
  }

  return `${String(hour24).padStart(2, "0")}:${String(minute).padStart(
    2,
    "0"
  )}`;
}

function ViewToggle({ activeView, onChange }) {
  return (
    <div className={`${oaTabStyles.wrapper} overflow-x-auto`}>
      {viewOptions.map((option) => {
        const isActive = activeView === option.key;

        return (
          <button
            key={option.key}
            type="button"
            onClick={() => onChange(option.key)}
            className={`${oaTabStyles.button} ${
              isActive ? oaTabStyles.active : oaTabStyles.inactive
            } whitespace-nowrap`}
          >
            <span>{option.label}</span>
          </button>
        );
      })}
    </div>
  );
}

function StatusBadge({ status, label }) {
  return (
    <span className={`${oaPillStyles.base} ${getStatusClass(status || "idle")}`}>
      {label || getStatusLabel(status)}
    </span>
  );
}

function ClearInputButton({ label, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
      aria-label={label}
    >
      <X size={13} />
    </button>
  );
}

function DumpJobActions({
  title,
  loading,
  disabled,
  canCancel,
  cancelling,
  onRun,
  onCancel,
  onSchedule,
  onOptions,
  runLabel = "Run"
}) {
  return (
    <div className="flex justify-end gap-2">
      {onOptions ? (
        <Tooltip text={`${title} options`} side="left">
          <button
            type="button"
            disabled={disabled || loading}
            onClick={onOptions}
            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-amber-300 outline-none transition hover:border-amber-500/60 hover:bg-amber-950/40 hover:text-amber-200 focus:border-amber-500 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label={`${title} options`}
          >
            <Edit3 size={15} />
          </button>
        </Tooltip>
      ) : null}

      {onSchedule ? (
        <Tooltip text={`Schedule ${title}`} side="left">
          <button
            type="button"
            disabled={disabled || loading}
            onClick={onSchedule}
            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label={`Schedule ${title}`}
          >
            <Clock3 size={15} />
          </button>
        </Tooltip>
      ) : null}

      <Tooltip text={loading ? `${title} running` : `${runLabel} ${title}`} side="left">
        <button
          type="button"
          disabled={disabled || loading}
          onClick={onRun}
          className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={`${runLabel} ${title}`}
        >
          {loading ? <Spinner size="xs" color="light" /> : <Play size={15} />}
        </button>
      </Tooltip>

      {canCancel && (
        <Tooltip text={`Cancel ${title}`} side="left">
          <button
            type="button"
            disabled={cancelling}
            onClick={onCancel}
            className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-red-400 outline-none transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-300 focus:border-red-500 disabled:cursor-not-allowed disabled:opacity-60"
            aria-label={`Cancel ${title}`}
          >
            {cancelling ? (
              <Spinner size="xs" color="light" />
            ) : (
              <XCircle size={15} />
            )}
          </button>
        </Tooltip>
      )}
    </div>
  );
}

function DataCollectionShell({
  activeView,
  onViewChange,
  diskSpace,
  children
}) {
  const diskUsedText = formatBytes(diskSpace?.used_bytes);
  const diskTotalText = formatBytes(diskSpace?.total_bytes);
  const diskPercent =
    diskSpace?.used_percent !== null && diskSpace?.used_percent !== undefined
      ? `${Number(diskSpace.used_percent).toFixed(1)}%`
      : "--";

  return (
    <div
      className={`${oaCardStyles.wrapper} flex h-[calc(100vh-24px)] min-h-0 flex-col overflow-hidden`}
    >
      <div className="shrink-0">
        <div
          className={`${oaCardStyles.header} flex min-h-[45px] items-center justify-between gap-3`}
        >
          <h2 className={oaCardStyles.headerTitle}>Data Collection</h2>
          <div className="flex min-w-0 items-center gap-2 rounded border border-oa-border bg-black px-2.5 py-1 font-mono text-[11px] text-oa-muted">
            <HardDrive size={14} className="shrink-0 text-sky-300" />
            <span className="shrink-0 uppercase tracking-[0.08em]">Disk</span>
            <span className="min-w-0 truncate text-white">
              {diskUsedText} / {diskTotalText}
            </span>
            <span className="shrink-0 text-oa-muted">({diskPercent})</span>
          </div>
        </div>

        <div className="flex flex-col gap-2 border-b border-oa-border bg-black px-3 py-1.5 md:flex-row md:items-center md:justify-between">
          <ViewToggle activeView={activeView} onChange={onViewChange} />
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col overflow-hidden bg-black">
        {children}
      </div>
    </div>
  );
}

function ScheduleManagerModal({
  open,
  title,
  schedules,
  formMode,
  formData,
  saving,
  savingScheduleId,
  deletingScheduleId,
  isAdminControlAllowed,
  onClose,
  onSave,
  onInputChange,
  onTimePartChange,
  onClearField,
  onEdit,
  onCancelEdit,
  onToggle,
  onDelete
}) {
  const is12HourFormat = formData.time_format === "12";
  const scheduleTimeParts = getScheduleTimeParts(formData.schedule_time);
  const canSave =
    isAdminControlAllowed &&
    formData.job_type &&
    formData.schedule_time &&
    formData.time_format &&
    formData.schedule_frequency;

  function handleSubmit(event) {
    event.preventDefault();
    onSave();
  }

  function renderScheduleCell(schedule, column) {
    if (column.key === "schedule_time") {
      const isEditing =
        formMode === "edit" && formData.schedule_id === schedule.schedule_id;

      return (
        <span
          className={`truncate oa-code-font font-semibold ${
            isEditing ? "text-sky-200" : "text-cyan-200"
          }`}
        >
          {formatScheduleTime(schedule)}
        </span>
      );
    }

    if (column.key === "next_run_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(schedule.next_run_at)}
        </span>
      );
    }

    if (column.key === "schedule_frequency") {
      return (
        <span className="truncate text-oa-text">
          {formatScheduleFrequency(schedule.schedule_frequency)}
        </span>
      );
    }

    if (column.key === "is_active") {
      return (
        <StatusBadge status={schedule.is_active ? "active" : "inactive"} />
      );
    }

    return <span className="truncate text-oa-muted">--</span>;
  }

  function renderScheduleActions(schedule) {
    const isSaving = savingScheduleId === schedule.schedule_id;
    const isDeleting = deletingScheduleId === schedule.schedule_id;

    return (
      <div className="flex justify-end gap-1.5">
        <button
          type="button"
          disabled={isSaving || isDeleting || !isAdminControlAllowed}
          onClick={() => onToggle(schedule)}
          className={`flex h-8 w-8 items-center justify-center rounded border outline-none transition disabled:cursor-not-allowed disabled:opacity-60 ${
            schedule.is_active
              ? "border-amber-500/30 bg-amber-950/20 text-amber-300 hover:border-amber-500/60 hover:bg-amber-950/40 hover:text-amber-200 focus:border-amber-500"
              : "border-emerald-500/30 bg-emerald-950/20 text-emerald-300 hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500"
          }`}
          aria-label={schedule.is_active ? "Disable schedule" : "Enable schedule"}
          title={schedule.is_active ? "Disable schedule" : "Enable schedule"}
        >
          {isSaving ? <Spinner size="xs" color="light" /> : <Power size={15} />}
        </button>

        <IconButton
          icon={Edit3}
          label="Edit schedule"
          variant="default"
          disabled={isSaving || isDeleting || !isAdminControlAllowed}
          onClick={() => onEdit(schedule)}
          tooltipSide="top"
        />

        <button
          type="button"
          disabled={isSaving || isDeleting || !isAdminControlAllowed}
          onClick={() => onDelete(schedule)}
          className="flex h-8 w-8 items-center justify-center rounded border border-red-500/30 bg-red-950/20 text-red-300 outline-none transition hover:border-red-500/60 hover:bg-red-950/40 hover:text-red-200 focus:border-red-500 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label="Delete schedule"
          title="Delete schedule"
        >
          {isDeleting ? (
            <Spinner size="xs" color="light" />
          ) : (
            <Trash2 size={15} />
          )}
        </button>
      </div>
    );
  }

  return (
    <Modal
      open={open}
      title={`${title} Scheduler`}
      onClose={onClose}
      width="max-w-3xl"
      footer={
        <div className="flex items-center justify-end gap-2">
          <IconButton
            icon={X}
            label="Close"
            variant="default"
            disabled={saving}
            onClick={onClose}
            tooltipSide="top"
          />
        </div>
      }
    >
      <div className="space-y-4 oa-table-font">
        <div className="w-full bg-black">
          <div className="mb-2 flex items-center justify-between">
            <p className="text-[12px] font-semibold uppercase tracking-wider text-white">
              Scheduled
            </p>

            <StatusBadge status="active" label={`${schedules.length} Total`} />
          </div>

          {schedules.length === 0 ? (
            <div className="-mx-4 flex items-center justify-center gap-2 border-y border-oa-border bg-black px-4 py-3 text-center text-[12px] text-oa-muted">
              {saving ? <Spinner size="xs" color="light" /> : null}
              <span>{saving ? "Loading schedules" : "No schedules added yet."}</span>
            </div>
          ) : (
            <div
              className={`-mx-4 w-[calc(100%+2rem)] border-y border-oa-border bg-black [&>div]:w-full [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent ${
                schedules.length > 4
                  ? "max-h-56 overflow-auto"
                  : "overflow-visible"
              }`}
            >
              <DataTable
                columns={scheduleColumns}
                rows={schedules}
                loading={saving && schedules.length === 0}
                loadingMessage="Loading schedules"
                emptyMessage="No schedules added yet."
                gridTemplateColumns={scheduleGridTemplateColumns}
                minWidth="min-w-full"
                getRowKey={(schedule) => schedule.schedule_id}
                renderCell={renderScheduleCell}
                renderActions={renderScheduleActions}
              />
            </div>
          )}
        </div>

        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="flex items-center justify-between border-b border-oa-border pb-2">
            <p className="text-[12px] font-semibold uppercase tracking-wider text-white">
              {formMode === "edit" ? "Edit Schedule" : "Add Schedule"}
            </p>
          </div>

          <div className="grid gap-3 md:grid-cols-3">
            <div>
              <label className={oaFormTextStyles.label}>Schedule Time</label>

              {is12HourFormat ? (
                <div className="mt-1 grid grid-cols-[1fr_1fr_84px_28px] gap-2">
                  <Input
                    type="number"
                    min="1"
                    max="12"
                    value={scheduleTimeParts.hour12}
                    onChange={(event) =>
                      onTimePartChange("hour12", event.target.value)
                    }
                    placeholder="HH"
                  />

                  <Input
                    type="number"
                    min="0"
                    max="59"
                    value={scheduleTimeParts.minute}
                    onChange={(event) =>
                      onTimePartChange("minute", event.target.value)
                    }
                    placeholder="MM"
                  />

                  <Select
                    value={scheduleTimeParts.period}
                    onChange={(event) =>
                      onTimePartChange("period", event.target.value)
                    }
                    options={timePeriodOptions}
                    ariaLabel="AM or PM"
                    minWidth="w-full"
                  />

                  <div className="relative">
                    {formData.schedule_time ? (
                      <ClearInputButton
                        label="Clear schedule time"
                        onClick={() => onClearField("schedule_time")}
                      />
                    ) : null}
                  </div>
                </div>
              ) : (
                <div className="relative mt-1">
                  <Input
                    name="schedule_time"
                    type="time"
                    value={formData.schedule_time}
                    onChange={onInputChange}
                    className="pr-9"
                  />

                  {formData.schedule_time ? (
                    <ClearInputButton
                      label="Clear schedule time"
                      onClick={() => onClearField("schedule_time")}
                    />
                  ) : null}
                </div>
              )}
            </div>

            <div>
              <label className={oaFormTextStyles.label}>Display Format</label>

              <div className="mt-1">
                <Select
                  name="time_format"
                  value={formData.time_format}
                  onChange={onInputChange}
                  options={timeFormatOptions}
                  ariaLabel="Time format"
                  minWidth="w-full"
                />
              </div>
            </div>

            <div>
              <label className={oaFormTextStyles.label}>Repeat</label>

              <div className="mt-1">
                <Select
                  name="schedule_frequency"
                  value={formData.schedule_frequency}
                  onChange={onInputChange}
                  options={scheduleFrequencyOptions}
                  ariaLabel="Schedule repeat"
                  minWidth="w-full"
                />
              </div>
            </div>
          </div>

          <label className="flex items-center gap-2 rounded border border-oa-border bg-black px-3 py-2 text-[12px] text-oa-muted">
            <input
              type="checkbox"
              name="is_active"
              checked={formData.is_active}
              onChange={onInputChange}
              className="h-4 w-4 accent-emerald-500"
            />
            Active schedule
          </label>

          <div className="flex justify-end gap-2 pt-1">
            {formMode === "edit" ? (
              <IconButton
                icon={X}
                label="Cancel edit"
                variant="danger"
                disabled={saving}
                onClick={onCancelEdit}
                tooltipSide="top"
              />
            ) : null}

            <IconButton
              icon={Check}
              label={formMode === "edit" ? "Update schedule" : "Save schedule"}
              variant="default"
              disabled={saving || !canSave}
              onClick={onSave}
              tooltipSide="top"
            />
          </div>

          <button type="submit" className="hidden" aria-hidden="true">
            Submit schedule
          </button>
        </form>
      </div>
    </Modal>
  );
}

function MonitorContent({
  searchValue,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  searchActive,
  hasActiveFilter,
  onClearAll,
  rows,
  loading,
  onRefresh,
  renderCell,
  renderActions,
  filterConfig
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder="Search collection monitor"
          filters={[]}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            }
          ]}
        />
      </div>

      <div className="min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        <DataTable
          columns={dumpJobColumns}
          rows={rows}
          loading={loading}
          loadingMessage="Loading data collection status"
          emptyMessage="No data collection jobs found."
          gridTemplateColumns={dumpJobGridTemplateColumns}
          minWidth="min-w-[980px]"
          getRowKey={(row) => row.id}
          renderCell={renderCell}
          renderActions={renderActions}
          filterConfig={filterConfig}
        />
      </div>
    </div>
  );
}

function DbPreviewContent({
  previewMode,
  searchValue,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  searchActive,
  sourceType,
  onSourceTypeChange,
  onClearSourceType,
  segment,
  onSegmentChange,
  onClearSegment,
  instrumentType,
  onInstrumentTypeChange,
  onClearInstrumentType,
  previewData,
  rows,
  loading,
  runPreviewDisabled,
  onRefresh,
  onRunPreview,
  onPreviousPage,
  onNextPage,
  onPageChange,
  hasActiveFilter,
  onClearAll,
  filterConfig
}) {
  const isExpired = previewMode === "expired";
  const title = isExpired ? "Expired Instruments" : "Current Instruments";
  const sourceOptions = isExpired
    ? expiredSourceTypeOptions
    : currentSourceTypeOptions;

  function renderPreviewCell(row, column) {
    if (column.key === "synced_at") {
      return (
        <span className="truncate oa-code-font text-oa-muted">
          {formatDateTime(row[column.key])}
        </span>
      );
    }

    if (column.key === "expiry") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row[column.key] || "--"}
        </span>
      );
    }

    if (column.key === "source_type") {
      return (
        <span
          className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}
        >
          {getSyncTypeLabel(row.source_type)}
        </span>
      );
    }

    if (column.key === "name") {
      return <span className="truncate text-white">{row.name || "--"}</span>;
    }

    if (column.key === "trading_symbol") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row.trading_symbol || "--"}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {row[column.key] ?? "--"}
      </span>
    );
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder={`Search ${title.toLowerCase()}`}
          filters={[
            {
              value: sourceType,
              onChange: (event) => onSourceTypeChange(event.target.value),
              options: sourceOptions,
              onClear: onClearSourceType,
              showClear: sourceType !== "all",
              ariaLabel: "Source type",
              minWidth: "w-40"
            },
            {
              value: segment,
              onChange: (event) => onSegmentChange(event.target.value),
              options: segmentOptions,
              onClear: onClearSegment,
              showClear: segment !== "all",
              ariaLabel: "Segment",
              minWidth: "w-36"
            },
            {
              value: instrumentType,
              onChange: (event) => onInstrumentTypeChange(event.target.value),
              options: instrumentTypeOptions,
              onClear: onClearInstrumentType,
              showClear: instrumentType !== "all",
              ariaLabel: "Instrument type",
              minWidth: "w-36"
            }
          ]}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            },
            {
              icon: Play,
              label: `Run ${title}`,
              variant: "add",
              disabled: runPreviewDisabled,
              onClick: onRunPreview
            }
          ]}
        />
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">
                Loading {title.toLowerCase()}
              </span>
            </div>
          </div>
        )}

        <DataTable
          columns={previewColumns}
          rows={rows}
          loading={false}
          loadingMessage={`Loading ${title.toLowerCase()}`}
          emptyMessage="No records found."
          gridTemplateColumns={previewGridTemplateColumns}
          minWidth="min-w-[2020px]"
          getRowKey={(row, index) =>
            `${row.instrument_key || row.trading_symbol || index}-${index}`
          }
          renderCell={renderPreviewCell}
          filterConfig={filterConfig}
        />
      </div>

      <PaginationFooter
        previewData={previewData}
        loading={loading}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}

function CheckboxGroup({ title, helper, options, selectedValues, onChange }) {
  function toggleValue(value) {
    const nextValues = selectedValues.includes(value)
      ? selectedValues.filter((item) => item !== value)
      : [...selectedValues, value];

    onChange(nextValues);
  }

  return (
    <div className="rounded border border-oa-border bg-black p-3">
      <div className="mb-2">
        <p className="text-[12px] font-semibold uppercase tracking-wider text-white">
          {title}
        </p>
        {helper ? (
          <p className="mt-1 text-[11px] text-oa-muted">{helper}</p>
        ) : null}
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {options.map((option) => (
          <label
            key={option.value}
            className="flex items-center gap-2 rounded border border-oa-border bg-oa-panel/40 px-3 py-2 text-[12px] text-oa-muted transition hover:border-oa-muted/40 hover:bg-oa-card hover:text-white"
          >
            <input
              type="checkbox"
              checked={selectedValues.includes(option.value)}
              onChange={() => toggleValue(option.value)}
              className="h-4 w-4 accent-emerald-500"
            />
            <span>{option.label}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

function OhlcvOptionsModal({
  open,
  formData,
  saving,
  onClose,
  onChange,
  onMultiChange,
  onSave
}) {
  const useCurrentDay = Boolean(formData.use_current_day);
  const autoDateRange = Boolean(formData.auto_date_range);
  const canSave =
    formData.sources.length > 0 &&
    formData.candle_modes.length > 0 &&
    formData.intervals.length > 0 &&
    !saving;

  function handleSubmit(event) {
    event.preventDefault();
    onSave();
  }

  return (
    <Modal
      open={open}
      title="OHLCV Options"
      onClose={onClose}
      width="max-w-4xl"
      footer={
        <div className="flex items-center justify-end gap-2">
          <IconButton
            icon={X}
            label="Close"
            variant="default"
            disabled={saving}
            onClick={onClose}
            tooltipSide="top"
          />

          <IconButton
            icon={Check}
            label="Save options"
            variant="default"
            disabled={!canSave}
            onClick={onSave}
            tooltipSide="top"
          />
        </div>
      }
    >
      <form
        onSubmit={handleSubmit}
        className="max-h-[calc(100vh-190px)] space-y-4 overflow-y-auto pb-4 pr-1 oa-table-font"
      >
        <CheckboxGroup
          title="Instrument Source"
          options={ohlcvSourceOptions}
          selectedValues={formData.sources}
          onChange={(values) => onMultiChange("sources", values)}
        />

        <CheckboxGroup
          title="OHLCV Mode"
          options={ohlcvModeOptions}
          selectedValues={formData.candle_modes}
          onChange={(values) => onMultiChange("candle_modes", values)}
        />

        <CheckboxGroup
          title="Intervals"
          options={ohlcvIntervalOptions}
          selectedValues={formData.intervals}
          onChange={(values) => onMultiChange("intervals", values)}
        />

        <div className="rounded border border-oa-border bg-black p-3">
          <p className="mb-3 text-[12px] font-semibold uppercase tracking-wider text-white">
            Date Range
          </p>

          <div className="grid gap-3 md:grid-cols-2">
            <div>
              <label className={oaFormTextStyles.label}>From Date</label>

              <div className="mt-1 grid grid-cols-[125px_minmax(0,1fr)] items-center gap-1.5">
                <Tooltip
                  text="Start from the last saved candle. If no saved candle exists, start from available Upstox history."
                  side="top"
                >
                  <span className="block h-8">
                    <label className={oaCheckboxControlStyles.wrapper}>
                      <input
                        type="checkbox"
                        name="auto_date_range"
                        checked={autoDateRange}
                        onChange={onChange}
                        className={oaCheckboxControlStyles.checkbox}
                        aria-label="Auto start from saved data"
                      />
                      <span className={oaCheckboxControlStyles.label}>
                        Auto start
                      </span>
                    </label>
                  </span>
                </Tooltip>

                <div className={autoDateRange ? "opacity-60" : ""}>
                  <DatePicker
                    name="from_date"
                    value={formData.from_date}
                    onChange={onChange}
                    placeholder={
                      autoDateRange ? "Auto from saved / available" : "From date"
                    }
                    ariaLabel="Select from date"
                    disabled={autoDateRange}
                  />
                </div>
              </div>
            </div>

            <div>
              <label className={oaFormTextStyles.label}>To Date</label>

              <div className="mt-1 grid grid-cols-[125px_minmax(0,1fr)] items-center gap-1.5">
                <Tooltip
                  text="Use current day as To Date and disable manual To Date selection."
                  side="top"
                >
                  <span className="block h-8">
                    <label className={oaCheckboxControlStyles.wrapper}>
                      <input
                        type="checkbox"
                        name="use_current_day"
                        checked={useCurrentDay}
                        onChange={onChange}
                        className={oaCheckboxControlStyles.checkbox}
                        aria-label="Use current day"
                      />
                      <span className={oaCheckboxControlStyles.label}>
                        Current day
                      </span>
                    </label>
                  </span>
                </Tooltip>

                <div className={useCurrentDay ? "opacity-60" : ""}>
                  <DatePicker
                    name="to_date"
                    value={useCurrentDay ? "" : formData.to_date}
                    onChange={onChange}
                    placeholder={useCurrentDay ? "Current day" : "To date"}
                    ariaLabel="Select to date"
                    disabled={useCurrentDay}
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-3 md:grid-cols-3">
          <div>
            <label className={oaFormTextStyles.label}>Instrument Scope</label>
            <div className="mt-1">
              <Select
                name="instrument_scope"
                value={formData.instrument_scope}
                onChange={onChange}
                options={[
                  { value: "all", label: "All Instruments" },
                  { value: "limit", label: "First N Instruments" },
                  { value: "single", label: "Single Instrument Key" }
                ]}
                ariaLabel="Instrument scope"
                minWidth="w-full"
              />
            </div>
          </div>

          <div>
            <label className={oaFormTextStyles.label}>First N Instruments</label>
            <div className="mt-1">
              <Input
                name="instrument_limit"
                type="number"
                min="1"
                value={formData.instrument_limit}
                onChange={onChange}
                disabled={formData.instrument_scope !== "limit"}
                placeholder="Example: 50"
              />
            </div>
          </div>

          <div>
            <label className={oaFormTextStyles.label}>
              Single Instrument Key
            </label>
            <div className="mt-1">
              <Input
                name="single_instrument_key"
                value={formData.single_instrument_key}
                onChange={onChange}
                disabled={formData.instrument_scope !== "single"}
                placeholder="NSE_EQ|INE002A01018"
              />
            </div>
          </div>
        </div>

        <button type="submit" className="hidden" aria-hidden="true">
          Save OHLCV options
        </button>
      </form>
    </Modal>
  );
}

function MarketCalendarContent({
  previewData,
  rows,
  loading,
  hasActiveJob,
  isAdminControlAllowed,
  searchValue,
  searchActive,
  holidayType,
  onHolidayTypeChange,
  onClearHolidayType,
  exchange,
  onExchangeChange,
  onClearExchange,
  tradingStatus,
  onTradingStatusChange,
  onClearTradingStatus,
  hasActiveFilter,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onClearAll,
  onSchedule,
  onRun,
  onRefresh,
  onPreviousPage,
  onNextPage,
  onPageChange,
  renderCell,
  filterConfig
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder="Search market calendar"
          filters={[
            {
              value: holidayType,
              onChange: (event) => onHolidayTypeChange(event.target.value),
              options: marketHolidayTypeOptions,
              onClear: onClearHolidayType,
              showClear: holidayType !== "all",
              ariaLabel: "Holiday type",
              minWidth: "w-44"
            },
            {
              value: exchange,
              onChange: (event) => onExchangeChange(event.target.value),
              options: marketHolidayExchangeOptions,
              onClear: onClearExchange,
              showClear: exchange !== "all",
              ariaLabel: "Exchange",
              minWidth: "w-36"
            },
            {
              value: tradingStatus,
              onChange: (event) => onTradingStatusChange(event.target.value),
              options: marketHolidayTradingStatusOptions,
              onClear: onClearTradingStatus,
              showClear: tradingStatus !== "all",
              ariaLabel: "Trading status",
              minWidth: "w-40"
            }
          ]}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            {
              icon: Clock3,
              label: "Schedule Market Calendar",
              variant: "default",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onSchedule
            },
            {
              icon: Play,
              label: "Run Market Calendar",
              variant: "add",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onRun
            },
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            }
          ]}
        />
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">
                Loading market calendar
              </span>
            </div>
          </div>
        )}

        <DataTable
          columns={marketHolidayPreviewColumns}
          rows={rows}
          loading={false}
          loadingMessage="Loading market calendar"
          emptyMessage="No market holidays found."
          gridTemplateColumns={marketHolidayPreviewGridTemplateColumns}
          minWidth="min-w-[2110px]"
          getRowKey={(row, index) => `${row.holiday_date || "calendar"}-${index}`}
          renderCell={renderCell}
          filterConfig={filterConfig}
        />
      </div>

      <PaginationFooter
        previewData={previewData}
        loading={loading}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}

function GenericPreviewContent({
  title,
  searchPlaceholder,
  previewData,
  rows,
  loading,
  hasActiveJob,
  isAdminControlAllowed,
  searchValue,
  searchActive,
  filters,
  hasActiveFilter,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onClearAll,
  onSchedule,
  onRun,
  onRefresh,
  onPreviousPage,
  onNextPage,
  onPageChange,
  renderCell,
  filterConfig,
  columns,
  gridTemplateColumns,
  minWidth,
  emptyMessage,
  getRowKey
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder={searchPlaceholder}
          filters={filters}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            onSchedule
              ? {
                  icon: Clock3,
                  label: `Schedule ${title}`,
                  variant: "default",
                  disabled: !isAdminControlAllowed || loading || hasActiveJob,
                  onClick: onSchedule
                }
              : null,
            {
              icon: Play,
              label: `Run ${title}`,
              variant: "add",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onRun
            },
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            }
          ].filter(Boolean)}
        />
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">
                Loading {title.toLowerCase()}
              </span>
            </div>
          </div>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          loading={false}
          loadingMessage={`Loading ${title.toLowerCase()}`}
          emptyMessage={emptyMessage}
          gridTemplateColumns={gridTemplateColumns}
          minWidth={minWidth}
          getRowKey={getRowKey}
          renderCell={renderCell}
          filterConfig={filterConfig}
        />
      </div>

      <PaginationFooter
        previewData={previewData}
        loading={loading}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}

function OhlcvTabContent({
  previewData,
  rows,
  loading,
  savingOptions,
  hasActiveJob,
  isAdminControlAllowed,
  searchValue,
  searchActive,
  hasActiveFilter,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onClearAll,
  onOptions,
  onSchedule,
  onRun,
  onRefresh,
  onPreviousPage,
  onNextPage,
  onPageChange,
  renderCell,
  filterConfig
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder="Search OHLCV"
          filters={[]}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            {
              icon: Edit3,
              label: "OHLCV options",
              variant: "default",
              disabled:
                !isAdminControlAllowed || loading || hasActiveJob || savingOptions,
              onClick: onOptions
            },
            {
              icon: Clock3,
              label: "Schedule OHLCV",
              variant: "default",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onSchedule
            },
            {
              icon: Play,
              label: "Run saved OHLCV",
              variant: "add",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onRun
            },
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            }
          ]}
        />
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">Loading OHLCV</span>
            </div>
          </div>
        )}

        <DataTable
          columns={ohlcvPreviewColumns}
          rows={rows}
          loading={false}
          loadingMessage="Loading OHLCV"
          emptyMessage="No OHLCV records found."
          gridTemplateColumns={ohlcvPreviewGridTemplateColumns}
          minWidth="min-w-[2860px]"
          getRowKey={(row, index) =>
            `${row.instrument_key || row.trading_symbol || "ohlcv"}-${
              row.timestamp || row.date || index
            }-${index}`
          }
          renderCell={renderCell}
          filterConfig={filterConfig}
        />
      </div>

      <PaginationFooter
        previewData={previewData}
        loading={loading}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}

function IpoCalendarTabContent({ activeSubTab, onSubTabChange, children }) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
        <div className={`${oaTabStyles.wrapper} overflow-x-auto`}>
          {ipoCalendarSubTabOptions.map((option) => {
            const isActive = activeSubTab === option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onSubTabChange(option.value)}
                className={`${oaTabStyles.button} ${
                  isActive ? oaTabStyles.active : oaTabStyles.inactive
                } whitespace-nowrap`}
              >
                <span>{option.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {children}
    </div>
  );
}

function CompanyFundamentalsContent({
  activeEndpoint,
  onEndpointChange,
  previewData,
  rows,
  loading,
  hasActiveJob,
  isAdminControlAllowed,
  searchValue,
  searchActive,
  statementType,
  onStatementTypeChange,
  onClearStatementType,
  timePeriod,
  onTimePeriodChange,
  onClearTimePeriod,
  segment,
  onSegmentChange,
  onClearSegment,
  hasActiveFilter,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  onClearAll,
  onSchedule,
  onRun,
  onRefresh,
  onPreviousPage,
  onNextPage,
  onPageChange,
  renderCell,
  filterConfig,
  columns,
  gridTemplateColumns,
  minWidth
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
        <div className={`${oaTabStyles.wrapper} overflow-x-auto`}>
          {companyFundamentalsEndpointOptions.map((option) => {
            const isActive = activeEndpoint === option.value;

            return (
              <button
                key={option.value}
                type="button"
                onClick={() => onEndpointChange(option.value)}
                className={`${oaTabStyles.button} ${
                  isActive ? oaTabStyles.active : oaTabStyles.inactive
                } whitespace-nowrap`}
              >
                <span>{option.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5 [&>div]:mb-0">
        <TableToolbar
          searchValue={searchValue}
          onSearchChange={onSearchChange}
          onSearchClear={onClearSearch}
          onSearchSubmit={onSearchSubmit}
          searchActive={searchActive}
          searchPlaceholder="Search company fundamentals"
          filters={[
            {
              value: statementType,
              onChange: (event) => onStatementTypeChange(event.target.value),
              options: companyFundamentalsStatementTypeOptions,
              onClear: onClearStatementType,
              showClear: statementType !== "all",
              ariaLabel: "Statement type",
              minWidth: "w-44"
            },
            {
              value: timePeriod,
              onChange: (event) => onTimePeriodChange(event.target.value),
              options: companyFundamentalsTimePeriodOptions,
              onClear: onClearTimePeriod,
              showClear: timePeriod !== "all",
              ariaLabel: "Time period",
              minWidth: "w-40"
            },
            {
              value: segment,
              onChange: (event) => onSegmentChange(event.target.value),
              options: segmentOptions,
              onClear: onClearSegment,
              showClear: segment !== "all",
              ariaLabel: "Segment",
              minWidth: "w-36"
            }
          ]}
          hasActiveFilter={hasActiveFilter}
          onClearAll={onClearAll}
          loading={loading}
          rightActions={[
            {
              icon: Clock3,
              label: "Schedule Company Fundamentals",
              variant: "default",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onSchedule
            },
            {
              icon: Play,
              label: "Run Company Fundamentals",
              variant: "add",
              disabled: !isAdminControlAllowed || loading || hasActiveJob,
              onClick: onRun
            },
            {
              icon: RefreshCcw,
              label: "Refresh",
              variant: "refresh",
              disabled: loading,
              onClick: onRefresh
            }
          ]}
        />
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">
                Loading company fundamentals
              </span>
            </div>
          </div>
        )}

        <DataTable
          columns={columns}
          rows={rows}
          loading={false}
          loadingMessage="Loading company fundamentals"
          emptyMessage="No company fundamentals found."
          gridTemplateColumns={gridTemplateColumns}
          minWidth={minWidth}
          getRowKey={(row, index) =>
            `${row.fundamental_id || row.isin || "fundamental"}-${index}`
          }
          renderCell={renderCell}
          filterConfig={filterConfig}
        />
      </div>

      <PaginationFooter
        previewData={previewData}
        loading={loading}
        onPreviousPage={onPreviousPage}
        onNextPage={onNextPage}
        onPageChange={onPageChange}
      />
    </div>
  );
}

function PaginationFooter({
  previewData,
  loading,
  onPreviousPage,
  onNextPage,
  onPageChange
}) {
  return (
    <div className="flex shrink-0 flex-col gap-2 border-t border-oa-border bg-black px-3 py-2 text-[12px] text-oa-muted md:flex-row md:items-center md:justify-between">
      <span>
        Records: {formatNumber(previewData.total_records)} | Page {" "}
        {previewData.page} of {previewData.total_pages}
      </span>

      <div className="flex items-center gap-1.5">
        <IconButton
          icon={ChevronLeft}
          label="Previous"
          variant="default"
          disabled={previewData.page <= 1 || loading}
          onClick={onPreviousPage}
          tooltipSide="top"
        />

        <div className="flex items-center gap-1">
          {getPaginationItems(previewData.page, previewData.total_pages).map(
            (item) => {
              if (String(item).includes("ellipsis")) {
                return (
                  <span
                    key={item}
                    className="flex h-8 min-w-8 items-center justify-center px-1 text-[12px] text-oa-muted"
                  >
                    ...
                  </span>
                );
              }

              const active = Number(item) === Number(previewData.page);

              return (
                <button
                  key={item}
                  type="button"
                  disabled={loading || active}
                  onClick={() => onPageChange(item)}
                  className={`flex h-8 min-w-8 items-center justify-center rounded border px-2 text-[12px] font-semibold outline-none transition ${
                    active
                      ? "border-sky-500/60 bg-sky-950/40 text-sky-200"
                      : "border-oa-border bg-black text-oa-muted hover:border-sky-500/40 hover:bg-oa-card hover:text-white focus:border-sky-500"
                  } disabled:cursor-default`}
                  aria-label={`Go to page ${item}`}
                >
                  {item}
                </button>
              );
            }
          )}
        </div>

        <IconButton
          icon={ChevronRight}
          label="Next"
          variant="default"
          disabled={previewData.page >= previewData.total_pages || loading}
          onClick={onNextPage}
          tooltipSide="top"
        />
      </div>
    </div>
  );
}

function DataCollection() {
  const [activeView, setActiveView] = useState("monitor");
  const [summary, setSummary] = useState(emptySummary);
  const [runs, setRuns] = useState([]);
  const [schedules, setSchedules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [schedulerLoading, setSchedulerLoading] = useState(false);
  const [runningJob, setRunningJob] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelRequested, setCancelRequested] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const activeSyncControllerRef = useRef(null);

  const [monitorSearch, setMonitorSearch] = useState("");
  const [appliedMonitorSearch, setAppliedMonitorSearch] = useState("");
  const [monitorColumnFilters, setMonitorColumnFilters] = useState({});
  const [draftMonitorColumnFilters, setDraftMonitorColumnFilters] = useState({});
  const [activeMonitorFilter, setActiveMonitorFilter] = useState(null);
  const [monitorSortConfig, setMonitorSortConfig] = useState({
    key: null,
    direction: null
  });

  const [selectedScheduleJob, setSelectedScheduleJob] = useState(null);
  const [scheduleFormMode, setScheduleFormMode] = useState("add");
  const [scheduleFormData, setScheduleFormData] = useState(emptyScheduleForm);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [savingScheduleId, setSavingScheduleId] = useState("");
  const [deletingScheduleId, setDeletingScheduleId] = useState("");

  const [previewSearch, setPreviewSearch] = useState("");
  const [appliedPreviewSearch, setAppliedPreviewSearch] = useState("");
  const [previewColumnFilters, setPreviewColumnFilters] = useState({});
  const [draftPreviewColumnFilters, setDraftPreviewColumnFilters] = useState({});
  const [activePreviewFilter, setActivePreviewFilter] = useState(null);
  const [previewSortConfig, setPreviewSortConfig] = useState({
    key: null,
    direction: null
  });
  const [previewSourceType, setPreviewSourceType] = useState("all");
  const [previewSegment, setPreviewSegment] = useState("all");
  const [previewInstrumentType, setPreviewInstrumentType] = useState("all");
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(emptyPreviewData);

  const [ohlcvOptionsOpen, setOhlcvOptionsOpen] = useState(false);
  const [ohlcvFormData, setOhlcvFormData] = useState(emptyOhlcvForm);
  const [ohlcvOptionsLoading, setOhlcvOptionsLoading] = useState(false);
  const [ohlcvOptionsSaving, setOhlcvOptionsSaving] = useState(false);
  const [ohlcvSearch, setOhlcvSearch] = useState("");
  const [appliedOhlcvSearch, setAppliedOhlcvSearch] = useState("");
  const [ohlcvColumnFilters, setOhlcvColumnFilters] = useState({});
  const [draftOhlcvColumnFilters, setDraftOhlcvColumnFilters] = useState({});
  const [activeOhlcvFilter, setActiveOhlcvFilter] = useState(null);
  const [ohlcvSortConfig, setOhlcvSortConfig] = useState({
    key: null,
    direction: null
  });
  const [ohlcvPage, setOhlcvPage] = useState(1);
  const [ohlcvPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [ohlcvLoading, setOhlcvLoading] = useState(false);
  const [ohlcvPreviewData, setOhlcvPreviewData] = useState(emptyPreviewData);

  const [marketCalendarSearch, setMarketCalendarSearch] = useState("");
  const [appliedMarketCalendarSearch, setAppliedMarketCalendarSearch] = useState("");
  const [marketCalendarColumnFilters, setMarketCalendarColumnFilters] = useState({});
  const [draftMarketCalendarColumnFilters, setDraftMarketCalendarColumnFilters] = useState({});
  const [activeMarketCalendarFilter, setActiveMarketCalendarFilter] = useState(null);
  const [marketCalendarSortConfig, setMarketCalendarSortConfig] = useState({
    key: null,
    direction: null
  });
  const [marketCalendarHolidayType, setMarketCalendarHolidayType] = useState("all");
  const [marketCalendarExchange, setMarketCalendarExchange] = useState("all");
  const [marketCalendarTradingStatus, setMarketCalendarTradingStatus] = useState("all");
  const [marketCalendarPage, setMarketCalendarPage] = useState(1);
  const [marketCalendarPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [marketCalendarLoading, setMarketCalendarLoading] = useState(false);
  const [marketCalendarPreviewData, setMarketCalendarPreviewData] = useState(emptyPreviewData);


  const [equityNewsSearch, setEquityNewsSearch] = useState("");
  const [appliedEquityNewsSearch, setAppliedEquityNewsSearch] = useState("");
  const [equityNewsSegment, setEquityNewsSegment] = useState("all");
  const [equityNewsColumnFilters, setEquityNewsColumnFilters] = useState({});
  const [draftEquityNewsColumnFilters, setDraftEquityNewsColumnFilters] = useState({});
  const [activeEquityNewsFilter, setActiveEquityNewsFilter] = useState(null);
  const [equityNewsSortConfig, setEquityNewsSortConfig] = useState({
    key: null,
    direction: null
  });
  const [equityNewsPage, setEquityNewsPage] = useState(1);
  const [equityNewsPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [equityNewsLoading, setEquityNewsLoading] = useState(false);
  const [equityNewsPreviewData, setEquityNewsPreviewData] = useState(emptyPreviewData);

  const [ipoCalendarSearch, setIpoCalendarSearch] = useState("");
  const [appliedIpoCalendarSearch, setAppliedIpoCalendarSearch] = useState("");
  const [ipoCalendarStatus, setIpoCalendarStatus] = useState("all");
  const [ipoCalendarIssueType, setIpoCalendarIssueType] = useState("all");
  const [ipoCalendarIndustry, setIpoCalendarIndustry] = useState("all");
  const [ipoCalendarColumnFilters, setIpoCalendarColumnFilters] = useState({});
  const [draftIpoCalendarColumnFilters, setDraftIpoCalendarColumnFilters] = useState({});
  const [activeIpoCalendarFilter, setActiveIpoCalendarFilter] = useState(null);
  const [ipoCalendarSortConfig, setIpoCalendarSortConfig] = useState({
    key: null,
    direction: null
  });
  const [ipoCalendarPage, setIpoCalendarPage] = useState(1);
  const [ipoCalendarPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [ipoCalendarLoading, setIpoCalendarLoading] = useState(false);
  const [ipoCalendarPreviewData, setIpoCalendarPreviewData] = useState(emptyPreviewData);
  const [ipoCalendarSubTab, setIpoCalendarSubTab] = useState("ipo");

  const [ipoScraperSearch, setIpoScraperSearch] = useState("");
  const [appliedIpoScraperSearch, setAppliedIpoScraperSearch] = useState("");
  const [ipoScraperStatus, setIpoScraperStatus] = useState("all");
  const [ipoScraperType, setIpoScraperType] = useState("all");
  const [ipoScraperColumnFilters, setIpoScraperColumnFilters] = useState({});
  const [draftIpoScraperColumnFilters, setDraftIpoScraperColumnFilters] = useState({});
  const [activeIpoScraperFilter, setActiveIpoScraperFilter] = useState(null);
  const [ipoScraperSortConfig, setIpoScraperSortConfig] = useState({
    key: null,
    direction: null
  });
  const [ipoScraperPage, setIpoScraperPage] = useState(1);
  const [ipoScraperPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [ipoScraperLoading, setIpoScraperLoading] = useState(false);
  const [ipoScraperPreviewData, setIpoScraperPreviewData] = useState(emptyPreviewData);

  const [companyFundamentalsEndpoint, setCompanyFundamentalsEndpoint] = useState("company_profile");
  const [companyFundamentalsSearch, setCompanyFundamentalsSearch] = useState("");
  const [appliedCompanyFundamentalsSearch, setAppliedCompanyFundamentalsSearch] = useState("");
  const [companyFundamentalsStatementType, setCompanyFundamentalsStatementType] = useState("all");
  const [companyFundamentalsTimePeriod, setCompanyFundamentalsTimePeriod] = useState("all");
  const [companyFundamentalsSegment, setCompanyFundamentalsSegment] = useState("all");
  const [companyFundamentalsColumnFilters, setCompanyFundamentalsColumnFilters] = useState({});
  const [draftCompanyFundamentalsColumnFilters, setDraftCompanyFundamentalsColumnFilters] = useState({});
  const [activeCompanyFundamentalsFilter, setActiveCompanyFundamentalsFilter] = useState(null);
  const [companyFundamentalsSortConfig, setCompanyFundamentalsSortConfig] = useState({
    key: null,
    direction: null
  });
  const [companyFundamentalsPage, setCompanyFundamentalsPage] = useState(1);
  const [companyFundamentalsPageSize] = useState(DATA_COLLECTION_PREVIEW_PAGE_SIZE);
  const [companyFundamentalsLoading, setCompanyFundamentalsLoading] = useState(false);
  const [companyFundamentalsPreviewData, setCompanyFundamentalsPreviewData] = useState(emptyPreviewData);

  const { showToast } = useToast();

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  const queuedJobIds = useMemo(() => {
    const jobs = Array.isArray(summary.queued_jobs?.jobs)
      ? summary.queued_jobs.jobs
      : [];

    return new Set(jobs.map(getQueuedDumpJobId).filter(Boolean));
  }, [summary.queued_jobs]);

  const hasQueuedJobs = queuedJobIds.size > 0;
  const hasActiveJob = Boolean(runningJob || summary.active_job || hasQueuedJobs);
  const isCancelRequested =
    cancelRequested || summary.active_job_status === "cancel_requested";

  const isCurrentJobRunning =
    !isCancelRequested &&
    (runningJob === "current" ||
      summary.active_job === "upstox_current_instruments");

  const isExpiredJobRunning =
    !isCancelRequested &&
    (runningJob === "expired" ||
      summary.active_job === "upstox_expired_instruments");

  const currentCancelRequested =
    isCancelRequested &&
    (runningJob === "current" ||
      summary.active_job === "upstox_current_instruments");
  const isCurrentJobQueued = queuedJobIds.has("current");

  const expiredCancelRequested =
    isCancelRequested &&
    (runningJob === "expired" ||
      summary.active_job === "upstox_expired_instruments");
  const isExpiredJobQueued = queuedJobIds.has("expired");

  const isOhlcvJobRunning =
    !isCancelRequested &&
    (runningJob === "ohlcv" || summary.active_job === "upstox_ohlcv_daily");

  const ohlcvCancelRequested =
    isCancelRequested &&
    (runningJob === "ohlcv" || summary.active_job === "upstox_ohlcv_daily");
  const isOhlcvJobQueued = queuedJobIds.has("ohlcv");

  const isMarketCalendarJobRunning =
    !isCancelRequested &&
    (runningJob === "market_calendar" ||
      summary.active_job === "upstox_market_holidays");

  const marketCalendarCancelRequested =
    isCancelRequested &&
    (runningJob === "market_calendar" ||
      summary.active_job === "upstox_market_holidays");
  const isMarketCalendarJobQueued = queuedJobIds.has("market_calendar");


  const isEquityNewsJobRunning =
    !isCancelRequested &&
    (runningJob === "equity_news" || summary.active_job === "upstox_equity_news");

  const equityNewsCancelRequested =
    isCancelRequested &&
    (runningJob === "equity_news" || summary.active_job === "upstox_equity_news");
  const isEquityNewsJobQueued = queuedJobIds.has("equity_news");

  const isIpoCalendarJobRunning =
    !isCancelRequested &&
    (runningJob === "ipo_calendar" || summary.active_job === "upstox_ipo_calendar");

  const ipoCalendarCancelRequested =
    isCancelRequested &&
    (runningJob === "ipo_calendar" || summary.active_job === "upstox_ipo_calendar");
  const isIpoCalendarJobQueued = queuedJobIds.has("ipo_calendar");

  const isIpoScraperJobRunning =
    !isCancelRequested &&
    (runningJob === "ipo_scraper" || summary.active_job === "ipo_gmp_scraper");

  const ipoScraperCancelRequested =
    isCancelRequested &&
    (runningJob === "ipo_scraper" || summary.active_job === "ipo_gmp_scraper");
  const isIpoScraperJobQueued = queuedJobIds.has("ipo_scraper");

  const isCompanyFundamentalsJobRunning =
    !isCancelRequested &&
    (runningJob === "company_fundamentals" ||
      summary.active_job === "upstox_company_fundamentals");

  const companyFundamentalsCancelRequested =
    isCancelRequested &&
    (runningJob === "company_fundamentals" ||
      summary.active_job === "upstox_company_fundamentals");
  const isCompanyFundamentalsJobQueued = queuedJobIds.has("company_fundamentals");

  const shouldShowCancelButton = hasActiveJob && !isCancelRequested;

  const currentLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_current_instruments"]);
  }, [runs]);

  const expiredLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_expired_instruments"]);
  }, [runs]);

  const ohlcvLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_ohlcv_daily"]);
  }, [runs]);

  const equityNewsLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_equity_news"]);
  }, [runs]);

  const ipoCalendarLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_ipo_calendar"]);
  }, [runs]);

  const ipoScraperLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["ipo_gmp_scraper"]);
  }, [runs]);

  const companyFundamentalsLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_company_fundamentals"]);
  }, [runs]);


  const marketCalendarLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_market_holidays"]);
  }, [runs]);

  const selectedSchedules = useMemo(() => {
    if (!selectedScheduleJob) {
      return [];
    }

    return schedules.filter(
      (schedule) => schedule.job_type === selectedScheduleJob
    );
  }, [schedules, selectedScheduleJob]);

  const selectedScheduleTitle = getSyncTypeLabel(selectedScheduleJob);

  const dumpJobRows = useMemo(() => {
    const currentRecords =
      isCurrentJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_current_instruments ?? 0;

    const expiredRecords =
      isExpiredJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_expired_instruments ?? 0;

    const currentRecordsAdded =
      isCurrentJobRunning &&
      summary.active_job === "upstox_current_instruments" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const expiredRecordsAdded =
      isExpiredJobRunning &&
      summary.active_job === "upstox_expired_instruments" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const ohlcvRecords =
      isOhlcvJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_ohlcv_daily ?? 0;

    const ohlcvRecordsAdded =
      isOhlcvJobRunning &&
      summary.active_job === "upstox_ohlcv_daily" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const equityNewsRecords =
      isEquityNewsJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_equity_news ?? 0;

    const equityNewsRecordsAdded =
      isEquityNewsJobRunning &&
      summary.active_job === "upstox_equity_news" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const ipoCalendarRecords =
      isIpoCalendarJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_ipo_calendar ?? summary.total_ipos ?? 0;

    const ipoCalendarRecordsAdded =
      isIpoCalendarJobRunning &&
      summary.active_job === "upstox_ipo_calendar" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const ipoScraperRecords =
      isIpoScraperJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_ipo_gmp_scraper ?? summary.total_ipo_scraper ?? 0;

    const ipoScraperRecordsAdded =
      isIpoScraperJobRunning &&
      summary.active_job === "ipo_gmp_scraper" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const marketCalendarRecords =
      isMarketCalendarJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_market_holidays ?? 0;

    const marketCalendarRecordsAdded =
      isMarketCalendarJobRunning &&
      summary.active_job === "upstox_market_holidays" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    const companyFundamentalsRecords =
      isCompanyFundamentalsJobRunning && summary.active_job_current_records != null
        ? summary.active_job_current_records
        : summary.total_company_fundamentals ?? 0;

    const companyFundamentalsRecordsAdded =
      isCompanyFundamentalsJobRunning &&
      summary.active_job === "upstox_company_fundamentals" &&
      summary.active_job_records_added != null
        ? summary.active_job_records_added
        : 0;

    return [
      {
        id: "current",
        title: "Current Instruments",
        scheduleJobType: "current_instruments",
        records: currentRecords,
        recordsAdded: currentRecordsAdded,
        lastSyncedAt: summary.current_last_sync_at || summary.last_sync_at,
        triggeredBy: currentLastRun?.triggered_by_name,
        triggerSource: currentLastRun?.trigger_source,
        duration: summary.current_duration_seconds,
        lastStatus: currentCancelRequested
          ? "cancel_requested"
          : isCurrentJobRunning
            ? "running"
            : isCurrentJobQueued
              ? "queued"
              : currentLastRun?.status,
        loading: isCurrentJobRunning,
        disabled: hasActiveJob && !isCurrentJobRunning,
        canCancel: isCurrentJobRunning && shouldShowCancelButton,
        onRun: handleCurrentSync
      },
      {
        id: "expired",
        title: "Expired Instruments",
        scheduleJobType: "expired_instruments",
        records: expiredRecords,
        recordsAdded: expiredRecordsAdded,
        lastSyncedAt: summary.expired_last_sync_at,
        triggeredBy: expiredLastRun?.triggered_by_name,
        triggerSource: expiredLastRun?.trigger_source,
        duration: summary.expired_duration_seconds,
        lastStatus: expiredCancelRequested
          ? "cancel_requested"
          : isExpiredJobRunning
            ? "running"
            : isExpiredJobQueued
              ? "queued"
              : expiredLastRun?.status,
        loading: isExpiredJobRunning,
        disabled: hasActiveJob && !isExpiredJobRunning,
        canCancel: isExpiredJobRunning && shouldShowCancelButton,
        onRun: handleExpiredSync
      },
      {
        id: "ohlcv",
        title: "OHLCV",
        scheduleJobType: "ohlcv_daily",
        records: ohlcvRecords,
        recordsAdded: ohlcvRecordsAdded,
        lastSyncedAt: summary.ohlcv_daily_last_sync_at,
        triggeredBy: ohlcvLastRun?.triggered_by_name,
        triggerSource: ohlcvLastRun?.trigger_source,
        duration: summary.ohlcv_daily_duration_seconds,
        lastStatus: ohlcvCancelRequested
          ? "cancel_requested"
          : isOhlcvJobRunning
            ? "running"
            : isOhlcvJobQueued
              ? "queued"
              : ohlcvLastRun?.status,
        loading: isOhlcvJobRunning,
        disabled: hasActiveJob && !isOhlcvJobRunning,
        canCancel: isOhlcvJobRunning && shouldShowCancelButton,
        onOptions: openOhlcvOptionsPopup,
        onRun: handleOhlcvSync,
        runLabel: "Run saved"
      },
      {
        id: "equity_news",
        title: "Equity News",
        scheduleJobType: "equity_news",
        records: equityNewsRecords,
        recordsAdded: equityNewsRecordsAdded,
        lastSyncedAt: summary.equity_news_last_sync_at,
        triggeredBy: equityNewsLastRun?.triggered_by_name,
        triggerSource: equityNewsLastRun?.trigger_source,
        duration: summary.equity_news_duration_seconds,
        lastStatus: equityNewsCancelRequested
          ? "cancel_requested"
          : isEquityNewsJobRunning
            ? "running"
            : isEquityNewsJobQueued
              ? "queued"
              : equityNewsLastRun?.status,
        loading: isEquityNewsJobRunning,
        disabled: hasActiveJob && !isEquityNewsJobRunning,
        canCancel: isEquityNewsJobRunning && shouldShowCancelButton,
        onRun: handleEquityNewsSync
      },
      {
        id: "ipo_calendar",
        title: "IPO Calendar",
        scheduleJobType: "ipo_calendar",
        records: ipoCalendarRecords,
        recordsAdded: ipoCalendarRecordsAdded,
        lastSyncedAt: summary.ipo_calendar_last_sync_at,
        triggeredBy: ipoCalendarLastRun?.triggered_by_name,
        triggerSource: ipoCalendarLastRun?.trigger_source,
        duration: summary.ipo_calendar_duration_seconds,
        lastStatus: ipoCalendarCancelRequested
          ? "cancel_requested"
          : isIpoCalendarJobRunning
            ? "running"
            : isIpoCalendarJobQueued
              ? "queued"
              : ipoCalendarLastRun?.status,
        loading: isIpoCalendarJobRunning,
        disabled: hasActiveJob && !isIpoCalendarJobRunning,
        canCancel: isIpoCalendarJobRunning && shouldShowCancelButton,
        onRun: handleIpoCalendarSync
      },
      {
        id: "ipo_scraper",
        title: "IPO Scrapper",
        scheduleJobType: "ipo_scraper",
        records: ipoScraperRecords,
        recordsAdded: ipoScraperRecordsAdded,
        lastSyncedAt:
          summary.ipo_gmp_scraper_last_sync_at || summary.ipo_scraper_last_sync_at,
        triggeredBy: ipoScraperLastRun?.triggered_by_name,
        triggerSource: ipoScraperLastRun?.trigger_source,
        duration:
          summary.ipo_gmp_scraper_duration_seconds ||
          summary.ipo_scraper_duration_seconds,
        lastStatus: ipoScraperCancelRequested
          ? "cancel_requested"
          : isIpoScraperJobRunning
            ? "running"
            : isIpoScraperJobQueued
              ? "queued"
              : ipoScraperLastRun?.status,
        loading: isIpoScraperJobRunning,
        disabled: hasActiveJob && !isIpoScraperJobRunning,
        canCancel: isIpoScraperJobRunning && shouldShowCancelButton,
        onRun: handleIpoScraperSync
      },
      {
        id: "company_fundamentals",
        title: "Company Fundamentals",
        scheduleJobType: "company_fundamentals",
        records: companyFundamentalsRecords,
        recordsAdded: companyFundamentalsRecordsAdded,
        lastSyncedAt: summary.company_fundamentals_last_sync_at,
        triggeredBy: companyFundamentalsLastRun?.triggered_by_name,
        triggerSource: companyFundamentalsLastRun?.trigger_source,
        duration: summary.company_fundamentals_duration_seconds,
        lastStatus: companyFundamentalsCancelRequested
          ? "cancel_requested"
          : isCompanyFundamentalsJobRunning
            ? "running"
            : isCompanyFundamentalsJobQueued
              ? "queued"
              : companyFundamentalsLastRun?.status,
        loading: isCompanyFundamentalsJobRunning,
        disabled: hasActiveJob && !isCompanyFundamentalsJobRunning,
        canCancel: isCompanyFundamentalsJobRunning && shouldShowCancelButton,
        onRun: handleCompanyFundamentalsSync
      },
      {
        id: "market_calendar",
        title: "Market Calendar",
        scheduleJobType: "market_holidays",
        records: marketCalendarRecords,
        recordsAdded: marketCalendarRecordsAdded,
        lastSyncedAt: summary.market_holidays_last_sync_at,
        triggeredBy: marketCalendarLastRun?.triggered_by_name,
        triggerSource: marketCalendarLastRun?.trigger_source,
        duration: summary.market_holidays_duration_seconds,
        lastStatus: marketCalendarCancelRequested
          ? "cancel_requested"
          : isMarketCalendarJobRunning
            ? "running"
            : isMarketCalendarJobQueued
              ? "queued"
              : marketCalendarLastRun?.status,
        loading: isMarketCalendarJobRunning,
        disabled: hasActiveJob && !isMarketCalendarJobRunning,
        canCancel: isMarketCalendarJobRunning && shouldShowCancelButton,
        onRun: handleMarketCalendarSync
      }
    ];
  }, [
    summary,
    currentCancelRequested,
    expiredCancelRequested,
    isCurrentJobRunning,
    isExpiredJobRunning,
    isOhlcvJobRunning,
    isMarketCalendarJobRunning,
    isEquityNewsJobRunning,
    isIpoCalendarJobRunning,
    isIpoScraperJobRunning,
    isCompanyFundamentalsJobRunning,
    currentLastRun,
    expiredLastRun,
    ohlcvLastRun,
    marketCalendarLastRun,
    equityNewsLastRun,
    ipoCalendarLastRun,
    ipoScraperLastRun,
    companyFundamentalsLastRun,
    isCurrentJobQueued,
    isExpiredJobQueued,
    isOhlcvJobQueued,
    isMarketCalendarJobQueued,
    isEquityNewsJobQueued,
    isIpoCalendarJobQueued,
    isIpoScraperJobQueued,
    isCompanyFundamentalsJobQueued,
    ohlcvCancelRequested,
    marketCalendarCancelRequested,
    equityNewsCancelRequested,
    ipoCalendarCancelRequested,
    ipoScraperCancelRequested,
    companyFundamentalsCancelRequested,
    hasActiveJob,
    shouldShowCancelButton
  ]);

  const monitorHeaderValues = useMemo(() => {
    return dumpJobColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        dumpJobRows,
        column.key,
        getDumpJobColumnValue
      );
      return result;
    }, {});
  }, [dumpJobRows]);

  const filteredDumpJobRows = useMemo(() => {
    let result = dumpJobRows;
    const query = appliedMonitorSearch.trim().toLowerCase();

    if (query) {
      result = result.filter((row) => {
        const values = dumpJobColumns.map((column) =>
          getDumpJobColumnValue(row, column.key)
        );

        return values.some((value) => String(value).toLowerCase().includes(query));
      });
    }

    result = applyColumnFilters(
      result,
      monitorColumnFilters,
      getDumpJobColumnValue
    );

    return applySort(result, monitorSortConfig, getDumpJobColumnValue);
  }, [
    dumpJobRows,
    appliedMonitorSearch,
    monitorColumnFilters,
    monitorSortConfig
  ]);

  const previewHeaderValues = useMemo(() => {
    return previewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        previewData.rows,
        column.key,
        getPreviewColumnValue
      );
      return result;
    }, {});
  }, [previewData.rows]);

  const filteredPreviewRows = useMemo(() => {
    let result = applyColumnFilters(
      previewData.rows,
      previewColumnFilters,
      getPreviewColumnValue
    );

    return applySort(result, previewSortConfig, getPreviewColumnValue);
  }, [previewData.rows, previewColumnFilters, previewSortConfig]);

  const ohlcvHeaderValues = useMemo(() => {
    return ohlcvPreviewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        ohlcvPreviewData.rows,
        column.key,
        getOhlcvColumnValue
      );
      return result;
    }, {});
  }, [ohlcvPreviewData.rows]);

  const filteredOhlcvRows = useMemo(() => {
    let result = applyColumnFilters(
      ohlcvPreviewData.rows,
      ohlcvColumnFilters,
      getOhlcvColumnValue
    );

    return applySort(result, ohlcvSortConfig, getOhlcvColumnValue);
  }, [ohlcvPreviewData.rows, ohlcvColumnFilters, ohlcvSortConfig]);


  const marketCalendarHeaderValues = useMemo(() => {
    return marketHolidayPreviewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        marketCalendarPreviewData.rows,
        column.key,
        getMarketHolidayColumnValue
      );
      return result;
    }, {});
  }, [marketCalendarPreviewData.rows]);

  const filteredMarketCalendarRows = useMemo(() => {
    let result = applyColumnFilters(
      marketCalendarPreviewData.rows,
      marketCalendarColumnFilters,
      getMarketHolidayColumnValue
    );

    return applySort(
      result,
      marketCalendarSortConfig,
      getMarketHolidayColumnValue
    );
  }, [
    marketCalendarPreviewData.rows,
    marketCalendarColumnFilters,
    marketCalendarSortConfig
  ]);


  const equityNewsHeaderValues = useMemo(() => {
    return equityNewsPreviewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        equityNewsPreviewData.rows,
        column.key,
        getEquityNewsColumnValue
      );
      return result;
    }, {});
  }, [equityNewsPreviewData.rows]);

  const filteredEquityNewsRows = useMemo(() => {
    let result = applyColumnFilters(
      equityNewsPreviewData.rows,
      equityNewsColumnFilters,
      getEquityNewsColumnValue
    );

    return applySort(result, equityNewsSortConfig, getEquityNewsColumnValue);
  }, [
    equityNewsPreviewData.rows,
    equityNewsColumnFilters,
    equityNewsSortConfig
  ]);

  const ipoCalendarHeaderValues = useMemo(() => {
    return ipoCalendarPreviewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        ipoCalendarPreviewData.rows,
        column.key,
        getIpoCalendarColumnValue
      );
      return result;
    }, {});
  }, [ipoCalendarPreviewData.rows]);

  const filteredIpoCalendarRows = useMemo(() => {
    let result = applyColumnFilters(
      ipoCalendarPreviewData.rows,
      ipoCalendarColumnFilters,
      getIpoCalendarColumnValue
    );

    return applySort(result, ipoCalendarSortConfig, getIpoCalendarColumnValue);
  }, [
    ipoCalendarPreviewData.rows,
    ipoCalendarColumnFilters,
    ipoCalendarSortConfig
  ]);

  const ipoScraperHeaderValues = useMemo(() => {
    return ipoScraperPreviewColumns.reduce((result, column) => {
      result[column.key] = getFilterValues(
        ipoScraperPreviewData.rows,
        column.key,
        getIpoScraperColumnValue
      );
      return result;
    }, {});
  }, [ipoScraperPreviewData.rows]);

  const filteredIpoScraperRows = useMemo(() => {
    let result = applyColumnFilters(
      ipoScraperPreviewData.rows,
      ipoScraperColumnFilters,
      getIpoScraperColumnValue
    );

    return applySort(result, ipoScraperSortConfig, getIpoScraperColumnValue);
  }, [
    ipoScraperPreviewData.rows,
    ipoScraperColumnFilters,
    ipoScraperSortConfig
  ]);

  const activeCompanyFundamentalsColumnGroup = useMemo(() => {
    return (
      companyFundamentalsColumnGroups[companyFundamentalsEndpoint] ||
      defaultCompanyFundamentalsColumnGroup
    );
  }, [companyFundamentalsEndpoint]);

  const companyFundamentalsHeaderValues = useMemo(() => {
    return activeCompanyFundamentalsColumnGroup.columns.reduce(
      (result, column) => {
        result[column.key] = getFilterValues(
          companyFundamentalsPreviewData.rows,
          column.key,
          getCompanyFundamentalsColumnValue
        );
        return result;
      },
      {}
    );
  }, [
    activeCompanyFundamentalsColumnGroup.columns,
    companyFundamentalsPreviewData.rows
  ]);

  const filteredCompanyFundamentalsRows = useMemo(() => {
    let result = applyColumnFilters(
      companyFundamentalsPreviewData.rows,
      companyFundamentalsColumnFilters,
      getCompanyFundamentalsColumnValue
    );

    return applySort(
      result,
      companyFundamentalsSortConfig,
      getCompanyFundamentalsColumnValue
    );
  }, [
    companyFundamentalsPreviewData.rows,
    companyFundamentalsColumnFilters,
    companyFundamentalsSortConfig
  ]);

  async function loadPreview(customPage = previewPage) {
    const previewMode = getPreviewMode(activeView);
    setPreviewLoading(true);

    try {
      const params = {
        search: appliedPreviewSearch,
        source_type: previewSourceType,
        segment: previewSegment,
        instrument_type: previewInstrumentType,
        page: customPage,
        page_size: previewPageSize
      };

      const response =
        previewMode === "expired"
          ? await getUpstoxExpiredInstrumentsPreview(params)
          : await getUpstoxInstrumentsPreview(params);

      const nextData = response.data.data || response.data || emptyPreviewData;

      setPreviewData(nextData);
      setPreviewPage(nextData.page || customPage);
    } catch (error) {
      setPreviewData(emptyPreviewData);
      showToast(
        getApiErrorMessage(
          error,
          previewMode === "expired"
            ? "Unable to load expired instruments."
            : "Unable to load current instruments."
        ),
        "error"
      );
    } finally {
      setPreviewLoading(false);
    }
  }

  async function loadOhlcvPreview(customPage = ohlcvPage, options = {}) {
    const { showLoading = true } = options;

    if (showLoading) {
      setOhlcvLoading(true);
    }

    try {
      const params = {
        search: appliedOhlcvSearch,
        page: customPage,
        page_size: ohlcvPageSize
      };

      const response = await getUpstoxOhlcvPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setOhlcvPreviewData(nextData);
      setOhlcvPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setOhlcvPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(error, "Unable to load OHLCV preview."),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setOhlcvLoading(false);
      }
    }
  }


  async function loadMarketCalendarPreview(
    customPage = marketCalendarPage,
    options = {}
  ) {
    const { showLoading = true } = options;

    if (showLoading) {
      setMarketCalendarLoading(true);
    }

    try {
      const params = {
        search: appliedMarketCalendarSearch,
        holiday_type: marketCalendarHolidayType,
        exchange: marketCalendarExchange,
        trading_status: marketCalendarTradingStatus,
        page: customPage,
        page_size: marketCalendarPageSize
      };

      const response = await getUpstoxMarketHolidaysPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setMarketCalendarPreviewData(nextData);
      setMarketCalendarPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setMarketCalendarPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(error, "Unable to load market calendar preview."),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setMarketCalendarLoading(false);
      }
    }
  }

  async function loadEquityNewsPreview(customPage = equityNewsPage, options = {}) {
    const { showLoading = true } = options;

    if (showLoading) {
      setEquityNewsLoading(true);
    }

    try {
      const params = {
        search: appliedEquityNewsSearch,
        segment: equityNewsSegment,
        source: "all",
        page: customPage,
        page_size: equityNewsPageSize
      };

      const response = await getUpstoxEquityNewsPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setEquityNewsPreviewData(nextData);
      setEquityNewsPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setEquityNewsPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(error, "Unable to load Equity News preview."),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setEquityNewsLoading(false);
      }
    }
  }

  async function loadIpoCalendarPreview(
    customPage = ipoCalendarPage,
    options = {}
  ) {
    const { showLoading = true } = options;

    if (showLoading) {
      setIpoCalendarLoading(true);
    }

    try {
      const params = {
        search: appliedIpoCalendarSearch,
        ipo_status: ipoCalendarStatus,
        issue_type: ipoCalendarIssueType,
        industry: ipoCalendarIndustry,
        page: customPage,
        page_size: ipoCalendarPageSize
      };

      const response = await getUpstoxIpoCalendarPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setIpoCalendarPreviewData(nextData);
      setIpoCalendarPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setIpoCalendarPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(error, "Unable to load IPO Calendar preview."),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setIpoCalendarLoading(false);
      }
    }
  }

  async function loadIpoScraperPreview(
    customPage = ipoScraperPage,
    options = {}
  ) {
    const { showLoading = true } = options;

    if (showLoading) {
      setIpoScraperLoading(true);
    }

    try {
      const params = {
        search: appliedIpoScraperSearch,
        ipo_status: ipoScraperStatus,
        ipo_type: ipoScraperType,
        page: customPage,
        page_size: ipoScraperPageSize
      };

      const response = await getIpoGmpScraperPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setIpoScraperPreviewData(nextData);
      setIpoScraperPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setIpoScraperPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(error, "Unable to load IPO Scrapper preview."),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setIpoScraperLoading(false);
      }
    }
  }

  async function loadCompanyFundamentalsPreview(
    customPage = companyFundamentalsPage,
    options = {}
  ) {
    const { showLoading = true } = options;

    if (showLoading) {
      setCompanyFundamentalsLoading(true);
    }

    try {
      const params = {
        search: appliedCompanyFundamentalsSearch,
        endpoint: companyFundamentalsEndpoint,
        statement_type: companyFundamentalsStatementType,
        time_period: companyFundamentalsTimePeriod,
        segment: companyFundamentalsSegment,
        page: customPage,
        page_size: companyFundamentalsPageSize
      };

      const response = await getUpstoxCompanyFundamentalsPreview(params);
      const nextData = response.data.data || response.data || emptyPreviewData;

      setCompanyFundamentalsPreviewData(nextData);
      setCompanyFundamentalsPage(nextData.page || customPage);
    } catch (error) {
      if (showLoading) {
        setCompanyFundamentalsPreviewData(emptyPreviewData);
        showToast(
          getApiErrorMessage(
            error,
            "Unable to load company fundamentals preview."
          ),
          "error"
        );
      }
    } finally {
      if (showLoading) {
        setCompanyFundamentalsLoading(false);
      }
    }
  }

  async function loadSchedules(showRefreshToast = false) {
    setSchedulerLoading(true);

    try {
      const response = await getUpstoxDataCollectionSchedules();
      setSchedules(response.data.data || response.data || []);

      if (showRefreshToast) {
        showToast("Schedules refreshed successfully.", "success");
      }
    } catch (error) {
      setSchedules([]);
      showToast(getApiErrorMessage(error, "Unable to load schedules."), "error");
    } finally {
      setSchedulerLoading(false);
    }
  }

  async function refreshAfterSync() {
    try {
      await loadData(false, { showLoading: false });
    } catch (error) {
      showToast(
        error.response?.data?.detail ||
          "Dump completed, but the latest status could not be refreshed.",
        "warning"
      );
    }
  }

  function scheduleStartedJobRefresh() {
    window.setTimeout(() => {
      loadData(false, { showLoading: false });
    }, 2000);
  }

  async function loadData(showRefreshToast = false, options = {}) {
    const { showLoading = true } = options;

    if (showLoading) {
      setLoading(true);
    }

    try {
      const [summaryResult, runsResult] = await Promise.allSettled([
        getUpstoxDataCollectionSummary(),
        getUpstoxDataCollectionRuns()
      ]);

      let nextSummary = summary;
      let nextRuns = runs;
      const errors = [];

      if (summaryResult.status === "fulfilled") {
        nextSummary =
          summaryResult.value.data.data ||
          summaryResult.value.data ||
          emptySummary;
        setSummary(nextSummary);
      } else {
        errors.push(summaryResult.reason);

        if (showLoading) {
          nextSummary = emptySummary;
          setSummary(emptySummary);
        }
      }

      if (runsResult.status === "fulfilled") {
        nextRuns = runsResult.value.data.data || runsResult.value.data || [];
        setRuns(nextRuns);
      } else {
        errors.push(runsResult.reason);

        if (showLoading) {
          nextRuns = [];
          setRuns([]);
        }
      }

      if (nextSummary.active_job_started_at) {
        setElapsedSeconds(
          getElapsedSecondsFromDate(nextSummary.active_job_started_at)
        );
      } else if (!nextSummary.active_job) {
        setElapsedSeconds(0);
      }

      const activeJobId = getQueuedDumpJobId(nextSummary.active_job);
      if (!nextSummary.active_job || (runningJob && runningJob !== activeJobId)) {
        setRunningJob(null);
        setCancelRequested(false);
      }

      if (errors.length > 0) {
        showToast(
          getApiErrorMessage(
            errors[0],
            "Unable to fully load data collection status."
          ),
          "warning"
        );
        return;
      }

      if (showRefreshToast) {
        showToast("Data collection status refreshed.", "success");
      }
    } catch (error) {
      if (showLoading) {
        setSummary(emptySummary);
        setRuns([]);
        setRunningJob(null);
        setElapsedSeconds(0);
      }

      showToast(
        getApiErrorMessage(error, "Unable to load data collection status."),
        "warning"
      );
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }

  async function handleCancelSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to cancel data collection.", "error");
      return;
    }

    setCancelling(true);
    setCancelRequested(true);
    setRunningJob(null);
    activeSyncControllerRef.current?.abort();

    try {
      const response = await cancelUpstoxDataCollection();
      const message =
        response.data?.message || "Cancel requested for data collection.";

      showToast(message, "warning");
      await loadData(false, { showLoading: false });
    } catch (error) {
      showToast(
        getApiErrorMessage(error, "Unable to cancel data collection."),
        "error"
      );
    } finally {
      setCancelling(false);
    }
  }

  async function handleCurrentSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    setRunningJob("current");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxCurrentInstruments({
        signal: activeSyncControllerRef.current.signal
      });

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "Current Instruments collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Current instruments dump cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "Current instruments dump completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run current instruments dump."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }
      activeSyncControllerRef.current = null;
    }
  }

  async function handleExpiredSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    setRunningJob("expired");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxExpiredInstruments(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "Expired Instruments collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Expired instruments dump cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "Expired instruments dump completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run expired instruments dump."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }
      activeSyncControllerRef.current = null;
    }
  }

  function normalizeOhlcvOptionsResponse(data) {
    const options = data?.options || data?.data?.options || data?.data || data || {};
    const nextOptions = {
      ...emptyOhlcvForm,
      ...options
    };

    if (!Array.isArray(nextOptions.sources)) {
      nextOptions.sources = emptyOhlcvForm.sources;
    }

    if (!Array.isArray(nextOptions.candle_modes)) {
      nextOptions.candle_modes = emptyOhlcvForm.candle_modes;
    }

    if (!Array.isArray(nextOptions.intervals)) {
      nextOptions.intervals = emptyOhlcvForm.intervals;
    }

    nextOptions.use_current_day = Boolean(
      nextOptions.use_current_day ?? emptyOhlcvForm.use_current_day
    );
    nextOptions.auto_date_range = Boolean(
      nextOptions.auto_date_range ?? emptyOhlcvForm.auto_date_range
    );

    if (nextOptions.use_current_day) {
      nextOptions.to_date = "";
    }

    if (nextOptions.auto_date_range) {
      nextOptions.from_date = "";
    }

    nextOptions.instrument_scope = nextOptions.single_instrument_key
      ? "single"
      : nextOptions.instrument_limit
        ? "limit"
        : "all";

    nextOptions.instrument_limit =
      nextOptions.instrument_limit === null || nextOptions.instrument_limit === undefined
        ? ""
        : String(nextOptions.instrument_limit);

    nextOptions.batch_size = String(nextOptions.batch_size || emptyOhlcvForm.batch_size);
    nextOptions.request_delay_ms = String(
      nextOptions.request_delay_ms ?? emptyOhlcvForm.request_delay_ms
    );
    nextOptions.batch_delay_seconds = String(
      nextOptions.batch_delay_seconds ?? emptyOhlcvForm.batch_delay_seconds
    );
    nextOptions.retry_count = String(nextOptions.retry_count || emptyOhlcvForm.retry_count);

    return nextOptions;
  }

  async function openOhlcvOptionsPopup() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to manage OHLCV options.", "error");
      return;
    }

    setOhlcvOptionsOpen(true);
    setOhlcvOptionsLoading(true);

    try {
      const response = await getUpstoxOhlcvOptions();
      setOhlcvFormData(normalizeOhlcvOptionsResponse(response.data));
    } catch (error) {
      setOhlcvFormData(emptyOhlcvForm);
      showToast(
        getApiErrorMessage(error, "Unable to load OHLCV options."),
        "warning"
      );
    } finally {
      setOhlcvOptionsLoading(false);
    }
  }

  function closeOhlcvOptionsPopup() {
    if (ohlcvOptionsSaving) {
      return;
    }

    setOhlcvOptionsOpen(false);
  }

  function handleOhlcvFormChange(event) {
    const { name, value, type, checked } = event.target;

    setOhlcvFormData((previous) => {
      const nextValue = type === "checkbox" ? checked : value;
      const nextData = {
        ...previous,
        [name]: nextValue
      };

      if (name === "use_current_day" && checked) {
        nextData.to_date = "";
      }

      if (name === "auto_date_range" && checked) {
        nextData.from_date = "";
      }

      return nextData;
    });
  }

  function handleOhlcvMultiChange(fieldName, values) {
    setOhlcvFormData((previous) => ({
      ...previous,
      [fieldName]: values
    }));
  }

  function buildOhlcvOptionsPayload() {
    const instrumentLimit = Number(ohlcvFormData.instrument_limit);

    return {
      sources: ohlcvFormData.sources,
      candle_modes: ohlcvFormData.candle_modes,
      intervals: ohlcvFormData.intervals,
      from_date: ohlcvFormData.auto_date_range ? null : ohlcvFormData.from_date || null,
      to_date: ohlcvFormData.use_current_day ? null : ohlcvFormData.to_date || null,
      use_current_day: Boolean(ohlcvFormData.use_current_day),
      auto_date_range: Boolean(ohlcvFormData.auto_date_range),
      skip_existing: true,
      respect_api_limits: true,
      retry_failed: true,
      instrument_limit:
        ohlcvFormData.instrument_scope === "limit" && instrumentLimit > 0
          ? instrumentLimit
          : null,
      single_instrument_key:
        ohlcvFormData.instrument_scope === "single"
          ? ohlcvFormData.single_instrument_key.trim()
          : "",
      batch_size: 25,
      request_delay_ms: 500,
      batch_delay_seconds: 2,
      retry_count: 3
    };
  }

  async function handleSaveOhlcvOptions() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to save OHLCV options.", "error");
      return;
    }

    if (ohlcvFormData.sources.length === 0) {
      showToast("Select at least one OHLCV source.", "warning");
      return;
    }

    if (ohlcvFormData.candle_modes.length === 0) {
      showToast("Select at least one OHLCV mode.", "warning");
      return;
    }

    if (ohlcvFormData.intervals.length === 0) {
      showToast("Select at least one interval.", "warning");
      return;
    }

    if (
      ohlcvFormData.instrument_scope === "single" &&
      !ohlcvFormData.single_instrument_key.trim()
    ) {
      showToast("Enter a single instrument key.", "warning");
      return;
    }

    setOhlcvOptionsSaving(true);

    try {
      const response = await saveUpstoxOhlcvOptions(buildOhlcvOptionsPayload());
      const nextData = response.data?.data || response.data;

      setOhlcvFormData(normalizeOhlcvOptionsResponse(nextData));
      setOhlcvOptionsOpen(false);
      showToast(response.data?.message || "OHLCV options saved.", "success");
    } catch (error) {
      showToast(getApiErrorMessage(error, "Unable to save OHLCV options."), "error");
    } finally {
      setOhlcvOptionsSaving(false);
    }
  }

  async function handleOhlcvSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("ohlcv");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxOhlcvDaily(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "OHLCV collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(response.data.message || "OHLCV collection cancelled.", "warning");
      } else {
        showToast(response.data?.message || "OHLCV collection completed.", "success");
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(getApiErrorMessage(error, "Unable to run OHLCV collection."), "error");
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }


  async function handleEquityNewsSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("equity_news");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxEquityNews(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "Equity News collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Equity News collection cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "Equity News collection completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run Equity News collection."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }

  async function handleIpoCalendarSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("ipo_calendar");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxIpoCalendar(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "IPO Calendar collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "IPO Calendar collection cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "IPO Calendar collection completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run IPO Calendar collection."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }

  async function handleIpoScraperSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("ipo_scraper");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncIpoGmpScraper(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "IPO Scrapper collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "IPO Scrapper collection cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "IPO Scrapper collection completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run IPO Scrapper collection."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }

  async function handleCompanyFundamentalsSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("company_fundamentals");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxCompanyFundamentals(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "Company Fundamentals collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Company Fundamentals collection cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "Company Fundamentals collection completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(
          error,
          "Unable to run Company Fundamentals collection."
        ),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }

  async function handleMarketCalendarSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    if (hasActiveJob) {
      showToast("Another data collection job is already running.", "warning");
      return;
    }

    setRunningJob("market_calendar");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();
    let backgroundStarted = false;

    try {
      const response = await syncUpstoxMarketHolidays(
        {},
        {
          signal: activeSyncControllerRef.current.signal
        }
      );

      if (response.data?.status === "started") {
        backgroundStarted = true;
        showToast(
          response.data.message || "Market Calendar collection started.",
          "success"
        );
        scheduleStartedJobRefresh();
      } else if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Market Calendar collection cancelled.",
          "warning"
        );
      } else {
        showToast(
          response.data?.message || "Market Calendar collection completed.",
          "success"
        );
      }

      if (!backgroundStarted) {
        await refreshAfterSync();
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        getApiErrorMessage(error, "Unable to run Market Calendar collection."),
        "error"
      );
    } finally {
      if (!backgroundStarted) {
        setRunningJob(null);
      }

      activeSyncControllerRef.current = null;
    }
  }

  async function openSchedulePopup(jobType) {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to manage schedules.", "error");
      return;
    }

    setSelectedScheduleJob(jobType);
    setScheduleFormMode("add");
    setScheduleFormData({
      ...emptyScheduleForm,
      job_type: jobType
    });

    await loadSchedules(false);
  }

  function closeSchedulePopup() {
    if (savingSchedule) {
      return;
    }

    setSelectedScheduleJob(null);
    setScheduleFormMode("add");
    setScheduleFormData(emptyScheduleForm);
  }

  function handleScheduleFormChange(event) {
    const { name, value, type, checked } = event.target;

    setScheduleFormData((previous) => ({
      ...previous,
      [name]: type === "checkbox" ? checked : value
    }));
  }

  function handleScheduleTimePartChange(partName, partValue) {
    setScheduleFormData((previous) => {
      const currentParts = getScheduleTimeParts(previous.schedule_time);
      const nextParts = {
        ...currentParts,
        [partName]: partValue
      };

      return {
        ...previous,
        schedule_time: buildScheduleTimeFrom12Hour(
          nextParts.hour12,
          nextParts.minute,
          nextParts.period
        )
      };
    });
  }

  function handleClearScheduleField(fieldName) {
    setScheduleFormData((previous) => ({
      ...previous,
      [fieldName]: ""
    }));
  }

  function handleEditSchedule(schedule) {
    setScheduleFormMode("edit");
    setScheduleFormData({
      schedule_id: schedule.schedule_id,
      job_type: schedule.job_type || selectedScheduleJob || "current_instruments",
      schedule_time: schedule.schedule_time || "",
      time_format: schedule.time_format || "24",
      schedule_frequency: schedule.schedule_frequency || "daily",
      is_active: Boolean(schedule.is_active)
    });
  }

  function handleCancelScheduleEdit() {
    setScheduleFormMode("add");
    setScheduleFormData({
      ...emptyScheduleForm,
      job_type: selectedScheduleJob || "current_instruments"
    });
  }

  async function handleSaveSchedule() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to save schedules.", "error");
      return;
    }

    if (!scheduleFormData.schedule_time) {
      showToast("Schedule time is required.", "warning");
      return;
    }

    setSavingSchedule(true);

    const payload = {
      job_type: scheduleFormData.job_type || selectedScheduleJob,
      schedule_time: scheduleFormData.schedule_time,
      time_format: scheduleFormData.time_format,
      schedule_frequency: scheduleFormData.schedule_frequency || "daily",
      is_active: Boolean(scheduleFormData.is_active)
    };

    try {
      if (scheduleFormMode === "edit") {
        await updateUpstoxDataCollectionSchedule(
          scheduleFormData.schedule_id,
          payload
        );
        showToast("Schedule updated successfully.", "success");
      } else {
        await createUpstoxDataCollectionSchedule(payload);
        showToast("Schedule created successfully.", "success");
      }

      await loadSchedules(false);
      setScheduleFormMode("add");
      setScheduleFormData({
        ...emptyScheduleForm,
        job_type: selectedScheduleJob || "current_instruments"
      });
    } catch (error) {
      showToast(getApiErrorMessage(error, "Unable to save schedule."), "error");
    } finally {
      setSavingSchedule(false);
    }
  }

  async function handleToggleSchedule(schedule) {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to update schedules.", "error");
      return;
    }

    setSavingScheduleId(schedule.schedule_id);

    try {
      const response = await toggleUpstoxDataCollectionSchedule(
        schedule.schedule_id
      );

      showToast(
        response.data?.message || "Schedule status updated successfully.",
        "success"
      );
      await loadSchedules(false);
    } catch (error) {
      showToast(
        getApiErrorMessage(error, "Unable to update schedule status."),
        "error"
      );
    } finally {
      setSavingScheduleId("");
    }
  }

  async function handleDeleteSchedule(schedule) {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to delete schedules.", "error");
      return;
    }

    setDeletingScheduleId(schedule.schedule_id);

    try {
      await deleteUpstoxDataCollectionSchedule(schedule.schedule_id);
      showToast("Schedule deleted successfully.", "success");
      await loadSchedules(false);

      if (scheduleFormData.schedule_id === schedule.schedule_id) {
        handleCancelScheduleEdit();
      }
    } catch (error) {
      showToast(getApiErrorMessage(error, "Unable to delete schedule."), "error");
    } finally {
      setDeletingScheduleId("");
    }
  }

  function handleMonitorSearchSubmit(event) {
    event.preventDefault();
    setAppliedMonitorSearch(monitorSearch.trim());
  }

  function handleClearMonitorSearch() {
    setMonitorSearch("");
    setAppliedMonitorSearch("");
  }

  function handlePreviewSearchSubmit(event) {
    event.preventDefault();
    setAppliedPreviewSearch(previewSearch.trim());
    setPreviewPage(1);
  }

  function handleClearPreviewSearch() {
    setPreviewSearch("");
    setAppliedPreviewSearch("");
    setPreviewPage(1);
  }

  function clearPreviewSourceType() {
    setPreviewSourceType("all");
    setPreviewPage(1);
  }

  function clearPreviewSegment() {
    setPreviewSegment("all");
    setPreviewPage(1);
  }

  function clearPreviewInstrumentType() {
    setPreviewInstrumentType("all");
    setPreviewPage(1);
  }

  function hasAnyActiveMonitorFilter() {
    return (
      appliedMonitorSearch.trim() !== "" ||
      monitorSortConfig.key !== null ||
      Object.values(monitorColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllMonitorFilters() {
    setMonitorSearch("");
    setAppliedMonitorSearch("");
    setMonitorColumnFilters({});
    setDraftMonitorColumnFilters({});
    setMonitorSortConfig({
      key: null,
      direction: null
    });
    setActiveMonitorFilter(null);
  }

  function hasAnyActivePreviewFilter() {
    return (
      appliedPreviewSearch.trim() !== "" ||
      previewSourceType !== "all" ||
      previewSegment !== "all" ||
      previewInstrumentType !== "all" ||
      previewSortConfig.key !== null ||
      Object.values(previewColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllPreviewFilters() {
    setPreviewSearch("");
    setAppliedPreviewSearch("");
    setPreviewSourceType("all");
    setPreviewSegment("all");
    setPreviewInstrumentType("all");
    setPreviewColumnFilters({});
    setDraftPreviewColumnFilters({});
    setPreviewSortConfig({
      key: null,
      direction: null
    });
    setActivePreviewFilter(null);
    setPreviewPage(1);
  }

  function openMonitorColumnFilter(key) {
    setDraftMonitorColumnFilters((previous) => ({
      ...previous,
      [key]: monitorColumnFilters[key] || []
    }));

    setActiveMonitorFilter((previous) => (previous === key ? null : key));
  }

  function applyMonitorColumnFilter(key) {
    setMonitorColumnFilters((previous) => ({
      ...previous,
      [key]: draftMonitorColumnFilters[key] || []
    }));

    setActiveMonitorFilter(null);
  }

  function clearMonitorColumnFilter(key) {
    setMonitorColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftMonitorColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveMonitorFilter(null);
  }

  function handleMonitorSort(key, direction) {
    setMonitorSortConfig({
      key,
      direction
    });

    setActiveMonitorFilter(null);
  }

  function isMonitorColumnFilterActive(key) {
    const selectedValues = monitorColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function openPreviewColumnFilter(key) {
    setDraftPreviewColumnFilters((previous) => ({
      ...previous,
      [key]: previewColumnFilters[key] || []
    }));

    setActivePreviewFilter((previous) => (previous === key ? null : key));
  }

  function applyPreviewColumnFilter(key) {
    setPreviewColumnFilters((previous) => ({
      ...previous,
      [key]: draftPreviewColumnFilters[key] || []
    }));

    setActivePreviewFilter(null);
  }

  function clearPreviewColumnFilter(key) {
    setPreviewColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftPreviewColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActivePreviewFilter(null);
  }

  function handlePreviewSort(key, direction) {
    setPreviewSortConfig({
      key,
      direction
    });

    setActivePreviewFilter(null);
  }

  function isPreviewColumnFilterActive(key) {
    const selectedValues = previewColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleOhlcvSearchSubmit(event) {
    event.preventDefault();
    setAppliedOhlcvSearch(ohlcvSearch.trim());
    setOhlcvPage(1);
  }

  function handleClearOhlcvSearch() {
    setOhlcvSearch("");
    setAppliedOhlcvSearch("");
    setOhlcvPage(1);
  }

  function hasAnyActiveOhlcvFilter() {
    return (
      appliedOhlcvSearch.trim() !== "" ||
      ohlcvSortConfig.key !== null ||
      Object.values(ohlcvColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllOhlcvFilters() {
    setOhlcvSearch("");
    setAppliedOhlcvSearch("");
    setOhlcvColumnFilters({});
    setDraftOhlcvColumnFilters({});
    setOhlcvSortConfig({
      key: null,
      direction: null
    });
    setActiveOhlcvFilter(null);
  }

  function openOhlcvColumnFilter(key) {
    setDraftOhlcvColumnFilters((previous) => ({
      ...previous,
      [key]: ohlcvColumnFilters[key] || []
    }));

    setActiveOhlcvFilter((previous) => (previous === key ? null : key));
  }

  function applyOhlcvColumnFilter(key) {
    setOhlcvColumnFilters((previous) => ({
      ...previous,
      [key]: draftOhlcvColumnFilters[key] || []
    }));

    setActiveOhlcvFilter(null);
  }

  function clearOhlcvColumnFilter(key) {
    setOhlcvColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftOhlcvColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveOhlcvFilter(null);
  }

  function handleOhlcvSort(key, direction) {
    setOhlcvSortConfig({
      key,
      direction
    });

    setActiveOhlcvFilter(null);
  }

  function isOhlcvColumnFilterActive(key) {
    const selectedValues = ohlcvColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleMarketCalendarSearchSubmit(event) {
    event.preventDefault();
    setAppliedMarketCalendarSearch(marketCalendarSearch.trim());
    setMarketCalendarPage(1);
  }

  function handleClearMarketCalendarSearch() {
    setMarketCalendarSearch("");
    setAppliedMarketCalendarSearch("");
    setMarketCalendarPage(1);
  }

  function clearMarketCalendarHolidayType() {
    setMarketCalendarHolidayType("all");
    setMarketCalendarPage(1);
  }

  function clearMarketCalendarExchange() {
    setMarketCalendarExchange("all");
    setMarketCalendarPage(1);
  }

  function clearMarketCalendarTradingStatus() {
    setMarketCalendarTradingStatus("all");
    setMarketCalendarPage(1);
  }

  function hasAnyActiveMarketCalendarFilter() {
    return (
      appliedMarketCalendarSearch.trim() !== "" ||
      marketCalendarHolidayType !== "all" ||
      marketCalendarExchange !== "all" ||
      marketCalendarTradingStatus !== "all" ||
      marketCalendarSortConfig.key !== null ||
      Object.values(marketCalendarColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllMarketCalendarFilters() {
    setMarketCalendarSearch("");
    setAppliedMarketCalendarSearch("");
    setMarketCalendarHolidayType("all");
    setMarketCalendarExchange("all");
    setMarketCalendarTradingStatus("all");
    setMarketCalendarColumnFilters({});
    setDraftMarketCalendarColumnFilters({});
    setMarketCalendarSortConfig({
      key: null,
      direction: null
    });
    setActiveMarketCalendarFilter(null);
    setMarketCalendarPage(1);
  }

  function openMarketCalendarColumnFilter(key) {
    setDraftMarketCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: marketCalendarColumnFilters[key] || []
    }));

    setActiveMarketCalendarFilter((previous) =>
      previous === key ? null : key
    );
  }

  function applyMarketCalendarColumnFilter(key) {
    setMarketCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: draftMarketCalendarColumnFilters[key] || []
    }));

    setActiveMarketCalendarFilter(null);
  }

  function clearMarketCalendarColumnFilter(key) {
    setMarketCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftMarketCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveMarketCalendarFilter(null);
  }

  function handleMarketCalendarSort(key, direction) {
    setMarketCalendarSortConfig({
      key,
      direction
    });

    setActiveMarketCalendarFilter(null);
  }

  function isMarketCalendarColumnFilterActive(key) {
    const selectedValues = marketCalendarColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleEquityNewsSearchSubmit(event) {
    event.preventDefault();
    setAppliedEquityNewsSearch(equityNewsSearch.trim());
    setEquityNewsPage(1);
  }

  function handleClearEquityNewsSearch() {
    setEquityNewsSearch("");
    setAppliedEquityNewsSearch("");
    setEquityNewsPage(1);
  }

  function clearEquityNewsSegment() {
    setEquityNewsSegment("all");
    setEquityNewsPage(1);
  }

  function hasAnyActiveEquityNewsFilter() {
    return (
      appliedEquityNewsSearch.trim() !== "" ||
      equityNewsSegment !== "all" ||
      equityNewsSortConfig.key !== null ||
      Object.values(equityNewsColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllEquityNewsFilters() {
    setEquityNewsSearch("");
    setAppliedEquityNewsSearch("");
    setEquityNewsSegment("all");
    setEquityNewsColumnFilters({});
    setDraftEquityNewsColumnFilters({});
    setEquityNewsSortConfig({
      key: null,
      direction: null
    });
    setActiveEquityNewsFilter(null);
    setEquityNewsPage(1);
  }

  function openEquityNewsColumnFilter(key) {
    setDraftEquityNewsColumnFilters((previous) => ({
      ...previous,
      [key]: equityNewsColumnFilters[key] || []
    }));

    setActiveEquityNewsFilter((previous) => (previous === key ? null : key));
  }

  function applyEquityNewsColumnFilter(key) {
    setEquityNewsColumnFilters((previous) => ({
      ...previous,
      [key]: draftEquityNewsColumnFilters[key] || []
    }));

    setActiveEquityNewsFilter(null);
  }

  function clearEquityNewsColumnFilter(key) {
    setEquityNewsColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftEquityNewsColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveEquityNewsFilter(null);
  }

  function handleEquityNewsSort(key, direction) {
    setEquityNewsSortConfig({
      key,
      direction
    });

    setActiveEquityNewsFilter(null);
  }

  function isEquityNewsColumnFilterActive(key) {
    const selectedValues = equityNewsColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleIpoCalendarSearchSubmit(event) {
    event.preventDefault();
    setAppliedIpoCalendarSearch(ipoCalendarSearch.trim());
    setIpoCalendarPage(1);
  }

  function handleClearIpoCalendarSearch() {
    setIpoCalendarSearch("");
    setAppliedIpoCalendarSearch("");
    setIpoCalendarPage(1);
  }

  function clearIpoCalendarStatus() {
    setIpoCalendarStatus("all");
    setIpoCalendarPage(1);
  }

  function clearIpoCalendarIssueType() {
    setIpoCalendarIssueType("all");
    setIpoCalendarPage(1);
  }

  function clearIpoCalendarIndustry() {
    setIpoCalendarIndustry("all");
    setIpoCalendarPage(1);
  }

  function hasAnyActiveIpoCalendarFilter() {
    return (
      appliedIpoCalendarSearch.trim() !== "" ||
      ipoCalendarStatus !== "all" ||
      ipoCalendarIssueType !== "all" ||
      ipoCalendarIndustry !== "all" ||
      ipoCalendarSortConfig.key !== null ||
      Object.values(ipoCalendarColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllIpoCalendarFilters() {
    setIpoCalendarSearch("");
    setAppliedIpoCalendarSearch("");
    setIpoCalendarStatus("all");
    setIpoCalendarIssueType("all");
    setIpoCalendarIndustry("all");
    setIpoCalendarColumnFilters({});
    setDraftIpoCalendarColumnFilters({});
    setIpoCalendarSortConfig({
      key: null,
      direction: null
    });
    setActiveIpoCalendarFilter(null);
    setIpoCalendarPage(1);
  }

  function openIpoCalendarColumnFilter(key) {
    setDraftIpoCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: ipoCalendarColumnFilters[key] || []
    }));

    setActiveIpoCalendarFilter((previous) => (previous === key ? null : key));
  }

  function applyIpoCalendarColumnFilter(key) {
    setIpoCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: draftIpoCalendarColumnFilters[key] || []
    }));

    setActiveIpoCalendarFilter(null);
  }

  function clearIpoCalendarColumnFilter(key) {
    setIpoCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftIpoCalendarColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveIpoCalendarFilter(null);
  }

  function handleIpoCalendarSort(key, direction) {
    setIpoCalendarSortConfig({
      key,
      direction
    });

    setActiveIpoCalendarFilter(null);
  }

  function isIpoCalendarColumnFilterActive(key) {
    const selectedValues = ipoCalendarColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleIpoScraperSearchSubmit(event) {
    event.preventDefault();
    setAppliedIpoScraperSearch(ipoScraperSearch.trim());
    setIpoScraperPage(1);
  }

  function handleClearIpoScraperSearch() {
    setIpoScraperSearch("");
    setAppliedIpoScraperSearch("");
    setIpoScraperPage(1);
  }

  function clearIpoScraperStatus() {
    setIpoScraperStatus("all");
    setIpoScraperPage(1);
  }

  function clearIpoScraperType() {
    setIpoScraperType("all");
    setIpoScraperPage(1);
  }

  function hasAnyActiveIpoScraperFilter() {
    return (
      appliedIpoScraperSearch.trim() !== "" ||
      ipoScraperStatus !== "all" ||
      ipoScraperType !== "all" ||
      ipoScraperSortConfig.key !== null ||
      Object.values(ipoScraperColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllIpoScraperFilters() {
    setIpoScraperSearch("");
    setAppliedIpoScraperSearch("");
    setIpoScraperStatus("all");
    setIpoScraperType("all");
    setIpoScraperColumnFilters({});
    setDraftIpoScraperColumnFilters({});
    setIpoScraperSortConfig({
      key: null,
      direction: null
    });
    setActiveIpoScraperFilter(null);
    setIpoScraperPage(1);
  }

  function openIpoScraperColumnFilter(key) {
    setDraftIpoScraperColumnFilters((previous) => ({
      ...previous,
      [key]: ipoScraperColumnFilters[key] || []
    }));

    setActiveIpoScraperFilter((previous) => (previous === key ? null : key));
  }

  function applyIpoScraperColumnFilter(key) {
    setIpoScraperColumnFilters((previous) => ({
      ...previous,
      [key]: draftIpoScraperColumnFilters[key] || []
    }));

    setActiveIpoScraperFilter(null);
  }

  function clearIpoScraperColumnFilter(key) {
    setIpoScraperColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftIpoScraperColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveIpoScraperFilter(null);
  }

  function handleIpoScraperSort(key, direction) {
    setIpoScraperSortConfig({
      key,
      direction
    });

    setActiveIpoScraperFilter(null);
  }

  function isIpoScraperColumnFilterActive(key) {
    const selectedValues = ipoScraperColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleCompanyFundamentalsSearchSubmit(event) {
    event.preventDefault();
    setAppliedCompanyFundamentalsSearch(companyFundamentalsSearch.trim());
    setCompanyFundamentalsPage(1);
  }

  function handleClearCompanyFundamentalsSearch() {
    setCompanyFundamentalsSearch("");
    setAppliedCompanyFundamentalsSearch("");
    setCompanyFundamentalsPage(1);
  }

  function clearCompanyFundamentalsStatementType() {
    setCompanyFundamentalsStatementType("all");
    setCompanyFundamentalsPage(1);
  }

  function clearCompanyFundamentalsTimePeriod() {
    setCompanyFundamentalsTimePeriod("all");
    setCompanyFundamentalsPage(1);
  }

  function clearCompanyFundamentalsSegment() {
    setCompanyFundamentalsSegment("all");
    setCompanyFundamentalsPage(1);
  }

  function hasAnyActiveCompanyFundamentalsFilter() {
    return (
      appliedCompanyFundamentalsSearch.trim() !== "" ||
      companyFundamentalsStatementType !== "all" ||
      companyFundamentalsTimePeriod !== "all" ||
      companyFundamentalsSegment !== "all" ||
      companyFundamentalsSortConfig.key !== null ||
      Object.values(companyFundamentalsColumnFilters).some(
        (value) => Array.isArray(value) && value.length > 0
      )
    );
  }

  function clearAllCompanyFundamentalsFilters() {
    setCompanyFundamentalsSearch("");
    setAppliedCompanyFundamentalsSearch("");
    setCompanyFundamentalsStatementType("all");
    setCompanyFundamentalsTimePeriod("all");
    setCompanyFundamentalsSegment("all");
    setCompanyFundamentalsColumnFilters({});
    setDraftCompanyFundamentalsColumnFilters({});
    setCompanyFundamentalsSortConfig({
      key: null,
      direction: null
    });
    setActiveCompanyFundamentalsFilter(null);
    setCompanyFundamentalsPage(1);
  }

  function openCompanyFundamentalsColumnFilter(key) {
    setDraftCompanyFundamentalsColumnFilters((previous) => ({
      ...previous,
      [key]: companyFundamentalsColumnFilters[key] || []
    }));

    setActiveCompanyFundamentalsFilter((previous) =>
      previous === key ? null : key
    );
  }

  function applyCompanyFundamentalsColumnFilter(key) {
    setCompanyFundamentalsColumnFilters((previous) => ({
      ...previous,
      [key]: draftCompanyFundamentalsColumnFilters[key] || []
    }));

    setActiveCompanyFundamentalsFilter(null);
  }

  function clearCompanyFundamentalsColumnFilter(key) {
    setCompanyFundamentalsColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setDraftCompanyFundamentalsColumnFilters((previous) => ({
      ...previous,
      [key]: []
    }));

    setActiveCompanyFundamentalsFilter(null);
  }

  function handleCompanyFundamentalsSort(key, direction) {
    setCompanyFundamentalsSortConfig({
      key,
      direction
    });

    setActiveCompanyFundamentalsFilter(null);
  }

  function isCompanyFundamentalsColumnFilterActive(key) {
    const selectedValues = companyFundamentalsColumnFilters[key] || [];
    return selectedValues.length > 0;
  }

  function handleViewChange(nextView) {
    if (nextView === activeView) {
      return;
    }

    setActiveView(nextView);

    if (isPreviewView(nextView)) {
      setPreviewSearch("");
      setAppliedPreviewSearch("");
      setPreviewSourceType("all");
      setPreviewSegment("all");
      setPreviewInstrumentType("all");
      setPreviewColumnFilters({});
      setDraftPreviewColumnFilters({});
      setPreviewSortConfig({
        key: null,
        direction: null
      });
      setActivePreviewFilter(null);
      setPreviewPage(1);
      setPreviewData(emptyPreviewData);
    }

    if (nextView === "ohlcv") {
      setOhlcvSearch("");
      setAppliedOhlcvSearch("");
      setOhlcvColumnFilters({});
      setDraftOhlcvColumnFilters({});
      setOhlcvSortConfig({
        key: null,
        direction: null
      });
      setActiveOhlcvFilter(null);
      setOhlcvPage(1);
      setOhlcvPreviewData(emptyPreviewData);
    }

    if (nextView === "equity_news") {
      setEquityNewsSearch("");
      setAppliedEquityNewsSearch("");
      setEquityNewsSegment("all");
      setEquityNewsColumnFilters({});
      setDraftEquityNewsColumnFilters({});
      setEquityNewsSortConfig({
        key: null,
        direction: null
      });
      setActiveEquityNewsFilter(null);
      setEquityNewsPage(1);
      setEquityNewsPreviewData(emptyPreviewData);
    }

    if (nextView === "ipo_calendar") {
      setIpoCalendarSearch("");
      setAppliedIpoCalendarSearch("");
      setIpoCalendarStatus("all");
      setIpoCalendarIssueType("all");
      setIpoCalendarIndustry("all");
      setIpoCalendarColumnFilters({});
      setDraftIpoCalendarColumnFilters({});
      setIpoCalendarSortConfig({
        key: null,
        direction: null
      });
      setActiveIpoCalendarFilter(null);
      setIpoCalendarPage(1);
      setIpoCalendarPreviewData(emptyPreviewData);
      setIpoCalendarSubTab("ipo");
      setIpoScraperSearch("");
      setAppliedIpoScraperSearch("");
      setIpoScraperStatus("all");
      setIpoScraperType("all");
      setIpoScraperColumnFilters({});
      setDraftIpoScraperColumnFilters({});
      setIpoScraperSortConfig({
        key: null,
        direction: null
      });
      setActiveIpoScraperFilter(null);
      setIpoScraperPage(1);
      setIpoScraperPreviewData(emptyPreviewData);
    }

    if (nextView === "company_fundamentals") {
      setCompanyFundamentalsEndpoint("company_profile");
      setCompanyFundamentalsSearch("");
      setAppliedCompanyFundamentalsSearch("");
      setCompanyFundamentalsStatementType("all");
      setCompanyFundamentalsTimePeriod("all");
      setCompanyFundamentalsSegment("all");
      setCompanyFundamentalsColumnFilters({});
      setDraftCompanyFundamentalsColumnFilters({});
      setCompanyFundamentalsSortConfig({
        key: null,
        direction: null
      });
      setActiveCompanyFundamentalsFilter(null);
      setCompanyFundamentalsPage(1);
      setCompanyFundamentalsPreviewData(emptyPreviewData);
    }

    if (nextView === "market_calendar") {
      setMarketCalendarSearch("");
      setAppliedMarketCalendarSearch("");
      setMarketCalendarHolidayType("all");
      setMarketCalendarExchange("all");
      setMarketCalendarTradingStatus("all");
      setMarketCalendarColumnFilters({});
      setDraftMarketCalendarColumnFilters({});
      setMarketCalendarSortConfig({
        key: null,
        direction: null
      });
      setActiveMarketCalendarFilter(null);
      setMarketCalendarPage(1);
      setMarketCalendarPreviewData(emptyPreviewData);
    }
  }

  function renderDumpJobCell(row, column) {
    if (column.key === "source") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row.title}
        </span>
      );
    }

    if (column.key === "saved") {
      const recordsAdded = Number(row.recordsAdded || 0);
      const savedLabel = formatCompactNumber(row.records);
      const addedLabel = formatCompactNumber(recordsAdded);

      return (
        <span
          className="inline-flex w-full min-w-[92px] items-center gap-1 overflow-visible whitespace-nowrap oa-code-font"
          title={
            recordsAdded > 0
              ? `${formatNumber(row.records)} saved (+${formatNumber(
                  recordsAdded
                )})`
              : `${formatNumber(row.records)} saved`
          }
        >
          <span className="inline-block min-w-[42px] text-right text-white">
            {savedLabel}
          </span>
          {row.loading && recordsAdded > 0 ? (
            <span className="inline-block shrink-0 text-emerald-300">
              (+{addedLabel})
            </span>
          ) : null}
        </span>
      );
    }

    if (column.key === "updated") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row.lastSyncedAt)}
        </span>
      );
    }

    if (column.key === "triggered_by") {
      const triggeredBy =
        row.triggerSource === "system" ? "System" : row.triggeredBy || "Manual";

      return <span className="truncate text-white">{triggeredBy || "--"}</span>;
    }

    if (column.key === "time") {
      const displaySeconds = row.loading ? elapsedSeconds : row.duration;

      return (
        <span className="truncate oa-code-font text-white">
          {formatDuration(displaySeconds)}
        </span>
      );
    }

    if (column.key === "last_update_status") {
      return <StatusBadge status={row.lastStatus || "idle"} />;
    }

    return <span className="truncate">--</span>;
  }

  function renderDumpJobActions(row) {
    return (
      <DumpJobActions
        title={row.title}
        loading={row.loading}
        disabled={row.disabled}
        canCancel={row.canCancel}
        cancelling={cancelling}
        onRun={row.onRun}
        onCancel={handleCancelSync}
        onSchedule={
          row.scheduleJobType
            ? () => openSchedulePopup(row.scheduleJobType)
            : null
        }
        onOptions={row.onOptions}
        runLabel={row.runLabel || "Run"}
      />
    );
  }

  function renderOhlcvCell(row, column) {
    if (column.key === "source") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getSyncTypeLabel(row.source)}
        </span>
      );
    }

    if (column.key === "mode") {
      return (
        <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
          {getSyncTypeLabel(row.mode)}
        </span>
      );
    }

    if (column.key === "interval_label") {
      return (
        <span className="truncate oa-code-font text-emerald-200">
          {row.interval_label || "--"}
        </span>
      );
    }

    if (column.key === "timestamp" || column.key === "ingested_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row[column.key])}
        </span>
      );
    }

    if (column.key === "date" || column.key === "expiry") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row[column.key] || "--"}
        </span>
      );
    }

    if (
      column.key === "open" ||
      column.key === "high" ||
      column.key === "low" ||
      column.key === "close"
    ) {
      return (
        <span className="truncate oa-code-font text-white">
          {formatPrice(row[column.key])}
        </span>
      );
    }

    if (column.key === "volume" || column.key === "open_interest") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatNumber(row[column.key] || 0)}
        </span>
      );
    }

    if (column.key === "trading_symbol") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row.trading_symbol || "--"}
        </span>
      );
    }

    if (column.key === "instrument_key") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row.instrument_key || "--"}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getOhlcvColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  function renderMarketCalendarCell(row, column) {
    if (column.key === "holiday_date") {
      return (
        <span className="truncate oa-code-font font-semibold text-cyan-200">
          {row.holiday_date || "--"}
        </span>
      );
    }

    if (column.key === "description") {
      return <span className="truncate text-white">{row.description || "--"}</span>;
    }

    if (column.key === "holiday_type") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getSyncTypeLabel(row.holiday_type)}
        </span>
      );
    }

    if (column.key === "is_trading_day") {
      return (
        <StatusBadge
          status={row.is_trading_day ? "active" : "inactive"}
          label={row.is_trading_day ? "Partially Open" : "Closed"}
        />
      );
    }

    if (column.key === "closed_exchanges") {
      return (
        <span className="truncate oa-code-font text-red-200">
          {formatJsonListCell(row.closed_exchanges)}
        </span>
      );
    }

    if (column.key === "open_exchanges") {
      return (
        <span className="truncate oa-code-font text-emerald-200">
          {formatJsonListCell(row.open_exchanges)}
        </span>
      );
    }

    if (column.key === "source_provider") {
      return (
        <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
          {getSyncTypeLabel(row.source_provider)}
        </span>
      );
    }

    if (column.key === "synced_at" || column.key === "updated_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row[column.key])}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getMarketHolidayColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  function renderEquityNewsCell(row, column) {
    if (column.key === "instrument_key") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row.instrument_key || "--"}
        </span>
      );
    }

    if (column.key === "trading_symbol") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row.trading_symbol || "--"}
        </span>
      );
    }

    if (column.key === "company_name" || column.key === "heading") {
      return (
        <span className="truncate text-white">
          {getEquityNewsColumnValue(row, column.key) || "--"}
        </span>
      );
    }

    if (column.key === "segment" || column.key === "source") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getEquityNewsColumnValue(row, column.key) || "--"}
        </span>
      );
    }

    if (column.key === "published_at" || column.key === "ingested_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row[column.key])}
        </span>
      );
    }

    if (column.key === "article_link") {
      const articleLink = getEquityNewsColumnValue(row, column.key);

      return articleLink ? (
        <a
          href={articleLink}
          target="_blank"
          rel="noreferrer"
          className="truncate oa-code-font text-sky-300 hover:text-sky-200"
        >
          {articleLink}
        </a>
      ) : (
        <span className="truncate oa-code-font text-oa-muted">--</span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getEquityNewsColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  function renderIpoCalendarCell(row, column) {
    if (column.key === "ipo_id" || column.key === "isin") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row[column.key] || "--"}
        </span>
      );
    }

    if (column.key === "symbol") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row.symbol || "--"}
        </span>
      );
    }

    if (column.key === "name" || column.key === "industry") {
      return <span className="truncate text-white">{row[column.key] || "--"}</span>;
    }

    if (column.key === "status") {
      return <StatusBadge status={String(row.status || "").toLowerCase()} label={getSyncTypeLabel(row.status)} />;
    }

    if (column.key === "issue_type") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getSyncTypeLabel(row.issue_type)}
        </span>
      );
    }

    if (column.key === "synced_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row.synced_at)}
        </span>
      );
    }

    if (
      column.key === "issue_size" ||
      column.key === "minimum_price" ||
      column.key === "maximum_price" ||
      column.key === "total_subscription"
    ) {
      return (
        <span className="truncate oa-code-font text-white">
          {formatPrice(row[column.key])}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getIpoCalendarColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  function renderIpoScraperCell(row, column) {
    if (column.key === "ipo_name") {
      return <span className="truncate text-white">{row.ipo_name || "--"}</span>;
    }

    if (column.key === "ipo_gmp") {
      return (
        <span className="truncate oa-code-font font-semibold text-emerald-200">
          {row.ipo_gmp || "--"}
        </span>
      );
    }

    if (column.key === "gain") {
      const isLoss = String(row.gain || "").includes("-");

      return (
        <span
          className={`truncate oa-code-font font-semibold ${
            isLoss ? "text-red-200" : "text-emerald-200"
          }`}
        >
          {row.gain || "--"}
        </span>
      );
    }

    if (column.key === "price_band" || column.key === "ipo_date") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row[column.key] || "--"}
        </span>
      );
    }

    if (column.key === "ipo_status") {
      return (
        <StatusBadge
          status={String(row.ipo_status || "").toLowerCase()}
          label={getSyncTypeLabel(row.ipo_status)}
        />
      );
    }

    if (column.key === "ipo_type") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getSyncTypeLabel(row.ipo_type)}
        </span>
      );
    }

    if (column.key === "scraped_at" || column.key === "updated_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row[column.key])}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getIpoScraperColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  function renderCompanyFundamentalsCell(row, column) {
    if (column.key === "isin" || column.key === "instrument_key") {
      return (
        <span className="truncate oa-code-font font-semibold text-white">
          {row[column.key] || "--"}
        </span>
      );
    }

    if (column.key === "trading_symbol") {
      return (
        <span className="truncate oa-code-font text-cyan-200">
          {row.trading_symbol || "--"}
        </span>
      );
    }

    if (column.key === "company_name" || column.key === "sector") {
      return <span className="truncate text-white">{row[column.key] || "--"}</span>;
    }

    if (column.key === "endpoint_label") {
      return (
        <span className={`${oaPillStyles.base} border-sky-500/40 bg-sky-950/40 text-sky-200`}>
          {row.endpoint_label || getSyncTypeLabel(row.endpoint)}
        </span>
      );
    }

    if (column.key === "statement_type" || column.key === "time_period") {
      return (
        <span className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}>
          {getSyncTypeLabel(row[column.key])}
        </span>
      );
    }

    if (column.key === "api_status") {
      return <StatusBadge status={row.api_status || "idle"} />;
    }

    if (column.key === "synced_at") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDateTime(row.synced_at)}
        </span>
      );
    }

    if (column.key === "latest_period") {
      return (
        <span className="truncate oa-code-font text-emerald-200">
          {row.latest_period || "--"}
        </span>
      );
    }

    if (
      column.key === "latest_revenue" ||
      column.key === "latest_operating_profit" ||
      column.key === "latest_net_profit" ||
      column.key === "latest_total_asset" ||
      column.key === "latest_total_liability" ||
      column.key === "latest_operating_cash_flow" ||
      column.key === "pe_ratio_company" ||
      column.key === "pb_ratio_company" ||
      column.key === "roe_company" ||
      column.key === "roce_company"
    ) {
      return (
        <span className="truncate oa-code-font text-white">
          {formatPrice(row[column.key])}
        </span>
      );
    }

    if (
      column.key === "period_count" ||
      column.key === "item_count" ||
      column.key === "corporate_action_count" ||
      column.key === "competitor_count"
    ) {
      return (
        <span className="truncate oa-code-font text-white">
          {formatNumber(row[column.key] || 0)}
        </span>
      );
    }

    return (
      <span className="truncate oa-code-font text-oa-muted">
        {getCompanyFundamentalsColumnValue(row, column.key) || "--"}
      </span>
    );
  }

  useEffect(() => {
    loadData(false);
    loadSchedules(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!isPreviewView(activeView)) {
      return;
    }

    loadPreview(previewPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    appliedPreviewSearch,
    previewSourceType,
    previewSegment,
    previewInstrumentType,
    previewPage
  ]);

  useEffect(() => {
    if (activeView !== "ohlcv") {
      return;
    }

    loadOhlcvPreview(ohlcvPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, appliedOhlcvSearch, ohlcvPage]);


  useEffect(() => {
    if (activeView !== "market_calendar") {
      return;
    }

    loadMarketCalendarPreview(marketCalendarPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    appliedMarketCalendarSearch,
    marketCalendarHolidayType,
    marketCalendarExchange,
    marketCalendarTradingStatus,
    marketCalendarPage
  ]);

  useEffect(() => {
    if (activeView !== "equity_news") {
      return;
    }

    loadEquityNewsPreview(equityNewsPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, appliedEquityNewsSearch, equityNewsSegment, equityNewsPage]);

  useEffect(() => {
    if (activeView !== "ipo_calendar" || ipoCalendarSubTab !== "ipo") {
      return;
    }

    loadIpoCalendarPreview(ipoCalendarPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    ipoCalendarSubTab,
    appliedIpoCalendarSearch,
    ipoCalendarStatus,
    ipoCalendarIssueType,
    ipoCalendarIndustry,
    ipoCalendarPage
  ]);

  useEffect(() => {
    if (activeView !== "ipo_calendar" || ipoCalendarSubTab !== "ipo_scraper") {
      return;
    }

    loadIpoScraperPreview(ipoScraperPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    ipoCalendarSubTab,
    appliedIpoScraperSearch,
    ipoScraperStatus,
    ipoScraperType,
    ipoScraperPage
  ]);

  useEffect(() => {
    if (activeView !== "company_fundamentals") {
      return;
    }

    loadCompanyFundamentalsPreview(companyFundamentalsPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    appliedCompanyFundamentalsSearch,
    companyFundamentalsEndpoint,
    companyFundamentalsStatementType,
    companyFundamentalsTimePeriod,
    companyFundamentalsSegment,
    companyFundamentalsPage
  ]);

  useEffect(() => {
    if (activeView !== "ohlcv" || !isOhlcvJobRunning) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadOhlcvPreview(ohlcvPage, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, isOhlcvJobRunning, ohlcvPage]);


  useEffect(() => {
    if (activeView !== "market_calendar" || !isMarketCalendarJobRunning) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadMarketCalendarPreview(marketCalendarPage, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, isMarketCalendarJobRunning, marketCalendarPage]);


  useEffect(() => {
    if (activeView !== "equity_news" || !isEquityNewsJobRunning) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadEquityNewsPreview(equityNewsPage, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, isEquityNewsJobRunning, equityNewsPage]);

  useEffect(() => {
    if (
      activeView !== "ipo_calendar" ||
      ipoCalendarSubTab !== "ipo" ||
      !isIpoCalendarJobRunning
    ) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadIpoCalendarPreview(ipoCalendarPage, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, ipoCalendarSubTab, isIpoCalendarJobRunning, ipoCalendarPage]);

  useEffect(() => {
    if (
      activeView !== "ipo_calendar" ||
      ipoCalendarSubTab !== "ipo_scraper" ||
      !isIpoScraperJobRunning
    ) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadIpoScraperPreview(ipoScraperPage, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, ipoCalendarSubTab, isIpoScraperJobRunning, ipoScraperPage]);

  useEffect(() => {
    if (
      activeView !== "company_fundamentals" ||
      !isCompanyFundamentalsJobRunning
    ) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadCompanyFundamentalsPreview(companyFundamentalsPage, {
        showLoading: false
      });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, isCompanyFundamentalsJobRunning, companyFundamentalsPage]);

  useEffect(() => {
    if (!hasActiveJob) {
      return undefined;
    }

    const intervalId = window.setInterval(() => {
      if (summary.active_job_started_at) {
        setElapsedSeconds(
          getElapsedSecondsFromDate(summary.active_job_started_at)
        );
        return;
      }

      setElapsedSeconds((currentValue) => currentValue + 1);
    }, 1000);

    return () => window.clearInterval(intervalId);
  }, [hasActiveJob, summary.active_job_started_at]);

  useEffect(() => {
    if (!hasActiveJob) {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadData(false, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveJob]);

  useEffect(() => {
    if (hasActiveJob || activeView !== "monitor") {
      return undefined;
    }

    const pollId = window.setInterval(() => {
      loadData(false, { showLoading: false });
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeView, hasActiveJob]);

  return (
    <MainLayout>
      <section className="h-screen overflow-hidden bg-black p-3">
        <div className="flex h-full min-h-0 flex-col gap-3">
          {!isAdminControlAllowed && (
            <div className="flex shrink-0 gap-3 rounded border border-red-500/30 bg-red-950/20 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-red-500/40 bg-black text-red-300">
                <AlertTriangle size={18} />
              </div>

              <div>
                <p className={oaCardStyles.headerTitle}>
                  Admin access required
                </p>
                <p className={`mt-1 ${oaFormTextStyles.helper}`}>
                  Only admin and super admin users can run Upstox data dump jobs
                  and manage schedules.
                </p>
              </div>
            </div>
          )}

          <div className="min-h-0 flex-1">
            <DataCollectionShell
              activeView={activeView}
              onViewChange={handleViewChange}
              diskSpace={summary.disk_space}
            >
              {activeView === "monitor" ? (
                <MonitorContent
                  searchValue={monitorSearch}
                  onSearchChange={setMonitorSearch}
                  onSearchSubmit={handleMonitorSearchSubmit}
                  onClearSearch={handleClearMonitorSearch}
                  searchActive={appliedMonitorSearch.trim() !== ""}
                  hasActiveFilter={hasAnyActiveMonitorFilter()}
                  onClearAll={clearAllMonitorFilters}
                  rows={filteredDumpJobRows}
                  loading={loading}
                  onRefresh={() => loadData(true)}
                  renderCell={renderDumpJobCell}
                  renderActions={renderDumpJobActions}
                  filterConfig={{
                    activeFilter: activeMonitorFilter,
                    headerValues: monitorHeaderValues,
                    columnFilters: monitorColumnFilters,
                    draftColumnFilters: draftMonitorColumnFilters,
                    rightAlignedKeys: ["saved", "updated", "time", "last_update_status"],
                    isColumnFilterActive: isMonitorColumnFilterActive,
                    onOpen: openMonitorColumnFilter,
                    onClose: () => setActiveMonitorFilter(null),
                    onChange: (key, values) =>
                      setDraftMonitorColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyMonitorColumnFilter,
                    onSort: handleMonitorSort,
                    onClear: clearMonitorColumnFilter
                  }}
                />
              ) : null}

              {isPreviewView(activeView) ? (
                <DbPreviewContent
                  previewMode={getPreviewMode(activeView)}
                  searchValue={previewSearch}
                  onSearchChange={setPreviewSearch}
                  onSearchSubmit={handlePreviewSearchSubmit}
                  onClearSearch={handleClearPreviewSearch}
                  searchActive={appliedPreviewSearch.trim() !== ""}
                  sourceType={previewSourceType}
                  onSourceTypeChange={(value) => {
                    setPreviewSourceType(value);
                    setPreviewPage(1);
                  }}
                  onClearSourceType={clearPreviewSourceType}
                  segment={previewSegment}
                  onSegmentChange={(value) => {
                    setPreviewSegment(value);
                    setPreviewPage(1);
                  }}
                  onClearSegment={clearPreviewSegment}
                  instrumentType={previewInstrumentType}
                  onInstrumentTypeChange={(value) => {
                    setPreviewInstrumentType(value);
                    setPreviewPage(1);
                  }}
                  onClearInstrumentType={clearPreviewInstrumentType}
                  previewData={previewData}
                  rows={filteredPreviewRows}
                  loading={previewLoading}
                  runPreviewDisabled={
                    !isAdminControlAllowed ||
                    loading ||
                    previewLoading ||
                    hasActiveJob
                  }
                  onRefresh={() => loadPreview(previewPage)}
                  onRunPreview={
                    getPreviewMode(activeView) === "expired"
                      ? handleExpiredSync
                      : handleCurrentSync
                  }
                  onPreviousPage={() =>
                    setPreviewPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setPreviewPage((value) =>
                      Math.min(previewData.total_pages || 1, value + 1)
                    )
                  }
                  onPageChange={(page) => setPreviewPage(page)}
                  hasActiveFilter={hasAnyActivePreviewFilter()}
                  onClearAll={clearAllPreviewFilters}
                  filterConfig={{
                    activeFilter: activePreviewFilter,
                    headerValues: previewHeaderValues,
                    columnFilters: previewColumnFilters,
                    draftColumnFilters: draftPreviewColumnFilters,
                    rightAlignedKeys: [
                      "segment",
                      "exchange",
                      "instrument_type",
                      "expiry",
                      "strike_price",
                      "source_type",
                      "synced_at"
                    ],
                    isColumnFilterActive: isPreviewColumnFilterActive,
                    onOpen: openPreviewColumnFilter,
                    onClose: () => setActivePreviewFilter(null),
                    onChange: (key, values) =>
                      setDraftPreviewColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyPreviewColumnFilter,
                    onSort: handlePreviewSort,
                    onClear: clearPreviewColumnFilter
                  }}
                />
              ) : null}

              {activeView === "ohlcv" ? (
                <OhlcvTabContent
                  previewData={ohlcvPreviewData}
                  rows={filteredOhlcvRows}
                  loading={ohlcvLoading}
                  savingOptions={ohlcvOptionsLoading || ohlcvOptionsSaving}
                  hasActiveJob={hasActiveJob}
                  isAdminControlAllowed={isAdminControlAllowed}
                  searchValue={ohlcvSearch}
                  onSearchChange={setOhlcvSearch}
                  onSearchSubmit={handleOhlcvSearchSubmit}
                  onClearSearch={handleClearOhlcvSearch}
                  searchActive={appliedOhlcvSearch.trim() !== ""}
                  hasActiveFilter={hasAnyActiveOhlcvFilter()}
                  onClearAll={clearAllOhlcvFilters}
                  onOptions={openOhlcvOptionsPopup}
                  onSchedule={() => openSchedulePopup("ohlcv_daily")}
                  onRun={handleOhlcvSync}
                  onRefresh={() => loadOhlcvPreview(ohlcvPage)}
                  onPreviousPage={() =>
                    setOhlcvPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setOhlcvPage((value) =>
                      Math.min(ohlcvPreviewData.total_pages || 1, value + 1)
                    )
                  }
                  onPageChange={(page) => setOhlcvPage(page)}
                  renderCell={renderOhlcvCell}
                  filterConfig={{
                    activeFilter: activeOhlcvFilter,
                    headerValues: ohlcvHeaderValues,
                    columnFilters: ohlcvColumnFilters,
                    draftColumnFilters: draftOhlcvColumnFilters,
                    rightAlignedKeys: [
                      "open",
                      "high",
                      "low",
                      "close",
                      "volume",
                      "open_interest",
                      "exchange",
                      "segment",
                      "instrument_type",
                      "expiry",
                      "ingested_at"
                    ],
                    isColumnFilterActive: isOhlcvColumnFilterActive,
                    onOpen: openOhlcvColumnFilter,
                    onClose: () => setActiveOhlcvFilter(null),
                    onChange: (key, values) =>
                      setDraftOhlcvColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyOhlcvColumnFilter,
                    onSort: handleOhlcvSort,
                    onClear: clearOhlcvColumnFilter
                  }}
                />
              ) : null}


              {activeView === "equity_news" ? (
                <GenericPreviewContent
                  title="Equity News"
                  searchPlaceholder="Search equity news"
                  previewData={equityNewsPreviewData}
                  rows={filteredEquityNewsRows}
                  loading={equityNewsLoading}
                  hasActiveJob={hasActiveJob}
                  isAdminControlAllowed={isAdminControlAllowed}
                  searchValue={equityNewsSearch}
                  onSearchChange={setEquityNewsSearch}
                  onSearchSubmit={handleEquityNewsSearchSubmit}
                  onClearSearch={handleClearEquityNewsSearch}
                  searchActive={appliedEquityNewsSearch.trim() !== ""}
                  filters={[
                    {
                      value: equityNewsSegment,
                      onChange: (event) => {
                        setEquityNewsSegment(event.target.value);
                        setEquityNewsPage(1);
                      },
                      options: segmentOptions,
                      onClear: clearEquityNewsSegment,
                      showClear: equityNewsSegment !== "all",
                      ariaLabel: "Segment",
                      minWidth: "w-36"
                    }
                  ]}
                  hasActiveFilter={hasAnyActiveEquityNewsFilter()}
                  onClearAll={clearAllEquityNewsFilters}
                  onSchedule={() => openSchedulePopup("equity_news")}
                  onRun={handleEquityNewsSync}
                  onRefresh={() => loadEquityNewsPreview(equityNewsPage)}
                  onPreviousPage={() =>
                    setEquityNewsPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setEquityNewsPage((value) =>
                      Math.min(equityNewsPreviewData.total_pages || 1, value + 1)
                    )
                  }
                  onPageChange={(page) => setEquityNewsPage(page)}
                  renderCell={renderEquityNewsCell}
                  filterConfig={{
                    activeFilter: activeEquityNewsFilter,
                    headerValues: equityNewsHeaderValues,
                    columnFilters: equityNewsColumnFilters,
                    draftColumnFilters: draftEquityNewsColumnFilters,
                    rightAlignedKeys: ["segment", "source", "published_at", "ingested_at"],
                    isColumnFilterActive: isEquityNewsColumnFilterActive,
                    onOpen: openEquityNewsColumnFilter,
                    onClose: () => setActiveEquityNewsFilter(null),
                    onChange: (key, values) =>
                      setDraftEquityNewsColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyEquityNewsColumnFilter,
                    onSort: handleEquityNewsSort,
                    onClear: clearEquityNewsColumnFilter
                  }}
                  columns={equityNewsPreviewColumns}
                  gridTemplateColumns={equityNewsPreviewGridTemplateColumns}
                  minWidth="min-w-[2830px]"
                  emptyMessage="No equity news found."
                  getRowKey={(row, index) =>
                    `${row.news_id || row.article_link || row.instrument_key || "news"}-${index}`
                  }
                />
              ) : null}

              {activeView === "ipo_calendar" ? (
                <IpoCalendarTabContent
                  activeSubTab={ipoCalendarSubTab}
                  onSubTabChange={(value) => {
                    setIpoCalendarSubTab(value);

                    if (value === "ipo") {
                      setIpoCalendarPage(1);
                      setIpoCalendarPreviewData(emptyPreviewData);
                    } else {
                      setIpoScraperPage(1);
                      setIpoScraperPreviewData(emptyPreviewData);
                    }
                  }}
                >
                  {ipoCalendarSubTab === "ipo" ? (
                    <GenericPreviewContent
                      title="IPO"
                      searchPlaceholder="Search IPO calendar"
                      previewData={ipoCalendarPreviewData}
                      rows={filteredIpoCalendarRows}
                      loading={ipoCalendarLoading}
                      hasActiveJob={hasActiveJob}
                      isAdminControlAllowed={isAdminControlAllowed}
                      searchValue={ipoCalendarSearch}
                      onSearchChange={setIpoCalendarSearch}
                      onSearchSubmit={handleIpoCalendarSearchSubmit}
                      onClearSearch={handleClearIpoCalendarSearch}
                      searchActive={appliedIpoCalendarSearch.trim() !== ""}
                      filters={[
                        {
                          value: ipoCalendarStatus,
                          onChange: (event) => {
                            setIpoCalendarStatus(event.target.value);
                            setIpoCalendarPage(1);
                          },
                          options: ipoStatusOptions,
                          onClear: clearIpoCalendarStatus,
                          showClear: ipoCalendarStatus !== "all",
                          ariaLabel: "IPO status",
                          minWidth: "w-36"
                        },
                        {
                          value: ipoCalendarIssueType,
                          onChange: (event) => {
                            setIpoCalendarIssueType(event.target.value);
                            setIpoCalendarPage(1);
                          },
                          options: ipoIssueTypeOptions,
                          onClear: clearIpoCalendarIssueType,
                          showClear: ipoCalendarIssueType !== "all",
                          ariaLabel: "Issue type",
                          minWidth: "w-40"
                        },
                        {
                          value: ipoCalendarIndustry,
                          onChange: (event) => {
                            setIpoCalendarIndustry(event.target.value);
                            setIpoCalendarPage(1);
                          },
                          options: ipoIndustryOptions,
                          onClear: clearIpoCalendarIndustry,
                          showClear: ipoCalendarIndustry !== "all",
                          ariaLabel: "Industry",
                          minWidth: "w-40"
                        }
                      ]}
                      hasActiveFilter={hasAnyActiveIpoCalendarFilter()}
                      onClearAll={clearAllIpoCalendarFilters}
                      onSchedule={() => openSchedulePopup("ipo_calendar")}
                      onRun={handleIpoCalendarSync}
                      onRefresh={() => loadIpoCalendarPreview(ipoCalendarPage)}
                      onPreviousPage={() =>
                        setIpoCalendarPage((value) => Math.max(1, value - 1))
                      }
                      onNextPage={() =>
                        setIpoCalendarPage((value) =>
                          Math.min(ipoCalendarPreviewData.total_pages || 1, value + 1)
                        )
                      }
                      onPageChange={(page) => setIpoCalendarPage(page)}
                      renderCell={renderIpoCalendarCell}
                      filterConfig={{
                        activeFilter: activeIpoCalendarFilter,
                        headerValues: ipoCalendarHeaderValues,
                        columnFilters: ipoCalendarColumnFilters,
                        draftColumnFilters: draftIpoCalendarColumnFilters,
                        rightAlignedKeys: [
                          "status",
                          "issue_type",
                          "issue_size",
                          "minimum_price",
                          "maximum_price",
                          "bidding_start_date",
                          "bidding_end_date",
                          "total_subscription",
                          "synced_at"
                        ],
                        isColumnFilterActive: isIpoCalendarColumnFilterActive,
                        onOpen: openIpoCalendarColumnFilter,
                        onClose: () => setActiveIpoCalendarFilter(null),
                        onChange: (key, values) =>
                          setDraftIpoCalendarColumnFilters((previous) => ({
                            ...previous,
                            [key]: values
                          })),
                        onApply: applyIpoCalendarColumnFilter,
                        onSort: handleIpoCalendarSort,
                        onClear: clearIpoCalendarColumnFilter
                      }}
                      columns={ipoCalendarPreviewColumns}
                      gridTemplateColumns={ipoCalendarPreviewGridTemplateColumns}
                      minWidth="min-w-[2730px]"
                      emptyMessage="No IPO records found."
                      getRowKey={(row, index) =>
                        `${row.ipo_id || row.id || row.symbol || "ipo"}-${index}`
                      }
                    />
                  ) : null}

                  {ipoCalendarSubTab === "ipo_scraper" ? (
                    <GenericPreviewContent
                      title="IPO Scrapper"
                      searchPlaceholder="Search IPO scrapper"
                      previewData={ipoScraperPreviewData}
                      rows={filteredIpoScraperRows}
                      loading={ipoScraperLoading}
                      hasActiveJob={hasActiveJob}
                      isAdminControlAllowed={isAdminControlAllowed}
                      searchValue={ipoScraperSearch}
                      onSearchChange={setIpoScraperSearch}
                      onSearchSubmit={handleIpoScraperSearchSubmit}
                      onClearSearch={handleClearIpoScraperSearch}
                      searchActive={appliedIpoScraperSearch.trim() !== ""}
                      filters={[
                        {
                          value: ipoScraperStatus,
                          onChange: (event) => {
                            setIpoScraperStatus(event.target.value);
                            setIpoScraperPage(1);
                          },
                          options: ipoStatusOptions,
                          onClear: clearIpoScraperStatus,
                          showClear: ipoScraperStatus !== "all",
                          ariaLabel: "IPO scraper status",
                          minWidth: "w-36"
                        },
                        {
                          value: ipoScraperType,
                          onChange: (event) => {
                            setIpoScraperType(event.target.value);
                            setIpoScraperPage(1);
                          },
                          options: ipoIssueTypeOptions,
                          onClear: clearIpoScraperType,
                          showClear: ipoScraperType !== "all",
                          ariaLabel: "IPO scraper type",
                          minWidth: "w-40"
                        }
                      ]}
                      hasActiveFilter={hasAnyActiveIpoScraperFilter()}
                      onClearAll={clearAllIpoScraperFilters}
                      onSchedule={() => openSchedulePopup("ipo_scraper")}
                      onRun={handleIpoScraperSync}
                      onRefresh={() => loadIpoScraperPreview(ipoScraperPage)}
                      onPreviousPage={() =>
                        setIpoScraperPage((value) => Math.max(1, value - 1))
                      }
                      onNextPage={() =>
                        setIpoScraperPage((value) =>
                          Math.min(ipoScraperPreviewData.total_pages || 1, value + 1)
                        )
                      }
                      onPageChange={(page) => setIpoScraperPage(page)}
                      renderCell={renderIpoScraperCell}
                      filterConfig={{
                        activeFilter: activeIpoScraperFilter,
                        headerValues: ipoScraperHeaderValues,
                        columnFilters: ipoScraperColumnFilters,
                        draftColumnFilters: draftIpoScraperColumnFilters,
                        rightAlignedKeys: [
                          "ipo_gmp",
                          "price_band",
                          "gain",
                          "ipo_date",
                          "ipo_type",
                          "ipo_status",
                          "last_updated",
                          "scraped_at",
                          "updated_at"
                        ],
                        isColumnFilterActive: isIpoScraperColumnFilterActive,
                        onOpen: openIpoScraperColumnFilter,
                        onClose: () => setActiveIpoScraperFilter(null),
                        onChange: (key, values) =>
                          setDraftIpoScraperColumnFilters((previous) => ({
                            ...previous,
                            [key]: values
                          })),
                        onApply: applyIpoScraperColumnFilter,
                        onSort: handleIpoScraperSort,
                        onClear: clearIpoScraperColumnFilter
                      }}
                      columns={ipoScraperPreviewColumns}
                      gridTemplateColumns={ipoScraperPreviewGridTemplateColumns}
                      minWidth="min-w-[1810px]"
                      emptyMessage="No IPO scrapper records found."
                      getRowKey={(row, index) =>
                        `${row.ipo_name || row.ipo_id || "ipo-scraper"}-${index}`
                      }
                    />
                  ) : null}
                </IpoCalendarTabContent>
              ) : null}

              {activeView === "company_fundamentals" ? (
                <CompanyFundamentalsContent
                  activeEndpoint={companyFundamentalsEndpoint}
                  onEndpointChange={(value) => {
                    setCompanyFundamentalsEndpoint(value);
                    setCompanyFundamentalsPage(1);
                  }}
                  previewData={companyFundamentalsPreviewData}
                  rows={filteredCompanyFundamentalsRows}
                  loading={companyFundamentalsLoading}
                  hasActiveJob={hasActiveJob}
                  isAdminControlAllowed={isAdminControlAllowed}
                  searchValue={companyFundamentalsSearch}
                  onSearchChange={setCompanyFundamentalsSearch}
                  onSearchSubmit={handleCompanyFundamentalsSearchSubmit}
                  onClearSearch={handleClearCompanyFundamentalsSearch}
                  searchActive={appliedCompanyFundamentalsSearch.trim() !== ""}
                  statementType={companyFundamentalsStatementType}
                  onStatementTypeChange={(value) => {
                    setCompanyFundamentalsStatementType(value);
                    setCompanyFundamentalsPage(1);
                  }}
                  onClearStatementType={clearCompanyFundamentalsStatementType}
                  timePeriod={companyFundamentalsTimePeriod}
                  onTimePeriodChange={(value) => {
                    setCompanyFundamentalsTimePeriod(value);
                    setCompanyFundamentalsPage(1);
                  }}
                  onClearTimePeriod={clearCompanyFundamentalsTimePeriod}
                  segment={companyFundamentalsSegment}
                  onSegmentChange={(value) => {
                    setCompanyFundamentalsSegment(value);
                    setCompanyFundamentalsPage(1);
                  }}
                  onClearSegment={clearCompanyFundamentalsSegment}
                  hasActiveFilter={hasAnyActiveCompanyFundamentalsFilter()}
                  onClearAll={clearAllCompanyFundamentalsFilters}
                  onSchedule={() => openSchedulePopup("company_fundamentals")}
                  onRun={handleCompanyFundamentalsSync}
                  onRefresh={() =>
                    loadCompanyFundamentalsPreview(companyFundamentalsPage)
                  }
                  onPreviousPage={() =>
                    setCompanyFundamentalsPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setCompanyFundamentalsPage((value) =>
                      Math.min(
                        companyFundamentalsPreviewData.total_pages || 1,
                        value + 1
                      )
                    )
                  }
                  onPageChange={(page) => setCompanyFundamentalsPage(page)}
                  renderCell={renderCompanyFundamentalsCell}
                  filterConfig={{
                    activeFilter: activeCompanyFundamentalsFilter,
                    headerValues: companyFundamentalsHeaderValues,
                    columnFilters: companyFundamentalsColumnFilters,
                    draftColumnFilters: draftCompanyFundamentalsColumnFilters,
                    rightAlignedKeys:
                      activeCompanyFundamentalsColumnGroup.rightAlignedKeys,
                    isColumnFilterActive: isCompanyFundamentalsColumnFilterActive,
                    onOpen: openCompanyFundamentalsColumnFilter,
                    onClose: () => setActiveCompanyFundamentalsFilter(null),
                    onChange: (key, values) =>
                      setDraftCompanyFundamentalsColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyCompanyFundamentalsColumnFilter,
                    onSort: handleCompanyFundamentalsSort,
                    onClear: clearCompanyFundamentalsColumnFilter
                  }}
                  columns={activeCompanyFundamentalsColumnGroup.columns}
                  gridTemplateColumns={
                    activeCompanyFundamentalsColumnGroup.gridTemplateColumns
                  }
                  minWidth={activeCompanyFundamentalsColumnGroup.minWidth}
                />
              ) : null}

              {activeView === "market_calendar" ? (
                <MarketCalendarContent
                  previewData={marketCalendarPreviewData}
                  rows={filteredMarketCalendarRows}
                  loading={marketCalendarLoading}
                  hasActiveJob={hasActiveJob}
                  isAdminControlAllowed={isAdminControlAllowed}
                  searchValue={marketCalendarSearch}
                  onSearchChange={setMarketCalendarSearch}
                  onSearchSubmit={handleMarketCalendarSearchSubmit}
                  onClearSearch={handleClearMarketCalendarSearch}
                  searchActive={appliedMarketCalendarSearch.trim() !== ""}
                  holidayType={marketCalendarHolidayType}
                  onHolidayTypeChange={(value) => {
                    setMarketCalendarHolidayType(value);
                    setMarketCalendarPage(1);
                  }}
                  onClearHolidayType={clearMarketCalendarHolidayType}
                  exchange={marketCalendarExchange}
                  onExchangeChange={(value) => {
                    setMarketCalendarExchange(value);
                    setMarketCalendarPage(1);
                  }}
                  onClearExchange={clearMarketCalendarExchange}
                  tradingStatus={marketCalendarTradingStatus}
                  onTradingStatusChange={(value) => {
                    setMarketCalendarTradingStatus(value);
                    setMarketCalendarPage(1);
                  }}
                  onClearTradingStatus={clearMarketCalendarTradingStatus}
                  hasActiveFilter={hasAnyActiveMarketCalendarFilter()}
                  onClearAll={clearAllMarketCalendarFilters}
                  onSchedule={() => openSchedulePopup("market_holidays")}
                  onRun={handleMarketCalendarSync}
                  onRefresh={() => loadMarketCalendarPreview(marketCalendarPage)}
                  onPreviousPage={() =>
                    setMarketCalendarPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setMarketCalendarPage((value) =>
                      Math.min(
                        marketCalendarPreviewData.total_pages || 1,
                        value + 1
                      )
                    )
                  }
                  onPageChange={(page) => setMarketCalendarPage(page)}
                  renderCell={renderMarketCalendarCell}
                  filterConfig={{
                    activeFilter: activeMarketCalendarFilter,
                    headerValues: marketCalendarHeaderValues,
                    columnFilters: marketCalendarColumnFilters,
                    draftColumnFilters: draftMarketCalendarColumnFilters,
                    rightAlignedKeys: [
                      "holiday_type",
                      "is_trading_day",
                      "source_provider",
                      "synced_at",
                      "updated_at"
                    ],
                    isColumnFilterActive: isMarketCalendarColumnFilterActive,
                    onOpen: openMarketCalendarColumnFilter,
                    onClose: () => setActiveMarketCalendarFilter(null),
                    onChange: (key, values) =>
                      setDraftMarketCalendarColumnFilters((previous) => ({
                        ...previous,
                        [key]: values
                      })),
                    onApply: applyMarketCalendarColumnFilter,
                    onSort: handleMarketCalendarSort,
                    onClear: clearMarketCalendarColumnFilter
                  }}
                />
              ) : null}
            </DataCollectionShell>
          </div>
        </div>

        <OhlcvOptionsModal
          open={ohlcvOptionsOpen}
          formData={ohlcvFormData}
          saving={ohlcvOptionsLoading || ohlcvOptionsSaving}
          onClose={closeOhlcvOptionsPopup}
          onChange={handleOhlcvFormChange}
          onMultiChange={handleOhlcvMultiChange}
          onSave={handleSaveOhlcvOptions}
        />

        <ScheduleManagerModal
          open={Boolean(selectedScheduleJob)}
          title={selectedScheduleTitle}
          schedules={selectedSchedules}
          formMode={scheduleFormMode}
          formData={scheduleFormData}
          saving={savingSchedule || schedulerLoading}
          savingScheduleId={savingScheduleId}
          deletingScheduleId={deletingScheduleId}
          isAdminControlAllowed={isAdminControlAllowed}
          onClose={closeSchedulePopup}
          onSave={handleSaveSchedule}
          onInputChange={handleScheduleFormChange}
          onTimePartChange={handleScheduleTimePartChange}
          onClearField={handleClearScheduleField}
          onEdit={handleEditSchedule}
          onCancelEdit={handleCancelScheduleEdit}
          onToggle={handleToggleSchedule}
          onDelete={handleDeleteSchedule}
        />
      </section>
    </MainLayout>
  );
}

export default DataCollection;
