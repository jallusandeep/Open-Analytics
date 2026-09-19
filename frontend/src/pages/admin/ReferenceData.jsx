import { useCallback, useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useLocation } from "react-router-dom";
import { referenceViews as VIEWS } from "../../utils/referenceNavigation";
import { Columns3, Download, History, RefreshCcw, Upload, X } from "lucide-react";

import axiosClient from "../../api/axiosClient";
import MainLayout from "../../components/layout/MainLayout";
import { PaginationFooter } from "./dataCollection/components";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import Modal from "../../components/common/Modal";
import IconButton from "../../components/common/IconButton";
import Select from "../../components/common/Select";
import Spinner from "../../components/common/Spinner";
import { useToast } from "../../components/common/ToastProvider";
import { oaCardStyles } from "../../components/common/uiStyles";

const BLANK_FILTER_VALUE = "__oa_reference_blank__";
const displayFilterValue = (value) => value === "" ? BLANK_FILTER_VALUE : value;

const auditValue = (value) => value === null || value === undefined || value === "" ? "Empty" : typeof value === "boolean" ? (value ? "Yes" : "No") : String(value);


const auditFieldLabel = (field) => ({ instrument_type: "Instrument Type", gbo_type: "GBO Type", description: "Description", is_active: "Active" }[field] || field.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase()));

function auditAction(event) {
  return ({ MANUAL_ADD: "Created", DISCOVERED: "Discovered", MANUAL_UPDATE: "Updated", MANUAL_CLEAR: "Cleared", DEACTIVATED: "Deactivated", REACTIVATED: "Reactivated", BASELINE: "Baseline recorded" })[event.action] || auditFieldLabel(String(event.action || "Changed").toLowerCase());
}

function auditDateLabel(value) {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "Unknown date";
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  const prefix = date.toDateString() === today.toDateString() ? "Today - " : date.toDateString() === yesterday.toDateString() ? "Yesterday - " : "";
  return prefix + date.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
}


function auditRecordLabel(event) {
  return [event.exchange, event.segment, event.source_type, event.security_type].filter(Boolean).join(" / ") || "Unknown record";
}

function AuditChangeDetails({ event }) {
  const changes = Object.entries(event.changes || {});
  const content = <div className="space-y-1 rounded-md border border-oa-border bg-oa-panel/30 px-2.5 py-[7px]">
    {event.source === "CSV_UPLOAD" && <h4 className="mb-1 text-[11px] font-bold text-zinc-200">{auditAction(event)}: {auditRecordLabel(event)}</h4>}
    {changes.length ? changes.map(([field, change]) => <div key={field} className="break-words text-[11px] leading-[1.45] text-oa-muted">
      <span className="font-semibold">{auditFieldLabel(field)}:</span>{" "}
      <span aria-label={`Previous value: ${auditValue(change?.from)}`} className="rounded-full border border-red-400/35 bg-red-500/15 px-[7px] py-px text-[10px] font-bold text-red-200">{auditValue(change?.from)}</span>
      <span className="px-1">&rarr;</span>
      <span aria-label={`New value: ${auditValue(change?.to)}`} className="rounded-full border border-emerald-400/35 bg-emerald-500/15 px-[7px] py-px text-[10px] font-bold text-emerald-200">{auditValue(change?.to)}</span>
    </div>) : <p className="text-[11px] text-oa-muted">No field changes recorded for this event.</p>}
  </div>;
  return event.source === "CSV_UPLOAD" ? <details className="mt-1.5" open>
    <summary className="cursor-pointer rounded-md border border-oa-border bg-oa-panel/30 px-3 py-2 text-xs font-semibold text-zinc-200">View upload details</summary>
    <div className="pt-1.5">{content}</div>
  </details> : <div className="mt-1.5">{content}</div>;
}

