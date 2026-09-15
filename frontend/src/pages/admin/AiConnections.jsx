import { useCallback, useEffect, useState } from "react";
import { Check, Edit3, Plus, PlugZap, RefreshCcw, Trash2, X } from "lucide-react";
import axiosClient from "../../api/axiosClient";
import DataTable from "../../components/tables/DataTable";
import TableToolbar from "../../components/tables/TableToolbar";
import IconButton from "../../components/common/IconButton";
import Input from "../../components/common/Input";
import Modal from "../../components/common/Modal";
import Select from "../../components/common/Select";
import { useToast } from "../../components/common/ToastProvider";
import { oaCardStyles, oaFormTextStyles } from "../../components/common/uiStyles";

const EMPTY = { name: "", provider: "openai", model: "", api_key: "" };
const COLUMNS = [{ key: "name", label: "Name" }, { key: "provider", label: "Provider" }, { key: "model", label: "Model" }, { key: "connection_status", label: "Status" }, { key: "updated_at", label: "Updated At" }];
function errorMessage(error) {
  const detail = error.response?.data?.detail;
  return typeof detail === "string" ? detail : "Unable to complete the AI action. Check the input fields.";
}
function cellValue(row, key) {
  if (key === "provider") return row.provider === "openai" ? "OpenAI" : "Gemini";
  if (key === "updated_at") return row.updated_at ? new Date(row.updated_at).toLocaleString("en-IN") : "--";
  return String(row[key] || "--");
}

