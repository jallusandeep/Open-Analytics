import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { referenceViews as VIEWS } from "../../utils/referenceNavigation";
import { Download, RefreshCcw, Upload } from "lucide-react";

import axiosClient from "../../api/axiosClient";
import MainLayout from "../../components/layout/MainLayout";
import { PaginationFooter } from "./dataCollection/components";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import Modal from "../../components/common/Modal";
import Select from "../../components/common/Select";
import IconButton from "../../components/common/IconButton";
import { useToast } from "../../components/common/ToastProvider";
import { oaCardStyles } from "../../components/common/uiStyles";

const BLANK_FILTER_VALUE = "__oa_reference_blank__";
const displayFilterValue = (value) => value === "" ? BLANK_FILTER_VALUE : value;

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
  const [sort, setSort] = useState({ key: view === "listings" ? "instrument_key" : "isin", direction: "asc" });
  const filters = JSON.stringify(columnFilters);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axiosClient.get(`/reference-data/tables/${view}`, { params: { search: appliedSearch, page, page_size: 50, filters, sort_by: sort.key, sort_direction: sort.direction } });
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
          showToast(`${response.data.message || "Reference sync finished."}${counts ? ` ${counts.securities} securities, ${counts.listings} listings; ${counts.added} added, ${counts.updated} updated, ${counts.invalid_skipped} invalid skipped.` : ""}`, response.data.status === "success" ? "success" : "warning");
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
            { icon: Upload, label: "Upload CSV", variant: "add", disabled: loading || busy, onClick: () => fileRef.current?.click() }
          ]} trailingContent={<IconButton icon={Download} label="Download data" disabled={loading || busy} onClick={() => setDownloadOpen(true)} tooltipSide="top" />} />
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={upload} className="hidden" aria-label="Upload reference data CSV" />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto [&>div]:border-0">
          <DataTable columns={data.columns || []} rows={data.rows} loading={loading} loadingMessage="Loading reference data" emptyMessage="No reference data found." gridTemplateColumns={(data.columns || []).map((column) => /name|industry|instrument_key|reason|value/.test(column.key) ? "240px" : "160px").join(" ")} minWidth="min-w-full" getRowKey={(row) => `${row.instrument_key || row.isin}:${row.index_code || row.identifier_type || ""}:${row.old_value || ""}:${row.new_value || ""}:${row.effective_from || ""}`} renderCell={(row, column) => { const value = row[column.key]; return value === null || value === undefined || value === "" ? "--" : String(value); }} filterConfig={{
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
  </MainLayout>;
}
