import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  Database,
  DownloadCloud,
  Eye,
  Play,
  RefreshCcw,
  Search,
  X,
  XCircle
} from "lucide-react";

import MainLayout from "../../components/layout/MainLayout";
import Spinner from "../../components/common/Spinner";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Select from "../../components/common/Select";
import Tooltip from "../../components/common/Tooltip";
import DataTable from "../../components/tables/DataTable";
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
  oaFormTextStyles,
  oaPillStyles,
  oaTableStyles
} from "../../components/common/uiStyles";
import {
  cancelUpstoxDataCollection,
  getUpstoxDataCollectionRuns,
  getUpstoxDataCollectionSummary,
  getUpstoxExpiredInstrumentsPreview,
  getUpstoxInstrumentsPreview,
  syncUpstoxAllInstruments,
  syncUpstoxCurrentInstruments,
  syncUpstoxExpiredInstruments
} from "../../api/dataCollectionApi";

const emptySummary = {
  connection_status: "not_connected",
  total_current_instruments: 0,
  total_expired_instruments: 0,
  total_sync_runs: 0,
  last_sync_at: "",
  last_duration_seconds: null,
  current_last_sync_at: "",
  current_duration_seconds: null,
  expired_last_sync_at: "",
  expired_duration_seconds: null,
  active_job: null,
  active_job_status: null,
  active_job_started_at: null
};

const emptyPreviewData = {
  rows: [],
  page: 1,
  page_size: 50,
  total_pages: 1,
  total_records: 0
};

const viewOptions = [
  {
    key: "monitor",
    label: "Collection Monitor",
    icon: DownloadCloud
  },
  {
    key: "preview",
    label: "DB Preview",
    icon: Eye
  }
];

const previewSourceOptions = [
  { value: "current", label: "Current Instruments" },
  { value: "expired", label: "Expired Instruments" }
];

