import {
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

import Spinner from "../../../components/common/Spinner";
import IconButton from "../../../components/common/IconButton";
import Input from "../../../components/common/Input";
import Select from "../../../components/common/Select";
import Tooltip from "../../../components/common/Tooltip";
import Modal from "../../../components/common/Modal";
import DataTable from "../../../components/tables/DataTable";
import TableToolbar from "../../../components/tables/TableToolbar";
import DatePicker from "../../../components/common/DatePicker";
import {
  oaCardStyles,
  oaCheckboxControlStyles,
  oaFormTextStyles,
  oaPillStyles,
  oaTabStyles
} from "../../../components/common/uiStyles";
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

export function ViewToggle({ activeView, onChange }) {
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

export function StatusBadge({ status, label }) {
  return (
    <span className={`${oaPillStyles.base} ${getStatusClass(status || "idle")}`}>
      {label || getStatusLabel(status)}
    </span>
  );
}

export function ClearInputButton({ label, onClick }) {
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

export function DumpJobActions({
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

export function DataCollectionShell({
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
        <div className={`${oaCardStyles.header} flex items-center justify-between gap-3`}>
          <h2 className={oaCardStyles.headerTitle}>Data Collection</h2>
          <div className="flex min-w-0 items-center gap-1.5 font-mono text-[11px] leading-none text-oa-muted">
            <HardDrive size={13} className="shrink-0 text-sky-300" />
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

export function ScheduleManagerModal({
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
            variant="filterCancel"
            size="filter"
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

export function MonitorContent({
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

export function DbPreviewContent({
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

export function CheckboxGroup({ title, helper, options, selectedValues, onChange }) {
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

export function OhlcvOptionsModal({
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
            variant="filterCancel"
            size="filter"
            disabled={saving}
            onClick={onClose}
            tooltipSide="top"
          />

          <IconButton
            icon={Check}
            label="Save options"
            variant="filterApply"
            size="filter"
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

export function MarketCalendarContent({
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

export function GenericPreviewContent({
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

export function OhlcvTabContent({
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

export function IpoCalendarTabContent({ activeSubTab, onSubTabChange, children }) {
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

export function CompanyFundamentalsContent({
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

export function PaginationFooter({
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