function AuditTrailDrawer({ open, loading, events, view, onClose }) {
  const selectedTabLabel = VIEWS.find((item) => item.value === view)?.label;
  const filteredEvents = events.filter((event) => event.tab === selectedTabLabel);
  useEffect(() => {
    if (!open) return undefined;
    const closeOnEscape = (event) => { if (event.key === "Escape") onClose(); };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [open, onClose]);
  const dateGroups = new Map();
  for (const event of filteredEvents) {
    const label = auditDateLabel(event.at);
    if (!dateGroups.has(label)) dateGroups.set(label, []);
    dateGroups.get(label).push(event);
  }
  return createPortal(<div inert={!open} aria-hidden={!open} data-state={open ? "open" : "closed"} className="oa-audit-drawer oa-app-font fixed inset-0 z-[10000] overflow-hidden">
    <button type="button" aria-label="Close audit trail" onClick={onClose} className="oa-audit-backdrop absolute inset-0 bg-black/65" />
    <aside role="dialog" aria-modal="true" aria-label="Reference data audit trail" className="oa-audit-panel absolute inset-y-0 right-0 flex w-full max-w-[520px] flex-col border-l border-oa-border bg-black shadow-2xl">
      <header className="flex shrink-0 items-center justify-between border-b border-oa-border bg-zinc-800/70 px-5 py-3.5">
        <h2 className={`flex items-center gap-2 ${oaCardStyles.modalTitle}`}><History size={13} />Audit Trail</h2>
        <IconButton icon={X} label="Close audit trail" onClick={onClose} variant="danger" tooltipSide="left" />
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-3.5">
        {loading ? <div role="status" aria-live="polite" className="flex h-full items-center justify-center gap-2 font-mono text-xs text-oa-muted"><Spinner size="sm" color="light" /><span>Loading audit trail...</span></div> : filteredEvents.length === 0 ? <div className="flex h-full items-center justify-center font-mono text-xs text-oa-muted">No audit events recorded.</div> : <div>{Array.from(dateGroups, ([dateLabel, groupEvents]) => <section key={dateLabel} className="mb-[18px]"><h3 className="mb-2 pl-[30px] text-[10px] font-bold uppercase tracking-[0.6px] text-oa-muted">{dateLabel}</h3>{groupEvents.map((event, eventIndex) => <article key={`${event.at}-${event.exchange}-${event.source_type}-${eventIndex}`} className="mb-0.5 flex gap-2.5 rounded-lg px-2.5 py-2 hover:bg-oa-panel/30">
          <div aria-hidden="true" className="flex w-3.5 shrink-0 flex-col items-center pt-[3px]">
            <span className="h-2.5 w-2.5 shrink-0 rounded-full border-2 border-black bg-blue-500" />
            {eventIndex < groupEvents.length - 1 && <span className="mt-[3px] w-0.5 flex-1 bg-oa-border" />}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0 break-words text-[13px] font-medium leading-[1.35] text-white">{event.source === "CSV_UPLOAD" ? "CSV Upload" : <>{auditAction(event)}: <span className="font-bold text-blue-400">{auditRecordLabel(event)}</span></>}</div>
              <time className="mt-0.5 shrink-0 whitespace-nowrap text-right text-[10px] text-oa-muted" title={event.at || undefined}>{event.at && !Number.isNaN(new Date(event.at).getTime()) ? new Date(event.at).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit", hour12: true }) : "--"}</time>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[11px] text-oa-muted">
              <span>by <strong className="font-semibold text-zinc-300">{event.actor || "Unknown actor"}</strong></span>
              <span className="rounded bg-blue-500/15 px-[7px] py-0.5 text-[9px] font-bold uppercase tracking-wide text-sky-300">{auditAction(event)}</span>
              <span className="text-[10px]">via {({ CSV_UPLOAD: "CSV Upload", UPSTOX_SYNC: "Upstox Sync" })[event.source] || auditFieldLabel(String(event.source || "Unknown source").toLowerCase())}</span>
            </div>
            <AuditChangeDetails event={event} />
          </div>
        </article>)}</section>)}</div>}
      </div>
    </aside>
  </div>, document.body);
}

function parseCsv(content) {
  const rows = [];
  let row = [];
  let cell = "";
  let quoted = false;
  for (let index = 0; index < content.length; index += 1) {
    const character = content[index];
    if (character === '"') {
      if (quoted && content[index + 1] === '"') { cell += '"'; index += 1; }
      else quoted = !quoted;
    } else if (character === "," && !quoted) {
      row.push(cell); cell = "";
    } else if ((character === "\n" || character === "\r") && !quoted) {
      if (character === "\r" && content[index + 1] === "\n") index += 1;
      row.push(cell); cell = "";
      if (row.some((value) => value.trim())) rows.push(row);
      row = [];
    } else cell += character;
  }
  if (quoted) throw new Error("CSV has an unclosed quoted value.");
  row.push(cell);
  if (row.some((value) => value.trim())) rows.push(row);
  const [header, ...data] = rows;
  if (!header) throw new Error("CSV is empty.");
  const keys = header.map((value) => value.replace(/^\uFEFF/, "").trim().toLowerCase());
  if (!keys.includes("flag")) throw new Error("Upload the Template + Data CSV with a flag column.");
  if (new Set(keys).size !== keys.length || keys.some((key) => !key)) throw new Error("CSV has duplicate or empty headers.");
  if (data.some((values) => values.length !== keys.length)) throw new Error("CSV rows must match the header column count.");
  return data.map((values) => Object.fromEntries(keys.map((key, index) => [key, values[index]?.trim() || ""])));
}

export default function ReferenceData() {
  const location = useLocation();
  const target = new URLSearchParams(location.search).get("view");
  const view = VIEWS.some((item) => item.value === target) ? target : "securities";
  return <ReferenceDataPage key={view} view={view} />;
}

function ReferenceDataPage({ view }) {
  const { showToast } = useToast();
  const fileRef = useRef(null);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloadType, setDownloadType] = useState("data");
  const [auditOpen, setAuditOpen] = useState(false);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditData, setAuditData] = useState({ events: [], total: 0 });
  const [columnConfigOpen, setColumnConfigOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ rows: [], page: 1, total_pages: 1, total_records: 0 });
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [columnFilters, setColumnFilters] = useState({});
  const [draftColumnFilters, setDraftColumnFilters] = useState({});
  const [activeFilter, setActiveFilter] = useState(null);
  const [sort, setSort] = useState({ key: view === "listings" ? "instrument_key" : view === "types" ? "exchange" : "isin", direction: "asc" });
  const filters = JSON.stringify(columnFilters);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axiosClient.get(`/reference-data/tables/${view}`, { params: { search: appliedSearch, page, page_size: 500, filters, sort_by: sort.key, sort_direction: sort.direction } });
      setData(response.data);
    } catch {
      showToast("Unable to load reference data.", "error");
    } finally {
      setLoading(false);
    }
  }, [appliedSearch, page, showToast, filters, sort, view]);

  useEffect(() => {
    const timer = window.setTimeout(load, 0);
    return () => window.clearTimeout(timer);
  }, [load]);


  useEffect(() => {
    if (!syncing) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const response = await axiosClient.get("/reference-data/sync/status");
        if (cancelled) return;
        if (!response.data.pending && response.data.status !== "running") {
          setSyncing(false);
          const counts = response.data.counts;
          showToast(`${response.data.message || "Reference sync finished."}${counts ? ` ${counts.type_mappings || 0} type mappings, ${counts.listings} listings, ${counts.securities} securities, ${counts.identifier_changes || 0} identifier changes; ${counts.added} added, ${counts.updated} updated, ${counts.invalid_skipped} invalid skipped.` : ""}`, response.data.status === "success" ? "success" : "warning");
          await load();
        }
      } catch { if (!cancelled) { setSyncing(false); showToast("Unable to check sync status. Check the collection monitor.", "error"); } }
    }, 2500);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [syncing, load, showToast]);

  function submitSearch(event) {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
  }

  async function download(template = false) {
    setBusy(true);
    try {
      const response = await axiosClient.get(`/reference-data/tables/${view}/download`, { params: { search: appliedSearch, template, filters, sort_by: sort.key, sort_direction: sort.direction }, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = `reference_${view}_${template ? "template" : "data"}.csv`;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setDownloadOpen(false);
    } catch {
      showToast("Unable to download reference data.", "error");
    } finally { setBusy(false); }
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const rows = parseCsv(await file.text());
      if (!rows.length || rows.length > 2000) throw new Error("CSV must contain 1 to 2,000 rows.");
      const response = await axiosClient.post(`/reference-data/tables/${view}/upload`, { rows });
      const { added, updated, deleted, skipped } = response.data;
      showToast(`Reference data: ${added} added, ${updated} updated, ${deleted} cleared, ${skipped} skipped.`, "success");
      await load();
    } catch (error) {
      showToast(error.response?.data?.detail || error.message || "Unable to upload reference data.", "error");
    } finally { setBusy(false); }
  }

  async function openAuditTrail() {
    setAuditOpen(true);
    setAuditData({ events: [], total: 0 });
    if (view !== "types") {
      setAuditLoading(false);
      return;
    }
    setAuditLoading(true);
    try {
      const response = await axiosClient.get("/reference-data/tables/types/audit", { params: { limit: 500 } });
      setAuditData(response.data);
    } catch {
      showToast("Unable to load the audit trail.", "error");
    } finally {
      setAuditLoading(false);
    }
  }

  return <MainLayout>
    <section className="oa-app-font h-screen min-h-0 overflow-hidden bg-black p-3">
      <div className={`${oaCardStyles.wrapper} flex h-full min-h-0 flex-col`}>
        <nav aria-label="Reference Data breadcrumb" className={`${oaCardStyles.header} flex flex-wrap items-center gap-2`}>
          <h1 className={oaCardStyles.headerTitle}><button type="button" className={`${oaCardStyles.headerTitle} ${oaCardStyles.breadcrumbButton}`} onClick={() => window.dispatchEvent(new Event("open-analytics:reference-navigation-toggle"))}>Reference Data</button></h1>
          <span aria-hidden="true" className={oaCardStyles.breadcrumb}>/</span>
          <button type="button" aria-current="page" className={`${oaCardStyles.breadcrumb} ${oaCardStyles.breadcrumbButton}`} onClick={() => window.dispatchEvent(new Event("open-analytics:reference-navigation-toggle"))}>{VIEWS.find((item) => item.value === view)?.label}</button>
        </nav>
        <div className="relative z-20 shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
          <TableToolbar hasActiveFilter={Object.values(columnFilters).some((values) => values.length)} onClearAll={() => { setColumnFilters({}); setPage(1); setActiveFilter(null); }} searchValue={search} onSearchChange={setSearch} onSearchClear={() => { setSearch(""); setAppliedSearch(""); setPage(1); }} onSearchSubmit={submitSearch} searchActive={Boolean(appliedSearch)} searchPlaceholder="Search reference data" loading={loading || busy} rightActions={[
            { icon: RefreshCcw, label: syncing ? "Upstox reference sync in progress" : "Pull reference data from Upstox", variant: "refresh", disabled: loading || busy || syncing, onClick: async () => {
              setBusy(true);
              try { const response = await axiosClient.post("/reference-data/sync");
                showToast(response.data.message, "success"); setSyncing(true);
              } catch (error) { showToast(error.response?.data?.detail || "Unable to sync Upstox instruments.", "error"); } finally { setBusy(false); }
            } },
            { icon: Upload, label: "Upload CSV", variant: "add", disabled: loading || busy, onClick: () => fileRef.current?.click() },
            { icon: Download, label: "Download data", disabled: loading || busy, onClick: () => setDownloadOpen(true) },
            { icon: History, label: "Open audit trail", disabled: loading || busy, onClick: openAuditTrail },
            { icon: Columns3, label: "Column config", disabled: loading || busy || !data.columns?.length, onClick: () => setColumnConfigOpen(true) }
          ]} />
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={upload} className="hidden" aria-label="Upload reference data CSV" />
        </div>
        <div className="min-h-0 flex-1 overflow-hidden [&>div]:border-0">
          <DataTable columnConfigOpen={columnConfigOpen} onColumnConfigClose={() => setColumnConfigOpen(false)} columns={data.columns || []} rows={data.rows} loading={loading} loadingMessage="Loading reference data" emptyMessage="No reference data found." gridTemplateColumns={(data.columns || []).map((column) => /name|industry|instrument_key|reason|value|description/.test(column.key) ? "240px" : "160px").join(" ")} minWidth="min-w-full" getRowKey={(row) => (data.columns || []).map((column) => row[column.key] ?? "").join(":")} renderCell={(row, column) => { const value = row[column.key]; return value === null || value === undefined || value === "" ? "--" : String(value); }} filterConfig={{
            activeFilter,
            headerValues: Object.fromEntries(Object.entries(data.header_values || {}).map(([key, values]) => [key, values.map((value) => ({ value: displayFilterValue(value), label: value === "" ? "--" : value }))])),
            columnFilters: Object.fromEntries(Object.entries(columnFilters).map(([key, values]) => [key, values.map(displayFilterValue)])),
            draftColumnFilters,
            isColumnFilterActive: (key) => Boolean(columnFilters[key]?.length),
            onOpen: (key) => { setDraftColumnFilters((previous) => ({ ...previous, [key]: (columnFilters[key] || []).map(displayFilterValue) })); setActiveFilter(key); },
            onClose: () => setActiveFilter(null),
            onChange: (key, values) => setDraftColumnFilters((previous) => ({ ...previous, [key]: values })),
            onApply: (key) => { setColumnFilters((previous) => ({ ...previous, [key]: (draftColumnFilters[key] || []).map((value) => value === BLANK_FILTER_VALUE ? "" : value) })); setPage(1); setActiveFilter(null); },
            onClear: (key) => { setColumnFilters((previous) => ({ ...previous, [key]: [] })); setPage(1); setActiveFilter(null); },
            onSort: (key, direction) => { setSort({ key, direction }); setPage(1); setActiveFilter(null); }
          }} />
        </div>
        <PaginationFooter previewData={{ ...data, page }} loading={loading || busy} onPreviousPage={() => setPage((value) => Math.max(1, value - 1))} onNextPage={() => setPage((value) => Math.min(data.total_pages, value + 1))} onPageChange={(value) => setPage(Number(value))} />
      </div>
    </section>
    <Modal open={downloadOpen} title="Download Data" onClose={() => !busy && setDownloadOpen(false)} closeOnOverlay={!busy} width="max-w-md">
      <form onSubmit={(event) => { event.preventDefault(); download(downloadType === "template"); }} className="oa-app-font space-y-4 text-xs text-white">
        <p className="leading-5 text-oa-muted">Download records matching the current search and filters across all pages. Template + Data can be edited and uploaded.</p>
        <label className="block space-y-2"><span>Download type</span><Select value={downloadType} onChange={(event) => setDownloadType(event.target.value)} options={[{ value: "data", label: "Data only" }, { value: "template", label: "Template + Data" }]} minWidth="w-full" disabled={busy} /></label>
        <button type="submit" disabled={busy} className="flex h-9 w-full items-center justify-center gap-2 rounded bg-white font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40"><Download size={14} />{busy ? "Downloading..." : "Download"}</button>
      </form>
    </Modal>
    <AuditTrailDrawer open={auditOpen} loading={auditLoading} events={auditData.events} view={view} onClose={() => setAuditOpen(false)} />
  </MainLayout>;
}
