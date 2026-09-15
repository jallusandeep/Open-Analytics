import { useCallback, useEffect, useRef, useState } from "react";
import { Download, RefreshCcw, Upload } from "lucide-react";

import axiosClient from "../../api/axiosClient";
import MainLayout from "../../components/layout/MainLayout";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import Modal from "../../components/common/Modal";
import Select from "../../components/common/Select";
import IconButton from "../../components/common/IconButton";
import { useToast } from "../../components/common/ToastProvider";
import { oaCardStyles } from "../../components/common/uiStyles";

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
  const [downloadOpen, setDownloadOpen] = useState(false);
  const [downloadType, setDownloadType] = useState("data");
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
      setDownloadOpen(false);
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
    <section className="oa-app-font h-screen min-h-0 overflow-hidden bg-black p-3">
      <div className={`${oaCardStyles.wrapper} flex h-full min-h-0 flex-col`}>
        <div className={oaCardStyles.header}><h1 className={oaCardStyles.headerTitle}>Reference Data</h1></div>
        <div className="relative z-20 shrink-0 border-b border-oa-border bg-black px-3 py-1.5">
          <TableToolbar searchValue={search} onSearchChange={setSearch} onSearchClear={() => { setSearch(""); setAppliedSearch(""); setPage(1); }} onSearchSubmit={submitSearch} searchActive={Boolean(appliedSearch)} searchPlaceholder="Search ISIN, symbol, name, exchange, segment" loading={loading || busy} rightActions={[
            { icon: RefreshCcw, label: "Refresh", variant: "refresh", disabled: loading || busy, onClick: load },
            { icon: Upload, label: "Upload CSV", variant: "add", disabled: loading || busy, onClick: () => fileRef.current?.click() }
          ]} trailingContent={<IconButton icon={Download} label="Download data" disabled={loading || busy || !data.total_records} onClick={() => setDownloadOpen(true)} tooltipSide="top" />} />
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
    <Modal open={downloadOpen} title="Download Data" onClose={() => !busy && setDownloadOpen(false)} closeOnOverlay={!busy} width="max-w-md">
      <form onSubmit={(event) => { event.preventDefault(); download(downloadType === "template"); }} className="oa-app-font space-y-4 text-xs text-white">
        <p className="leading-5 text-oa-muted">Download records matching the current search across all pages. Template + Data can be edited and uploaded.</p>
        <label className="block space-y-2"><span>Download type</span><Select value={downloadType} onChange={(event) => setDownloadType(event.target.value)} options={[{ value: "data", label: "Data only" }, { value: "template", label: "Template + Data" }]} minWidth="w-full" disabled={busy} /></label>
        <button type="submit" disabled={busy} className="flex h-9 w-full items-center justify-center gap-2 rounded bg-white font-semibold text-black disabled:cursor-not-allowed disabled:opacity-40"><Download size={14} />{busy ? "Downloading..." : "Download"}</button>
      </form>
    </Modal>
  </MainLayout>;
}
