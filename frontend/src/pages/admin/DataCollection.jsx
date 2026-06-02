import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  Check,
  ChevronLeft,
  ChevronRight,
  Clock3,
  DownloadCloud,
  Edit3,
  Play,
  Power,
  RefreshCcw,
  Search,
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
import { useToast } from "../../components/common/ToastProvider";
import {
  oaCardStyles,
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
  getUpstoxDataCollectionSummary,
  getUpstoxEquityInstrumentsPreview,
  getUpstoxExpiredInstrumentsPreview,
  getUpstoxInstrumentsPreview,
  syncUpstoxAllInstruments,
  syncUpstoxCurrentInstruments,
  syncUpstoxEquityInstruments,
  syncUpstoxExpiredInstruments,
  toggleUpstoxDataCollectionSchedule,
  updateUpstoxDataCollectionSchedule
} from "../../api/dataCollectionApi";

const emptySummary = {
  connection_status: "not_connected",
  total_current_instruments: 0,
  total_expired_instruments: 0,
  total_equity_instruments: 0,
  total_sync_runs: 0,
  last_sync_at: "",
  last_duration_seconds: null,
  current_last_sync_at: "",
  current_duration_seconds: null,
  expired_last_sync_at: "",
  expired_duration_seconds: null,
  equity_last_sync_at: "",
  equity_duration_seconds: null,
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

const emptyScheduleForm = {
  schedule_id: "",
  job_type: "current_instruments",
  schedule_time: "",
  time_format: "24",
  is_active: true
};

const viewOptions = [
  {
    key: "monitor",
    label: "Collection Monitor"
  },
  {
    key: "current_preview",
    label: "Current Instruments"
  },
  {
    key: "expired_preview",
    label: "Expired Instruments"
  },
  {
    key: "equity_preview",
    label: "Equity"
  }
];

const timeFormatOptions = [
  {
    value: "24",
    label: "24 Hours"
  },
  {
    value: "12",
    label: "12 Hours"
  }
];

const timePeriodOptions = [
  { value: "AM", label: "AM" },
  { value: "PM", label: "PM" }
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

const securityTypeOptions = [
  { value: "all", label: "All Security Types" },
  { value: "NORMAL", label: "NORMAL" },
  { value: "BE", label: "BE" }
];

const dumpJobColumns = [
  { key: "source", label: "Source", filterable: false },
  { key: "saved", label: "Saved", filterable: false },
  { key: "updated", label: "Updated", filterable: false },
  { key: "triggered_by", label: "Scheduled By", filterable: false },
  { key: "time", label: "Time", filterable: false },
  { key: "last_update_status", label: "Last Update Status", filterable: false }
];

const dumpJobGridTemplateColumns =
  "1.25fr 0.55fr 0.75fr 0.8fr 0.5fr 0.7fr 152px";

const scheduleColumns = [
  { key: "schedule_time", label: "Time", filterable: false },
  { key: "next_run_at", label: "Next Run", filterable: false },
  { key: "is_active", label: "Status", filterable: false }
];

const scheduleGridTemplateColumns = "1fr 1.35fr 0.75fr 112px";

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
  "280px 300px 300px 150px 150px 130px 150px 140px 190px 230px";

const equityPreviewColumns = [
  { key: "instrument_key", label: "Instrument Key", filterable: false },
  { key: "trading_symbol", label: "Trading Symbol", filterable: false },
  { key: "name", label: "Name", filterable: false },
  { key: "isin", label: "ISIN", filterable: false },
  { key: "exchange", label: "Exchange", filterable: false },
  { key: "segment", label: "Segment", filterable: false },
  { key: "exchange_token", label: "Exchange Token", filterable: false },
  { key: "tick_size", label: "Tick Size", filterable: false },
  { key: "lot_size", label: "Lot Size", filterable: false },
  { key: "freeze_quantity", label: "Freeze Qty", filterable: false },
  { key: "short_name", label: "Short Name", filterable: false },
  { key: "security_type", label: "Security Type", filterable: false },
  { key: "downloaded_at", label: "Downloaded At", filterable: false }
];

const equityPreviewGridTemplateColumns =
  "280px 220px 320px 170px 130px 130px 160px 120px 120px 150px 180px 150px 230px";

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

  if (error?.response?.status) {
    return `${fallbackMessage} (HTTP ${error.response.status})`;
  }

  return error?.message || fallbackMessage;
}

function getSyncTypeLabel(value) {
  const labels = {
    upstox_current_instruments: "Current Instruments",
    upstox_expired_instruments: "Expired Instruments",
    upstox_equity_instruments: "Equity",
    upstox_all_instruments: "All Instruments",
    upstox_instruments: "All Instruments",
    current_instruments: "Current Instruments",
    expired_instruments: "Expired Instruments",
    equity_instruments: "Equity",
    bod_complete: "BOD Complete",
    suspended: "Suspended",
    expired_option: "Expired Options",
    expired_future: "Expired Futures"
  };

  return labels[value] || value || "--";
}

function getStatusClass(status) {
  if (status === "success" || status === "connected" || status === "active") {
    return "border-emerald-500/40 bg-emerald-950/50 text-emerald-200";
  }

  if (status === "running" || status === "cancel_requested") {
    return "border-cyan-500/40 bg-cyan-950/50 text-cyan-200";
  }

  if (status === "failed" || status === "cancelled" || status === "inactive") {
    return "border-red-500/40 bg-red-950/50 text-red-200";
  }

  if (status === "saved") {
    return "border-sky-500/40 bg-sky-950/50 text-sky-200";
  }

  return "border-zinc-600 bg-zinc-900 text-zinc-200";
}

function getStatusLabel(status) {
  if (status === "success") return "Success";
  if (status === "running") return "Running";
  if (status === "cancel_requested") return "Cancelling";
  if (status === "cancelled") return "Cancelled";
  if (status === "failed") return "Failed";
  if (status === "active") return "Active";
  if (status === "inactive") return "Inactive";

  return status || "Idle";
}

function getLatestRunByTypes(runs, syncTypes = []) {
  return runs.find((run) => syncTypes.includes(run.sync_type)) || null;
}

function getPreviewTypeFromView(activeView) {
  if (activeView === "expired_preview") {
    return "expired";
  }

  if (activeView === "equity_preview") {
    return "equity";
  }

  return "current";
}

function isPreviewView(activeView) {
  return (
    activeView === "current_preview" ||
    activeView === "expired_preview" ||
    activeView === "equity_preview"
  );
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
    <div className={oaTabStyles.wrapper}>
      {viewOptions.map((option) => {
        const isActive = activeView === option.key;

        return (
          <button
            key={option.key}
            type="button"
            onClick={() => onChange(option.key)}
            className={`${oaTabStyles.button} ${
              isActive ? oaTabStyles.active : oaTabStyles.inactive
            }`}
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
  onSchedule
}) {
  return (
    <div className="flex justify-end gap-2">
      <Tooltip text={`Schedule ${title}`} side="left">
        <button
          type="button"
          onClick={onSchedule}
          className="flex h-8 w-8 items-center justify-center rounded border border-oa-border bg-black text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500"
          aria-label={`Schedule ${title}`}
        >
          <Clock3 size={15} />
        </button>
      </Tooltip>

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

function DataCollectionShell({ activeView, onViewChange, children }) {
  return (
    <div
      className={`${oaCardStyles.wrapper} flex h-[calc(100vh-24px)] min-h-0 flex-col overflow-hidden`}
    >
      <div className="shrink-0">
        <div className={oaCardStyles.header}>
          <h2 className={oaCardStyles.headerTitle}>Data Collection</h2>
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
    formData.time_format;

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

          <div className="grid gap-3 md:grid-cols-2">
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
  rows,
  loading,
  canRunAll,
  runAllDisabled,
  onRefresh,
  onBulkSync,
  renderCell,
  renderActions
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
        <form
          onSubmit={onSearchSubmit}
          className="flex flex-wrap items-center gap-2"
        >
          <div className="relative w-full md:w-80">
            <Input
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder="Search collection monitor"
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

          <Tooltip text="Search collection monitor" side="top">
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded border border-sky-500/30 bg-sky-950/20 text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500"
              aria-label="Search collection monitor"
            >
              <Search size={14} />
            </button>
          </Tooltip>

          <IconButton
            icon={RefreshCcw}
            label="Refresh"
            variant="refresh"
            disabled={loading}
            onClick={onRefresh}
            tooltipSide="top"
          />

          {canRunAll && (
            <Tooltip text="Run all dumps" side="top">
              <button
                type="button"
                disabled={runAllDisabled}
                onClick={onBulkSync}
                className="flex h-8 w-8 items-center justify-center rounded border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Run all data collection dumps"
              >
                <DownloadCloud size={14} />
              </button>
            </Tooltip>
          )}
        </form>
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
        />
      </div>
    </div>
  );
}

function DbPreviewContent({
  previewType,
  previewLabel,
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
  securityType,
  onSecurityTypeChange,
  previewData,
  loading,
  canRunAll,
  runAllDisabled,
  onRefresh,
  onBulkSync,
  onPreviousPage,
  onNextPage,
  onPageChange
}) {
  const isEquityPreview = previewType === "equity";
  const activeColumns = isEquityPreview ? equityPreviewColumns : previewColumns;
  const activeGridTemplateColumns = isEquityPreview
    ? equityPreviewGridTemplateColumns
    : previewGridTemplateColumns;
  const activeMinWidth = isEquityPreview ? "min-w-[2440px]" : "min-w-[2020px]";

  function renderPreviewCell(row, column) {
    if (isEquityPreview) {
      if (column.key === "downloaded_at") {
        return (
          <span className="truncate oa-code-font text-oa-muted">
            {formatDateTime(row.downloaded_at)}
          </span>
        );
      }

      if (column.key === "security_type") {
        return (
          <span
            className={`${oaPillStyles.base} ${
              row.security_type === "BE"
                ? "border-amber-500/40 bg-amber-950/40 text-amber-200"
                : "border-emerald-500/40 bg-emerald-950/40 text-emerald-200"
            }`}
          >
            {row.security_type || "--"}
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

      const mutedKeys = ["exchange", "segment", "isin", "short_name"];

      return (
        <span
          className={`truncate oa-code-font ${
            mutedKeys.includes(column.key) ? "text-oa-muted" : "text-white"
          }`}
        >
          {row[column.key] ?? "--"}
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
    <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="relative z-30 shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
        <form
          onSubmit={onSearchSubmit}
          className="flex flex-wrap items-center gap-2"
        >
          <div className="relative w-full md:w-80">
            <Input
              value={searchValue}
              onChange={(event) => onSearchChange(event.target.value)}
              placeholder={`Search ${previewLabel.toLowerCase()}`}
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

          {isEquityPreview ? (
            <Select
              value={securityType}
              onChange={(event) => onSecurityTypeChange(event.target.value)}
              options={securityTypeOptions}
              ariaLabel="Security type"
              minWidth="w-44"
            />
          ) : (
            <>
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
            </>
          )}

          <Tooltip text="Search instruments" side="top">
            <button
              type="submit"
              className="flex h-8 w-8 items-center justify-center rounded border border-sky-500/30 bg-sky-950/20 text-sky-300 outline-none transition hover:border-sky-500/60 hover:bg-sky-950/40 hover:text-sky-200 focus:border-sky-500"
              aria-label="Search instruments"
            >
              <Search size={14} />
            </button>
          </Tooltip>

          <IconButton
            icon={RefreshCcw}
            label="Refresh"
            variant="refresh"
            disabled={loading}
            onClick={onRefresh}
            tooltipSide="top"
          />

          {canRunAll && (
            <Tooltip text="Run all dumps" side="top">
              <button
                type="button"
                disabled={runAllDisabled}
                onClick={onBulkSync}
                className="flex h-8 w-8 items-center justify-center rounded border border-emerald-500/30 bg-emerald-950/20 text-emerald-300 outline-none transition hover:border-emerald-500/60 hover:bg-emerald-950/40 hover:text-emerald-200 focus:border-emerald-500 disabled:cursor-not-allowed disabled:opacity-60"
                aria-label="Run all data collection dumps"
              >
                <DownloadCloud size={14} />
              </button>
            </Tooltip>
          )}
        </form>
      </div>

      <div className="relative min-h-0 flex-1 overflow-auto bg-black [&>div]:rounded-none [&>div]:border-0 [&>div]:bg-transparent">
        {loading && (
          <div className="sticky left-0 top-0 z-20 flex h-full min-h-[320px] w-full items-center justify-center bg-black/80">
            <div className="flex flex-col items-center gap-3 text-oa-muted">
              <Spinner size="md" color="light" />
              <span className="oa-code-font text-[12px]">
                Loading {previewLabel.toLowerCase()}
              </span>
            </div>
          </div>
        )}

        <DataTable
          columns={activeColumns}
          rows={previewData.rows}
          loading={false}
          loadingMessage={`Loading ${previewLabel.toLowerCase()}`}
          emptyMessage="No dumped records found."
          gridTemplateColumns={activeGridTemplateColumns}
          minWidth={activeMinWidth}
          getRowKey={(row, index) => `${row.instrument_key || index}-${index}`}
          renderCell={renderPreviewCell}
        />
      </div>

      <div className="flex shrink-0 flex-col gap-2 border-t border-oa-border bg-black px-3 py-2 text-[12px] text-oa-muted md:flex-row md:items-center md:justify-between">
        <span>
          Records: {formatNumber(previewData.total_records)} | Page{" "}
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

  const [selectedScheduleJob, setSelectedScheduleJob] = useState(null);
  const [scheduleFormMode, setScheduleFormMode] = useState("add");
  const [scheduleFormData, setScheduleFormData] = useState(emptyScheduleForm);
  const [savingSchedule, setSavingSchedule] = useState(false);
  const [savingScheduleId, setSavingScheduleId] = useState("");
  const [deletingScheduleId, setDeletingScheduleId] = useState("");

  const [previewSearch, setPreviewSearch] = useState("");
  const [appliedPreviewSearch, setAppliedPreviewSearch] = useState("");
  const [previewSourceType, setPreviewSourceType] = useState("all");
  const [previewSegment, setPreviewSegment] = useState("all");
  const [previewInstrumentType, setPreviewInstrumentType] = useState("all");
  const [previewSecurityType, setPreviewSecurityType] = useState("all");
  const [previewPage, setPreviewPage] = useState(1);
  const [previewPageSize] = useState(50);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewData, setPreviewData] = useState(emptyPreviewData);

  const { showToast } = useToast();

  const currentUser = useMemo(() => getStoredCurrentUser(), []);
  const isAdminControlAllowed = ["admin", "super_admin"].includes(
    currentUser?.role
  );

  const previewType = getPreviewTypeFromView(activeView);
  const previewLabel =
    previewType === "expired"
      ? "Expired Instruments"
      : previewType === "equity"
        ? "Equity"
        : "Current Instruments";

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

  const isEquityJobRunning =
    !isCancelRequested &&
    (runningJob === "equity" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_equity_instruments");

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

  const equityCancelRequested =
    isCancelRequested &&
    (runningJob === "equity" ||
      isBulkJobRunning ||
      summary.active_job === "upstox_equity_instruments" ||
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

  const equityLastRun = useMemo(() => {
    return getLatestRunByTypes(runs, ["upstox_equity_instruments"]);
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
    return [
      {
        id: "current",
        title: "Current Instruments",
        scheduleJobType: "current_instruments",
        description:
          "Downloads Upstox BOD complete and suspended instrument files.",
        records: summary.total_current_instruments,
        lastSyncedAt: summary.current_last_sync_at || summary.last_sync_at,
        triggeredBy: currentLastRun?.triggered_by_name,
        triggerSource: currentLastRun?.trigger_source,
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
        scheduleJobType: "expired_instruments",
        description:
          "Pulls expired options and futures using saved Upstox token.",
        records: summary.total_expired_instruments,
        lastSyncedAt: summary.expired_last_sync_at || summary.last_sync_at,
        triggeredBy: expiredLastRun?.triggered_by_name,
        triggerSource: expiredLastRun?.trigger_source,
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
      },
      {
        id: "equity",
        title: "Equity",
        scheduleJobType: "equity_instruments",
        description:
          "Collects NSE_EQ equity instruments once per day from current instruments.",
        records: summary.total_equity_instruments,
        lastSyncedAt: summary.equity_last_sync_at || summary.last_sync_at,
        triggeredBy: equityLastRun?.triggered_by_name,
        triggerSource: equityLastRun?.trigger_source,
        duration: summary.equity_duration_seconds,
        lastStatus: equityCancelRequested
          ? "cancel_requested"
          : isEquityJobRunning
            ? "running"
            : equityLastRun?.status,
        loading: isEquityJobRunning,
        disabled: hasActiveJob && !isEquityJobRunning,
        canCancel: isEquityJobRunning && shouldShowCancelButton,
        onRun: handleEquitySync
      }
    ];
  }, [
    summary,
    currentCancelRequested,
    expiredCancelRequested,
    equityCancelRequested,
    isCurrentJobRunning,
    isExpiredJobRunning,
    isEquityJobRunning,
    currentLastRun,
    expiredLastRun,
    equityLastRun,
    hasActiveJob,
    shouldShowCancelButton
  ]);

  const filteredDumpJobRows = useMemo(() => {
    const query = appliedMonitorSearch.trim().toLowerCase();

    if (!query) {
      return dumpJobRows;
    }

    return dumpJobRows.filter((row) => {
      const values = [
        row.title,
        row.description,
        formatNumber(row.records),
        formatDateTime(row.lastSyncedAt),
        row.triggerSource === "system" ? "System" : row.triggeredBy || "Manual",
        formatDuration(row.duration),
        getStatusLabel(row.lastStatus)
      ];

      return values.some((value) => String(value).toLowerCase().includes(query));
    });
  }, [dumpJobRows, appliedMonitorSearch]);

  async function loadPreview(customPage = previewPage) {
    setPreviewLoading(true);

    try {
      const params = {
        search: appliedPreviewSearch,
        page: customPage,
        page_size: previewPageSize
      };

      let response;

      if (previewType === "expired") {
        response = await getUpstoxExpiredInstrumentsPreview({
          ...params,
          source_type: previewSourceType,
          segment: previewSegment,
          instrument_type: previewInstrumentType
        });
      } else if (previewType === "equity") {
        response = await getUpstoxEquityInstrumentsPreview({
          ...params,
          security_type: previewSecurityType
        });
      } else {
        response = await getUpstoxInstrumentsPreview({
          ...params,
          source_type: previewSourceType,
          segment: previewSegment,
          instrument_type: previewInstrumentType
        });
      }

      const nextData = response.data.data || response.data || emptyPreviewData;

      setPreviewData(nextData);
      setPreviewPage(nextData.page || customPage);
    } catch (error) {
      setPreviewData(emptyPreviewData);
      showToast(
        error.response?.data?.detail || "Unable to load instruments.",
        "error"
      );
    } finally {
      setPreviewLoading(false);
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

  async function loadData(showRefreshToast = false, options = {}) {
    const { showLoading = true } = options;

    if (showLoading) {
      setLoading(true);
    }

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

      await refreshAfterSync();
    } catch (error) {
      if (isRequestCancelled(error)) {
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

      await refreshAfterSync();
    } catch (error) {
      if (isRequestCancelled(error)) {
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

      await refreshAfterSync();
    } catch (error) {
      if (isRequestCancelled(error)) {
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

  async function handleEquitySync() {
    if (!isAdminControlAllowed) {
      showToast("Admin access required to run data collection.", "error");
      return;
    }

    setRunningJob("equity");
    setCancelRequested(false);
    setElapsedSeconds(0);
    activeSyncControllerRef.current = new AbortController();

    try {
      const response = await syncUpstoxEquityInstruments({
        signal: activeSyncControllerRef.current.signal
      });

      if (response.data?.status === "cancelled") {
        showToast(
          response.data.message || "Equity instruments dump cancelled.",
          "warning"
        );
      } else if (response.data?.skipped) {
        showToast(
          response.data.message || "Equity instruments already collected today.",
          "success"
        );
      } else {
        showToast("Equity instruments dump completed.", "success");
      }

      await refreshAfterSync();
    } catch (error) {
      if (isRequestCancelled(error)) {
        return;
      }

      showToast(
        error.response?.data?.detail || "Unable to run equity instruments dump.",
        "error"
      );
    } finally {
      setRunningJob(null);
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
      job_type: schedule.job_type || selectedScheduleJob,
      schedule_time: schedule.schedule_time || "",
      time_format: schedule.time_format || "24",
      is_active: Boolean(schedule.is_active)
    });
  }

  function handleCancelScheduleEdit() {
    setScheduleFormMode("add");
    setScheduleFormData({
      ...emptyScheduleForm,
      job_type: selectedScheduleJob
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
      job_type: scheduleFormData.job_type,
      schedule_time: scheduleFormData.schedule_time,
      time_format: scheduleFormData.time_format,
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
        job_type: selectedScheduleJob
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

  function handleViewChange(nextView) {
    setActiveView(nextView);

    if (isPreviewView(nextView)) {
      setPreviewSearch("");
      setAppliedPreviewSearch("");
      setPreviewSourceType("all");
      setPreviewSegment("all");
      setPreviewInstrumentType("all");
      setPreviewSecurityType("all");
      setPreviewPage(1);
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

    if (column.key === "triggered_by") {
      const triggeredBy =
        row.triggerSource === "system" ? "System" : row.triggeredBy || "Manual";

      return <span className="truncate text-white">{triggeredBy || "--"}</span>;
    }

    if (column.key === "time") {
      return (
        <span className="truncate oa-code-font text-white">
          {formatDuration(row.duration || elapsedSeconds)}
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
        onSchedule={() => openSchedulePopup(row.scheduleJobType)}
      />
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
    previewSecurityType,
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
            >
              {activeView === "monitor" ? (
                <MonitorContent
                  searchValue={monitorSearch}
                  onSearchChange={setMonitorSearch}
                  onSearchSubmit={handleMonitorSearchSubmit}
                  onClearSearch={handleClearMonitorSearch}
                  rows={filteredDumpJobRows}
                  loading={loading}
                  canRunAll={shouldShowRunAllButton}
                  runAllDisabled={!isAdminControlAllowed || loading}
                  onRefresh={() => loadData(true)}
                  onBulkSync={handleBulkSync}
                  renderCell={renderDumpJobCell}
                  renderActions={renderDumpJobActions}
                />
              ) : null}

              {isPreviewView(activeView) ? (
                <DbPreviewContent
                  previewType={previewType}
                  previewLabel={previewLabel}
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
                  securityType={previewSecurityType}
                  onSecurityTypeChange={(value) => {
                    setPreviewSecurityType(value);
                    setPreviewPage(1);
                  }}
                  previewData={previewData}
                  loading={previewLoading}
                  canRunAll={shouldShowRunAllButton}
                  runAllDisabled={
                    !isAdminControlAllowed || loading || previewLoading
                  }
                  onRefresh={() => loadPreview(previewPage)}
                  onBulkSync={handleBulkSync}
                  onPreviousPage={() =>
                    setPreviewPage((value) => Math.max(1, value - 1))
                  }
                  onNextPage={() =>
                    setPreviewPage((value) =>
                      Math.min(previewData.total_pages || 1, value + 1)
                    )
                  }
                  onPageChange={(page) => setPreviewPage(page)}
                />
              ) : null}
            </DataCollectionShell>
          </div>
        </div>

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