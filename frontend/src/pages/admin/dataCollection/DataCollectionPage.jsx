import { useEffect, useMemo, useRef, useState } from "react";
import { AlertTriangle, Clock3, Edit3, Play, RefreshCcw } from "lucide-react";

import MainLayout from "../../../components/layout/MainLayout";
import { useToast } from "../../../components/common/ToastProvider";
import { oaCardStyles, oaFormTextStyles } from "../../../components/common/uiStyles";
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
} from "../../../api/dataCollectionApi";
import {
  emptySummary,
  emptyPreviewData,
  DATA_COLLECTION_PREVIEW_PAGE_SIZE,
  emptyScheduleForm,
  emptyOhlcvForm,
  viewOptions,
  timeFormatOptions,
  scheduleFrequencyOptions,
  timePeriodOptions,
  currentSourceTypeOptions,
  expiredSourceTypeOptions,
  segmentOptions,
  instrumentTypeOptions,
  ohlcvSourceOptions,
  ohlcvModeOptions,
  ohlcvIntervalOptions,
  marketHolidayTypeOptions,
  marketHolidayExchangeOptions,
  marketHolidayTradingStatusOptions,
  ipoCalendarSubTabOptions,
  ipoStatusOptions,
  ipoIssueTypeOptions,
  ipoIndustryOptions,
  companyFundamentalsEndpointOptions,
  companyFundamentalsStatementTypeOptions,
  companyFundamentalsTimePeriodOptions,
  dumpJobColumns,
  dumpJobGridTemplateColumns,
  scheduleColumns,
  scheduleGridTemplateColumns,
  previewColumns,
  previewGridTemplateColumns,
  ohlcvPreviewColumns,
  ohlcvPreviewGridTemplateColumns,
  marketHolidayPreviewColumns,
  marketHolidayPreviewGridTemplateColumns,
  equityNewsPreviewColumns,
  equityNewsPreviewGridTemplateColumns,
  ipoCalendarPreviewColumns,
  ipoCalendarPreviewGridTemplateColumns,
  ipoScraperPreviewColumns,
  ipoScraperPreviewGridTemplateColumns,
  companyFundamentalsColumnGroups,
  defaultCompanyFundamentalsColumnGroup
} from "./constants";
import {
  getStoredCurrentUser,
  formatNumber,
  formatCompactNumber,
  formatBytes,
  formatDuration,
  formatDateTime,
  normalizeCellValue,
  getFilterValues,
  applyColumnFilters,
  applySort,
  getDumpJobColumnValue,
  getPreviewColumnValue,
  parseMaybeJsonArray,
  formatOhlcvList,
  formatPrice,
  getOhlcvColumnValue,
  formatJsonListCell,
  getMarketHolidayColumnValue,
  getEquityNewsColumnValue,
  getIpoCalendarColumnValue,
  getIpoScraperColumnValue,
  getCompanyFundamentalsColumnValue,
  getElapsedSecondsFromDate,
  isRequestCancelled,
  getApiErrorMessage,
  getSyncTypeLabel,
  getQueuedDumpJobId,
  getStatusClass,
  getStatusLabel,
  getLatestRunByTypes,
  isPreviewView,
  getPreviewMode,
  getPaginationItems,
  formatScheduleTime,
  formatScheduleFrequency,
  getScheduleTimeParts,
  buildScheduleTimeFrom12Hour
} from "./helpers";
import {
  ViewToggle,
  StatusBadge,
  ClearInputButton,
  DumpJobActions,
  DataCollectionShell,
  ScheduleManagerModal,
  MonitorContent,
  DbPreviewContent,
  CheckboxGroup,
  OhlcvOptionsModal,
  MarketCalendarContent,
  GenericPreviewContent,
  OhlcvTabContent,
  IpoCalendarTabContent,
  CompanyFundamentalsContent,
  PaginationFooter
} from "./components";

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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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

      if (response.data?.status === "started" || response.data?.status === "queued") {
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
    }, isCancelRequested ? 1000 : 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveJob, isCancelRequested]);

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
