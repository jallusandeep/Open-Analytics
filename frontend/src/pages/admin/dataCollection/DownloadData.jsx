import { useState } from "react";
import { Download } from "lucide-react";
import axiosClient from "../../../api/axiosClient";
import Modal from "../../../components/common/Modal";
import Select from "../../../components/common/Select";
import { useToast } from "../../../components/common/ToastProvider";

export default function DownloadData({ activeView, companyFundamentalsEndpoint, ipoCalendarSubTab, getDownloadRows }) {
  const { showToast } = useToast();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [options, setOptions] = useState(null);
  const [format, setFormat] = useState("csv");
  const [dateColumn, setDateColumn] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const dataset = activeView === "ipo_calendar" && ipoCalendarSubTab === "ipo_scraper" ? "ipo_scraper" : activeView;
  async function showDialog() {
    setBusy(true);
    setOptions(null);
    try {
      const response = await axiosClient.get(`/data/export/${dataset}/options`);
      const supportedDates = {
        monitor: [], current_preview: ["expiry", "synced_at"], expired_preview: ["expiry", "synced_at"],
        ohlcv: ["candle_date", "timestamp", "expiry", "ingested_at", "updated_at"],
        equity_news: ["published_at", "ingested_at", "updated_at"],
        ipo_calendar: ["bidding_start_date", "bidding_end_date", "ingested_at", "updated_at"],
        ipo_scraper: ["scraped_at", "updated_at"], company_fundamentals: ["synced_at", "updated_at"],
        market_calendar: ["holiday_date", "synced_at", "updated_at"]
      };
      const dates = response.data.date_columns.filter((column) => supportedDates[dataset]?.includes(column));
      setOptions({ ...response.data, date_columns: dates });
      setDateColumn(dates.includes(response.data.default_date_column) ? response.data.default_date_column : dates[0] || "");
      setStart(""); setEnd("");
      setOpen(true);
    } catch { showToast("Unable to load download options.", "error"); }
    finally { setBusy(false); }
  }
  async function download(event) {
    event.preventDefault();
    setBusy(true);
    try {
      const { headers, rows } = await getDownloadRows({ dateColumn, start, end });
      const response = await axiosClient.post(`/data/export/${dataset}/filtered`,
        { headers, rows }, { responseType: "blob", timeout: 120000, params: { format } });
      const url = URL.createObjectURL(response.data);
      const link = document.createElement("a");
      link.href = url; link.download = `${dataset}.${format}`;
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
      setOpen(false);
    } catch (error) {
      let message = error.response ? "Unable to download data." : error.message || "Unable to download data.";
      try { message = JSON.parse(await error.response.data.text()).detail || message; } catch { /* Use fallback. */ }
      showToast(message, "error");
    } finally { setBusy(false); }
  }
  return <>
    <button type="button" onClick={showDialog} disabled={busy} title="Download data" aria-label="Download data" className="flex h-8 w-8 shrink-0 items-center justify-center rounded border border-oa-border text-oa-muted hover:border-white/50 hover:text-white disabled:opacity-50"><Download size={14} /></button>
    <Modal open={open} title="Download Data" onClose={() => !busy && setOpen(false)} closeOnOverlay={!busy} width="max-w-md">
      <form onSubmit={download} className="oa-app-font space-y-4 text-xs text-white">
        <p className="leading-5 text-oa-muted">Download records matching the current search and selected filters across all pages (up to 100,000 rows).</p>
        <label className="block space-y-2"><span>File format</span><Select value={format} onChange={(event) => setFormat(event.target.value)} options={[{ value: "csv", label: "CSV" }, { value: "xlsx", label: "Excel (.xlsx)" }]} minWidth="w-full" disabled={busy} /></label>
        {options?.date_columns.length > 0 ? <>
          <label className="block space-y-2"><span>Date field</span><Select value={dateColumn} onChange={(event) => setDateColumn(event.target.value)} options={options.date_columns.map((value) => ({ value, label: value.replaceAll("_", " ") }))} minWidth="w-full" disabled={busy} /></label>
          <div className="grid grid-cols-2 gap-3">
            <label className="space-y-2"><span className="block">From (optional)</span><input type="date" value={start} max={end || undefined} disabled={busy} onChange={(event) => setStart(event.target.value)} className="h-9 w-full rounded border border-oa-border bg-black px-2 [color-scheme:dark]" /></label>
            <label className="space-y-2"><span className="block">To (optional)</span><input type="date" value={end} min={start || undefined} disabled={busy} onChange={(event) => setEnd(event.target.value)} className="h-9 w-full rounded border border-oa-border bg-black px-2 [color-scheme:dark]" /></label>
          </div>
        </> : null}
        <button type="submit" disabled={busy} className="flex h-9 w-full items-center justify-center gap-2 rounded bg-white font-semibold text-black disabled:opacity-50"><Download size={14} />{busy ? "Downloading..." : "Download"}</button>
      </form>
    </Modal>
  </>;
}
