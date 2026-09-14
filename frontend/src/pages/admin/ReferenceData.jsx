import { useCallback, useEffect, useRef, useState } from "react";
import { Download, RefreshCcw, Upload } from "lucide-react";

import axiosClient from "../../api/axiosClient";
import MainLayout from "../../components/layout/MainLayout";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import { useToast } from "../../components/common/ToastProvider";
import { oaCardStyles, oaIconButtonStyles, oaSelectStyles } from "../../components/common/uiStyles";

const COLUMNS = [
  { key: "isin", label: "ISIN" },
  { key: "trading_symbol", label: "Trading Symbol" },
  { key: "name", label: "Name" },
  { key: "exchange", label: "Exchange" },
  { key: "segment", label: "Segment" }
];

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
  if (!["isin", "trading_symbol", "exchange", "segment", "reference_name", "flag"].every((key) => keys.includes(key))) {
    throw new Error("Upload the Template + Data CSV with ISIN, trading symbol, exchange, segment, reference_name, and flag columns.");
  }
  return data.map((values) => Object.fromEntries(keys.map((key, index) => [key, values[index]?.trim() || ""])));
}

export default function ReferenceData() {
  const { showToast } = useToast();
  const fileRef = useRef(null);
  const downloadRef = useRef(null);
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState({ rows: [], page: 1, total_pages: 1, total_records: 0 });
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const response = await axiosClient.get("/reference-data/equities", { params: { search: appliedSearch, page, page_size: 50 } });
      setData(response.data);
    } catch {
      showToast("Unable to load reference equities.", "error");
    } finally {
      setLoading(false);
    }
  }, [appliedSearch, page, showToast]);

  useEffect(() => {
    const timer = window.setTimeout(load, 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!downloadOpen) return undefined;
    function close(event) {
      if (!downloadRef.current?.contains(event.target)) setDownloadOpen(false);
    }
    function closeOnEscape(event) {
      if (event.key === "Escape") setDownloadOpen(false);
    }
    document.addEventListener("pointerdown", close);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", close);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [downloadOpen]);

  function submitSearch(event) {
    event.preventDefault();
    setPage(1);
    setAppliedSearch(search.trim());
  }

  async function download(template = false) {
    setBusy(true);
    try {
      const response = await axiosClient.get("/reference-data/equities/download", { params: { search: appliedSearch, template }, responseType: "blob" });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url;
      link.download = template ? "reference_equities_template.csv" : "reference_equities_data.csv";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch {
      showToast("Unable to download reference equities.", "error");
    } finally { setBusy(false); }
  }

  async function upload(event) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setBusy(true);
    try {
      const rows = parseCsv(await file.text());
      if (!rows.length || rows.length > 2000) throw new Error("CSV must contain 1 to 2,000 equity rows.");
      const response = await axiosClient.post("/reference-data/equities/upload", { rows });
      const { added, updated, deleted, skipped } = response.data;
      showToast(`Reference data: ${added} added, ${updated} updated, ${deleted} cleared, ${skipped} skipped.`, "success");
      await load();
    } catch (error) {
      showToast(error.response?.data?.detail || error.message || "Unable to upload reference equities.", "error");
    } finally { setBusy(false); }
  }

  return <MainLayout>
    <section className="oa-app-font h-[calc(100vh-24px)] min-h-0 bg-black p-3">
      <div className={`${oaCardStyles.wrapper} flex h-full min-h-0 flex-col`}>
        <div className={oaCardStyles.header}><h1 className={oaCardStyles.headerTitle}>Reference Data</h1></div>
        <div className="relative z-20 shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
          <TableToolbar searchValue={search} onSearchChange={setSearch} onSearchClear={() => { setSearch(""); setAppliedSearch(""); setPage(1); }} onSearchSubmit={submitSearch} searchActive={Boolean(appliedSearch)} searchPlaceholder="Search ISIN, symbol, name, exchange, segment" loading={loading || busy} rightActions={[
            { icon: RefreshCcw, label: "Refresh", variant: "refresh", disabled: loading || busy, onClick: load },
            { icon: Upload, label: "Upload CSV", variant: "add", disabled: loading || busy, onClick: () => fileRef.current?.click() }
          ]} trailingContent={<div ref={downloadRef} className="relative">
            <button type="button" disabled={loading || busy || !data.total_records} onClick={() => setDownloadOpen((open) => !open)} aria-expanded={downloadOpen} aria-haspopup="menu" aria-label="Download options" title="Download options" className={`${oaIconButtonStyles.base} ${downloadOpen ? oaIconButtonStyles.variantActive.default : oaIconButtonStyles.variantButton.default}`}>
              <Download size={14} className={oaIconButtonStyles.variantIcon.default} />
            </button>
            {downloadOpen && <div role="menu" aria-label="Download options" className={`${oaSelectStyles.menu} !absolute !left-auto !right-0 !top-8 z-50 !w-48 origin-top-right !border-sky-500/50 animate-[oaSelectDown_0.1s_ease-out]`}>
              <button role="menuitem" type="button" onClick={() => { setDownloadOpen(false); download(false); }} className={`${oaSelectStyles.option} ${oaSelectStyles.optionDefault}`}>Data only</button>
              <button role="menuitem" type="button" onClick={() => { setDownloadOpen(false); download(true); }} className={`${oaSelectStyles.option} ${oaSelectStyles.optionDefault}`}>Template + Data</button>
            </div>}
          </div>} />
          <input ref={fileRef} type="file" accept=".csv,text/csv" onChange={upload} className="hidden" aria-label="Upload reference equities CSV" />
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto [&>div]:border-0">
          <DataTable columns={COLUMNS} rows={data.rows} loading={loading} loadingMessage="Loading reference equities" emptyMessage="No equity reference data found." gridTemplateColumns="220px 180px 320px 140px 160px" minWidth="min-w-full" getRowKey={(row) => `${row.isin}:${row.exchange}:${row.segment}`} renderCell={(row, column) => row[column.key] || "--"} />
        </div>
        <div className="flex shrink-0 items-center justify-between border-t border-oa-border px-3 py-2 font-mono text-xs text-oa-muted">
          <span>{data.total_records.toLocaleString()} equities</span>
          <div className="flex items-center gap-3">
            <button type="button" disabled={loading || page <= 1} onClick={() => setPage((value) => value - 1)} className="disabled:opacity-40">Previous</button>
            <span>{page} / {data.total_pages}</span>
            <button type="button" disabled={loading || page >= data.total_pages} onClick={() => setPage((value) => value + 1)} className="disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
    </section>
  </MainLayout>;
}
