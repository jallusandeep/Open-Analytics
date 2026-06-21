import { scheduleFrequencyOptions } from "./constants";

export function getStoredCurrentUser() {
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

export function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "0";
  }

  return Number(value).toLocaleString("en-IN");
}

export function formatCompactNumber(value) {
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

export function formatBytes(value) {
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

export function formatDuration(seconds) {
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

export function formatDateTime(value) {
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

export function normalizeCellValue(value) {
  if (value === null || value === undefined || value === "") {
    return "--";
  }

  return String(value);
}

export function getFilterValues(rows, key, getValue) {
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

export function applyColumnFilters(rows, columnFilters, getValue) {
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

export function applySort(rows, sortConfig, getValue) {
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

export function getDumpJobColumnValue(row, key) {
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

export function getPreviewColumnValue(row, key) {
  if (key === "synced_at") {
    return formatDateTime(row.synced_at);
  }

  if (key === "source_type") {
    return getSyncTypeLabel(row.source_type);
  }

  return row[key];
}

export function parseMaybeJsonArray(value) {
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

export function formatOhlcvList(value) {
  const values = parseMaybeJsonArray(value);

  if (values.length === 0) {
    return "--";
  }

  return values
    .map((item) => getSyncTypeLabel(item))
    .join(", ");
}

export function formatPrice(value) {
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

export function getOhlcvColumnValue(row, key) {
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

export function formatJsonListCell(value, displayKey = "exchange") {
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

export function getMarketHolidayColumnValue(row, key) {
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

export function getEquityNewsColumnValue(row, key) {
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

export function getIpoCalendarColumnValue(row, key) {
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

export function getIpoScraperColumnValue(row, key) {
  if (key === "scraped_at" || key === "updated_at") {
    return formatDateTime(row[key]);
  }

  if (key === "ipo_type" || key === "ipo_status") {
    return getSyncTypeLabel(row[key]);
  }

  return row[key];
}

export function getCompanyFundamentalsColumnValue(row, key) {
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

export function getElapsedSecondsFromDate(value) {
  if (!value) {
    return 0;
  }

  const startedAt = new Date(value);

  if (Number.isNaN(startedAt.getTime())) {
    return 0;
  }

  return Math.max(0, Math.floor((Date.now() - startedAt.getTime()) / 1000));
}

export function isRequestCancelled(error) {
  return (
    error?.name === "CanceledError" ||
    error?.code === "ERR_CANCELED" ||
    error?.message === "canceled"
  );
}

export function getApiErrorMessage(error, fallbackMessage) {
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

export function getSyncTypeLabel(value) {
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

export function getQueuedDumpJobId(jobName) {
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

export function getStatusClass(status) {
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

export function getStatusLabel(status) {
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

export function getLatestRunByTypes(runs, syncTypes = []) {
  return runs.find((run) => syncTypes.includes(run.sync_type)) || null;
}

export function isPreviewView(activeView) {
  return activeView === "current_preview" || activeView === "expired_preview";
}

export function getPreviewMode(activeView) {
  if (activeView === "expired_preview") {
    return "expired";
  }

  return "current";
}

export function getPaginationItems(currentPage, totalPages) {
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

export function formatScheduleTime(schedule) {
  if (!schedule) {
    return "--";
  }

  if (schedule.time_format === "12") {
    return schedule.schedule_label || schedule.schedule_time || "--";
  }

  return schedule.schedule_time || "--";
}

export function formatScheduleFrequency(scheduleFrequency) {
  const option = scheduleFrequencyOptions.find(
    (item) => item.value === String(scheduleFrequency || "").toLowerCase()
  );

  return option?.label || "Daily";
}

export function getScheduleTimeParts(scheduleTime) {
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

export function buildScheduleTimeFrom12Hour(hourValue, minuteValue, periodValue) {
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