export default function AiConnections({ allowed }) {
  const { showToast } = useToast();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [form, setForm] = useState(null);
  const [editing, setEditing] = useState(null);
  const [models, setModels] = useState([]);
  const [modelsLoading, setModelsLoading] = useState(false);
  const [modelsError, setModelsError] = useState("");
  const provider = form?.provider;
  const apiKey = form?.api_key;
  const editingId = editing?.connection_id;
  const formOpen = Boolean(form);
  useEffect(() => {
    if (!formOpen) return;
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setModels([]); setModelsError("");
      if (!apiKey?.trim() && !editingId) { setModelsLoading(false); return; }
      setModelsLoading(true);
      try {
        const response = await axiosClient.post("/connections/ai/models", { provider, api_key: apiKey?.trim() || null, connection_id: editingId || null }, { signal: controller.signal, timeout: 60000 });
        if (controller.signal.aborted) return;
        setModels(response.data.models);
        setForm((previous) => previous ? { ...previous, model: response.data.models.some((item) => item.value === previous.model) ? previous.model : (response.data.models[0]?.value || "") } : previous);
        if (!response.data.models.length) setModelsError("No models available for this API key.");
      } catch (error) {
        if (!controller.signal.aborted) setModelsError(errorMessage(error));
      } finally { if (!controller.signal.aborted) setModelsLoading(false); }
    }, 500);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [formOpen, provider, apiKey, editingId]);
  const [activeFilter, setActiveFilter] = useState(null);
  const [columnFilters, setColumnFilters] = useState({});
  const [draftColumnFilters, setDraftColumnFilters] = useState({});
  const [sort, setSort] = useState(null);
  const load = useCallback(async () => {
    if (!allowed) { setLoading(false); return; }
    setLoading(true);
    try { setRows((await axiosClient.get("/connections/ai")).data.connections); }
    catch (error) { showToast(errorMessage(error), "error"); }
    finally { setLoading(false); }
  }, [allowed, showToast]);
  useEffect(() => { const timer = window.setTimeout(load, 0); return () => window.clearTimeout(timer); }, [load]);
  const headerValues = Object.fromEntries(COLUMNS.map(({ key }) => [key, [...new Set(rows.map((row) => cellValue(row, key)))].sort()]));
  let filteredRows = rows.filter((row) => COLUMNS.some(({ key }) => cellValue(row, key).toLowerCase().includes(appliedSearch.toLowerCase())) && Object.entries(columnFilters).every(([key, values]) => !values.length || values.includes(cellValue(row, key))));
  if (sort) filteredRows = [...filteredRows].sort((a, b) => cellValue(a, sort.key).localeCompare(cellValue(b, sort.key)) * (sort.direction === "asc" ? 1 : -1));
  async function action(task, success) {
    if (busy || !allowed) return false;
    setBusy(true);
    try { await task(); showToast(success, "success"); await load(); return true; }
    catch (error) { showToast(errorMessage(error), "error"); await load(); return false; }
    finally { setBusy(false); }
  }
  async function save(event) {
    event?.preventDefault();
    if (!form.name.trim() || !models.some((item) => item.value === form.model) || modelsLoading || (!editing && !form.api_key.trim())) { showToast("Enter a connection name and API key, then select an available model.", "warning"); return; }
    const payload = Object.fromEntries(Object.keys(EMPTY).map((key) => [key, form[key]]));
    payload.api_key = form.api_key.trim() || null;
    const saved = await action(() => editing ? axiosClient.put(`/connections/ai/${editing.connection_id}`, payload) : axiosClient.post("/connections/ai", payload), "AI connection saved.");
    if (saved) setForm(null);
  }
  function field(name, label, options = {}) {
    return <label className="block space-y-1" key={name}><span className={oaFormTextStyles.label}>{label}</span><Input name={name} value={form[name]} disabled={busy} onChange={(event) => { if (name === "api_key") { setModels([]); setModelsError(""); } setForm((previous) => ({ ...previous, [name]: event.target.value })); }} {...options} /></label>;
  }
  return <>
    <div className={oaCardStyles.wrapper}>
      <div className={oaCardStyles.header}><h2 className={oaCardStyles.headerTitle}>AI Connections</h2></div>
      <div className="relative z-20 border-b border-oa-border px-3 py-1.5">
        <TableToolbar searchValue={search} onSearchChange={setSearch} onSearchClear={() => { setSearch(""); setAppliedSearch(""); }} onSearchSubmit={(event) => { event.preventDefault(); setAppliedSearch(search.trim()); }} searchPlaceholder="Search AI connections" searchActive={Boolean(appliedSearch)} loading={loading || busy} hasActiveFilter={Object.values(columnFilters).some((values) => values.length)} onClearAll={() => { setColumnFilters({}); setActiveFilter(null); }} rightActions={[
          { icon: RefreshCcw, label: "Refresh AI connections", variant: "refresh", disabled: loading || busy || !allowed, onClick: load },
          { icon: Plus, label: "Add AI connection", variant: "add", disabled: busy || !allowed, onClick: () => { setEditing(null); setModels([]); setModelsError(""); setForm({ ...EMPTY }); } },

        ]} />
      </div>
      <div className="max-h-[50vh] overflow-y-auto [&>div]:border-0">
        <DataTable columns={COLUMNS} rows={filteredRows} loading={loading} loadingMessage="Loading AI connections" loadingPlacement="table" stateMessageMinHeight={64} emptyMessage="No AI connections configured." gridTemplateColumns="180px 120px 220px 100px 180px 120px" getRowKey={(row) => row.connection_id} renderCell={(row, column) => cellValue(row, column.key)} renderActions={(row) => <div className="flex gap-1.5">
          <IconButton icon={Edit3} label="Edit AI connection" disabled={busy || !allowed} onClick={() => { setEditing(row); setModels([]); setModelsError(""); setForm({ ...EMPTY, ...row, api_key: "" }); }} />
          <IconButton icon={PlugZap} label="Test AI connection" disabled={busy || !allowed} onClick={() => action(() => axiosClient.post(`/connections/ai/${row.connection_id}/test`, null, { timeout: 130000 }), "API key and model access verified.")} />
          <IconButton icon={Trash2} label="Delete AI connection" variant="danger" disabled={busy || !allowed} onClick={() => action(() => axiosClient.delete(`/connections/ai/${row.connection_id}`), "AI connection deleted.")} />
        </div>} filterConfig={{ activeFilter, headerValues, columnFilters, draftColumnFilters,
          isColumnFilterActive: (key) => Boolean(columnFilters[key]?.length),
          onOpen: (key) => { setDraftColumnFilters((previous) => ({ ...previous, [key]: columnFilters[key] || [] })); setActiveFilter(key); },
          onClose: () => setActiveFilter(null), onChange: (key, values) => setDraftColumnFilters((previous) => ({ ...previous, [key]: values })),
          onApply: (key) => { setColumnFilters((previous) => ({ ...previous, [key]: draftColumnFilters[key] || [] })); setActiveFilter(null); },
          onClear: (key) => { setColumnFilters((previous) => ({ ...previous, [key]: [] })); setActiveFilter(null); },
          onSort: (key, direction) => { setSort({ key, direction }); setActiveFilter(null); }
        }} />
      </div>
    </div>
    <Modal open={Boolean(form)} title={editing ? "Edit AI Connection" : "Add AI Connection"} onClose={() => !busy && setForm(null)} closeOnOverlay={!busy} width="max-w-xl" footer={<div className="flex gap-2"><IconButton icon={X} label="Cancel" variant="filterCancel" disabled={busy} onClick={() => setForm(null)} /><IconButton icon={Check} label="Save AI connection" variant="filterApply" disabled={busy || !allowed} onClick={save} /></div>}>
      {form && <form onSubmit={save} className="max-h-[65vh] space-y-3 overflow-y-auto oa-table-font">
        {field("name", "Connection name", { required: true, maxLength: 100 })}
        <label className="block space-y-1"><span className={oaFormTextStyles.label}>Provider</span><Select value={form.provider} options={[{ value: "openai", label: "OpenAI" }, { value: "gemini", label: "Google Gemini" }]} onChange={(event) => { setModels([]); setModelsError(""); setForm((previous) => ({ ...previous, provider: event.target.value, model: "" })); }} disabled={busy || Boolean(editing)} minWidth="w-full" ariaLabel="AI provider" /></label>
        {field("api_key", "API key", { type: "password", autoComplete: "new-password", required: !editing, placeholder: editing?.has_api_key ? "Saved - leave empty to keep, or enter a replacement" : "Enter API key" })}
        <div className="space-y-1"><span className={oaFormTextStyles.label}>Available models</span><Select value={form.model} options={models.length ? models : [{ value: "", label: modelsLoading ? "Loading models..." : "Enter API key to load models" }]} onChange={(event) => setForm((previous) => ({ ...previous, model: event.target.value }))} disabled={busy || modelsLoading || !models.length} minWidth="w-full" ariaLabel="Available AI models" /></div>
        {modelsError && <p className="text-xs text-red-400">{modelsError}</p>}
        <button type="submit" className="hidden">Save</button>
      </form>}
    </Modal>
  </>;
}