const sourceTypeOptions = [
  { value: "all", label: "All Sources" },
  { value: "bod_complete", label: "BOD Complete" },
  { value: "suspended", label: "Suspended" },
  { value: "expired_option", label: "Expired Options" },
  { value: "expired_future", label: "Expired Futures" }
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

const dumpJobColumns = [
  { key: "source", label: "Source", filterable: false },
  { key: "saved", label: "Saved", filterable: false },
  { key: "updated", label: "Updated", filterable: false },
  { key: "time", label: "Time", filterable: false },
  { key: "last_update_status", label: "Last Update Status", filterable: false }
];

const dumpJobGridTemplateColumns =
  "1.4fr 0.6fr 0.75fr 0.55fr 0.75fr 112px";

const previewColumns = [
  { key: "instrument_key", label: "Instrument Key", filterable: false },
  { key: "trading_symbol", label: "Trading Symbol", filterable: false },
  { key: "name", label: "Name", filterable: false },
  { key: "segment", label: "Segment", filterable: false },
  { key: "exchange", label: "Exchange", filterable: false },
  { key: "instrument_type", label: "Type", filterable: false },
  { key: "expiry", label: "Expiry", filterable: false },
  { key: "strike_price", label: "Strike", filterable: false },
  { key: "source_type", label: "Source", filterable: false },
  { key: "synced_at", label: "Synced At", filterable: false }
];

const previewGridTemplateColumns =
  "1.65fr 1fr 1.25fr 0.75fr 0.75fr 0.7fr 0.75fr 0.7fr 0.9fr 1fr";

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

function getSyncTypeLabel(value) {
  const labels = {
    upstox_current_instruments: "Current Instruments",
    upstox_expired_instruments: "Expired Instruments",
    upstox_all_instruments: "All Instruments",
    upstox_instruments: "All Instruments",
    bod_complete: "BOD Complete",
    suspended: "Suspended",
    expired_option: "Expired Options",
    expired_future: "Expired Futures"
  };

  return labels[value] || value || "--";
}

function getStatusClass(status) {
  if (status === "success" || status === "connected") {
    return "border-emerald-500/40 bg-emerald-950/50 text-emerald-200";
  }

  if (status === "running" || status === "cancel_requested") {
    return "border-cyan-500/40 bg-cyan-950/50 text-cyan-200";
  }

  if (status === "failed" || status === "cancelled") {
    return "border-red-500/40 bg-red-950/50 text-red-200";
  }

  if (status === "saved") {
    return "border-sky-500/40 bg-sky-950/50 text-sky-200";
  }

  return "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function getStatusLabel(status) {
  if (status === "success") {
    return "Success";
  }

  if (status === "running") {
    return "Running";
  }

  if (status === "cancel_requested") {
    return "Cancelling";
  }

  if (status === "cancelled") {
    return "Cancelled";
  }

  if (status === "failed") {
    return "Failed";
  }

  return status || "Idle";
}

function getLatestRunByTypes(runs, syncTypes = []) {
  return runs.find((run) => syncTypes.includes(run.sync_type)) || null;
}

function ViewToggle({ activeView, onChange }) {
  return (
    <div className="flex items-center gap-1">
      {viewOptions.map((option) => {
        const Icon = option.icon;
        const isActive = activeView === option.key;

        return (
          <button
            key={option.key}
            type="button"
            onClick={() => onChange(option.key)}
            className={`flex h-7 items-center gap-1.5 border-b px-2.5 text-[12px] transition ${
              isActive
                ? "border-cyan-400 text-white"
                : "border-transparent text-oa-muted hover:border-oa-border hover:text-white"
            }`}
          >
            <Icon
              size={13}
              className={isActive ? "text-cyan-300" : "text-oa-muted"}
            />
            {option.label}
          </button>
        );
      })}
    </div>
  );
}

function PreviewSourceToggle({ value, onChange }) {
  return (
    <div className="flex items-center gap-1">
      {previewSourceOptions.map((option) => {
        const isActive = value === option.value;

        return (
          <button
            key={option.value}
            type="button"
            onClick={() => onChange(option.value)}
            className={`flex h-7 items-center border-b px-2.5 text-[12px] transition ${
              isActive
                ? "border-emerald-400 text-white"
                : "border-transparent text-oa-muted hover:border-oa-border hover:text-white"
            }`}
          >
            {option.label}
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

function DumpJobActions({
  title,
  loading,
  disabled,
  canCancel,
  cancelling,
  onRun,
  onCancel
}) {
  return (
    <div className="flex justify-end gap-2">
      <Tooltip text={loading ? `${title} running` : `Run ${title}`} side="left">
        <button
          type="button"
          disabled={disabled || loading}
          onClick={onRun}
          className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
          aria-label={`Run ${title}`}
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
  loading,
  previewLoading,
  shouldShowRunAllButton,
  isAdminControlAllowed,
  onBulkSync,
  onRefresh,
  children
}) {
  return (
    <div className="overflow-hidden rounded border border-oa-border bg-black shadow-2xl">
      <div className="flex items-center gap-3 border-b border-oa-border bg-oa-panel px-4 py-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-sky-500/25 bg-sky-950/20 text-sky-300">
          <Database size={18} />
        </div>

        <div className="min-w-0">
          <h2 className="truncate text-[15px] font-bold text-white">
            Data Collection
          </h2>
          <p className="mt-0.5 truncate text-[12px] text-oa-muted">
            Track Upstox instrument dumps, expired contracts, sync duration, and
            saved database records.
          </p>
        </div>
      </div>

      <div className="flex flex-col gap-2 border-b border-oa-border bg-black px-3 py-1.5 md:flex-row md:items-center md:justify-between">
        <ViewToggle activeView={activeView} onChange={onViewChange} />

        <div className="flex flex-wrap items-center gap-2">
          {shouldShowRunAllButton && (
            <Tooltip text="Run all dumps" side="top">
              <button
                type="button"
                disabled={!isAdminControlAllowed || loading}
                onClick={onBulkSync}
                className="flex h-8 w-8 items-center justify-center rounded border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Run all data collection dumps"
              >
                <DownloadCloud size={14} />
              </button>
            </Tooltip>
          )}

          <IconButton
            icon={RefreshCcw}
            label="Refresh"
            variant="refresh"
            disabled={loading || previewLoading}
            onClick={onRefresh}
            tooltipSide="top"
          />
        </div>
      </div>

      {children}
    </div>
  );
}

function DbPreviewContent({
  previewType,
  onPreviewTypeChange,
  searchValue,
  onSearchChange,
  onSearchSubmit,
  onClearSearch,
  sourceType,
  onSourceTypeChange,
  segment,
  onSegmentChange,
  instrumentType,
  onInstrumentTypeChange,
  previewData,
  loading,
  onRefresh,
  onPreviousPage,
  onNextPage
}) {
  function renderPreviewCell(row, column) {
    if (column.key === "source_type") {
      return (
        <span
          className={`${oaPillStyles.base} border-zinc-600 bg-zinc-900 text-zinc-200`}
        >
          {getSyncTypeLabel(row.source_type)}
        </span>
      );
    }

    if (column.key === "synced_at") {
      return (
        <span className="truncate oa-code-font text-oa-muted">
          {formatDateTime(row.synced_at)}
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

    if (column.key === "name") {
      return <span className="truncate text-white">{row.name || "--"}</span>;
    }

    if (column.key === "strike_price") {
      return (
        <span className="truncate oa-code-font text-white">
          {row.strike_price ?? "--"}
        </span>
      );
    }

    const mutedKeys = ["segment", "exchange"];

    return (
      <span
        className={`truncate oa-code-font ${
          mutedKeys.includes(column.key) ? "text-oa-muted" : "text-white"
        }`}
      >
        {row[column.key] || "--"}
      </span>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-2 border-b border-oa-border bg-black px-3 py-1.5 xl:flex-row xl:items-center xl:justify-between">
        <form
          onSubmit={onSearchSubmit}
          className="flex flex-wrap items-center gap-2"
        >
          <div className="relative w-full md:w-80">
            <Input
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search key, symbol, name, segment"
              className="pr-9"
            />

            {searchValue ? (
              <button
                type="button"
                onClick={onClearSearch}
                className="absolute right-2 top-1/2 flex h-5 w-5 -translate-y-1/2 items-center justify-center rounded text-oa-muted transition hover:bg-oa-card hover:text-white"
                aria-label="Clear search"
              >
                <X size={13} />
              </button>
            ) : null}
          </div>

          <Select
            value={sourceType}
            onChange={(event) => onSourceTypeChange(event.target.value)}
            options={sourceTypeOptions}
            ariaLabel="Source type"
            minWidth="w-40"
          />

          <Select
            value={segment}
            onChange={(event) => onSegmentChange(event.target.value)}
            options={segmentOptions}
            ariaLabel="Segment"
            minWidth="w-36"
          />

          <Select
            value={instrumentType}
            onChange={(event) => onInstrumentTypeChange(event.target.value)}
            options={instrumentTypeOptions}
            ariaLabel="Instrument type"
            minWidth="w-36"
          />

          <Tooltip text="Search preview" side="top">
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded border border-sky-500/30 bg-sky-950/20 text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500"
              aria-label="Search preview"
            >
              <Search size={14} />
            </button>
          </Tooltip>
        </form>

        <div className="flex items-center gap-2">
          <PreviewSourceToggle
            value={previewType}
            onChange={onPreviewTypeChange}
          />

          <IconButton
            icon={RefreshCcw}
            label="Refresh preview"
            variant="refresh"
            disabled={loading}
            onClick={onRefresh}
            tooltipSide="left"
          />
        </div>
      </div>

      <div className="overflow-x-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        <DataTable
          columns={previewColumns}
          rows={previewData.rows}
          loading={loading}
          loadingMessage="Loading DB preview"
          emptyMessage="No dumped records found."
          gridTemplateColumns={previewGridTemplateColumns}
          minWidth="min-w-[1380px]"
          getRowKey={(row, index) => `${row.instrument_key || index}-${index}`}
          renderCell={renderPreviewCell}
        />
      </div>

      <div
        className={`flex flex-col gap-2 border-t border-oa-border bg-black px-3 py-2 md:flex-row md:items-center md:justify-between ${oaTableStyles.mutedText}`}
      >
        <span>
          Records: {formatNumber(previewData.total_records)} | Page{" "}
          {previewData.page} of {previewData.total_pages}
        </span>

        <div className="flex items-center gap-2">
          <IconButton
            icon={ChevronLeft}
            label="Previous"
            variant="default"
            disabled={previewData.page <= 1 || loading}
            onClick={onPreviousPage}
            tooltipSide="top"
          />

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
    </>
  );
}

function DataCollection() {
  const [activeView, setActiveView] = useState("monitor");
  const [summary, setSummary] = useState(emptySummary);
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [runningJob, setRunningJob] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelRequested, setCancelRequested] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  const activeSyncControllerRef = useRef(null);

  const [previewType, setPreviewType] = useState("current");
  const [previewSearch, setPreviewSearch] = useState("");
  const [appliedPreviewSearch, setAppliedPreviewSearch] = useState("");
  const [previewSourceType, setPreviewSourceType] = useState("all");
  const [previewSegment, setPreviewSegment] = useState("all");
  const [previewInstrumentType, setPreviewInstrumentType] = useState("all");
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize] = useState(50);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(emptyPreviewData);

  const { showToast } = useToast();

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  const hasActiveJob = Boolean(runningJob || summary.active_job);
  const isCancelRequested =
    cancelRequested || summary.active_job_status === "cancel_requested";

  const isBulkJobRunning =
    runningJob === "bulk" || summary.active_job === "upstox_all_instruments";

  const isCurrentJobRunning =
    !isCancelRequested &&
    (runningJob === "current" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_current_instruments");

  const isExpiredJobRunning =
    !isCancelRequested &&
    (runningJob === "expired" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_expired_instruments");

  const currentCancelRequested =
    isCancelRequested &&
    (runningJob === "current" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_current_instruments" ||
      summary.active_job === "upstox_all_instruments");

  const expiredCancelRequested =
    isCancelRequested &&
    (runningJob === "expired" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_expired_instruments" ||
      summary.active_job === "upstox_all_instruments");

  const shouldShowRunAllButton = !hasActiveJob;
  const shouldShowCancelButton = hasActiveJob && !isCancelRequested;

  const currentLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, [
      "upstox_current_instruments",
      "bod_complete",
      "suspended"
    ]);
  }, [runs]);

  const expiredLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, [
      "upstox_expired_instruments",
      "expired_option",
      "expired_future"
    ]);
  }, [runs]);

  const dumpJobRows = useMemo(() => {
    return [
      {
        id: "current",
        title: "Current Instruments",
        description:
          "Downloads Upstox BOD complete and suspended instrument files.",
        records: summary.total_current_instruments,
        lastSyncedAt: summary.current_last_sync_at || summary.last_sync_at,
        duration: summary.current_duration_seconds,
        lastStatus: currentCancelRequested
          ? "cancel_requested"
          : isCurrentJobRunning
            ? "running"
            : currentLastRun?.status,
        loading: isCurrentJobRunning,
        disabled: hasActiveJob && !isCurrentJobRunning,
        canCancel: isCurrentJobRunning && shouldShowCancelButton,
        onRun: handleCurrentSync
      },
      {
        id: "expired",
        title: "Expired Instruments",
        description: "Pulls expired options and futures using saved Upstox token.",
        records: summary.total_expired_instruments,
        lastSyncedAt: summary.expired_last_sync_at || summary.last_sync_at,
        duration: summary.expired_duration_seconds,
        lastStatus: expiredCancelRequested
          ? "cancel_requested"
          : isExpiredJobRunning
            ? "running"
            : expiredLastRun?.status,
        loading: isExpiredJobRunning,
        disabled: hasActiveJob && !isExpiredJobRunning,
        canCancel: isExpiredJobRunning && shouldShowCancelButton,
        onRun: handleExpiredSync
      }
    ];
  }, [
    summary,
    currentCancelRequested,
    expiredCancelRequested,
    isCurrentJobRunning,
    isExpiredJobRunning,
    currentLastRun,
    expiredLastRun,
    hasActiveJob,
    shouldShowCancelButton
  ]);

  async function loadPreview(customPage = previewPage) {
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
        previewType === "expired"
          ? await getUpstoxExpiredInstrumentsPreview(params)
          : await getUpstoxInstrumentsPreview(params);

      const nextData = response.data.data || response.data || emptyPreviewData;

      setPreviewData(nextData);
      setPreviewPage(nextData.page || customPage);
    } catch (error) {
      setPreviewData(emptyPreviewData);
      showToast(
        error.response?.data?.detail || "Unable to load DB preview.",
        "error"
      );
    } finally {
      setPreviewLoading(false);
    }
  }

  async function handleBulkSync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    setRunningJob("bulk");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();

    try {
      const response = await syncUpstoxAllInstruments({
        signal: activeSyncControllerRef.current.signal
      });

      if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "All instrument dumps cancelled.",
          "warning"
        );
      } else {
        showToast("All instrument dumps completed.", "success");
      }

      await loadData(false);
      if (activeView === "preview") {
        await loadPreview(1);
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        showToast("Cancel requested for data collection.", "warning");
        return;
      }

      showToast(
        error.response?.data?.detail || "Unable to run all instrument dumps.",
        "error"
      );
    } finally {
      setRunningJob(null);
      activeSyncControllerRef.current = null;
    }
  }

  async function loadData(showRefreshToast = false) {
    setLoading(true);

    try {
      const [summaryResponse, runsResponse] = await Promise.all([
        getUpstoxDataCollectionSummary(),
        getUpstoxDataCollectionRuns()
      ]);

      const nextSummary =
        summaryResponse.data.data || summaryResponse.data || emptySummary;

      setSummary(nextSummary);
      setRuns(runsResponse.data.data || runsResponse.data || []);

      if (nextSummary.active_job_started_at) {
        setElapsedSeconds(
          getElapsedSecondsFromDate(nextSummary.active_job_started_at)
        );
      } else if (!nextSummary.active_job) {
        setElapsedSeconds(0);
      }

      if (!nextSummary.active_job) {
        setRunningJob(null);
        setCancelRequested(false);
      }

      if (showRefreshToast) {
        showToast("Data collection status refreshed.", "success");
      }
    } catch (error) {
      setSummary(emptySummary);
      setRuns([]);
      setRunningJob(null);
      setElapsedSeconds(0);
      showToast(
        error.response?.data?.detail ||
          "Backend data collection APIs are not added yet.",
        "warning"
      );
    } finally {
      setLoading(false);
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
      await loadData(false);
    } catch (error) {
      showToast(
        error.response?.data?.detail || "Unable to cancel data collection.",
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

    try {
      const response = await syncUpstoxCurrentInstruments({
        signal: activeSyncControllerRef.current.signal
      });

      if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Current instruments dump cancelled.",
          "warning"
        );
      } else {
        showToast("Current instruments dump completed.", "success");
      }

      await loadData(false);
      if (activeView === "preview" && previewType === "current") {
        await loadPreview(1);
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        showToast("Cancel requested for current instruments dump.", "warning");
        return;
      }

      showToast(
        error.response?.data?.detail ||
          "Unable to run current instruments dump.",
        "error"
      );
    } finally {
      setRunningJob(null);
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

    try {
      const response = await syncUpstoxExpiredInstruments({
        signal: activeSyncControllerRef.current.signal
      });

      if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Expired instruments dump cancelled.",
          "warning"
        );
      } else {
        showToast("Expired instruments dump completed.", "success");
      }

      await loadData(false);
      if (activeView === "preview" && previewType === "expired") {
        await loadPreview(1);
      }
    } catch (error) {
      if (isRequestCancelled(error)) {
        showToast("Cancel requested for expired instruments dump.", "warning");
        return;
      }

      showToast(
        error.response?.data?.detail ||
          "Unable to run expired instruments dump.",
        "error"
      );
    } finally {
      setRunningJob(null);
      activeSyncControllerRef.current = null;
    }
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

  function handlePreviewTypeChange(value) {
    setPreviewType(value);
    setPreviewSourceType("all");
    setPreviewSegment("all");
    setPreviewInstrumentType("all");
    setPreviewPage(1);
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
      return (
        <span className="truncate oa-code-font text-white">
          {formatNumber(row.records)}
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

    if (column.key === "time") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDuration(row.duration)}
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
      />
    );
  }

  useEffect(() => {
    loadData(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (activeView !== "preview") {
      return;
    }

    loadPreview(previewPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeView,
    previewType,
    appliedPreviewSearch,
    previewSourceType,
    previewSegment,
    previewInstrumentType,
    previewPage
  ]);

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
      loadData(false);
    }, 5000);

    return () => window.clearInterval(pollId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hasActiveJob]);

  return (
    <MainLayout>
      <section className="min-h-screen bg-black p-3">
        <div className="space-y-3">
          {!isAdminControlAllowed && (
            <div className="flex gap-3 rounded border border-red-500/30 bg-red-950/20 p-3">
              <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded border border-red-500/40 bg-black text-red-300">
                <AlertTriangle size={18} />
              </div>

              <div>
                <p className={oaCardStyles.headerTitle}>
                  Admin access required
                </p>
                <p className={`mt-1 ${oaFormTextStyles.helper}`}>
                  Only admin and super admin users can run Upstox data dump
                  jobs.
                </p>
              </div>
            </div>
          )}

          <DataCollectionShell
            activeView={activeView}
            onViewChange={setActiveView}
            loading={loading}
            previewLoading={previewLoading}
            shouldShowRunAllButton={shouldShowRunAllButton}
            isAdminControlAllowed={isAdminControlAllowed}
            onBulkSync={handleBulkSync}
            onRefresh={() => {
              if (activeView === "preview") {
                loadPreview(previewPage);
              } else {
                loadData(true);
              }
            }}
          >
            {activeView === "monitor" ? (
              <div className="overflow-x-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
                <DataTable
                  columns={dumpJobColumns}
                  rows={dumpJobRows}
                  loading={loading}
                  loadingMessage="Loading data collection status"
                  emptyMessage="No data collection jobs found."
                  gridTemplateColumns={dumpJobGridTemplateColumns}
                  minWidth="min-w-[980px]"
                  getRowKey={(row) => row.id}
                  renderCell={renderDumpJobCell}
                  renderActions={renderDumpJobActions}
                />
              </div>
            ) : (
              <DbPreviewContent
                previewType={previewType}
                onPreviewTypeChange={handlePreviewTypeChange}
                searchValue={previewSearch}
                onSearchChange={setPreviewSearch}
                onSearchSubmit={handlePreviewSearchSubmit}
                onClearSearch={handleClearPreviewSearch}
                sourceType={previewSourceType}
                onSourceTypeChange={(value) => {
                  setPreviewSourceType(value);
                  setPreviewPage(1);
                }}
                segment={previewSegment}
                onSegmentChange={(value) => {
                  setPreviewSegment(value);
                  setPreviewPage(1);
                }}
                instrumentType={previewInstrumentType}
                onInstrumentTypeChange={(value) => {
                  setPreviewInstrumentType(value);
                  setPreviewPage(1);
                }}
                previewData={previewData}
                loading={previewLoading}
                onRefresh={() => loadPreview(previewPage)}
                onPreviousPage={() =>
                  setPreviewPage((value) => Math.max(1, value - 1))
                }
                onNextPage={() =>
                  setPreviewPage((value) =>
                    Math.min(previewData.total_pages || 1, value + 1)
                  )
                }
              />
            )}
          </DataCollectionShell>
        </div>
      </section>
    </MainLayout>
  );
}

export default DataCollection;